/**
 * StatTile — Tremor-style KPI tile: muted uppercase label, large semibold
 * tabular value, small hint line. `size="lg"` is the hero variant used for
 * the primary experiment result on /ket-qua.
 */

import Card from "./Card";
import { cx } from "./cx";

type Tone = "ink" | "good" | "warn" | "critical";

const TONE: Record<Tone, string> = {
  ink: "text-ink",
  good: "text-good",
  warn: "text-warn",
  critical: "text-critical",
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
      <div className="text-[11px] font-medium uppercase tracking-wide text-mut">{label}</div>
      <div
        className={cx(
          "mt-1 font-semibold tabular-nums tracking-tight",
          size === "lg" ? "text-4xl" : "text-2xl",
          TONE[tone],
        )}
      >
        {value}
      </div>
      {hint != null ? (
        <div className="mt-1.5 text-[11px] leading-snug text-sec">{hint}</div>
      ) : null}
    </Card>
  );
}
