"use client";

/**
 * error.tsx — ranh giới lỗi cấp route (Next.js App Router).
 *
 * VÌ SAO CÓ TỆP NÀY: trước ngày 14/09/2026 thư mục `app/` KHÔNG có error.tsx,
 * global-error.tsx hay not-found.tsx. Một lỗi render bất kỳ sẽ rơi xuống màn
 * hình mặc định của Next — bản dev in NGUYÊN vết ngăn xếp (đường dẫn tệp, tên
 * hàm nội bộ), bản prod in một trang tiếng Anh trống trơn. Cả hai đều là thứ
 * KHÔNG được phép hiện ra trước hội đồng chấm, và vết ngăn xếp còn là rò rỉ
 * thông tin (trọng tâm 8 của thể lệ).
 *
 * NGUYÊN TẮC: người dùng thấy một câu tiếng Việt nói rõ việc cần làm; thông tin
 * gỡ lỗi chỉ còn `digest` — mã băm do Next sinh, tra được trong log máy chủ mà
 * không tiết lộ gì về mã nguồn.
 */

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Ghi ra console trình duyệt để người phát triển còn lần được; KHÔNG hiển
    // thị nội dung này trên giao diện.
    console.error("[LiveLift] lỗi giao diện:", error);
  }, [error]);

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6 py-16">
      <p className="text-label uppercase tracking-wide text-mut">LiveLift</p>

      <h1 className="mt-2 text-title font-semibold text-ink">Trang này gặp trục trặc</h1>

      <div
        role="alert"
        className="mt-5 flex items-start gap-2 rounded-md border border-critical/40 bg-critical/10 px-3 py-2.5 text-body"
      >
        <span aria-hidden className="mt-px shrink-0 font-bold text-crit-ink">
          ✕
        </span>
        <div className="min-w-0 leading-snug text-sec">
          Giao diện dựng trang không thành công. Dữ liệu của bạn{" "}
          <strong className="text-ink">không bị ảnh hưởng</strong> — lỗi nằm ở phần hiển thị,
          không phải ở kho dữ liệu.
        </div>
      </div>

      <p className="mt-5 text-body leading-relaxed text-sec">Thử theo thứ tự này:</p>
      <ol className="mt-2 list-decimal space-y-1 pl-5 text-body leading-relaxed text-sec">
        <li>
          Bấm <strong className="text-ink">Tải lại trang</strong> bên dưới.
        </li>
        <li>
          Nếu vẫn lỗi, về <strong className="text-ink">Trang chủ</strong> rồi vào lại.
        </li>
        <li>
          Nếu vẫn lỗi, chạy <code className="font-num text-meta text-ink">
            python scripts/kiem_tra_truoc_demo.py
          </code>{" "}
          để biết phân hệ nào đang hỏng.
        </li>
      </ol>

      <div className="mt-7 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={reset}
          className="focus-ring rounded-md bg-brand px-4 py-2 text-body font-medium text-page transition hover:opacity-90"
        >
          Tải lại trang
        </button>
        <a
          href="/"
          className="focus-ring rounded-md border border-strong px-4 py-2 text-body font-medium text-ink transition hover:bg-raised"
        >
          Về trang chủ
        </a>
      </div>

      {error.digest ? (
        <p className="mt-8 text-meta text-mut">
          Mã tra cứu sự cố:{" "}
          <code className="font-num text-ink">{error.digest}</code> — đọc cho người trực kỹ
          thuật để tra đúng dòng log.
        </p>
      ) : null}
    </main>
  );
}
