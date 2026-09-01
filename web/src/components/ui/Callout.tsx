/**
 * Callout — slim inline banner for warnings/errors (the desk degraded state,
 * the schedule balance warning, API errors). Amber/red text on a tinted
 * hairline surface; `role` conveys urgency to screen readers.
 */

import { cx } from "./cx";

type Tone = "warn" | "critical";

const TONE: Record<Tone, { box: string; icon: string }> = {
  warn: { box: "border-warn/40 bg-warn/10", icon: "text-warn" },
  critical: { box: "border-critical/40 bg-critical/10", icon: "text-critical" },
};

interface Props {
  tone?: Tone;
  /** Compact single-line banner (desk toolbar) vs. comfortable callout. */
  slim?: boolean;
  className?: string;
  children: React.ReactNode;
}

export default function Callout({ tone = "warn", slim = false, className, children }: Props) {
  return (
    <div
      role={tone === "critical" ? "alert" : "status"}
      className={cx(
        "flex items-start gap-2 rounded-md border",
        slim ? "px-3 py-1.5 text-[11px]" : "px-3 py-2.5 text-xs",
        TONE[tone].box,
        className,
      )}
    >
      <span aria-hidden className={cx("mt-px shrink-0 font-bold", TONE[tone].icon)}>
        {tone === "critical" ? "✕" : "⚠"}
      </span>
      <div className="min-w-0 leading-snug text-sec [&_strong]:text-ink">{children}</div>
    </div>
  );
}
