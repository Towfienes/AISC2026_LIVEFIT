"use client";

/**
 * Switchback block timeline — OPERATOR VIEW ONLY (the host screen is blinded
 * and must never render this component). Shows ON/OFF blocks, washout hatch,
 * and the current position marker.
 */

import { fmtElapsed } from "@/lib/format";
import { BLOCK_OFF_COLOR, BLOCK_ON_COLOR } from "@/lib/palette";
import { BlockInfo } from "@/lib/types";

interface Props {
  blocks: BlockInfo[];
  /** Total planned duration in seconds (defines the strip's scale). */
  durationS: number;
  /** Current position in seconds (marker); null hides the marker. */
  positionS: number | null;
}

export default function BlockStrip({ blocks, durationS, positionS }: Props) {
  if (durationS <= 0 || blocks.length === 0) {
    return <div className="h-8 rounded bg-surface" />;
  }
  const pct = (s: number) => `${Math.min(100, Math.max(0, (s / durationS) * 100))}%`;

  return (
    <div>
      <div className="relative h-7 w-full overflow-hidden rounded border border-edge bg-surface">
        {blocks.map((b) => {
          const left = pct(b.start_offset_s);
          const width = pct(b.end_offset_s - b.start_offset_s);
          const isOn = b.assignment === "ON";
          return (
            <div
              key={b.block_index}
              className={`absolute top-0 flex h-full items-center justify-center text-[10px] font-semibold ${
                b.is_washout ? "hatch-washout" : ""
              }`}
              style={{
                left,
                width: `calc(${width} - 2px)`, // 2px surface gap between blocks
                background: b.is_washout
                  ? undefined
                  : isOn
                    ? BLOCK_ON_COLOR
                    : BLOCK_OFF_COLOR,
                color: b.is_washout ? "#898781" : isOn ? "#0d0d0d" : "#c3c2b7",
              }}
              title={`Khối ${b.block_index + 1} · ${
                b.is_washout ? "trôi" : b.assignment === "ON" ? "BẬT" : "TẮT"
              } · ${fmtElapsed(b.start_offset_s)}–${fmtElapsed(b.end_offset_s)}`}
            >
              {b.is_washout ? "" : isOn ? "BẬT" : "TẮT"}
            </div>
          );
        })}
        {positionS != null && (
          <div
            className="absolute top-0 h-full w-0.5 bg-ink"
            style={{ left: pct(positionS) }}
            aria-label="Vị trí hiện tại"
          />
        )}
      </div>
      <div className="mt-1 flex items-center gap-4 px-0.5 text-[10px] text-muted">
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-3 rounded-sm" style={{ background: BLOCK_ON_COLOR }} />
          Khối BẬT (can thiệp)
        </span>
        <span className="flex items-center gap-1">
          <span
            className="inline-block h-2 w-3 rounded-sm border border-edge"
            style={{ background: BLOCK_OFF_COLOR }}
          />
          Khối TẮT (đối chứng)
        </span>
        <span className="flex items-center gap-1">
          <span className="hatch-washout inline-block h-2 w-3 rounded-sm border border-edge" />
          Trôi (washout)
        </span>
        <span className="ml-auto">Chỉ hiển thị cho trung control — màn hình host không thấy khối</span>
      </div>
    </div>
  );
}
