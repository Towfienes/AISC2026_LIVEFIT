"use client";

/**
 * Desk toolbar: one compact row — session picker, live/mock status, vitals
 * (viewers, clock), and the mode toggle. Shows the "DEMO DATA" badge whenever
 * the hook reports mock mode.
 */

import { fmtClock, fmtNumber } from "@/lib/format";
import type { ConnectionKind, SessionMode, SessionSummary } from "@/lib/types";
import type { SocketStatus } from "@/lib/useLiveSocket";

import Badge from "./ui/Badge";
import Button from "./ui/Button";
import { fieldCls } from "./ui/field";

export function DemoBadge() {
  return (
    <Badge tone="warn" className="tracking-wider">
      DEMO DATA
    </Badge>
  );
}

export function ConnectionBadge({
  connection,
  wsStatus,
}: {
  connection: ConnectionKind;
  wsStatus?: SocketStatus;
}) {
  if (connection === "mock") return <DemoBadge />;
  if (connection === "connecting") {
    return <span className="text-[11px] text-mut">Đang kết nối…</span>;
  }
  const wsOpen = wsStatus === "open";
  return (
    <span className="flex items-center gap-1.5 text-[11px] text-sec">
      <span
        aria-hidden
        className={`inline-block h-2 w-2 rounded-full ${wsOpen ? "bg-good motion-safe:animate-pulse" : "bg-warn"}`}
      />
      {wsOpen ? "TRỰC TIẾP" : "TRỰC TIẾP (đang nối lại WS)"}
    </span>
  );
}

interface Props {
  connection: ConnectionKind;
  wsStatus?: SocketStatus;
  sessions: SessionSummary[];
  sessionId: string | null;
  onSelectSession: (id: string) => void;
  elapsedS: number;
  durationS: number;
  viewers: number;
  mode: SessionMode;
  onSetMode?: (m: SessionMode) => void;
  canToggleMode?: boolean;
  /** Shown only when the selected session is live on a real API. */
  onEndSession?: () => void;
  canEndSession?: boolean;
  endBusy?: boolean;
}

export default function StatusBar({
  connection,
  wsStatus,
  sessions,
  sessionId,
  onSelectSession,
  elapsedS,
  durationS,
  viewers,
  mode,
  onSetMode,
  canToggleMode,
  onEndSession,
  canEndSession,
  endBusy,
}: Props) {
  return (
    <header className="flex h-11 shrink-0 items-center gap-3 rounded-lg border border-hairline bg-surface px-3">
      <span className="shrink-0 text-xs font-semibold text-sec">Phiên đang xem</span>

      <select
        value={sessionId ?? ""}
        onChange={(e) => onSelectSession(e.target.value)}
        className={`${fieldCls} max-w-[340px] px-2 py-1 text-xs`}
        aria-label="Chọn phiên"
      >
        {sessions.map((s) => (
          <option key={s.session_id} value={s.session_id}>
            {s.title ?? s.session_id} · {s.platform} ·{" "}
            {s.status === "live" ? "đang live" : s.status === "ended" ? "đã kết thúc" : s.status}
          </option>
        ))}
      </select>

      <ConnectionBadge connection={connection} wsStatus={wsStatus} />

      <div className="ml-auto flex items-center gap-4 text-xs text-sec">
        <span>
          Người xem: <span className="tnum font-semibold text-ink">{fmtNumber(viewers)}</span>
        </span>
        <span className="tnum">
          <span className="font-semibold text-ink">{fmtClock(elapsedS)}</span>
          <span className="text-mut"> / {fmtClock(durationS)}</span>
        </span>

        {/* mode toggle — segmented control */}
        <div
          className="flex items-center overflow-hidden rounded-md border border-hairline"
          role="group"
          aria-label="Chế độ vận hành"
        >
          {(["suggest", "auto"] as const).map((m) => (
            <button
              key={m}
              type="button"
              disabled={!canToggleMode}
              onClick={() => onSetMode?.(m)}
              aria-pressed={mode === m}
              className={`focus-ring px-2.5 py-1 text-[11px] font-semibold transition-colors duration-150 ${
                mode === m ? "bg-s7 text-page" : "bg-raised text-sec"
              } ${canToggleMode ? "hover:text-ink" : "cursor-default"} ${
                mode === m && canToggleMode ? "hover:text-page" : ""
              }`}
              title={
                canToggleMode
                  ? m === "suggest"
                    ? "Hệ thống chỉ đề xuất — bạn bấm Thực hiện mới ghim"
                    : "Hệ thống tự ghim theo gợi ý sau khi đếm ngược"
                  : "Chế độ do máy chủ quyết định khi kết nối trực tiếp"
              }
            >
              {m === "suggest" ? "Gợi ý" : "Tự động"}
            </button>
          ))}
        </div>

        {canEndSession && onEndSession ? (
          <Button
            variant="danger"
            size="sm"
            onClick={onEndSession}
            disabled={endBusy}
            title="Kết thúc phiên đang phát — dữ liệu đã ghi được giữ nguyên"
          >
            {endBusy ? "Đang kết thúc…" : "Kết thúc phiên"}
          </Button>
        ) : null}
      </div>
    </header>
  );
}
