"use client";

/**
 * Flash — lớp phủ "giá trị vừa đổi" (gói UI-3).
 *
 * Một con số đổi lặng lẽ trên bàn điều khiển là một con số bị bỏ lỡ: người vận
 * hành đang nhìn luồng phát, chỉ liếc màn hình. Lớp này sáng nền lên trong
 * 120ms rồi tắt dần trong 400ms — đủ để đuôi mắt bắt được, không đủ để thành
 * nhiễu nền.
 *
 * Bốn ràng buộc, tất cả đều nằm trong thiết kế của nó:
 *   1. chỉ đổi NỀN, alpha trần 12% (--flash-alpha) — chữ vẫn đọc được suốt;
 *   2. `position: absolute` ⇒ không chiếm chỗ, không đẩy được một pixel bố cục;
 *   3. `aria-hidden` ⇒ trình đọc màn hình không thấy gì (giá trị mới đã nằm
 *      trong chính phần tử bên cạnh);
 *   4. lần gắn đầu tiên KHÔNG nháy (`useChangeKey` trả 0) — mở màn hình lên mà
 *      cả bàn nháy một loạt thì không xác nhận điều gì cả.
 *
 * Phần tử cha phải có `position: relative`.
 */

import { useChangeKey } from "@/lib/motion";

import { cx } from "./cx";

interface Props {
  /** Giá trị được theo dõi: đổi (theo `Object.is`) là nháy một lần. */
  value: unknown;
  /** Hộp của lớp phủ. Mặc định phủ đúng phần tử cha. */
  className?: string;
}

export default function Flash({ value, className }: Props) {
  const key = useChangeKey(value);
  if (key === 0) return null;
  return (
    <span
      key={key}
      aria-hidden
      className={cx("motion-flash pointer-events-none absolute rounded-md", className ?? "inset-0")}
    />
  );
}
