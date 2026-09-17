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
 * MỘT DÒNG Ở 1366 (gói C5, ảnh f06): thanh từng gãy thành hai dòng vì nhãn chữ
 * "Phiên đang xem" (nay là nhãn cho trình đọc màn hình), ô chọn phiên rộng
 * 340px và huy hiệu "Mã TK" (gói C10: mã bằng chứng lịch chuyển xuống thẻ lịch
 * BẬT/TẮT với tên dễ hiểu). Nút "Kết thúc phiên" TÁCH XA công tắc Gợi ý/Tự
 * động: đứng một mình ở mép phải sau vạch ngăn — bản cũ để hai thứ sát nhau,
 * bấm nhầm khi căng thẳng là kết thúc cả buổi live.
 *
 * XÁC NHẬN HAI BƯỚC TẠI CHỖ (gói C9): thay hộp xác nhận của trình duyệt (lệch
 * ngôn ngữ thiết kế, chặn luôn cả trang) bằng bước xác nhận ngay trên thanh:
 * bấm lần một hiện "Kết thúc ngay / Huỷ", tự huỷ sau 10 giây. Một cú bấm ĐÚP
 * không được vượt qua bước này (sửa lỗi P1 17/09) — xem EndSessionControl.
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

import { useEffect, useRef, useState } from "react";

import { fmtClock, fmtDateHCM, fmtTimeHCM } from "@/lib/format";
import type { ConnectionKind, SessionMode, SessionStatus, SessionSummary } from "@/lib/types";
import type { SocketStatus } from "@/lib/useLiveSocket";

import Badge from "./ui/Badge";
import Button from "./ui/Button";
import Callout from "./ui/Callout";
import { fieldCls } from "./ui/field";
import StatusMark from "./ui/StatusMark";

export function DemoBadge() {
  return (
    <Badge tone="warn" className="tracking-wider">
      DỮ LIỆU MẪU
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
      {/* Không in "WS": người bán không cần biết tên giao thức. */}
      {wsOpen ? "TRỰC TIẾP" : "TRỰC TIẾP (đang nối lại)"}
    </span>
  );
}

/**
 * Nhãn tiếng Việt cho TỪNG trạng thái phiên.
 *
 * Trước đây chỉ `live`/`ended` có nhãn, còn lại rơi thẳng ra mã tiếng Anh
 * ("planned") trong ô chọn phiên. Từ migration 0008 còn thêm `cancelled` —
 * "đã đóng mà chưa từng lên sóng", khác hẳn "đã kết thúc" — nên bảng nhãn
 * phải đủ, không để trạng thái nào lọt ra ngoài bằng tên máy.
 */
const STATUS_VI: Record<SessionStatus, string> = {
  planned: "mới lập",
  scheduled: "đã có lịch gán",
  live: "đang live",
  ended: "đã kết thúc",
  cancelled: "đã huỷ (chưa phát sóng)",
};

/** Tên nền tảng cho người bán — không in mã máy ("youtube", "mo_phong"). */
const PLATFORM_VI: Record<string, string> = {
  youtube: "YouTube",
  facebook: "Facebook",
  shopee: "Shopee",
  tiktok: "TikTok",
  mo_phong: "mô phỏng",
};

/** "HH:MM DD/MM" giờ lên sóng (giờ Việt Nam), null khi phiên chưa lên sóng. */
export function onAirWhen(s: SessionSummary): string | null {
  if (!s.start_ts || !Number.isFinite(Date.parse(s.start_ts))) return null;
  return `${fmtTimeHCM(s.start_ts).slice(0, 5)} ${fmtDateHCM(s.start_ts).slice(0, 5)}`;
}

/**
 * Nhãn một phiên trong ô chọn (gói C8): TÊN phiên, không có tên thì GIỜ lên
 * sóng — không bao giờ in UUID thô ("d666df55-e357-4a89-ab69-…" trong ảnh f06
 * không nói được với người bán đó là buổi nào).
 */
export function sessionOptionLabel(s: SessionSummary): string {
  const when = onAirWhen(s);
  const title = s.title?.trim();
  const name = title
    ? title
    : when
      ? `Phiên lên sóng ${when}`
      : "Phiên chưa đặt tên, chưa lên sóng";
  const parts = [name];
  if (title && when) parts.push(when);
  parts.push(PLATFORM_VI[s.platform] ?? s.platform);
  parts.push(STATUS_VI[s.status] ?? s.status);
  if (s.is_demo) parts.push("dữ liệu mẫu");
  return parts.join(" · ");
}

/**
 * ĐÈN TRẠNG THÁI PHÁT SÓNG (gói DESK-HOST v2, khoảnh khắc S1 của spec
 * UI-VISUAL). Đèn ĐANG PHÁT đỏ với chấm pulse 8px là NGOẠI LỆ LẶP VÔ HẠN duy
 * nhất của màn vận hành — quy ước phát sóng toàn cầu, và nó gắn trên ĐÈN chứ
 * không phải trên chữ hay card (`.live-dot` trong globals.css; prefers-
 * reduced-motion tắt nhịp đập). Màu --live chỉ dành cho trạng thái đang-phát
 * + nút Kết thúc phiên. Các trạng thái khác là chip TĨNH trung tính — cả ba
 * kết cục (đang phát / đã kết thúc / chưa phát) được trình bày tử tế ngang
 * nhau, không tôn vinh riêng trạng thái đẹp.
 */
const STATUS_CHIP: Record<SessionStatus, string> = {
  planned: "CHƯA PHÁT SÓNG",
  scheduled: "ĐÃ CÓ LỊCH — CHƯA PHÁT",
  live: "ĐANG PHÁT",
  ended: "ĐÃ KẾT THÚC",
  cancelled: "ĐÃ HUỶ",
};

function OnAirLight({ status }: { status: SessionStatus | null }) {
  if (status === "live") {
    return (
      <span className="flex shrink-0 items-center gap-2 rounded-full border border-live/40 bg-live/10 px-3 py-1 text-meta font-bold tracking-[0.12em] text-live">
        <span aria-hidden className="live-dot" />
        ĐANG PHÁT
      </span>
    );
  }
  if (!status) return null;
  return (
    <span className="flex shrink-0 items-center gap-2 rounded-full border border-hairline bg-raised px-3 py-1 text-meta font-bold tracking-[0.12em] text-sec">
      {STATUS_CHIP[status]}
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

/**
 * Tên NGẮN của một phiên cho câu xác nhận: tên phiên, không có tên thì giờ lên
 * sóng. Không bao giờ UUID (cùng luật với ô chọn phiên — gói C8).
 */
export function sessionShortName(s: SessionSummary): string {
  const title = s.title?.trim();
  if (title) return title;
  const when = onAirWhen(s);
  return when ? `Phiên lên sóng ${when}` : "Phiên chưa đặt tên";
}

/** Thời gian bước xác nhận tự huỷ nếu không ai bấm tiếp. */
const CONFIRM_TIMEOUT_MS = 10000;

/**
 * Khoảng CHƯA NHẬN BẤM ngay sau khi bước xác nhận hiện ra (sửa lỗi P1 17/09).
 *
 * Cú bấm đúp vào "Kết thúc phiên" từng kết thúc luôn buổi live: cú đầu mở bước
 * xác nhận, React vẽ lại ngay trong sự kiện, cú thứ hai (≤ 500ms — thời gian
 * nhấp đúp mặc định của Windows) rơi trúng nút mới. Trong 600ms đầu "Kết thúc
 * ngay" bị khoá và "Huỷ" bỏ qua cú bấm, nên cú bấm thứ hai KHÔNG làm gì: bước
 * xác nhận vẫn đứng đó cho người vận hành đọc.
 */
export const CONFIRM_ARM_MS = 600;

/** Nhãn nút bước một — cũng là khuôn đo bề ngang cho nút "Huỷ" ở bước hai. */
const END_LABEL = "Kết thúc phiên";

/**
 * Nút Kết thúc phiên với XÁC NHẬN HAI BƯỚC TẠI CHỖ — không hộp của trình
 * duyệt, không lớp phủ. Bước hai đặt focus vào "Huỷ" (lựa chọn an toàn), nên
 * một cú Enter lỡ tay không kết thúc buổi live.
 *
 * CHỐNG BẤM ĐÚP (sửa lỗi P1 17/09) — hai lớp độc lập:
 *  1. HÌNH HỌC: "Huỷ" đứng CUỐI cụm (mép phải, đúng chỗ nút cũ) và rộng ĐÚNG
 *     bằng nút "Kết thúc phiên" — nhãn bước một nằm tàng hình trong nút để đo
 *     bề ngang, nên không phụ thuộc phông chữ. Cặp nút không bao giờ tách dòng,
 *     vậy "Kết thúc ngay" luôn nằm ngoài dải ngang của nút cũ, dù thanh có gãy
 *     dòng hay không.
 *  2. THỜI GIAN: `CONFIRM_ARM_MS` — xem trên.
 *
 * Câu xác nhận in TÊN phiên; trang gắn `key` theo phiên nên đổi ô chọn phiên
 * sẽ xoá bước xác nhận đang mở (không kết thúc nhầm phiên vừa chọn).
 */
function EndSessionControl({
  onEnd,
  busy,
  sessionName,
}: {
  onEnd: () => void;
  busy?: boolean;
  sessionName: string | null;
}) {
  const [confirming, setConfirming] = useState(false);
  const [armed, setArmed] = useState(false);
  useEffect(() => {
    if (!confirming) return;
    const arm = setTimeout(() => setArmed(true), CONFIRM_ARM_MS);
    const t = setTimeout(() => setConfirming(false), CONFIRM_TIMEOUT_MS);
    return () => {
      clearTimeout(arm);
      clearTimeout(t);
    };
  }, [confirming]);

  if (busy) {
    return (
      <Button variant="danger" disabled>
        Đang kết thúc…
      </Button>
    );
  }
  if (!confirming) {
    return (
      <Button
        variant="danger"
        onClick={() => {
          setArmed(false);
          setConfirming(true);
        }}
        title="Kết thúc phiên đang phát — dữ liệu đã ghi được giữ nguyên"
      >
        {END_LABEL}
      </Button>
    );
  }
  return (
    <div
      role="group"
      aria-label={sessionName ? `Xác nhận kết thúc ${sessionName}` : "Xác nhận kết thúc phiên"}
      className="flex flex-wrap items-center justify-end gap-2"
    >
      <span className="min-w-0 text-meta font-semibold text-crit-ink">
        <span aria-hidden>⚠</span> Kết thúc{" "}
        {sessionName ? (
          <>
            “
            <span className="inline-block max-w-[14rem] truncate align-bottom" title={sessionName}>
              {sessionName}
            </span>
            ”
          </>
        ) : (
          "phiên"
        )}
        ? Khối chưa chạy sẽ không được tính.
      </span>
      {/* Cặp nút KHÔNG tách dòng: "Huỷ" luôn giữ mép phải — chỗ nút cũ. */}
      <span className="flex shrink-0 items-center gap-2">
        <Button
          variant="danger"
          disabled={!armed}
          onClick={() => {
            if (!armed) return;
            setConfirming(false);
            onEnd();
          }}
        >
          Kết thúc ngay
        </Button>
        <Button
          variant="ghost"
          autoFocus
          onClick={() => {
            if (armed) setConfirming(false);
          }}
        >
          <span className="grid">
            <span aria-hidden className="invisible col-start-1 row-start-1">
              {END_LABEL}
            </span>
            <span className="col-start-1 row-start-1 text-center">Huỷ</span>
          </span>
        </Button>
      </span>
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
   * Lỗi vận hành đang cần người xử lý (lệnh Thực hiện trượt, kết thúc phiên
   * thất bại…). `null` = ô trống, không chiếm chỗ.
   */
  alert?: string | null;
  onDismissAlert?: () => void;
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
  alert,
  onDismissAlert,
}: Props) {
  const session = sessions.find((s) => s.session_id === sessionId) ?? null;
  return (
    <header className="shrink-0 rounded-lg border border-hairline bg-surface">
      <div className="flex min-h-bar flex-wrap items-center gap-x-3 gap-y-2 px-3 py-1.5">
        {/* đèn phát sóng — trạng thái phiên là thứ đầu tiên trên thanh */}
        <OnAirLight status={session?.status ?? null} />

        {/* timecode mono — đồng hồ PHIÊN, khác đồng hồ KHỐI ở hero bên dưới.
            Nhảy mỗi giây ⇒ KHÔNG transition, chỉ `tnum` để chữ số không xê. */}
        <span className="flex shrink-0 items-baseline gap-1.5">
          <span className="tnum font-num text-title font-bold leading-none text-ink">{fmtClock(elapsedS)}</span>
          <span className="tnum font-num text-meta text-dim">/ {fmtClock(durationS)}</span>
        </span>

        {/* Nhãn "Phiên đang xem" dành cho trình đọc màn hình: chữ nhìn thấy
            được tốn ~110px và là một lý do thanh gãy dòng ở 1366. Ô chọn in
            TÊN/GIỜ phiên (không UUID); nhãn đầy đủ nằm trong title. */}
        <select
          value={sessionId ?? ""}
          onChange={(e) => onSelectSession(e.target.value)}
          className={`${fieldCls} min-w-0 max-w-[17rem] shrink truncate px-2 py-1 text-body`}
          aria-label="Phiên đang xem"
          title={session ? sessionOptionLabel(session) : undefined}
        >
          {sessions.map((s) => (
            <option key={s.session_id} value={s.session_id}>
              {sessionOptionLabel(s)}
            </option>
          ))}
        </select>

        {/* phiên DỮ LIỆU MẪU phải tự khai trên mọi ảnh chụp (không trộn
            demo/thật); chế độ mock đã có huy hiệu từ ConnectionBadge —
            không in hai huy hiệu trùng nhau. */}
        {connection !== "mock" && session?.is_demo ? <DemoBadge /> : null}

        <ConnectionBadge connection={connection} wsStatus={wsStatus} />

        {/* mode toggle — segmented control.
            `min-h-tap` là sàn WCAG 2.2 SC 2.5.8 (24px); `h-ctl` nâng thực tế
            lên 36px vì đây là control người vận hành bấm khi đang nhìn stream. */}
        <ModeToggle mode={mode} onSetMode={onSetMode} canToggleMode={canToggleMode} />

        {/* Kết thúc phiên: mép phải, sau vạch ngăn — xa công tắc chế độ. */}
        {canEndSession && onEndSession ? (
          <div className="ml-auto flex items-center border-l border-hairline pl-4">
            {/* key theo phiên: đổi phiên thì bước xác nhận đang mở biến mất. */}
            <EndSessionControl
              key={sessionId ?? "none"}
              onEnd={onEndSession}
              busy={endBusy}
              sessionName={session ? sessionShortName(session) : null}
            />
          </div>
        ) : null}
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
