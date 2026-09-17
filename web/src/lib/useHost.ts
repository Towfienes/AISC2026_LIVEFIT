"use client";

/**
 * BLINDED data hook for the host screen (rule L6).
 *
 * Everything this hook returns is a HostState: pinned product name, price,
 * stock, and total elapsed time — plus TRANSPORT/labelling flags (connection,
 * degraded, sessionNotFound, offAir, concurrentLive, sampleData) that say
 * nothing about blocks or arms. It never exposes blocks, assignments, or
 * anything that could reveal the ON/OFF schedule to the host.
 *
 * BUG ĐỒNG HỒ 328:36:29 (đã sửa, gói DESK-HOST): hook từng chọn
 * `list.find(s => s.status === "live")` — phiên live ĐẦU TIÊN theo thứ tự
 * tạo. Kho bền còn giữ các phiên mô phỏng cũ chưa bao giờ được kết thúc
 * (status vẫn "live", start_ts 29/08), và máy chủ tính elapsed = now − start_ts
 * một cách trung thực → màn host hiển thị ~328 giờ. Nay chọn phiên live LÊN
 * SÓNG GẦN NHẤT khi phải chọn mới (`pickHostSession`).
 *
 * BUG KHOÁ NHẦM PHIÊN (đã sửa, gói D): hook từng chọn phiên MỘT LẦN lúc tải.
 * Checklist bước 4 dặn "mở màn người dẫn TRƯỚC rồi mới bấm Bắt đầu phát sóng"
 * — làm đúng lời dặn là màn bị khoá vào một phiên khác đang có trong kho.
 *
 * KIỂM TOÁN 17/09 — ba lỗi đã sửa ở hook này:
 *   1. `/host` trơn CƯỚP MÀN: gói D chọn lại "phiên live mới nhất" ở MỖI lần
 *      poll, nên bấm "Xem thử ngay" (`/demo/seed` để lại một phiên mẫu live)
 *      hay một khách tự bắt đầu phiên là màn của buổi thật đang phát nhảy sang
 *      hàng mẫu tới hết buổi. Nay `pickHostSession`: phiên thật live thì bỏ
 *      phiên mẫu; phiên đang chiếu còn live thì GIỮ NGUYÊN; từ 2 phiên cùng
 *      loại cùng live thì báo (`concurrentLive`) thay vì tự đổi.
 *   2. `?session=<phiên đã kết thúc>` vẫn in "Sản phẩm đang ghim — giới thiệu
 *      ngay" với hàng ghim cuối của buổi cũ. Nay phiên trong link không live
 *      thì KHÔNG đọc hàng ghim: màn trống kèm lý do (`offAir`), và vẫn poll
 *      tiếp — phiên chưa lên sóng tự hiện hàng khi bấm phát sóng.
 *   3. ĐƯỜNG MẠNG RIÊNG (sự cố 27/08 là rò rỉ ở TẦNG MẠNG): hook từng import
 *      `./api` và `./mock`, nên JS tĩnh tải về máy người dẫn chứa danh sách
 *      khoá cấm (`assignment`, `design_hash`…) và cả bộ sinh lịch khối mô
 *      phỏng. Nay hook KHÔNG import hai module đó: tự gọi đúng hai đường đọc
 *      (`/sessions`, `/sessions/{id}/state?role=host`), chiếu payload qua một
 *      DANH SÁCH CHO PHÉP bốn trường, và có bản mô phỏng riêng chỉ sinh
 *      HostState. `tests/test_web_replay_host.py` khoá cả đồ thị import.
 * Trạng thái live/kết thúc của PHIÊN không phải nhánh BẬT/TẮT của KHỐI.
 */

import { useEffect, useRef, useState } from "react";
import { pickHostSession } from "./pickSession";
import type { ConnectionKind, HostState, SessionSummary } from "./types";

const MOCK_FORCED = process.env.NEXT_PUBLIC_MOCK === "1";

/** Cùng biểu thức với `API_BASE` của api.ts (test khoá hai chỗ luôn khớp). */
const HOST_API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

/** Số lần poll hỏng liên tiếp trước khi báo "mất kết nối" (2 s một lần). */
const DEGRADED_AFTER_FAILS = 3;

/** Nhịp poll máy chủ (ms). Bản mô phỏng tự tính nên cập nhật mỗi giây. */
const POLL_MS = 2000;
const MOCK_POLL_MS = 1000;

/** GET một đường ĐỌC của máy chủ, hỏng nhanh khi máy chủ không trả lời. */
async function hostGet<T>(path: string, timeoutMs: number): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(`${HOST_API_BASE}${path}`, { signal: ctrl.signal, cache: "no-store" });
    if (!res.ok) throw new Error(`API ${res.status} — ${path}`);
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Bốn trường DUY NHẤT màn người dẫn đọc từ `/state?role=host` — đúng
 * `HostState` phía máy chủ (`extra="forbid"`). Danh sách CHO PHÉP thay cho
 * danh sách cấm: không phải liệt kê (và gửi xuống máy người dẫn) tên các
 * trường khối để loại chúng.
 */
const HOST_PAYLOAD_KEYS: readonly string[] = ["pinned_product", "price", "stock", "elapsed_s"];

function finiteOrNull(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

/** Chiếu payload máy chủ xuống HostState — trường ngoài danh sách bị bỏ qua. */
export function toHostState(raw: Record<string, unknown>): HostState {
  const extra = Object.keys(raw).filter((k) => !HOST_PAYLOAD_KEYS.includes(k));
  if (extra.length > 0) {
    // Chỉ in SỐ trường lạ, không in tên: tên trường cũng là thông tin.
    console.warn(
      `[livelift] payload màn người dẫn có ${extra.length} trường ngoài danh sách cho phép — đã bỏ qua.`,
    );
  }
  const product = raw.pinned_product;
  const obj =
    product != null && typeof product === "object" ? (product as Record<string, unknown>) : null;
  const name =
    typeof product === "string" ? product : typeof obj?.name === "string" ? obj.name : null;
  return {
    product_name: name,
    price: finiteOrNull(raw.price) ?? finiteOrNull(obj?.price),
    stock: finiteOrNull(raw.stock) ?? finiteOrNull(obj?.stock),
    elapsed_s: finiteOrNull(raw.elapsed_s) ?? 0,
  };
}

async function readHostState(sessionId: string): Promise<HostState> {
  const raw = await hostGet<Record<string, unknown>>(
    `/sessions/${encodeURIComponent(sessionId)}/state?role=host`,
    3500,
  );
  return toHostState(raw);
}

/**
 * Bản mô phỏng CỦA RIÊNG màn người dẫn (khi không có máy chủ): chỉ sinh
 * HostState, không có lịch khối. Khớp nhịp với bản ghi "mock-live-01" mà bàn
 * trợ live chạy (mock.ts: phiên 90 phút, đổi hàng ghim mỗi 240 s qua
 * MOCK_PRODUCTS, đồng hồ demo bắt đầu ở 40% và chạy 6x theo giờ máy) — hai tab
 * mở cạnh nhau vẫn thấy cùng một món. Test đối chiếu danh sách với mock.ts.
 */
const MOCK_HOST_PRODUCTS: readonly { name: string; price: number; stock: number }[] = [
  { name: "Váy hoa nhí vintage", price: 259000, stock: 42 },
  { name: "Áo thun cotton oversize", price: 129000, stock: 120 },
  { name: "Quần jean ống rộng", price: 319000, stock: 65 },
  { name: "Áo khoác gió unisex", price: 349000, stock: 30 },
  { name: "Chân váy tennis xếp ly", price: 179000, stock: 80 },
  { name: "Sơ mi lụa công sở", price: 289000, stock: 55 },
];
const MOCK_HOST_DURATION_S = 90 * 60;
const MOCK_HOST_PIN_EVERY_S = 240;

export function mockHostState(nowMs: number): HostState {
  const base = Math.min(2100, Math.floor(MOCK_HOST_DURATION_S * 0.4));
  const span = Math.max(60, MOCK_HOST_DURATION_S - base);
  const el = base + (((nowMs / 1000) * 6) % span);
  const p =
    MOCK_HOST_PRODUCTS[Math.floor(el / MOCK_HOST_PIN_EVERY_S) % MOCK_HOST_PRODUCTS.length];
  return { product_name: p.name, price: p.price, stock: p.stock, elapsed_s: el };
}

/**
 * Phiên trong `?session=` không đang phát: chưa lên sóng, đã phát xong, hay đã
 * huỷ. `cancelled` tách khỏi `ended` vì nó là phiên ĐÓNG MÀ CHƯA TỪNG LÊN SÓNG
 * (schemas.SessionStatus, migration 0008) — gọi nó là "đã kết thúc" là khai
 * sai một buổi phát không hề diễn ra.
 */
export type HostOffAir = "not_started" | "ended" | "cancelled" | null;

export function offAirOf(status: SessionSummary["status"]): HostOffAir {
  if (status === "live") return null;
  if (status === "ended") return "ended";
  if (status === "cancelled") return "cancelled";
  return "not_started";
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
   * Phiên trong link chưa lên sóng / đã kết thúc: màn KHÔNG chiếu hàng ghim
   * (người dẫn có thể giới thiệu nhầm hàng của buổi đã xong). Trạng thái PHIÊN,
   * không phải khối.
   */
  offAir: HostOffAir;
  /**
   * `/host` trơn: số phiên cùng loại đang live khi có từ 2 trở lên (0 = không
   * mơ hồ). Màn giữ phiên đang chiếu và nhắc mở lại bằng link có mã phiên.
   */
  concurrentLive: number;
  /**
   * Phiên đang chiếu là DỮ LIỆU MẪU (`SessionSummary.is_demo`, hoặc bản mô
   * phỏng khi không có máy chủ). Nhãn bắt buộc của dự án — không phải nhánh.
   */
  sampleData: boolean;
}

/**
 * @param requestedSessionId mã phiên từ `?session=` của URL — có thì chỉ
 *   chiếu đúng phiên đó; không có thì chọn theo `pickHostSession`.
 */
export function useHost(requestedSessionId?: string | null): HostFeed {
  const requested = requestedSessionId?.trim() ? requestedSessionId.trim() : null;
  const [connection, setConnection] = useState<ConnectionKind>(
    MOCK_FORCED ? "mock" : "connecting",
  );
  const [host, setHost] = useState<HostState | null>(null);
  const [degraded, setDegraded] = useState(false);
  const [sessionNotFound, setSessionNotFound] = useState(false);
  const [offAir, setOffAir] = useState<HostOffAir>(null);
  const [concurrentLive, setConcurrentLive] = useState(0);
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
    /** Màn này đã từng chiếu một phiên THẬT → không bao giờ lùi về phiên mẫu. */
    let shownReal = false;
    let lastServerElapsed: number | null = null;

    failStreak.current = 0;
    clockRunning.current = false;
    setHost(null);
    setDegraded(false);
    setSessionNotFound(false);
    setOffAir(null);
    setConcurrentLive(0);
    setSampleData(MOCK_FORCED);
    setConnection(MOCK_FORCED ? "mock" : "connecting");

    const fail = () => {
      failStreak.current += 1;
      if (failStreak.current >= DEGRADED_AFTER_FAILS) setDegraded(true);
    };

    /** Một lần đọc thành công: `sessionId` null = không có hàng nào để chiếu. */
    const show = (sessionId: string | null, h: HostState | null, isDemo?: boolean) => {
      if (sessionId !== shownSessionId) {
        shownSessionId = sessionId;
        lastServerElapsed = null;
      }
      if (h != null && isDemo === false) shownReal = true;
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
        list = await hostGet<SessionSummary[]>("/sessions", 2500);
      } catch {
        list = null;
      }
      if (cancelled) return;

      // 1) Link có ?session=<id>: ưu tiên tuyệt đối, không bao giờ đổi phiên.
      if (requested) {
        if (!list) {
          // Không đọc được danh sách thì không biết phiên còn live không —
          // giữ nguyên màn, không đoán.
          fail();
          return;
        }
        const row = list.find((s) => s.session_id === requested) ?? null;
        if (!row) {
          setSessionNotFound(true);
          setOffAir(null);
          show(null, null, false);
          return;
        }
        setSessionNotFound(false);
        const off = offAirOf(row.status);
        if (off) {
          // Phiên chưa/không còn phát: KHÔNG đọc hàng ghim. Poll tiếp — phiên
          // chưa lên sóng tự hiện hàng ngay khi bấm "Bắt đầu phát sóng".
          setOffAir(off);
          show(null, null, row.is_demo);
          return;
        }
        try {
          const h = await readHostState(requested);
          if (cancelled) return;
          setOffAir(null);
          show(requested, h, row.is_demo);
        } catch {
          if (!cancelled) fail();
        }
        return;
      }

      // 2) Không có tham số: giữ phiên đang chiếu, chỉ chọn lại khi cần.
      if (!list) {
        if (!everConnected) {
          // Chưa từng nối được máy chủ: giữ hành vi cũ — bản mô phỏng CÓ NHÃN.
          mock = true;
          clockRunning.current = false;
          setSampleData(true);
          setConnection("mock");
          setHost(mockHostState(Date.now()));
          return;
        }
        fail();
        return;
      }
      const picked = pickHostSession(list, shownSessionId, !shownReal);
      setConcurrentLive(picked.liveCount >= 2 ? picked.liveCount : 0);
      if (!picked.session) {
        show(null, null, false);
        return;
      }
      const chosen = picked.session;
      try {
        const h = await readHostState(chosen.session_id);
        if (cancelled) return;
        show(chosen.session_id, h, chosen.is_demo);
      } catch {
        if (!cancelled) fail();
      }
    };

    const loop = async () => {
      if (cancelled) return;
      if (mock) setHost(mockHostState(Date.now()));
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

  return { host, connection, degraded, sessionNotFound, offAir, concurrentLive, sampleData };
}
