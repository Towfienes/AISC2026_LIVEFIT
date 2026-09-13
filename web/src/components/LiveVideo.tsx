"use client";

/**
 * "Khung xem live" — the video context panel of the KOL desk (gói UI-KOL).
 *
 * OPERATOR VIEW ONLY by placement: the frame itself only shows the PUBLIC
 * video stream (no assignment, no block boundary — nothing L6 protects), but
 * it renders inside /desk, which must never be shown to the blinded host.
 *
 * Design rules:
 * - Video is CONTEXT, data is the job (spec a3): the panel collapses to a
 *   single button, remembers the choice per browser, and defaults to
 *   collapsed below the xl breakpoint where screen space is scarce.
 * - No autoplay, no sound decisions made for the operator: the iframe loads
 *   paused (`youtube-nocookie.com/embed/{id}` with no autoplay param) and the
 *   operator presses play themselves.
 * - Never a silent black frame: a session without a resolvable video id gets
 *   a Vietnamese empty state saying WHY there is nothing to embed.
 */

import { useEffect, useState } from "react";

import { cx } from "./ui/cx";

const STORAGE_KEY = "ll-video-collapsed";

function readStoredCollapse(): boolean | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw === "1") return true;
    if (raw === "0") return false;
  } catch {
    // storage blocked (private mode) — fall through to the viewport default
  }
  return null;
}

interface Props {
  /** YouTube video id (11 chars) or null when the session has none. */
  videoId: string | null;
  /** Session platform, for the empty-state explanation. */
  platform: string | null;
  /**
   * Mặc định THU GỌN bất kể bề rộng màn (desk v2 đặt video ở đáy cột KPI —
   * video là bối cảnh nhường chỗ đầu tiên, mở ra khi người vận hành cần).
   * Lựa chọn đã lưu của người vận hành vẫn thắng.
   */
  defaultCollapsed?: boolean;
  className?: string;
}

export default function LiveVideo({ videoId, platform, defaultCollapsed, className }: Props) {
  // null = chưa quyết (trước mount). Mặc định THU GỌN — an toàn cho màn hẹp;
  // effect dưới mở ra trên màn rộng trừ khi người vận hành đã tự chọn.
  const [collapsed, setCollapsed] = useState<boolean | null>(null);

  useEffect(() => {
    const stored = readStoredCollapse();
    if (stored != null) {
      setCollapsed(stored);
      return;
    }
    if (defaultCollapsed) {
      setCollapsed(true);
      return;
    }
    // Chưa từng chọn: mở trên màn ≥ xl (1280px), thu gọn dưới đó (spec B).
    setCollapsed(!window.matchMedia("(min-width: 1280px)").matches);
  }, [defaultCollapsed]);

  const toggle = () => {
    const next = !(collapsed ?? true);
    setCollapsed(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
    } catch {
      // không lưu được thì thôi — lựa chọn vẫn có hiệu lực trong phiên này
    }
  };

  if (collapsed !== false) {
    return (
      <div className={cx("flex", className)}>
        <button
          type="button"
          onClick={toggle}
          className="focus-ring flex min-h-ctl w-full items-center justify-center gap-2 rounded-lg border border-hairline bg-surface px-3 text-body text-sec transition-colors duration-short2 ease-emphasized hover:border-white/20 hover:text-ink"
        >
          <span aria-hidden>▸</span> Mở khung xem live
        </button>
      </div>
    );
  }

  return (
    <section
      aria-label="Khung xem live"
      className={cx("flex flex-col rounded-lg border border-hairline bg-surface p-3", className)}
    >
      <div className="mb-2 flex shrink-0 items-baseline justify-between gap-3">
        <h2 className="text-label uppercase text-dim">Xem live</h2>
        <button
          type="button"
          onClick={toggle}
          className="focus-ring flex min-h-tap items-center rounded px-1 text-meta text-dim underline decoration-dotted underline-offset-2 transition-colors duration-short2 ease-emphasized hover:text-sec"
        >
          Thu gọn
        </button>
      </div>
      {videoId ? (
        <iframe
          title="Video của phiên live (YouTube)"
          src={`https://www.youtube-nocookie.com/embed/${videoId}`}
          allow="encrypted-media; picture-in-picture"
          allowFullScreen
          loading="lazy"
          className="aspect-video w-full rounded-md border border-hairline bg-page"
        />
      ) : (
        <div className="flex aspect-video w-full flex-col items-center justify-center gap-1.5 rounded-md border border-hairline bg-page px-4 text-center">
          <p className="text-body text-sec">Phiên này không có video để nhúng.</p>
          <p className="text-meta leading-snug text-dim">
            {platform === "replay"
              ? "Nguồn phiên không kèm id video YouTube — nạp lại buổi live bằng đường phân tích replay để có khung xem."
              : `Nền tảng ${platform ?? "này"} không cung cấp khung nhúng — bàn vẫn chạy đủ tín hiệu bên cạnh.`}
          </p>
        </div>
      )}
    </section>
  );
}
