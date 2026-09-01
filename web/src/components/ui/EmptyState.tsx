/**
 * EmptyState — never a blank panel: icon, plain-Vietnamese title, one hint,
 * and the next action(s) (NN/g empty-state guidance).
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
      <h2 className="text-lg font-semibold tracking-tight text-ink">{title}</h2>
      {hint != null ? (
        <p className="max-w-md text-[13px] leading-relaxed text-sec">{hint}</p>
      ) : null}
      {action != null ? (
        <div className="mt-1 flex flex-wrap items-center justify-center gap-3">{action}</div>
      ) : null}
    </div>
  );
}
