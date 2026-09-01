/**
 * SectionTitle — Linear-style "eyebrow" label: 11px, semibold, positive
 * letter-spacing, muted ink. Optional right-aligned meta slot keeps zone
 * headers on a single baseline (desk zones, replay zones).
 */

import { cx } from "./cx";

interface Props {
  children: React.ReactNode;
  /** Right-aligned secondary info on the same baseline. */
  meta?: React.ReactNode;
  className?: string;
}

export default function SectionTitle({ children, meta, className }: Props) {
  return (
    <div className={cx("mb-2 flex shrink-0 items-baseline justify-between gap-3", className)}>
      <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-mut">
        {children}
      </h2>
      {meta != null ? <span className="min-w-0 truncate text-[11px] text-sec">{meta}</span> : null}
    </div>
  );
}
