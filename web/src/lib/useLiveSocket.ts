"use client";

/**
 * WebSocket hook for /ws/{sessionId} with automatic reconnect
 * (exponential backoff, capped at 10 s).
 */

import { useEffect, useRef, useState } from "react";
import { wsUrl } from "./api";
import type { WsMessage } from "./types";

export type SocketStatus = "idle" | "connecting" | "open" | "closed";

export function useLiveSocket(
  sessionId: string | null,
  onMessage: (msg: WsMessage) => void,
  enabled = true,
): SocketStatus {
  const [status, setStatus] = useState<SocketStatus>("idle");
  const handlerRef = useRef(onMessage);
  handlerRef.current = onMessage;

  useEffect(() => {
    if (!sessionId || !enabled) {
      setStatus("idle");
      return;
    }
    let ws: WebSocket | null = null;
    let closedByUs = false;
    let attempt = 0;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      setStatus("connecting");
      try {
        ws = new WebSocket(wsUrl(sessionId));
      } catch {
        scheduleRetry();
        return;
      }
      ws.onopen = () => {
        attempt = 0;
        setStatus("open");
      };
      ws.onmessage = (ev) => {
        // A malformed frame or a handler bug must NOT be swallowed silently:
        // that is exactly how the {type,data} envelope mismatch stayed
        // invisible while the desk looked "connected". Log and move on.
        let msg: WsMessage;
        try {
          const parsed: unknown = JSON.parse(ev.data as string);
          if (
            typeof parsed !== "object" ||
            parsed === null ||
            typeof (parsed as { type?: unknown }).type !== "string"
          ) {
            console.warn("[livelift] Khung WebSocket sai hợp đồng {type, data} — bỏ qua:", parsed);
            return;
          }
          msg = parsed as WsMessage;
        } catch (e) {
          console.warn("[livelift] Không đọc được khung WebSocket (JSON hỏng) — bỏ qua:", e);
          return;
        }
        try {
          handlerRef.current(msg);
        } catch (e) {
          console.warn(`[livelift] Lỗi khi xử lý thông điệp WebSocket loại "${msg.type}":`, e);
        }
      };
      ws.onclose = () => {
        if (!closedByUs) scheduleRetry();
      };
      ws.onerror = () => {
        ws?.close();
      };
    };

    const scheduleRetry = () => {
      setStatus("closed");
      attempt += 1;
      const delay = Math.min(1000 * 2 ** Math.min(attempt, 4), 10000);
      retryTimer = setTimeout(connect, delay);
    };

    connect();
    return () => {
      closedByUs = true;
      if (retryTimer) clearTimeout(retryTimer);
      ws?.close();
      setStatus("idle");
    };
  }, [sessionId, enabled]);

  return status;
}
