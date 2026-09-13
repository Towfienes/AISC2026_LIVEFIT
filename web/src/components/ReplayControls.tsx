"use client";

/**
 * Replay transport: session picker (ended sessions only), play/pause,
 * speed 1x/4x/16x, and a progress scrubber.
 *
 * Every control clears the WCAG 2.2 SC 2.5.8 24px target floor: play is a full
 * `md` button, the speed segments carry `min-h-tap`/`min-w-tap`, and — being
 * inside an `overflow-hidden` group — they take the inset focus ring so the
 * keyboard ring is not clipped away.
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
    <div className="flex h-bar shrink-0 items-center gap-3 rounded-lg border border-hairline bg-surface px-3">
      <select
        value={sessionId ?? ""}
        onChange={(e) => onSelectSession(e.target.value)}
        className={`${fieldCls} max-w-[320px] px-2 py-1 text-meta`}
        aria-label="Chọn phiên đã kết thúc"
      >
        {sessions.map((s) => (
          <option key={s.session_id} value={s.session_id}>
            {s.title ?? s.session_id}
            {s.start_ts ? ` · ${fmtDateHCM(s.start_ts)}` : ""}
          </option>
        ))}
      </select>

      <Button onClick={onTogglePlay} disabled={disabled} className="w-28">
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
            className={`focus-ring focus-ring-inset tnum min-h-tap min-w-tap px-3 py-1 text-meta font-semibold transition-colors duration-short2 ease-emphasized ${
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
        className="focus-ring min-h-tap min-w-0 flex-1 cursor-pointer accent-[#8b7bff]"
        aria-label="Tua đến vị trí"
      />

      <span className="tnum flex shrink-0 items-baseline gap-1 text-meta text-dim">
        <span className="text-strong text-ink">{fmtElapsed(t)}</span>
        <span>/ {fmtElapsed(durationS)}</span>
      </span>
    </div>
  );
}
