"use client";

/**
 * Slim top navigation shared by every page. The current page is highlighted
 * (recognition over recall). Carries NO session or block information, so it is
 * safe on the blinded /host screen.
 *
 * v2 (gói SKIN, spec UX-FLOW a): 7 mục tên-màn-hình → 5 mục tên-theo-việc,
 * nhóm theo pha TRƯỚC/TRONG/SAU live. Hai trang RỜI KHỎI NAV nhưng route vẫn
 * sống nguyên:
 *   /bat-dau — công cụ tra cứu MỘT LẦN ("buổi live của tôi dùng được gì?"),
 *              vào từ cửa số 1 của trang chủ và từ empty state, không phải
 *              điểm đến hằng ngày;
 *   /host    — màn hình THỨ CẤP mở ra màn phụ/TV cho người dẫn, vào bằng nút
 *              "Mở màn hình người dẫn" từ Chuẩn bị phiên / Bàn trợ live; để
 *              trên nav chỉ dụ người vận hành mở nhầm màn bị làm mù.
 * Góc phải luôn có chip chế độ DEMO/THẬT (ModeChip) — người dùng biết mình
 * đang ở thế giới dữ liệu nào trên mọi trang.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";

import ModeChip from "./ModeChip";

interface NavLink {
  href: string;
  label: string;
}

/** Nhãn pha đứng TRƯỚC nhóm — chữ mờ, không bấm được. */
const GROUPS: { phase: string | null; links: NavLink[] }[] = [
  { phase: null, links: [{ href: "/", label: "Bắt đầu" }] },
  { phase: "Trước live", links: [{ href: "/chay-phien", label: "Chuẩn bị phiên" }] },
  { phase: "Trong live", links: [{ href: "/desk", label: "Bàn trợ live" }] },
  {
    phase: "Sau live",
    links: [
      { href: "/replay", label: "Xem lại phiên" },
      { href: "/ket-qua", label: "Kết quả & chiến lược" },
    ],
  },
];

export default function TopNav() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Điều hướng chính"
      className="flex min-h-ctl shrink-0 items-center gap-1 overflow-x-auto border-b border-hairline bg-page px-3"
    >
      <Link
        href="/"
        className="focus-ring mr-2 flex shrink-0 items-center gap-2 rounded px-1 font-display text-body font-bold tracking-tight text-ink"
      >
        <span aria-hidden className="logo-mark" />
        LiveLift
      </Link>
      {GROUPS.map((g, gi) => (
        <div key={g.phase ?? gi} className="flex shrink-0 items-center gap-1">
          {g.phase ? (
            <span
              aria-hidden
              className="ml-2 mr-0.5 shrink-0 select-none border-l border-hairline pl-3 text-meta font-semibold uppercase tracking-[0.08em] text-mut"
            >
              {g.phase}
            </span>
          ) : null}
          {g.links.map((l) => {
            const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={active ? "page" : undefined}
                className={`focus-ring flex min-h-tap shrink-0 items-center rounded-md px-2.5 py-1 text-meta transition-colors duration-short2 ease-emphasized ${
                  active
                    ? "font-semibold text-ink shadow-[inset_0_-2px_0_0_#7c6cff]"
                    : "text-sec hover:bg-surface hover:text-ink"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </div>
      ))}
      <span className="ml-auto flex shrink-0 items-center pl-2">
        <ModeChip />
      </span>
    </nav>
  );
}
