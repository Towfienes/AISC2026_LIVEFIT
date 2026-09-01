"use client";

/**
 * Replay transport: session picker (ended sessions only), play/pause,
 * speed 1x/4x/16x, and a progress scrubber.
 */

import { fmtDateHCM, fmtElapsed } from "@/lib/format";
import type { SessionSummary } from "@/lib/types";
import type { ReplaySpeed } from "@/lib/useReplay";

import Button from "./ui/Button";
import { fieldCls } from "./ui/field";

const SPEEDS: ReplaySpeed[] = [1, 4, 16];

interface Props {
  sessions: SessionSummary[];
  sessionId: string | null;
  onSelectSession: (id: string) => void;
  t: number;
  durationS: number;
  playing: boolean;
  onTogglePlay: () => void;
  speed: ReplaySpeed;
  onSetSpeed: (s: ReplaySpeed) => void;
  onSeek: (t: number) => void;
  disabled?: boolean;
}

export default function ReplayControls({
  sessions,
  sessionId,
  onSelectSession,
  t,
  durationS,
  playing,
  onTogglePlay,
  speed,
  onSetSpeed,
  onSeek,
  disabled,
}: Props) {
  return (
    <div className="flex h-11 shrink-0 items-center gap-3 rounded-lg border border-hairline bg-surface px-3">
      <select
        value={sessionId ?? ""}
        onChange={(e) => onSelectSession(e.target.value)}
        className={`${fieldCls} max-w-[320px] px-2 py-1 text-xs`}
        aria-label="Chọn phiên đã kết thúc"
      >
        {sessions.map((s) => (
          <option key={s.session_id} value={s.session_id}>
            {s.title ?? s.session_id}
            {s.start_ts ? ` · ${fmtDateHCM(s.start_ts)}` : ""}
          </option>
        ))}
      </select>

      <Button size="sm" onClick={onTogglePlay} disabled={disabled} className="w-24 py-1.5">
        {playing ? "Tạm dừng" : "Phát"}
      </Button>

      <div
        className="flex items-center overflow-hidden rounded-md border border-hairline"
        role="group"
        aria-label="Tốc độ phát lại"
      >
        {SPEEDS.map((s) => (
          <button
            key={s}
            type="button"
            disabled={disabled}
            onClick={() => onSetSpeed(s)}
            aria-pressed={speed === s}
            className={`focus-ring tnum px-2.5 py-1 text-[11px] font-semibold transition-colors duration-150 ${
              speed === s ? "bg-s7 text-page" : "bg-raised text-sec hover:text-ink"
            } disabled:cursor-not-allowed disabled:text-mut`}
          >
            {s}x
          </button>
        ))}
      </div>

      <input
        type="range"
        min={0}
        max={Math.max(1, Math.floor(durationS))}
        step={1}
        value={Math.floor(t)}
        onChange={(e) => onSeek(Number(e.target.value))}
        disabled={disabled}
        className="focus-ring min-w-0 flex-1 accent-[#9085e9]"
        aria-label="Tua đến vị trí"
      />

      <span className="tnum shrink-0 text-xs text-sec">
        <span className="font-semibold text-ink">{fmtElapsed(t)}</span>
        <span className="text-mut"> / {fmtElapsed(durationS)}</span>
      </span>
    </div>
  );
}
