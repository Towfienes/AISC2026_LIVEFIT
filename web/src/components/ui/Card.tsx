/**
 * Card — the one surface primitive every panel uses.
 *
 * Pattern source: shadcn/ui Card (hairline ring, uniform padding var) and
 * Linear's surface layering — depth comes from bg-surface on bg-page plus a
 * hairline border, never a drop shadow.
 */

import { cx } from "./cx";

type Padding = "none" | "sm" | "md" | "lg";

const PAD: Record<Padding, string> = {
  none: "",
  sm: "p-3",
  md: "p-4",
  lg: "p-5",
};

interface CardProps extends React.HTMLAttributes<HTMLElement> {
  as?: "div" | "section" | "article" | "header";
  padding?: Padding;
  /** Adds the calm Linear-style hover affordance (border lightens). */
  interactive?: boolean;
}

export default function Card({
  as: Tag = "div",
  padding = "md",
  interactive = false,
  className,
  children,
  ...rest
}: CardProps) {
  return (
    <Tag
      className={cx(
        "rounded-lg border border-hairline bg-surface",
        PAD[padding],
        interactive && "transition-colors duration-150 hover:border-white/20",
        className,
      )}
      {...rest}
    >
      {children}
    </Tag>
  );
}
