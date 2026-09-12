/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  eslint: { ignoreDuringBuilds: true },
  /**
   * Thư mục build. Mặc định `.next` — y như trước.
   *
   * Biến môi trường cho phép chạy MỘT máy chủ dev thứ hai (ví dụ để chụp ảnh
   * kiểm chứng trên cổng khác) mà không giẫm lên thư mục build của máy chủ
   * đang phục vụ cổng 3000:
   *
   *   LIVELIFT_DIST_DIR=.next-kiemchung npx next dev -p 3100
   */
  distDir: process.env.LIVELIFT_DIST_DIR ?? ".next",
};

export default nextConfig;
