"use client";

/**
 * Slim top navigation shared by every page. The current page is highlighted
 * (recognition over recall — the user always knows where they are and where
 * the other three screens live). Carries NO session or block information, so
 * it is safe on the blinded /host screen.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Trang chính" },
  // Gói WIZARD: lối vào cho câu hỏi đầu tiên của mọi người dùng mới — "tôi có
  // một buổi live, dùng được gì?". Đứng ngay sau trang chính vì đó là bước
  // trước cả việc chạy phiên.
  { href: "/bat-dau", label: "Tôi có buổi live" },
  { href: "/chay-phien", label: "Chạy phiên" },
  { href: "/desk", label: "Bàn điều khiển" },
  { href: "/host", label: "Màn hình host" },
  { href: "/replay", label: "Phát lại / Phân tích" },
  { href: "/ket-qua", label: "Kết quả" },
] as const;

export default function TopNav() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Điều hướng chính"
      className="flex h-ctl shrink-0 items-center gap-1 overflow-x-auto border-b border-hairline bg-page px-3"
    >
      <Link
        href="/"
        className="focus-ring mr-2 flex shrink-0 items-center rounded px-1 text-body font-bold tracking-tight text-ink"
      >
        LiveLift
      </Link>
      {LINKS.map((l) => {
        const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
        return (
          <Link
            key={l.href}
            href={l.href}
            aria-current={active ? "page" : undefined}
            className={`focus-ring flex min-h-tap shrink-0 items-center rounded-md px-2.5 py-1 text-meta transition-colors duration-short2 ease-emphasized ${
              active
                ? "bg-raised font-semibold text-ink"
                : "text-sec hover:bg-surface hover:text-ink"
            }`}
          >
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}
