import type { Config } from "tailwindcss";

/**
 * LiveLift control-desk theme — committed dark look.
 * Chart/ink tokens follow the validated dataviz reference palette (dark column).
 *
 * ---------------------------------------------------------------------------
 * TYPE SCALE (ISO 9241-303)
 * ---------------------------------------------------------------------------
 * ISO 9241-303 asks for a cap height of 16–22 arcmin at the design viewing
 * distance. At 70 cm, 96 dpi (1 px = 0.2646 mm) and a cap-height ratio of 0.75
 * for system-ui, one CSS pixel subtends
 *
 *     0.2646 mm x 0.75 / 700 mm x 3437.75 arcmin/rad  ≈  0.975 arcmin/px
 *
 * so the arcmin value of a step is ≈ its px value. The desk used to run at
 * 11 px (≈ 10.7 arcmin) — roughly a third below the minimum — which is exactly
 * what operators reported ("chữ còn quá nhỏ"). Every step below is named by
 * ROLE, never by size, so callers cannot drift back down:
 *
 *   meta    13 px ≈ 12.7'  non-critical metadata only (timestamps, hints)
 *   label   15 px ≈ 14.6'  eyebrow/section labels (pair with `uppercase`)
 *   body    16 px ≈ 15.6'  reading text
 *   strong  18 px ≈ 17.5'  in band — emphasised text, toolbar vitals
 *   title   20 px ≈ 19.5'  in band — page/panel titles
 *   num-s   28 px          display figures (KPI tile)
 *   num-m   40 px          display figures (hero tile)
 *   num-l   56 px          display figures (headline result)
 *   num-xl  72 px          display figures (host screen, read from ~2 m)
 *
 * `font-variant-numeric: tabular-nums` for the four num-* steps is applied in
 * globals.css (Tailwind's fontSize tuple cannot carry it).
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      /**
       * PLANE LADDER v2 — "Phòng điều khiển phát sóng" (gói SKIN, spec
       * UI-VISUAL v2). Tên token GIỮ NGUYÊN (page/surface/raised/axis…) để
       * mọi trang cũ không vỡ; GIÁ TRỊ đổi từ thang xám chết sang thang xanh
       * đêm #07080d→#191d29 (hue ~225°) + mực chữ đã đo lại WCAG trên cả 4
       * plane mới (bảng trong globals.css). Nguồn sự thật: :root của
       * globals.css (--canvas/--s1/--s2/--s3, --ink…, --brand…).
       */
      colors: {
        page: "#07080d", // page plane (--canvas)
        surface: "#0d0f16", // chart / card surface (--s1)
        raised: "#13161f", // elevated surface (tooltips, chips) (--s2)
        ink: "#f4f5f8", // primary ink — 15.4–18.4:1
        sec: "#b6bcc8", // secondary ink — 8.8–10.5:1
        mut: "#7d8494", // muted (--ink-3) — CHỈ trên page/surface/raised (4.48:1 trên axis)
        muted: "#7d8494", // alias — some components use text-muted
        dim: "#8a91a3", // muted TEXT that still clears 4.5:1 on every plane (--ink-3-raised)
        grid: "#1b1e28", // hairline gridline
        axis: "#191d29", // highest plane / neutral fill (--s3)
        s1: "#3987e5", // categorical slot 1 — blue
        s2: "#d95926", // slot 2 — orange
        s3: "#199e70", // slot 3 — aqua
        s4: "#c98500", // slot 4 — yellow
        s5: "#d55181", // slot 5 — magenta
        s6: "#008300", // slot 6 — green
        s7: "#8b7bff", // slot 7 — violet (block strip ON, khớp --st-on v2)
        good: "#3ddc7a", // fill — text on it must be dark (#07080d = 11.2:1)
        warn: "#fab219",
        serious: "#ec835a",
        critical: "#d03b3b",

        /**
         * BRAND — MỘT accent duy nhất toàn app (tím điện), thay cho tình
         * trạng "mỗi trang một màu nút". Chỉ dành cho: logo, CTA chính,
         * focus, khối BẬT, link nhấn. live CHỈ cho trạng thái đang-phát +
         * nút Kết thúc phiên — tuyệt đối không dùng việc khác.
         */
        brand: "#7c6cff", // chữ #0c0d12 trên nó = 5.03:1 AA
        "brand-hi": "#a99cff", // hover, gradient text
        "brand-ink": "#b3aaf2", // chữ tím trên nền tối — 7.96–9.48:1
        live: "#ff4d5e", // 5.18–6.17:1 trên cả 4 plane

        /**
         * STATUS INKS — the *text* half of every status token pair. The base
         * tones above stay as fills/borders (they are chosen for area, not for
         * type); these are chosen so status TEXT clears WCAG 1.4.3 AA (4.5:1)
         * on page (#0d0d0d), surface (#1a1a19), raised (#232322) AND on the
         * lightest plane the desk ever paints, axis (#383835). Ratios are
         * listed in globals.css next to the custom properties.
         *
         * Colour is never the only channel: every status also carries a shape
         * (.status-mark: filled disc = BẬT, hollow ring = TẮT, half disc =
         * trôi) and a Vietnamese word.
         */
        "on-fill": "var(--st-on)", // #9085e9 — BẬT fill
        "on-ink": "var(--st-on-ink)", // #b3aaf2 — 9.21:1 page … 5.57:1 axis
        "off-fill": "var(--st-off)", // #383835 — TẮT fill
        "off-ink": "var(--st-off-ink)", // #c3c2b7 — 10.85:1 page … 6.57:1 axis
        "drift-ink": "var(--st-drift-ink)", // #a3a19a — 7.52:1 page … 4.55:1 axis
        "good-ink": "var(--st-good-ink)", // #4ed44e — 10.04:1 page … 6.08:1 axis
        "warn-ink": "var(--st-warn-ink)", // #fab219 — 10.59:1 page … 6.41:1 axis
        // base #d03b3b only reaches 4.05:1 on page — it may fill, never letter
        "crit-ink": "var(--st-crit-ink)", // #f08a8a — 8.06:1 page … 4.88:1 axis
        // base #3987e5 drops to 4.32:1 on the raised plane
        "info-ink": "var(--st-info-ink)", // #78b0f0 — 8.58:1 page … 5.19:1 axis
        focus: "var(--focus-ring)", // #78b0f0 — 8.58:1 on page (SC 1.4.11 needs 3:1)
      },
      borderColor: {
        // v2: hairline .06 cho card (spec --hair), strong .11 cho control
        // tương tác (spec --hair-strong).
        hairline: "rgba(255,255,255,0.06)",
        edge: "rgba(255,255,255,0.06)", // alias — some components use border-edge
        strong: "rgba(255,255,255,0.11)",
      },
      /**
       * HỆ CHỮ v2 — ba họ Google Fonts có subset vietnamese (nạp qua @import
       * trong globals.css, display=swap, fallback stack thật):
       *   sans    Be Vietnam Pro — body/nút/nhãn (thiết kế gốc cho tiếng Việt)
       *   display Space Grotesk — H1/H2/H3, tên card, chữ BẬT/TẮT to
       *   num     JetBrains Mono — MỌI con số dữ liệu (tabular tự nhiên)
       */
      fontFamily: {
        sans: ["Be Vietnam Pro", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        display: ["Space Grotesk", "Be Vietnam Pro", "system-ui", "sans-serif"],
        num: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Consolas", "monospace"],
      },
      fontSize: {
        meta: ["13px", { lineHeight: "18px", fontWeight: "400" }],
        label: ["15px", { lineHeight: "20px", fontWeight: "600", letterSpacing: "0.06em" }],
        body: ["16px", { lineHeight: "22px", fontWeight: "400" }],
        strong: ["18px", { lineHeight: "24px", fontWeight: "600" }],
        title: ["20px", { lineHeight: "26px", fontWeight: "600" }],
        "num-s": ["28px", { lineHeight: "30px", fontWeight: "650" }],
        "num-m": ["40px", { lineHeight: "42px", fontWeight: "650" }],
        "num-l": ["56px", { lineHeight: "54px", fontWeight: "700", letterSpacing: "-0.02em" }],
        "num-xl": ["72px", { lineHeight: "68px", fontWeight: "700", letterSpacing: "-0.02em" }],
      },
      /**
       * Operating-density tokens. `tap` is the WCAG 2.2 SC 2.5.8 (Target Size
       * Minimum) floor; `ctl` is the height of a primary desk control — big
       * enough to hit while watching the stream, small enough that the 44 px
       * toolbar still holds one. Tailwind 3.4 feeds the spacing scale into
       * min-h, min-w, h, w, p and gap utilities alike.
       */
      spacing: {
        tap: "24px", // SC 2.5.8 minimum target
        ctl: "36px", // primary control height (md button, input, select)
        bar: "44px", // toolbar / status bar row
      },
      /**
       * MOTION — Material 3 duration tokens, resolved through CSS custom
       * properties so `prefers-reduced-motion: reduce` can collapse every
       * duration in one place (globals.css).
       */
      transitionDuration: {
        short2: "var(--dur-short2)", // 100ms — hover/press feedback
        short4: "var(--dur-short4)", // 200ms — small element enter/exit
        medium1: "var(--dur-medium1)", // 250ms
        medium2: "var(--dur-medium2)", // 300ms — panel/surface change
        medium3: "var(--dur-medium3)", // 350ms — count-up tween của KPI
        // Gói UI-3 — ba thời lượng gắn với một sự kiện vận hành cụ thể.
        tick: "var(--dur-tick)", // 1000ms LINEAR — playhead + thanh tiến trình
        enter: "var(--dur-enter)", // 180ms — dòng bình luận / thẻ mới
        switch: "var(--dur-switch)", // 280ms — chuyển khối BẬT ↔ TẮT
      },
      transitionTimingFunction: {
        emphasized: "var(--ease-emphasized)", // cubic-bezier(0.2, 0, 0, 1)
        standard: "var(--ease-standard)",
      },
    },
  },
  plugins: [],
};
export default config;
