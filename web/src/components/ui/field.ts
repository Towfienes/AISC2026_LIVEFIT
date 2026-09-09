/**
 * Shared input/select look — hairline border on the raised plane, accent
 * border on focus, keyboard focus ring (shadcn/ui convention).
 *
 * `min-h-ctl` (36px) puts every field on the same control height as a primary
 * `md` button, comfortably over the WCAG 2.2 SC 2.5.8 24px floor. Callers pick
 * the type step (`text-meta` in dense toolbars, `text-body` in forms).
 */
export const fieldCls =
  "focus-ring min-h-ctl rounded-md border border-hairline bg-raised text-ink outline-none " +
  "transition-colors duration-short2 ease-emphasized placeholder:text-mut focus:border-s1/60 " +
  "disabled:cursor-not-allowed disabled:text-mut";
