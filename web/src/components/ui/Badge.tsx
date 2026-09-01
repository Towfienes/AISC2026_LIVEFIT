/**
 * Badge — small status pill. The two source tones encode the E2-04 rule and
 * must keep their exact semantics:
 * - "neutral" → forecast-sourced numbers ("Ước lượng dự báo", gray, no CI ever)
 * - "good"    → experiment-sourced numbers ("Tác động đo được · KTC 95%", green)
 */

import { cx } from "./cx";

export type BadgeTone = "neutral" | "good" | "warn" | "violet" | "critical";

const TONE: Record<BadgeTone, string> = {
  neutral: "border-hairline bg-axis text-sec",
  good: "border-[#0ca30c66] bg-[#0ca30c1f] text-[#4ed44e]",
  warn: "border-warn/60 bg-warn/10 text-warn",
  violet: "border-s7/50 bg-s7/15 text-s7",
  critical: "border-critical/50 bg-critical/10 text-critical",
};

const DOT: Record<BadgeTone, string> = {
  neutral: "bg-mut",
  good: "bg-[#0ca30c]",
  warn: "bg-warn",
  violet: "bg-s7",
  critical: "bg-critical",
};

interface Props {
  tone?: BadgeTone;
  /** Leading status dot (identity never by color alone — text always present). */
  dot?: boolean;
  className?: string;
  children: React.ReactNode;
}

export default function Badge({ tone = "neutral", dot = false, className, children }: Props) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold",
        TONE[tone],
        className,
      )}
    >
      {dot ? (
        <span aria-hidden className={cx("inline-block h-1.5 w-1.5 rounded-full", DOT[tone])} />
      ) : null}
      {children}
    </span>
  );
}
