"use client";

/**
 * global-error.tsx — lưới an toàn CUỐI CÙNG (Next.js App Router).
 *
 * Bắt cả lỗi xảy ra trong chính `app/layout.tsx`, tức là chỗ mà `error.tsx`
 * không với tới. Vì nó THAY THẾ luôn layout gốc nên bắt buộc phải tự dựng
 * <html> và <body>, và KHÔNG được dựa vào bất kỳ provider/context nào.
 *
 * Cũng vì vậy tệp này không dùng lớp tiện ích Tailwind: nếu lỗi xảy ra trước
 * khi CSS kịp nạp (đúng kịch bản sự cố 13/09/2026 — `.next/static/css` rỗng,
 * layout.css trả 404), lớp Tailwind sẽ chẳng có tác dụng gì. Toàn bộ màu và
 * khoảng cách đặt thẳng bằng style nội tuyến, lấy đúng token của globals.css,
 * nên trang vẫn đọc được ngay cả khi không còn tệp CSS nào.
 */

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="vi">
      {/* <style> phải nằm trong <head>: <html> chỉ nhận <head> và <body> làm con,
          đặt thẳng dưới <html> là HTML sai lồng thẻ và React báo lỗi đúng lúc
          trang lỗi hiện ra.
          Vòng focus phải sống sót cả khi globals.css không nạp được — xem phần
          đầu tệp. Vì vậy dùng bộ chọn THEO THẺ chứ không theo lớp `focus-ring`:
          một lớp CSS ở đây cũng vô nghĩa như lớp Tailwind. Màu lấy đúng token
          --focus-ring của globals.css để hai nơi trông giống nhau. */}
      <head>
        <style
          dangerouslySetInnerHTML={{
            __html:
              "button:focus-visible,a:focus-visible{outline:2px solid #78b0f0;outline-offset:2px}",
          }}
        />
      </head>
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "24px",
          backgroundColor: "#07080d",
          color: "#f4f5f8",
          fontFamily:
            '"Be Vietnam Pro", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
          lineHeight: 1.55,
        }}
      >
        <main style={{ maxWidth: "34rem", width: "100%" }}>
          <p
            style={{
              margin: 0,
              fontSize: "15px",
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "#7d8494",
            }}
          >
            LiveLift
          </p>

          <h1 style={{ margin: "8px 0 0", fontSize: "20px", fontWeight: 600 }}>
            Ứng dụng không khởi động được giao diện
          </h1>

          <div
            role="alert"
            style={{
              marginTop: "20px",
              border: "1px solid rgba(208, 59, 59, 0.4)",
              backgroundColor: "rgba(208, 59, 59, 0.1)",
              borderRadius: "6px",
              padding: "10px 12px",
              fontSize: "16px",
              color: "#b6bcc8",
            }}
          >
            Đây là lỗi ở lớp ngoài cùng của giao diện. <strong style={{ color: "#f4f5f8" }}>
              Dữ liệu trong kho không bị ảnh hưởng
            </strong>{" "}
            — máy chủ API và cơ sở dữ liệu chạy tách rời với trang web này.
          </div>

          <p style={{ marginTop: "20px", fontSize: "16px", color: "#b6bcc8" }}>
            Việc cần làm, theo thứ tự:
          </p>
          <ol
            style={{
              marginTop: "8px",
              paddingLeft: "20px",
              fontSize: "16px",
              color: "#b6bcc8",
            }}
          >
            <li>Bấm “Thử lại” bên dưới.</li>
            <li>
              Nếu vẫn lỗi, dựng lại giao diện:{" "}
              <code style={{ fontFamily: '"JetBrains Mono", monospace', color: "#f4f5f8" }}>
                docker compose up -d --build web
              </code>
            </li>
            <li>
              Chạy{" "}
              <code style={{ fontFamily: '"JetBrains Mono", monospace', color: "#f4f5f8" }}>
                python scripts/kiem_tra_truoc_demo.py
              </code>{" "}
              để biết phân hệ nào đang hỏng.
            </li>
          </ol>

          <div style={{ marginTop: "28px", display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={reset}
              style={{
                border: "none",
                borderRadius: "6px",
                backgroundColor: "#7c6cff",
                color: "#07080d",
                padding: "9px 16px",
                fontSize: "16px",
                fontWeight: 500,
                cursor: "pointer",
                fontFamily: "inherit",
              }}
            >
              Thử lại
            </button>
            <a
              href="/"
              style={{
                borderRadius: "6px",
                border: "1px solid rgba(255,255,255,0.11)",
                color: "#f4f5f8",
                padding: "9px 16px",
                fontSize: "16px",
                fontWeight: 500,
                textDecoration: "none",
              }}
            >
              Về trang chủ
            </a>
          </div>

          {error.digest ? (
            <p style={{ marginTop: "32px", fontSize: "13px", color: "#7d8494" }}>
              Mã tra cứu sự cố:{" "}
              <code style={{ fontFamily: '"JetBrains Mono", monospace', color: "#f4f5f8" }}>
                {error.digest}
              </code>
            </p>
          ) : null}
        </main>
      </body>
    </html>
  );
}
