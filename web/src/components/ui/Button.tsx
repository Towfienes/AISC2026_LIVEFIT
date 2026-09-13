/**
 * Button — three calm variants with the shadcn/ui focus-visible ring
 * convention (visible ring only on keyboard focus, offset from the surface)
 * and explicit disabled states. `buttonCls()` is exported so <Link> and
 * <label> elements can share the exact same look.
 *
 * Target size: `sm` used to render ~22.6 px tall, under the 24x24 CSS px floor
 * of WCAG 2.2 SC 2.5.8 (Target Size Minimum). Both sizes now pin a minimum:
 *   sm → min-h-tap (24px) — dense toolbars only
 *   md → min-h-ctl (36px) — the DEFAULT, and the required size for a primary
 *        action on the desk, where the operator clicks while watching a stream.
 */

import { cx } from "./cx";

export type ButtonVariant = "primary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md";

const BASE =
  "focus-ring inline-flex shrink-0 select-none items-center justify-center gap-1.5 " +
  "rounded-md font-semibold transition-colors duration-short2 ease-emphasized " +
  "disabled:cursor-not-allowed";

const VARIANT: Record<ButtonVariant, string> = {
  // v2 (gói SKIN): CTA chính chuyển từ xanh Bootstrap-mặc-định sang MỘT accent
  // brand tím điện thống nhất toàn app; chữ #0c0d12 trên #7c6cff = 5.03:1 AA.
  primary:
    "bg-brand text-[#0c0d12] hover:bg-brand-hi disabled:bg-raised disabled:text-mut",
  ghost:
    "border border-strong bg-transparent text-sec hover:border-white/20 hover:bg-raised hover:text-ink " +
    "disabled:border-hairline disabled:bg-transparent disabled:text-mut",
  danger:
    "border border-critical/50 bg-transparent text-crit-ink hover:bg-critical/10 " +
    "disabled:border-hairline disabled:text-mut",
};

const SIZE: Record<ButtonSize, string> = {
  sm: "min-h-tap min-w-tap px-3 py-1 text-meta",
  md: "min-h-ctl px-4 py-2 text-body",
};

export function buttonCls(variant: ButtonVariant = "primary", size: ButtonSize = "md"): string {
  return cx(BASE, VARIANT[variant], SIZE[size]);
}

interface Props extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export default function Button({
  variant = "primary",
  size = "md",
  type = "button",
  className,
  ...rest
}: Props) {
  return <button type={type} className={cx(buttonCls(variant, size), className)} {...rest} />;
}
