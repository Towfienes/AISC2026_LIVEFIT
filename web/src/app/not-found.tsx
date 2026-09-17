/**
 * not-found.tsx — trang 404 tiếng Việt.
 *
 * Mặc định Next trả một trang 404 tiếng Anh trần. Giám khảo gõ nhầm một đường
 * dẫn (hoặc bấm một shortlink /r/{code} đã hết hạn mà Caddy chuyển tiếp về
 * web) sẽ thấy đúng trang này, kèm lối đi tiếp — thay vì một dòng “404 This
 * page could not be found”.
 *
 * Đây là Server Component: không cần JavaScript phía trình duyệt để hiển thị.
 *
 * Đánh giá UI 17/09/2026: tên các lối đi khớp đúng thuật ngữ thống nhất của
 * thanh điều hướng ("Bàn trợ live", "Chuẩn bị phiên"), và mô tả của /bat-dau
 * nói đúng việc trang đó làm (ba câu hỏi) — bản cũ gán cho nó việc bốc thăm
 * lịch, vốn thuộc /chay-phien. Chuyển động hover dùng token thời lượng.
 */

import Link from "next/link";

const LOI_DI = [
  { href: "/", nhan: "Trang chính", mo_ta: "Ba lối vào: buổi live của tôi, xem thử, phân tích video" },
  {
    href: "/bat-dau",
    nhan: "Buổi live của tôi dùng được gì?",
    mo_ta: "Trả lời ba câu hỏi, biết ngay làm được gì với buổi live của mình",
  },
  { href: "/chay-phien", nhan: "Chuẩn bị phiên", mo_ta: "Bốc thăm lịch BẬT/TẮT trước giờ lên sóng" },
  { href: "/desk", nhan: "Bàn trợ live", mo_ta: "Theo dõi bình luận và gợi ý ghim khi đang live" },
  { href: "/ket-qua", nhan: "Kết quả & chiến lược", mo_ta: "Kết luận và báo cáo của các phiên đã chạy" },
];

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6 py-16">
      <p className="text-label uppercase tracking-wide text-mut">LiveLift · 404</p>

      <h1 className="mt-2 text-title font-semibold text-ink">Không có trang nào ở địa chỉ này</h1>

      <p className="mt-3 text-body leading-relaxed text-sec">
        Đường dẫn bạn vừa mở không tồn tại trong ứng dụng. Nếu bạn vừa bấm một link đo{" "}
        <code className="font-num text-meta text-ink">/r/&#123;mã&#125;</code>, nhiều khả năng mã
        đó đã bị xóa hoặc thuộc về một phiên khác — lượt bấm vẫn được ghi nhận, nhưng không còn
        đích để chuyển tới.
      </p>

      <nav aria-label="Các trang chính" className="mt-7 grid gap-2">
        {LOI_DI.map((muc) => (
          <Link
            key={muc.href}
            href={muc.href}
            className="focus-ring min-h-ctl rounded-md border border-hairline bg-surface px-4 py-3 transition-colors duration-short2 ease-emphasized hover:border-strong hover:bg-raised"
          >
            <span className="block text-body font-medium text-ink">{muc.nhan}</span>
            <span className="mt-0.5 block text-meta text-dim">{muc.mo_ta}</span>
          </Link>
        ))}
      </nav>
    </main>
  );
}
