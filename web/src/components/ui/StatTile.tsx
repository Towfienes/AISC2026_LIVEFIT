/**
 * StatTile — Tremor-style KPI tile: `label` eyebrow, a DISPLAY figure on the
 * num-* steps (tabular by construction), and a `meta` hint line.
 * `size="lg"` is the hero variant used for the primary experiment result on
 * /ket-qua.
 *
 * Sizes: md → num-s (28px), lg → num-m (40px). Both are display figures, well
 * clear of the ISO 9241-303 band, so a judge reads the number across the room.
 */

import Card from "./Card";
import { cx } from "./cx";

type Tone = "ink" | "good" | "warn" | "critical";

/** Value inks — the AA-safe status tokens, never the fill tones. */
const TONE: Record<Tone, string> = {
  ink: "text-ink",
  good: "text-good-ink",
  warn: "text-warn-ink",
  critical: "text-crit-ink",
};

interface Props {
  label: React.ReactNode;
  value: React.ReactNode;
  hint?: React.ReactNode;
  tone?: Tone;
  size?: "md" | "lg";
  className?: string;
}

export default function StatTile({
  label,
  value,
  hint,
  tone = "ink",
  size = "md",
  className,
}: Props) {
  return (
    <Card padding={size === "lg" ? "lg" : "md"} className={className}>
      <div className="text-label uppercase text-dim">{label}</div>
      <div
        className={cx(
          "mt-1.5 tracking-tight",
          size === "lg" ? "text-num-m" : "text-num-s",
          TONE[tone],
        )}
      >
        {value}
      </div>
      {hint != null ? <div className="mt-2 text-meta leading-snug text-sec">{hint}</div> : null}
    </Card>
  );
}
