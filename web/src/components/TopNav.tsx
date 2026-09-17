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
 * Góc phải luôn có chip "kho đang chứa gì" (ModeChip) — người dùng biết mình
 * đang ở thế giới dữ liệu nào trên mọi trang.
 *
 * v3 (đánh giá UI 17/09/2026): trên điện thoại 390px nav cũ là MỘT dải cuộn
 * ngang (`overflow-x-auto`) — cắt chữ "Chuẩn bị ph…" và đẩy chip chế độ ra
 * ngoài màn hình, trong khi trang chủ dặn "chip ở góc phải thanh điều hướng".
 * Bố cục mới:
 *   - dưới `lg`: một hàng logo + chip kho (LUÔN thấy, được phép xuống dòng) +
 *     nút "Các trang" mở/đóng danh sách dọc (aria-expanded, aria-controls);
 *   - từ `lg`: các mục nằm ngang như cũ; nhãn pha chỉ hiện từ `xl` để hàng
 *     không bao giờ tràn.
 * Không có hiệu ứng chuyển động nào ngoài đổi màu hover (đường render /desk).
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

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

const MENU_ID = "topnav-cac-trang";

function isActive(href: string, pathname: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export default function TopNav() {
  const pathname = usePathname() ?? "";
  const [open, setOpen] = useState(false);

  // Đổi trang thì gập danh sách lại — không để menu che trang mới.
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  // Esc đóng danh sách (thói quen bàn phím của mọi menu).
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <nav aria-label="Điều hướng chính" className="shrink-0 border-b border-hairline bg-page">
      <div className="flex min-h-ctl items-center gap-1 px-3 py-1 lg:py-0">
        <Link
          href="/"
          className="focus-ring mr-2 flex min-h-tap shrink-0 items-center gap-2 rounded px-1 font-display text-body font-bold tracking-tight text-ink"
        >
          <span aria-hidden className="logo-mark" />
          LiveLift
        </Link>

        {/* Màn rộng: các mục nằm ngang, nhãn pha chỉ hiện khi đủ chỗ (xl). */}
        <div className="hidden shrink-0 items-center gap-1 lg:flex">
          {GROUPS.map((g, gi) => (
            <div key={g.phase ?? gi} className="flex shrink-0 items-center gap-1">
              {g.phase ? (
                <span
                  aria-hidden
                  className="ml-2 mr-0.5 hidden shrink-0 select-none border-l border-hairline pl-3 text-meta font-semibold uppercase tracking-[0.08em] text-mut xl:inline-block"
                >
                  {g.phase}
                </span>
              ) : null}
              {g.links.map((l) => {
                const active = isActive(l.href, pathname);
                return (
                  <Link
                    key={l.href}
                    href={l.href}
                    aria-current={active ? "page" : undefined}
                    className={`focus-ring flex min-h-tap shrink-0 items-center whitespace-nowrap rounded-md px-2.5 py-1 text-meta transition-colors duration-short2 ease-emphasized ${
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
        </div>

        {/* Cụm phải: chip kho + nút "Các trang". `flex-wrap-reverse` — khi
            không đủ chỗ, NÚT nằm hàng trên và chip xuống hàng dưới, cả hai
            căn phải: chip kho LUÔN thấy, không bao giờ bị đẩy ra ngoài màn. */}
        <div className="ml-auto flex min-w-0 flex-1 flex-wrap-reverse items-center justify-end gap-1.5 pl-2">
          <ModeChip />

          {/* Màn hẹp: nút mở/đóng danh sách trang. */}
          <button
            type="button"
            aria-expanded={open}
            aria-controls={MENU_ID}
            onClick={() => setOpen((v) => !v)}
            className="focus-ring inline-flex min-h-ctl shrink-0 items-center gap-1.5 rounded-md border border-strong px-3 text-meta font-semibold text-sec transition-colors duration-short2 ease-emphasized hover:bg-raised hover:text-ink lg:hidden"
          >
            <svg
              aria-hidden
              viewBox="0 0 24 24"
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              {open ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
            </svg>
            {open ? "Đóng" : "Các trang"}
          </button>
        </div>
      </div>

      {/* Danh sách dọc cho màn hẹp — nhóm theo pha, mỗi mục cao ≥ 36px. */}
      <div
        id={MENU_ID}
        hidden={!open}
        className="border-t border-hairline px-3 pb-3 pt-1 lg:hidden"
      >
        {GROUPS.map((g, gi) => (
          <div key={g.phase ?? gi} className="pt-2">
            {g.phase ? (
              <p className="px-2.5 pb-1 text-meta font-semibold uppercase tracking-[0.08em] text-mut">
                {g.phase}
              </p>
            ) : null}
            <ul className="flex flex-col gap-0.5">
              {g.links.map((l) => {
                const active = isActive(l.href, pathname);
                return (
                  <li key={l.href}>
                    <Link
                      href={l.href}
                      aria-current={active ? "page" : undefined}
                      onClick={() => setOpen(false)}
                      className={`focus-ring flex min-h-ctl items-center rounded-md px-2.5 text-body transition-colors duration-short2 ease-emphasized ${
                        active
                          ? "bg-surface font-semibold text-ink shadow-[inset_2px_0_0_0_#7c6cff]"
                          : "text-sec hover:bg-surface hover:text-ink"
                      }`}
                    >
                      {l.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </nav>
  );
}
