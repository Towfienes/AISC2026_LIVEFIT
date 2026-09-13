"use client";

/**
 * BLINDED data hook for the host screen (rule L6).
 *
 * Everything this hook returns is a HostState: pinned product name, price,
 * stock, and total elapsed time. It never exposes blocks, assignments, or
 * anything that could reveal the ON/OFF schedule to the host.
 *
 * BUG ĐỒNG HỒ 328:36:29 (đã sửa, gói DESK-HOST): hook từng chọn
 * `list.find(s => s.status === "live")` — phiên live ĐẦU TIÊN theo thứ tự
 * tạo. Kho bền còn giữ các phiên mô phỏng cũ chưa bao giờ được kết thúc
 * (status vẫn "live", start_ts 29/08), và máy chủ tính elapsed = now − start_ts
 * một cách trung thực → màn host hiển thị ~328 giờ. Nay dùng
 * `pickCurrentSession` (phiên live LÊN SÓNG GẦN NHẤT); pickSession chỉ đọc
 * SessionSummary nên không đụng ranh giới làm mù.
 */

import { useEffect, useRef, useState } from "react";
import { getHostState, listSessions } from "./api";
import { MOCK_SESSIONS, mockElapsedS, mockRecording } from "./mock";
import { pickCurrentSession } from "./pickSession";
import type { ConnectionKind, HostState } from "./types";

const MOCK_FORCED = process.env.NEXT_PUBLIC_MOCK === "1";

/** Số lần poll hỏng liên tiếp trước khi báo "mất kết nối" (2 s một lần). */
const DEGRADED_AFTER_FAILS = 3;

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

export function useHost(): {
  host: HostState | null;
  connection: ConnectionKind;
  /**
   * `true` khi vài lần poll liên tiếp hỏng: màn host hiện "Mất kết nối — cứ
   * tiếp tục nói chuyện" thay vì để người dẫn hoảng vì màn đứng im. Đây là
   * trạng thái ĐƯỜNG TRUYỀN, không phải dữ liệu thí nghiệm — không đụng L6.
   */
  degraded: boolean;
} {
  const [connection, setConnection] = useState<ConnectionKind>(
    MOCK_FORCED ? "mock" : "connecting",
  );
  const [sessionId, setSessionId] = useState<string | null>(
    MOCK_FORCED ? MOCK_SESSIONS[0].session_id : null,
  );
  const [host, setHost] = useState<HostState | null>(null);
  const [degraded, setDegraded] = useState(false);
  const failStreak = useRef(0);

  useEffect(() => {
    if (MOCK_FORCED) return;
    let cancelled = false;
    listSessions(2500)
      .then((list) => {
        if (cancelled) return;
        const picked = pickCurrentSession(list);
        setSessionId(picked ? picked.session_id : null);
        setConnection("live");
      })
      .catch(() => {
        if (cancelled) return;
        setSessionId(MOCK_SESSIONS[0].session_id);
        setConnection("mock");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!sessionId || connection === "connecting") return;
    let cancelled = false;
    const pull = async () => {
      if (connection === "mock") {
        setHost(mockHostState(sessionId));
        return;
      }
      try {
        const h = await getHostState(sessionId);
        if (cancelled) return;
        setHost(h);
        failStreak.current = 0;
        setDegraded(false);
      } catch {
        // keep last known state; the clock keeps running locally
        if (cancelled) return;
        failStreak.current += 1;
        if (failStreak.current >= DEGRADED_AFTER_FAILS) setDegraded(true);
      }
    };
    pull();
    const timer = setInterval(pull, connection === "mock" ? 1000 : 2000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [sessionId, connection]);

  // Smooth 1 s clock between live polls.
  useEffect(() => {
    if (connection !== "live") return;
    const timer = setInterval(
      () => setHost((h) => (h ? { ...h, elapsed_s: h.elapsed_s + 1 } : h)),
      1000,
    );
    return () => clearInterval(timer);
  }, [connection]);

  return { host, connection, degraded };
}
