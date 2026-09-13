/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  eslint: { ignoreDuringBuilds: true },
  /**
   * Thư mục build. Mặc định `.next` — y như trước.
   *
   * LUẬT BẮT BUỘC (sự cố 13/09/2026): MỌI tiến trình `next dev` / `next build`
   * chạy SONG SONG phải đặt `LIVELIFT_DIST_DIR` RIÊNG. Hôm ấy nhiều tiến trình
   * cùng ghi một thư mục `.next`, thư mục build hỏng (`.next/static/css` rỗng),
   * `/_next/static/css/app/layout.css` trả 404 và trang chủ hiện ra dưới dạng
   * HTML thô không CSS. Không lệnh nào kêu ca, vì Next không hề coi việc hai
   * tiến trình dùng chung thư mục build là lỗi.
   *
   * Quy ước tên đang dùng — đừng trùng nhau:
   *   .next                    máy chủ dev gõ tay (`npm run dev`)
   *   .next-chay-local         scripts/chay_local.py (lệnh khởi động hằng ngày)
   *   .next-gate-css           scripts/gate_css_web.py (cổng CSS, chạy tay)
   *   .next-gate-css-pytest    tests/test_web_css_gate.py
   *   .next-<việc của bạn>     mọi tiến trình song song khác
   *
   *   LIVELIFT_DIST_DIR=.next-kiemchung npx next dev -p 3100
   *
   * web/.gitignore đã bỏ qua mọi đường dẫn bắt đầu bằng `/.next-`, nên thư
   * mục tạm không vào git. Thư mục thừa được dọn tự động ở bước (b) của
   * scripts/chay_local.py.
   *
   * (Lưu ý khi sửa khối chú thích này: đừng viết dấu sao rồi gạch chéo trong
   * một mẫu đường dẫn — nó đóng luôn khối chú thích và Next sẽ không nạp được
   * tệp cấu hình. Cổng CSS đã bắt đúng lỗi ấy một lần.)
   */
  distDir: process.env.LIVELIFT_DIST_DIR ?? ".next",
};

export default nextConfig;
