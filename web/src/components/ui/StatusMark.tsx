/**
 * StatusMark — the non-colour channel of a status token (WCAG 1.4.1).
 *
 * A colour-blind operator has to read BẬT / TẮT / trôi without seeing hue, so
 * every status carries a SHAPE as well as a colour and a Vietnamese word:
 *
 *   BẬT  → chấm đặc      (filled disc)
 *   TẮT  → vòng rỗng     (hollow ring)
 *   trôi → nửa đặc       (half-filled disc)
 *
 * The shapes live in globals.css (.status-mark); this component only picks the
 * modifier and the matching AA-safe ink token.
 */

import { cx } from "./cx";

export type StatusShape = "on" | "off" | "drift";

/** Từ tiếng Việt đi kèm mỗi trạng thái — mark không đứng một mình. */
export const STATUS_TEXT: Record<StatusShape, string> = {
  on: "BẬT",
  off: "TẮT",
  drift: "trôi",
};

const INK: Record<StatusShape, string> = {
  on: "text-on-ink",
  off: "text-off-ink",
  drift: "text-drift-ink",
};

interface Props {
  shape: StatusShape;
  /** Kế thừa màu chữ xung quanh thay vì dùng mực trạng thái riêng. */
  inherit?: boolean;
  /**
   * Cạnh của ký hiệu tính bằng px. Bỏ trống = 10px (mặc định trong globals.css,
   * đủ cho chữ cỡ body). Chip trạng thái cỡ hiển thị (num-l) cần một ký hiệu
   * lớn tương ứng, nếu không kênh HÌNH DẠNG sẽ biến mất bên cạnh con chữ 56px.
   * Đặt bằng style vì `.status-mark` khai báo width/height trong globals.css
   * sau `@tailwind utilities` — một class tiện ích sẽ thua nó.
   */
  size?: number;
  /**
   * Nhãn cho trình đọc màn hình. Bỏ trống khi ngay cạnh mark đã có chữ (mặc
   * định) — khi đó mark là trang trí và được ẩn khỏi cây trợ năng.
   */
  label?: string;
  className?: string;
}

export default function StatusMark({ shape, inherit, size, label, className }: Props) {
  return (
    <span
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      style={
        size
          ? { width: size, height: size, borderWidth: Math.max(2, Math.round(size / 6)) }
          : undefined
      }
      className={cx("status-mark", `status-mark--${shape}`, !inherit && INK[shape], className)}
    />
  );
}
