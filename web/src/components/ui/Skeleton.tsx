/**
 * Skeleton — pulse placeholder (shadcn/ui pattern). Shape comes entirely from
 * the caller's className; respects prefers-reduced-motion via globals.css.
 */

import { cx } from "./cx";

export default function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cx("animate-pulse rounded-md bg-raised", className)} />;
}
