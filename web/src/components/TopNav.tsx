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
  { href: "/desk", label: "Bàn điều khiển" },
  { href: "/host", label: "Màn hình host" },
  { href: "/replay", label: "Phát lại / Phân tích" },
] as const;

export default function TopNav() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Điều hướng chính"
      className="flex h-9 shrink-0 items-center gap-1 overflow-x-auto border-b border-hairline bg-page px-3"
    >
      <Link href="/" className="mr-2 shrink-0 text-[13px] font-bold tracking-tight text-ink">
        LiveLift
      </Link>
      {LINKS.map((l) => {
        const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
        return (
          <Link
            key={l.href}
            href={l.href}
            aria-current={active ? "page" : undefined}
            className={`shrink-0 rounded px-2.5 py-1 text-xs transition-colors ${
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
