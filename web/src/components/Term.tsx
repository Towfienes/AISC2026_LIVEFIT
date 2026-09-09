"use client";

/**
 * Inline term with a plain-language tooltip (hover / keyboard focus / tap).
 *
 * In-context help beats a manual: jargon stays short on screen and the
 * explanation appears exactly where the confusion happens (NN/g in-context
 * learning cues). Pure CSS (group-hover / group-focus-within) — no portal.
 *
 * The span is focusable (tabIndex=0) because the tooltip must open by keyboard
 * too; it therefore carries the shared `.focus-ring` — with plain `outline-none`
 * the focus stop existed but was invisible (WCAG 2.4.7 Focus Visible).
 */

import type { ReactNode } from "react";

interface Props {
  /** Plain-Vietnamese explanation shown in the tooltip. */
  tip: string;
  children: ReactNode;
  /** Where the bubble opens; pick "bottom" inside scroll containers whose top clips. */
  side?: "top" | "bottom";
  /** Dotted underline hint (default true; badges/pills turn it off). */
  underline?: boolean;
  className?: string;
}

export default function Term({ tip, children, side = "top", underline = true, className }: Props) {
  return (
    <span
      tabIndex={0}
      className={`focus-ring group relative inline-flex cursor-help items-center rounded-sm ${className ?? ""}`}
    >
      <span
        className={
          underline ? "underline decoration-mut decoration-dotted underline-offset-2" : undefined
        }
      >
        {children}
      </span>
      <span
        role="tooltip"
        className={`pointer-events-none absolute left-1/2 z-50 hidden w-72 -translate-x-1/2 rounded border border-hairline bg-raised px-3 py-2 text-left text-meta font-normal normal-case leading-snug tracking-normal text-sec shadow-lg group-focus-within:block group-hover:block ${
          side === "top" ? "bottom-full mb-1.5" : "top-full mt-1.5"
        }`}
      >
        {tip}
      </span>
    </span>
  );
}
