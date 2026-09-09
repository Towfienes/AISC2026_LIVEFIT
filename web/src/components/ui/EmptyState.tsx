/**
 * EmptyState — never a blank panel: icon, plain-Vietnamese title, one hint,
 * and the next action(s) (NN/g empty-state guidance). Title rides the `title`
 * step (20px) and the hint the `body` step (16px): this is the first screen a
 * new operator reads, so it never uses the metadata size.
 */

import { cx } from "./cx";

interface Props {
  icon?: React.ReactNode;
  title: string;
  hint?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export default function EmptyState({ icon, title, hint, action, className }: Props) {
  return (
    <div
      className={cx(
        "flex flex-col items-center justify-center gap-3 p-6 text-center",
        className,
      )}
    >
      {icon != null ? (
        <div aria-hidden className="text-4xl">
          {icon}
        </div>
      ) : null}
      <h2 className="text-title tracking-tight text-ink">{title}</h2>
      {hint != null ? (
        <p className="max-w-lg text-body leading-relaxed text-sec">{hint}</p>
      ) : null}
      {action != null ? (
        <div className="mt-1 flex flex-wrap items-center justify-center gap-3">{action}</div>
      ) : null}
    </div>
  );
}
