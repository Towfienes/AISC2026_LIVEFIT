import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LiveLift — Phòng điều khiển livestream bán hàng",
  description:
    "Nền tảng thí nghiệm switchback cho livestream bán hàng: bốc thăm BẬT/TẮT trước giờ lên sóng, gợi ý ghim theo thời gian thực, chứng minh tác động bằng kiểm định nhân quả (AISC'26)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body className="bg-page text-ink antialiased">{children}</body>
    </html>
  );
}
