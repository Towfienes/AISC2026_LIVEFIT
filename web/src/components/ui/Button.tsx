/**
 * Button — three calm variants with the shadcn/ui focus-visible ring
 * convention (visible ring only on keyboard focus, offset from the surface)
 * and explicit disabled states. `buttonCls()` is exported so <Link> and
 * <label> elements can share the exact same look.
 */

import { cx } from "./cx";

export type ButtonVariant = "primary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md";

const BASE =
  "focus-ring inline-flex shrink-0 select-none items-center justify-center gap-1.5 " +
  "rounded-md font-semibold transition-colors duration-150 disabled:cursor-not-allowed";

const VARIANT: Record<ButtonVariant, string> = {
  primary:
    "bg-s1 text-page hover:bg-[#5099ea] disabled:bg-raised disabled:text-mut",
  ghost:
    "border border-hairline bg-transparent text-sec hover:border-white/20 hover:bg-raised hover:text-ink " +
    "disabled:border-hairline disabled:bg-transparent disabled:text-mut",
  danger:
    "border border-critical/50 bg-transparent text-critical hover:bg-critical/10 " +
    "disabled:border-hairline disabled:text-mut",
};

const SIZE: Record<ButtonSize, string> = {
  sm: "px-2.5 py-1 text-[11px]",
  md: "px-4 py-2 text-sm",
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
