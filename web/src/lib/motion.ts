"use client";

/**
 * Chuyển động của bàn điều khiển — phần chạy bằng JavaScript (gói UI-3).
 *
 * ---------------------------------------------------------------------------
 * Nguyên tắc
 * ---------------------------------------------------------------------------
 * Đây là màn hình VẬN HÀNH, không phải trang giới thiệu. Người ta nhìn nó 90
 * phút liền trong lúc phải nhìn cả luồng phát trực tiếp. Vì thế mọi chuyển
 * động phải TRẢ LỜI một sự kiện vừa xảy ra, và phải kết thúc:
 *
 *   ĐƯỢC   nháy nền 520ms khi một con số vừa đổi (xác nhận "máy có nhận");
 *          count-up 350ms cho KPI nhảy bậc (giữ được liên hệ giá trị cũ → mới);
 *          crossfade 280ms khi khối chuyển BẬT ↔ TẮT.
 *   KHÔNG  bất cứ thứ gì lặp vô hạn (`animate-pulse` chạy suốt phiên là nhiễu
 *          nền: mắt vẫn bắt chuyển động nhưng não đã bỏ qua nội dung của nó);
 *          animate đồng hồ/đếm ngược (số nhảy mỗi giây mà có transition thì
 *          không bao giờ đứng yên đủ lâu để đọc).
 *
 * Toàn bộ file này tôn trọng `prefers-reduced-motion: reduce`: khi người dùng
 * bật, mọi tween trả về giá trị đích ngay lập tức (CSS thì đã được rút gọn
 * trong globals.css).
 */

import { useEffect, useMemo, useRef, useState } from "react";

export const MOTION = {
  /** Count-up của KPI — trùng token M3 medium3 (--dur-medium3). */
  tweenMs: 350,
  /**
   * NGƯỠNG ĐÁNG TWEEN. Dưới 5% thay đổi thì gán thẳng: một tween 350ms cho
   * "1.204 → 1.207" chỉ làm con số rung, không thêm một chút thông tin nào.
   */
  tweenThreshold: 0.05,
  /** Nháy xác nhận: 120ms sáng + 400ms tắt dần (khớp --dur-flash-*). */
  flashMs: 520,
  /** Dòng bình luận mới trượt vào (khớp --dur-enter). */
  enterMs: 180,
  /** Bậc so le giữa các dòng mới… */
  staggerMs: 60,
  /** …và TRẦN 3 bậc: so le 10 dòng thì dòng cuối vào sau nửa giây. */
  staggerMax: 3,
} as const;

/**
 * `true` khi hệ điều hành báo người dùng muốn giảm chuyển động.
 *
 * Trả về `false` ở lần render đầu (server-side không có `matchMedia`) rồi tự
 * sửa trong effect — an toàn vì mọi hiệu ứng ở đây đều bắt đầu từ một THAY ĐỔI
 * giá trị, không phải từ lần gắn đầu tiên.
 */
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setReduced(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);
  return reduced;
}

/** Số chữ số của phần nguyên — đổi số chữ số là đổi cả hình dạng con số. */
function digitCount(n: number): number {
  return Math.abs(Math.round(n)).toString().length;
}

/** Ease-out mũ ba: nhanh ngay lập tức rồi hãm dần — đọc được ngay từ frame đầu. */
function easeOutCubic(p: number): number {
  return 1 - Math.pow(1 - p, 3);
}

/**
 * Đưa một KPI về giá trị mới bằng tween 350ms ease-out, viết bằng
 * `requestAnimationFrame` (không thêm thư viện nào).
 *
 * Tween CHỈ chạy khi thay đổi đủ lớn để mắt cần một cầu nối:
 *   - lệch ≥ 5% so với giá trị cũ, HOẶC
 *   - số chữ số đổi (999 → 1.000 là một sự kiện, dù chỉ hơn nhau 1).
 * Ngoài hai trường hợp đó — và luôn luôn, khi người dùng chọn giảm chuyển động
 * — giá trị được gán thẳng.
 *
 * `null` (chưa có số liệu) đi thẳng qua, không tween từ/về 0: đếm từ 0 lên là
 * bịa ra một quá trình chưa từng xảy ra.
 */
export function useCountUp(target: number | null): number | null {
  const reduced = usePrefersReducedMotion();
  const [shown, setShown] = useState<number | null>(target);
  /** Giá trị đang hiện trên màn — điểm xuất phát khi một tween cắt ngang tween cũ. */
  const shownRef = useRef<number | null>(target);
  /** Đích của lần trước — mốc để so ngưỡng 5% (không dùng giá trị đang chạy). */
  const lastTarget = useRef<number | null>(target);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const commit = (v: number | null) => {
      shownRef.current = v;
      setShown(v);
    };
    const from = shownRef.current;
    const previous = lastTarget.current;
    lastTarget.current = target;

    if (target == null || from == null || previous == null || reduced) {
      commit(target);
      return;
    }
    const delta = Math.abs(target - previous);
    const worthTweening =
      delta / Math.max(Math.abs(previous), 1) >= MOTION.tweenThreshold ||
      digitCount(target) !== digitCount(previous);
    if (delta === 0 || !worthTweening) {
      commit(target);
      return;
    }

    const t0 = typeof performance !== "undefined" ? performance.now() : Date.now();
    const step = (now: number) => {
      const p = Math.min(1, (now - t0) / MOTION.tweenMs);
      commit(from + (target - from) * easeOutCubic(p));
      rafRef.current = p < 1 ? requestAnimationFrame(step) : null;
    };
    rafRef.current = requestAnimationFrame(step);
    return () => {
      if (rafRef.current != null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, [target, reduced]);

  return shown;
}

/**
 * Bộ đếm "giá trị đã đổi bao nhiêu lần". Dùng làm `key` cho lớp nháy xác nhận:
 * key đổi ⇒ React gắn lại phần tử ⇒ keyframes chạy lại từ đầu.
 *
 * Trả về 0 ở lần gắn đầu tiên, nên màn hình vừa mở KHÔNG nháy một loạt — nháy
 * lúc đó chẳng xác nhận điều gì cả.
 */
export function useChangeKey(value: unknown): number {
  const previous = useRef(value);
  const [key, setKey] = useState(0);
  useEffect(() => {
    if (Object.is(previous.current, value)) return;
    previous.current = value;
    setKey((k) => k + 1);
  }, [value]);
  return key;
}

/**
 * Câu thông báo cho trình đọc màn hình, CHỈ đổi khi `key` đổi.
 *
 * Vùng `aria-live="polite"` gắn với nó vì thế chỉ phát mỗi lần chuyển khối một
 * câu, thay vì đọc lại mỗi giây theo đồng hồ đếm ngược — đọc liên tục thì
 * người dùng trình đọc màn hình sẽ tắt hẳn vùng đó và mất luôn cả thông báo
 * quan trọng.
 */
export function useAnnounceOnChange(key: string, message: string): string {
  const seen = useRef<string | null>(null);
  const [text, setText] = useState("");
  useEffect(() => {
    if (seen.current === key) return;
    const first = seen.current === null;
    seen.current = key;
    setText(first ? "" : message);
  }, [key, message]);
  return text;
}

/**
 * Đánh dấu những phần tử vừa xuất hiện trong danh sách, kèm bậc so le.
 *
 * Trả về `Map<id, bậc>` với bậc trong [0, `staggerMax`): phần tử mới thứ tư
 * trở đi dùng lại bậc cuối, nên một loạt 20 bình luận vào cùng lúc vẫn xong
 * trong ~300ms chứ không xếp hàng hơn một giây.
 *
 * Danh sách "đã thấy" được cập nhật trong effect (không phải trong lúc render),
 * nên React StrictMode render đôi vẫn cho cùng một kết quả.
 */
export function useEnterStagger<T>(
  items: readonly T[],
  keyOf: (item: T) => string,
): ReadonlyMap<string, number> {
  // `keyOf` thường là arrow function viết tại chỗ (đổi mỗi lần render); giữ nó
  // trong ref để `items` là phụ thuộc DUY NHẤT — nếu không, effect chạy mọi
  // lần render và đánh dấu "đã thấy" trước khi kịp vẽ hiệu ứng.
  const keyRef = useRef(keyOf);
  keyRef.current = keyOf;
  const seen = useRef<Set<string> | null>(null);
  const stagger = useMemo(() => {
    const known = seen.current;
    const map = new Map<string, number>();
    // Lần đầu: cả danh sách là "cũ" — mở màn hình không phải là một sự kiện.
    if (known == null) return map;
    let i = 0;
    for (const item of items) {
      const id = keyRef.current(item);
      if (known.has(id)) continue;
      map.set(id, Math.min(i, MOTION.staggerMax - 1));
      i += 1;
    }
    return map;
  }, [items]);
  useEffect(() => {
    seen.current = new Set(items.map((item) => keyRef.current(item)));
  }, [items]);
  return stagger;
}
