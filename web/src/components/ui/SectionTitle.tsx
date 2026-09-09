/**
 * SectionTitle — the "eyebrow" zone label. Was 11px (≈10.7 arcmin at 70 cm,
 * a third under the ISO 9241-303 floor); now the `label` step of the scale —
 * 15px / 600 / +0.06em, paired with `uppercase` here so the token itself stays
 * a pure size+weight+tracking triple. Ink is `dim`, the muted tone that still
 * clears 4.5:1 on every plane the desk paints. The optional right-aligned meta
 * slot keeps zone headers on a single baseline (desk zones, replay zones).
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
      <h2 className="text-label uppercase text-dim">{children}</h2>
      {meta != null ? <span className="min-w-0 truncate text-meta text-sec">{meta}</span> : null}
    </div>
  );
}
