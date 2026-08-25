"use client";

/**
 * Zone 2 action card ("Hành động gợi ý").
 *
 * E2-04 display rule (hard project rule):
 * - source="forecast"   → gray badge "Ước lượng dự báo". NEVER render any
 *   interval, even if ci fields somehow arrive populated (api.sanitizeCard
 *   already strips them; this component guards again).
 * - source="experiment" → green badge "Tác động đo được · KTC 95%" and the
 *   [ci_low, ci_high] interval.
 *
 * Mode behavior:
 * - "auto"    → execute/skip disabled, note "Tự động thực thi" (+ countdown).
 * - "suggest" → active "Thực hiện" and "Bỏ qua" buttons.
 */

import { fmtPct } from "@/lib/format";
import type { ActionCardData, SessionMode } from "@/lib/types";

interface Props {
  card: ActionCardData;
  mode: SessionMode;
  executed?: boolean;
  /** Replay view: no buttons at all (actions happened in the past). */
  readOnly?: boolean;
  onExecute?: () => void;
  onSkip?: () => void;
}

function SourceBadge({ card }: { card: ActionCardData }) {
  if (card.source === "experiment") {
    return (
      <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-[#0ca30c66] bg-[#0ca30c1f] px-2 py-0.5 text-[10px] font-semibold text-[#4ed44e]">
        <span aria-hidden className="inline-block h-1.5 w-1.5 rounded-full bg-[#0ca30c]" />
        Tác động đo được · KTC 95%
      </span>
    );
  }
  return (
    <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-hairline bg-axis px-2 py-0.5 text-[10px] font-semibold text-sec">
      Ước lượng dự báo
    </span>
  );
}

export default function ActionCard({ card, mode, executed, readOnly, onExecute, onSkip }: Props) {
  // E2-04: an interval may only ever be shown for experiment-sourced cards.
  const showCi = card.source === "experiment" && card.ci_low != null && card.ci_high != null;

  return (
    <article
      className={`flex min-h-0 flex-col gap-1.5 rounded-lg border border-hairline bg-surface p-3 ${
        executed ? "opacity-60" : ""
      }`}
      aria-label={`Gợi ý hạng ${card.rank}: ${card.headline}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-baseline gap-2">
          <span className="tnum shrink-0 rounded bg-raised px-1.5 py-0.5 text-[11px] font-bold text-sec">
            #{card.rank}
          </span>
          <h3 className="truncate text-sm font-semibold text-ink">{card.headline}</h3>
        </div>
        <SourceBadge card={card} />
      </div>

      <p className="line-clamp-2 text-xs leading-snug text-sec">{card.rationale}</p>

      <div className="mt-auto flex items-center justify-between gap-2 pt-1">
        <div className="tnum text-xs text-mut">
          {card.estimate != null && (
            <span className="font-semibold text-ink">{fmtPct(card.estimate)}</span>
          )}
          {showCi && (
            <span className="ml-1.5 text-sec">
              KTC 95% [{fmtPct(card.ci_low as number)}, {fmtPct(card.ci_high as number)}]
            </span>
          )}
          {card.estimate == null && !showCi && <span>—</span>}
        </div>

        {readOnly ? (
          <span className="text-[10px] text-mut">Bản ghi phát lại</span>
        ) : executed ? (
          <span className="rounded px-2 py-1 text-[11px] font-semibold text-[#4ed44e]">
            Đã thực hiện
          </span>
        ) : mode === "auto" ? (
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-mut">
              Tự động thực thi
              {card.auto_execute_in_s != null && (
                <span className="tnum"> · {Math.max(0, Math.round(card.auto_execute_in_s))}s</span>
              )}
            </span>
            <button
              type="button"
              disabled
              className="cursor-not-allowed rounded border border-hairline bg-raised px-2.5 py-1 text-[11px] font-semibold text-mut"
            >
              Thực hiện
            </button>
            <button
              type="button"
              disabled
              className="cursor-not-allowed rounded border border-hairline px-2.5 py-1 text-[11px] text-mut"
            >
              Bỏ qua
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onExecute}
              className="rounded bg-s1 px-2.5 py-1 text-[11px] font-semibold text-ink transition-colors hover:bg-[#5099ea]"
            >
              Thực hiện
            </button>
            <button
              type="button"
              onClick={onSkip}
              className="rounded border border-hairline px-2.5 py-1 text-[11px] text-sec transition-colors hover:bg-raised"
            >
              Bỏ qua
            </button>
          </div>
        )}
      </div>
    </article>
  );
}
