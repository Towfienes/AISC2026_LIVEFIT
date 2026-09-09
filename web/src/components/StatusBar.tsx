"use client";

/**
 * Desk toolbar — session chrome plus the desk's one reserved ALERT SLOT.
 *
 * Two rows inside a single surface:
 *   1. session picker · connection · design commitment · session clock ·
 *      mode toggle · end-session;
 *   2. a slot that stays in the DOM at all times and fills with an operational
 *      error when one happens.
 *
 * Why a slot and not a toast (gói UI-2): a command that fails on the desk has
 * to be seen and stay seen. A toast disappears on a timer and, worse, floats
 * over the figures the operator is reading; a modal steals the stream. The slot
 * lives in the bar's own layout flow, pushes the panels down instead of
 * covering them, and only leaves when the operator dismisses it. `Callout`
 * carries `role="alert"`, so INSERTING it is what announces the message — the
 * wrapper deliberately holds no second live region, which would double-speak.
 *
 * Density: the row is `min-h-bar` and WRAPS. It used to be a fixed `h-bar` with
 * `overflow` left to chance, so at 1366 px the mode toggle and the end-session
 * button were squeezed out of the layout instead of moving to a second line.
 * Vitals (viewers, clicks/min) are no longer here at all — they belong to the
 * operating clock, where they get the num-* display steps and a real label.
 *
 * The segmented control sits inside an `overflow-hidden` group, so it uses
 * `.focus-ring-inset`: an offset ring would be clipped away and the keyboard
 * focus would be invisible.
 *
 * ---------------------------------------------------------------------------
 * CHUYỂN ĐỘNG & TRỢ NĂNG (gói UI-3)
 * ---------------------------------------------------------------------------
 * 1. Chấm TRỰC TIẾP từng chạy `animate-pulse` — một nhịp đập KHÔNG BAO GIỜ DỪNG
 *    suốt 90 phút phát sóng. Đó là chuyển động môi trường: nó không báo điều gì
 *    mới (kết nối vẫn thế), nhưng mắt vẫn phải bắt nó vài nghìn lần một phiên,
 *    và nó nằm ngay cạnh vùng số liệu người ta cần đọc. Đã GỠ HẲN. Trạng thái
 *    kết nối vẫn phân biệt được bằng ba kênh tĩnh: HÌNH DẠNG (chấm đặc = nối
 *    thẳng, nửa đặc = đang nối lại), MÀU và CHỮ tiếng Việt.
 * 2. Đồng hồ phiên nhảy mỗi giây nên KHÔNG có transition, chỉ `tabular-nums`.
 * 3. Bộ chọn chế độ Gợi ý / Tự động là `radiogroup` + `radio` thật, có điều
 *    hướng bằng phím mũi tên và roving tabindex — `aria-pressed` trên hai nút
 *    rời rạc không nói được rằng chúng loại trừ nhau.
 */

import { useRef } from "react";

import { fmtClock } from "@/lib/format";
import type { ConnectionKind, SessionMode, SessionSummary } from "@/lib/types";
import type { SocketStatus } from "@/lib/useLiveSocket";

import Badge from "./ui/Badge";
import Button from "./ui/Button";
import Callout from "./ui/Callout";
import { fieldCls } from "./ui/field";
import StatusMark from "./ui/StatusMark";

export function DemoBadge() {
  return (
    <Badge tone="warn" className="tracking-wider">
      DEMO DATA
    </Badge>
  );
}

export function ConnectionBadge({
  connection,
  wsStatus,
}: {
  connection: ConnectionKind;
  wsStatus?: SocketStatus;
}) {
  if (connection === "mock") return <DemoBadge />;
  if (connection === "connecting") {
    return <span className="text-body text-dim">Đang kết nối…</span>;
  }
  const wsOpen = wsStatus === "open";
  // Shape + word, not colour alone: chấm đặc = nối thẳng, nửa đặc = đang nối lại.
  // Ký hiệu TĨNH — xem ghi chú "CHUYỂN ĐỘNG & TRỢ NĂNG" ở đầu file.
  return (
    <span className="flex shrink-0 items-center gap-1.5 text-body font-semibold text-sec">
      <StatusMark
        shape={wsOpen ? "on" : "drift"}
        inherit
        className={wsOpen ? "text-good-ink" : "text-warn-ink"}
      />
      {wsOpen ? "TRỰC TIẾP" : "TRỰC TIẾP (đang nối lại WS)"}
    </span>
  );
}

/** Hai chế độ vận hành — nhãn và giải thích đi liền nhau, một nguồn duy nhất. */
const MODES = [
  {
    value: "suggest" as const,
    label: "Gợi ý",
    tip: "Hệ thống chỉ đề xuất — bạn bấm Thực hiện mới ghim",
  },
  {
    value: "auto" as const,
    label: "Tự động",
    tip: "Hệ thống tự ghim theo gợi ý sau khi đếm ngược",
  },
];

/**
 * Bộ chọn chế độ — `radiogroup` với hai `radio`.
 *
 * Vì sao không phải hai nút `aria-pressed`: hai nút bật/tắt rời rạc nói với
 * trình đọc màn hình rằng có thể bật cả hai, hoặc không bật cái nào. Ở đây
 * đúng một chế độ luôn được chọn, và đó chính là ngữ nghĩa của radiogroup.
 *
 * Bàn phím theo mẫu APG: ← ↑ / → ↓ chuyển và CHỌN luôn, Home/End nhảy về đầu
 * và cuối; chỉ ô đang chọn nằm trong thứ tự Tab (roving tabindex), nên Tab đi
 * qua cả nhóm bằng một lần bấm thay vì hai.
 */
function ModeToggle({
  mode,
  onSetMode,
  canToggleMode,
}: {
  mode: SessionMode;
  onSetMode?: (m: SessionMode) => void;
  canToggleMode?: boolean;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  const move = (to: number) => {
    const i = (to + MODES.length) % MODES.length;
    onSetMode?.(MODES[i].value);
    refs.current[i]?.focus();
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>, i: number) => {
    if (!canToggleMode) return;
    switch (e.key) {
      case "ArrowRight":
      case "ArrowDown":
        e.preventDefault();
        move(i + 1);
        break;
      case "ArrowLeft":
      case "ArrowUp":
        e.preventDefault();
        move(i - 1);
        break;
      case "Home":
        e.preventDefault();
        move(0);
        break;
      case "End":
        e.preventDefault();
        move(MODES.length - 1);
        break;
      default:
        break;
    }
  };

  return (
    <div
      role="radiogroup"
      aria-label="Chế độ vận hành"
      className="flex items-center overflow-hidden rounded-md border border-hairline"
    >
      {MODES.map((m, i) => {
        const selected = mode === m.value;
        return (
          <button
            key={m.value}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={selected}
            tabIndex={selected ? 0 : -1}
            disabled={!canToggleMode}
            onClick={() => onSetMode?.(m.value)}
            onKeyDown={(e) => onKeyDown(e, i)}
            className={`focus-ring focus-ring-inset flex h-ctl min-h-tap min-w-tap items-center px-3 text-body font-semibold transition-colors duration-short2 ease-emphasized ${
              selected ? "bg-s7 text-page" : "bg-raised text-sec"
            } ${canToggleMode ? "hover:text-ink" : "cursor-default"} ${
              selected && canToggleMode ? "hover:text-page" : ""
            }`}
            title={canToggleMode ? m.tip : "Chế độ do máy chủ quyết định khi kết nối trực tiếp"}
          >
            {m.label}
          </button>
        );
      })}
    </div>
  );
}

interface Props {
  connection: ConnectionKind;
  wsStatus?: SocketStatus;
  sessions: SessionSummary[];
  sessionId: string | null;
  onSelectSession: (id: string) => void;
  elapsedS: number;
  durationS: number;
  mode: SessionMode;
  onSetMode?: (m: SessionMode) => void;
  canToggleMode?: boolean;
  /** Shown only when the selected session is live on a real API. */
  onEndSession?: () => void;
  canEndSession?: boolean;
  endBusy?: boolean;
  /**
   * Cam kết thiết kế (SHA-256 của tham số thiết kế + seed), công bố trước phát
   * sóng — gói Q3. Hiển thị 8 ký tự đầu, hash đầy đủ trong tooltip: người vận
   * hành đối chiếu được bằng mắt mà không tốn thêm dòng nào trên thanh.
   * `null`/thiếu khi phiên chưa có lịch (chế độ demo, phiên trước gói Q3) —
   * khi đó KHÔNG hiện gì, vì một ô trống còn thật thà hơn một hash bịa.
   */
  designHash?: string | null;
  /**
   * Lỗi vận hành đang cần người xử lý (lệnh Thực hiện trượt, kết thúc phiên
   * thất bại…). `null` = ô trống, không chiếm chỗ.
   */
  alert?: string | null;
  onDismissAlert?: () => void;
}

/** Mã thiết kế rút gọn — chỉ 8 ký tự đầu, đủ để đối chiếu bằng mắt. */
export function DesignHashBadge({ hash }: { hash: string }) {
  return (
    <span
      className="tnum shrink-0 text-meta text-dim"
      title={`Cam kết thiết kế (SHA-256 tham số + seed), công bố trước phát sóng: ${hash}`}
    >
      Mã TK <span className="font-semibold text-sec">{hash.slice(0, 8)}</span>
    </span>
  );
}

export default function StatusBar({
  connection,
  wsStatus,
  sessions,
  sessionId,
  onSelectSession,
  elapsedS,
  durationS,
  mode,
  onSetMode,
  canToggleMode,
  onEndSession,
  canEndSession,
  endBusy,
  designHash,
  alert,
  onDismissAlert,
}: Props) {
  return (
    <header className="shrink-0 rounded-lg border border-hairline bg-surface">
      <div className="flex min-h-bar flex-wrap items-center gap-x-3 gap-y-2 px-3 py-1.5">
        <span className="shrink-0 text-meta font-semibold text-sec">Phiên đang xem</span>

        <select
          value={sessionId ?? ""}
          onChange={(e) => onSelectSession(e.target.value)}
          className={`${fieldCls} max-w-[340px] px-2 py-1 text-body`}
          aria-label="Chọn phiên"
        >
          {sessions.map((s) => (
            <option key={s.session_id} value={s.session_id}>
              {s.title ?? s.session_id} · {s.platform} ·{" "}
              {s.status === "live" ? "đang live" : s.status === "ended" ? "đã kết thúc" : s.status}
            </option>
          ))}
        </select>

        <ConnectionBadge connection={connection} wsStatus={wsStatus} />

        {designHash ? <DesignHashBadge hash={designHash} /> : null}

        <div className="ml-auto flex flex-wrap items-center gap-x-3 gap-y-2">
          {/* đồng hồ PHIÊN — khác đồng hồ KHỐI ở khối tiêu điểm bên dưới.
              Nhảy mỗi giây ⇒ KHÔNG transition, chỉ `tnum` để chữ số không xê. */}
          <span className="flex items-baseline gap-1.5 text-meta text-dim">
            Đã phát:
            <span className="tnum text-strong text-ink">{fmtClock(elapsedS)}</span>
            <span className="tnum">/ {fmtClock(durationS)}</span>
          </span>

          {/* mode toggle — segmented control.
              `min-h-tap` là sàn WCAG 2.2 SC 2.5.8 (24px); `h-ctl` nâng thực tế
              lên 36px vì đây là control người vận hành bấm khi đang nhìn stream. */}
          <ModeToggle mode={mode} onSetMode={onSetMode} canToggleMode={canToggleMode} />

          {canEndSession && onEndSession ? (
            <Button
              variant="danger"
              onClick={onEndSession}
              disabled={endBusy}
              title="Kết thúc phiên đang phát — dữ liệu đã ghi được giữ nguyên"
            >
              {endBusy ? "Đang kết thúc…" : "Kết thúc phiên"}
            </Button>
          ) : null}
        </div>
      </div>

      {/* Ô DÀNH SẴN cho lỗi vận hành — luôn có trong DOM, chỉ chiếm chỗ khi có
          lỗi, và không bao giờ đè lên vùng số liệu bên dưới. */}
      <div className="empty:hidden">
        {alert ? (
          <div className="flex items-start gap-2 border-t border-hairline px-3 py-2">
            <Callout tone="critical" className="min-w-0 flex-1">
              {alert}
            </Callout>
            {onDismissAlert ? (
              <Button
                size="sm"
                variant="ghost"
                onClick={onDismissAlert}
                aria-label="Đóng thông báo lỗi"
              >
                Đóng
              </Button>
            ) : null}
          </div>
        ) : null}
      </div>
    </header>
  );
}
