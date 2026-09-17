"use client";

/**
 * BLINDED data hook for the host screen (rule L6).
 *
 * Everything this hook returns is a HostState: pinned product name, price,
 * stock, and total elapsed time — plus three TRANSPORT/labelling flags
 * (connection, degraded, sessionNotFound, sampleData) that say nothing about
 * blocks or arms. It never exposes blocks, assignments, or anything that could
 * reveal the ON/OFF schedule to the host.
 *
 * BUG ĐỒNG HỒ 328:36:29 (đã sửa, gói DESK-HOST): hook từng chọn
 * `list.find(s => s.status === "live")` — phiên live ĐẦU TIÊN theo thứ tự
 * tạo. Kho bền còn giữ các phiên mô phỏng cũ chưa bao giờ được kết thúc
 * (status vẫn "live", start_ts 29/08), và máy chủ tính elapsed = now − start_ts
 * một cách trung thực → màn host hiển thị ~328 giờ. Nay dùng
 * `pickCurrentSession` (phiên live LÊN SÓNG GẦN NHẤT); pickSession chỉ đọc
 * SessionSummary nên không đụng ranh giới làm mù.
 *
 * BUG KHOÁ NHẦM PHIÊN (đã sửa, gói D): hook từng chọn phiên MỘT LẦN lúc tải.
 * Checklist bước 4 dặn "mở màn người dẫn TRƯỚC rồi mới bấm Bắt đầu phát sóng"
 * — làm đúng lời dặn là màn bị khoá vào một phiên khác đang có trong kho, và
 * sau khi phiên mới lên sóng + ghim hàng, người dẫn vẫn thấy "Chưa ghim sản
 * phẩm". Nay:
 *   - `?session=<id>` trong link được ƯU TIÊN TUYỆT ĐỐI: chỉ chiếu đúng phiên
 *     đó; máy chủ không có phiên ấy thì nói thẳng (`sessionNotFound`), KHÔNG
 *     lặng lẽ chiếu phiên khác;
 *   - không có tham số: MỖI LẦN POLL chọn lại phiên đang live mới nhất, nên
 *     màn mở trước giờ lên sóng tự bắt được phiên vừa bấm phát. Chưa có phiên
 *     nào live thì màn trống ("Chưa ghim sản phẩm") thay vì chiếu hàng đang
 *     ghim của một buổi đã kết thúc — người dẫn có thể giới thiệu nhầm.
 * Trạng thái live/kết thúc của PHIÊN không phải nhánh BẬT/TẮT của KHỐI — hook
 * chỉ dùng nó để chọn phiên, không trả nó ra ngoài.
 */

import { useEffect, useRef, useState } from "react";
import { getHostState, listSessions } from "./api";
import { MOCK_SESSIONS, mockElapsedS, mockRecording } from "./mock";
import { pickCurrentSession } from "./pickSession";
import type { ConnectionKind, HostState, SessionSummary } from "./types";

const MOCK_FORCED = process.env.NEXT_PUBLIC_MOCK === "1";

/** Số lần poll hỏng liên tiếp trước khi báo "mất kết nối" (2 s một lần). */
const DEGRADED_AFTER_FAILS = 3;

/** Nhịp poll máy chủ (ms). Bản mô phỏng tự tính nên cập nhật mỗi giây. */
const POLL_MS = 2000;
const MOCK_POLL_MS = 1000;

/** Project a mock recording down to the blinded HostState at the demo clock. */
function mockHostState(sessionId: string): HostState {
  const rec = mockRecording(sessionId);
  const el = mockElapsedS(rec.duration_s);
  const visible = rec.ticks.filter((t) => t.offset_s <= el);
  const last = visible[visible.length - 1];
  const product = rec.products.find((p) => p.product_id === last?.pinned_product_id) ?? null;
  return {
    product_name: product?.name ?? null,
    price: product?.price ?? null,
    stock: product?.stock ?? null,
    elapsed_s: el,
  };
}

export interface HostFeed {
  host: HostState | null;
  connection: ConnectionKind;
  /**
   * `true` khi vài lần poll liên tiếp hỏng: màn host hiện "Mất kết nối — cứ
   * tiếp tục nói chuyện" thay vì để người dẫn hoảng vì màn đứng im. Đây là
   * trạng thái ĐƯỜNG TRUYỀN, không phải dữ liệu thí nghiệm — không đụng L6.
   */
  degraded: boolean;
  /** Link mang `?session=<id>` nhưng máy chủ không có phiên đó. */
  sessionNotFound: boolean;
  /**
   * Phiên đang chiếu là DỮ LIỆU MẪU (`SessionSummary.is_demo`, hoặc bản mô
   * phỏng khi không có máy chủ). Nhãn bắt buộc của dự án — không phải nhánh.
   */
  sampleData: boolean;
}

/**
 * @param requestedSessionId mã phiên từ `?session=` của URL — có thì chỉ
 *   chiếu đúng phiên đó; không có thì mỗi lần poll chọn lại phiên đang live.
 */
export function useHost(requestedSessionId?: string | null): HostFeed {
  const requested = requestedSessionId?.trim() ? requestedSessionId.trim() : null;
  const [connection, setConnection] = useState<ConnectionKind>(
    MOCK_FORCED ? "mock" : "connecting",
  );
  const [host, setHost] = useState<HostState | null>(null);
  const [degraded, setDegraded] = useState(false);
  const [sessionNotFound, setSessionNotFound] = useState(false);
  const [sampleData, setSampleData] = useState(MOCK_FORCED);
  const failStreak = useRef(0);
  /** Đồng hồ 1 giây giữa hai lần poll chỉ chạy khi máy chủ thấy nó ĐANG chạy. */
  const clockRunning = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let mock = MOCK_FORCED;
    let everConnected = false;
    let shownSessionId: string | null = null;
    let lastServerElapsed: number | null = null;

    failStreak.current = 0;
    clockRunning.current = false;
    setHost(null);
    setDegraded(false);
    setSessionNotFound(false);
    setSampleData(MOCK_FORCED);
    setConnection(MOCK_FORCED ? "mock" : "connecting");

    const fail = () => {
      failStreak.current += 1;
      if (failStreak.current >= DEGRADED_AFTER_FAILS) setDegraded(true);
    };

    /** Một lần đọc thành công: `sessionId` null = không có phiên nào để chiếu. */
    const show = (sessionId: string | null, h: HostState | null, isDemo?: boolean) => {
      if (sessionId !== shownSessionId) {
        shownSessionId = sessionId;
        lastServerElapsed = null;
      }
      // Phiên đã kết thúc/chưa phát có elapsed đứng yên — đồng hồ cục bộ không
      // được tự nhích rồi giật lùi mỗi lần poll.
      clockRunning.current =
        h != null && lastServerElapsed != null && h.elapsed_s > lastServerElapsed;
      lastServerElapsed = h ? h.elapsed_s : null;
      setHost(h);
      if (isDemo !== undefined) setSampleData(isDemo);
      failStreak.current = 0;
      setDegraded(false);
      everConnected = true;
      setConnection("live");
    };

    const pull = async () => {
      let list: SessionSummary[] | null = null;
      try {
        list = await listSessions(2500);
      } catch {
        list = null;
      }
      if (cancelled) return;

      // 1) Link có ?session=<id>: ưu tiên tuyệt đối, không bao giờ đổi phiên.
      if (requested) {
        const row = list?.find((s) => s.session_id === requested) ?? null;
        if (list && !row) {
          setSessionNotFound(true);
          show(null, null, false);
          return;
        }
        try {
          const h = await getHostState(requested);
          if (cancelled) return;
          setSessionNotFound(false);
          show(requested, h, row ? row.is_demo : undefined);
        } catch {
          if (!cancelled) fail();
        }
        return;
      }

      // 2) Không có tham số: chọn lại phiên đang live MỖI LẦN POLL.
      if (!list) {
        if (!everConnected) {
          // Chưa từng nối được máy chủ: giữ hành vi cũ — bản mô phỏng CÓ NHÃN.
          mock = true;
          clockRunning.current = false;
          setSampleData(true);
          setConnection("mock");
          setHost(mockHostState(MOCK_SESSIONS[0].session_id));
          return;
        }
        fail();
        return;
      }
      const picked = pickCurrentSession(list.filter((s) => s.status === "live"));
      if (!picked) {
        show(null, null, false);
        return;
      }
      try {
        const h = await getHostState(picked.session_id);
        if (cancelled) return;
        show(picked.session_id, h, picked.is_demo);
      } catch {
        if (!cancelled) fail();
      }
    };

    const loop = async () => {
      if (cancelled) return;
      if (mock) setHost(mockHostState(MOCK_SESSIONS[0].session_id));
      else await pull();
      // setTimeout nối đuôi (không setInterval): máy chủ chậm thì hai lần
      // poll không bao giờ chồng lên nhau và trả kết quả lộn thứ tự.
      if (!cancelled) timer = setTimeout(loop, mock ? MOCK_POLL_MS : POLL_MS);
    };
    void loop();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [requested]);

  // Smooth 1 s clock between live polls.
  useEffect(() => {
    if (connection !== "live") return;
    const timer = setInterval(() => {
      if (!clockRunning.current) return;
      setHost((h) => (h ? { ...h, elapsed_s: h.elapsed_s + 1 } : h));
    }, 1000);
    return () => clearInterval(timer);
  }, [connection]);

  return { host, connection, degraded, sessionNotFound, sampleData };
}
