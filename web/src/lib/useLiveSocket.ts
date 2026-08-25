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
        try {
          const msg = JSON.parse(ev.data as string) as WsMessage;
          handlerRef.current(msg);
        } catch {
          // ignore malformed frames
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
