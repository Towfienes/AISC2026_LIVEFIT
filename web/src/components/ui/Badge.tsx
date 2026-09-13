/**
 * Badge — small status pill. The two source tones encode the E2-04 rule and
 * must keep their exact semantics:
 * - "neutral" → forecast-sourced numbers ("Ước lượng dự báo", gray, no CI ever)
 * - "good"    → experiment-sourced numbers ("Tác động đo được · KTC 95%", green)
 *
 * Type: `meta` (13px) — the floor of the scale. Ink: the AA-safe *-ink tokens,
 * so a badge clears 4.5:1 on the tinted surface it sits on.
 */

import { cx } from "./cx";
import StatusMark, { type StatusShape } from "./StatusMark";

export type BadgeTone = "neutral" | "good" | "warn" | "violet" | "critical";

const TONE: Record<BadgeTone, string> = {
  neutral: "border-hairline bg-axis text-off-ink",
  good: "border-good/40 bg-good/10 text-good-ink",
  warn: "border-warn/60 bg-warn/10 text-warn-ink",
  violet: "border-s7/50 bg-s7/15 text-on-ink",
  critical: "border-critical/50 bg-critical/10 text-crit-ink",
};

const DOT: Record<BadgeTone, string> = {
  neutral: "bg-mut",
  good: "bg-good",
  warn: "bg-warn",
  violet: "bg-s7",
  critical: "bg-critical",
};

interface Props {
  tone?: BadgeTone;
  /** Leading status dot (identity never by color alone — text always present). */
  dot?: boolean;
  /**
   * Trạng thái BẬT/TẮT/trôi: vẽ ký hiệu hình dạng (chấm đặc / vòng rỗng /
   * nửa đặc) thay cho chấm tròn, để phân biệt được khi không thấy màu.
   */
  mark?: StatusShape;
  className?: string;
  children: React.ReactNode;
}

export default function Badge({
  tone = "neutral",
  dot = false,
  mark,
  className,
  children,
}: Props) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-meta font-semibold",
        TONE[tone],
        className,
      )}
    >
      {mark ? <StatusMark shape={mark} inherit /> : null}
      {!mark && dot ? (
        <span aria-hidden className={cx("inline-block h-2 w-2 rounded-full", DOT[tone])} />
      ) : null}
      {children}
    </span>
  );
}
