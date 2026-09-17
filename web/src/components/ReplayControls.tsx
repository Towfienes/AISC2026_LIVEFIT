"use client";

/**
 * Replay transport: session picker (ended sessions only), play/pause,
 * speed 1x/4x/16x/30x/60x, and a progress scrubber.
 *
 * Every control clears the WCAG 2.2 SC 2.5.8 24px target floor: play is a full
 * `md` button, the speed segments carry `min-h-tap`/`min-w-tap`, and — being
 * inside an `overflow-hidden` group — they take the inset focus ring so the
 * keyboard ring is not clipped away.
 *
 * Gói D: thanh này từng là một hàng `h-bar` cố định — ở màn hẹp năm nút tốc
 * độ + ô chọn phiên + thanh tua bị bóp chồng lên nhau. Nay hàng WRAP được
 * (thanh tua xuống dòng riêng trên điện thoại). Nút Phát mang cả HÌNH (▶ / ❚❚)
 * lẫn CHỮ; dòng chọn phiên dán nhãn "dữ liệu mẫu" cho phiên demo và không in
 * mã UUID thô khi phiên chưa đặt tên.
 */

import { fmtDateHCM, fmtElapsed } from "@/lib/format";
import type { SessionSummary } from "@/lib/types";
import type { ReplaySpeed } from "@/lib/useReplay";

import Button from "./ui/Button";
import { fieldCls } from "./ui/field";

const SPEEDS: ReplaySpeed[] = [1, 4, 16, 30, 60];

/** Nhãn một dòng trong ô chọn phiên — tên, ngày, và nhãn dữ liệu mẫu. */
function sessionLabel(s: SessionSummary): string {
  const name = s.title ?? `Phiên chưa đặt tên · ${s.session_id.slice(0, 8)}`;
  const day = s.start_ts ? ` · ${fmtDateHCM(s.start_ts)}` : "";
  return `${name}${day}${s.is_demo ? " · dữ liệu mẫu" : ""}`;
}

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
    <div className="flex min-h-bar shrink-0 flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-hairline bg-surface px-3 py-1.5">
      <select
        value={sessionId ?? ""}
        onChange={(e) => onSelectSession(e.target.value)}
        className={`${fieldCls} w-full min-w-0 px-2 py-1 text-meta sm:w-auto sm:max-w-[320px]`}
        aria-label="Chọn phiên đã kết thúc"
      >
        {sessions.map((s) => (
          <option key={s.session_id} value={s.session_id}>
            {sessionLabel(s)}
          </option>
        ))}
      </select>

      <Button onClick={onTogglePlay} disabled={disabled} className="min-w-[7.5rem]">
        <span aria-hidden>{playing ? "❚❚" : "▶"}</span>
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
            className={`focus-ring focus-ring-inset tnum min-h-tap min-w-tap px-2.5 py-1 text-meta font-semibold transition-colors duration-short2 ease-emphasized sm:px-3 ${
              speed === s ? "bg-s7 text-page" : "bg-raised text-sec hover:text-ink"
            } disabled:cursor-not-allowed disabled:text-mut`}
          >
            {s}x
          </button>
        ))}
      </div>

      <div className="flex min-w-0 basis-full items-center gap-3 sm:flex-1 sm:basis-48">
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
    </div>
  );
}
