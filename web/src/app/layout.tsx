import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LiveLift — Bàn trung control",
  description: "Bàn trung control cho thí nghiệm vận hành livestream thương mại (AISC'26)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body className="bg-page text-ink antialiased">{children}</body>
    </html>
  );
}
