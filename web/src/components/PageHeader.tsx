/**
 * PageHeader — header chuẩn của MỌI trang (spec UX-FLOW d1, gói SKIN).
 *
 * Trả lời tại chỗ ba câu người mới luôn hỏi: trang này thuộc pha nào của buổi
 * live (chip TRƯỚC/TRONG/SAU), trang này là việc gì (H1 font display), và
 * dùng để làm gì / cho ai (câu lead một dòng). Mọi trang dùng CHUNG component
 * này để không trang nào tự chế một kiểu header riêng nữa.
 *
 * `size="sm"` cho màn VẬN HÀNH (desk): một dòng gọn, không chiếm chỗ của số
 * liệu. `size="lg"` (mặc định) cho màn kể chuyện.
 */

import { cx } from "./ui/cx";

export type LivePhase = "truoc" | "trong" | "sau";

const PHASE_LABEL: Record<LivePhase, string> = {
  truoc: "TRƯỚC LIVE",
  trong: "TRONG LIVE",
  sau: "SAU LIVE",
};

const PHASE_CLS: Record<LivePhase, string> = {
  truoc: "border-s7/40 bg-s7/10 text-brand-ink",
  trong: "border-live/40 bg-live/10 text-crit-ink",
  sau: "border-good/30 bg-good/10 text-good-ink",
};

interface Props {
  /** Pha của buổi live — bỏ trống cho trang không thuộc pha nào. */
  phase?: LivePhase;
  title: React.ReactNode;
  /** Một câu: trang này để làm gì — cho ai — khi nào dùng. */
  lead?: React.ReactNode;
  /** Nội dung phụ ngay dưới lead (badge, đoạn giải thích dài hơn…). */
  children?: React.ReactNode;
  /** Hành động căn phải trên cùng hàng với tiêu đề. */
  actions?: React.ReactNode;
  size?: "lg" | "sm";
  className?: string;
}

export default function PageHeader({
  phase,
  title,
  lead,
  children,
  actions,
  size = "lg",
  className,
}: Props) {
  return (
    <header className={cx(size === "lg" ? "mb-6" : "mb-2", className)}>
      {phase ? (
        <span
          className={cx(
            "mb-2 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5",
            "text-meta font-semibold tracking-[0.08em]",
            PHASE_CLS[phase],
          )}
        >
          {PHASE_LABEL[phase]}
        </span>
      ) : null}
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
        <h1
          className={cx(
            "font-display font-bold tracking-tight text-ink",
            size === "lg" ? "text-[34px] leading-tight" : "text-title",
          )}
        >
          {title}
        </h1>
        {actions}
      </div>
      {lead ? (
        <p
          className={cx(
            "max-w-3xl leading-relaxed text-sec",
            size === "lg" ? "mt-2 text-body" : "mt-0.5 text-meta",
          )}
        >
          {lead}
        </p>
      ) : null}
      {children}
    </header>
  );
}
