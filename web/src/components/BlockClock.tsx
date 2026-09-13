"use client";

/**
 * "Đồng hồ vận hành" — the control desk's hero row (gói DESK-HOST v2, theo
 * mockup mock_desk.png của spec UI-VISUAL).
 *
 * OPERATOR VIEW ONLY. Block index, assignment (BẬT/TẮT) and the boundary
 * countdown are precisely the facts the blinded /host screen must never see:
 * this component may not be imported from HostView.tsx, and it must never be
 * fed a HostState.
 *
 * ---------------------------------------------------------------------------
 * Bố cục v2 — hai thẻ trên một hàng hero
 * ---------------------------------------------------------------------------
 *   THẺ KHỐI HIỆN TẠI (trái, ~20rem)
 *     nhãn KHỐI HIỆN TẠI · #n · pha → chữ BẬT/TẮT cỡ hiển thị (num-m→num-l,
 *     Space Grotesk) + StatusMark phóng to (kênh HÌNH DẠNG, WCAG 1.4.1)
 *     → MỘT CÂU GIẢI THÍCH ("Hệ thống đang điều khiển việc ghim sản phẩm" /
 *     "Vận hành như thường lệ — nhánh đối chứng") → đếm ngược "Chuyển khối
 *     sau" ở bậc num-l/num-xl (con số được liếc nhiều nhất của phiên) →
 *     thanh tiến trình. Khi khối BẬT: thẻ nhuộm tím G3 + VÒNG SÁNG ON-AIR
 *     (`.onair-ring`) — đèn báo "hệ thống đang điều khiển", chỉ tồn tại khi
 *     BẬT, tắt là viền thường; prefers-reduced-motion biến nó thành viền tĩnh.
 *   THẺ LỊCH BẬT/TẮT (phải, co giãn)
 *     tiêu đề "Lịch BẬT / TẮT — bốc thăm trước giờ lên sóng" + dải khối
 *     (BlockStrip: khối on tím, playhead trắng "đang ở đây", chú giải một
 *     dòng + câu ranh giới làm mù).
 *
 * Hai chỉ số vận hành (người xem, lượt bấm/phút) đã CHUYỂN sang cột KPI của
 * trang desk (SignalTiles v2) — hero chỉ còn đúng một việc: trạng thái khối.
 *
 * ---------------------------------------------------------------------------
 * CHUYỂN ĐỘNG (kế thừa gói UI-3 — luật không đổi)
 * ---------------------------------------------------------------------------
 *   ĐẾM NGƯỢC   KHÔNG hiệu ứng. Con số nhảy mỗi giây; chỉ `tabular-nums` và
 *               đổi mực sang hổ phách khi sắp tới ranh giới (tĩnh, một lần).
 *   CHUYỂN KHỐI hiệu ứng "to" DUY NHẤT của phiên: mặt thẻ chuyển màu
 *               (`transition-colors`, 280ms), chữ trạng thái mới quét
 *               (`.motion-switch`), cả thẻ nháy nền MỘT lần (Flash) — khoảnh
 *               khắc S2 "đổi ca" của spec, thấy được từ 2 mét.
 *   ON-AIR RING ngoại lệ lặp thứ hai của app (sau đèn ĐANG PHÁT): vòng conic
 *               quét quanh thẻ khi và chỉ khi hệ thống đang điều khiển. Nó là
 *               đèn báo, không phải trang trí — sự có/không của nó là tín hiệu.
 */

import { fmtMinSec } from "@/lib/format";
import { useAnnounceOnChange } from "@/lib/motion";
import type { Assignment, BlockInfo, CurrentBlock, Phase } from "@/lib/types";

import BlockStrip from "./BlockStrip";
import Card from "./ui/Card";
import Flash from "./ui/Flash";
import SectionTitle from "./ui/SectionTitle";
import StatusMark, { STATUS_TEXT, type StatusShape } from "./ui/StatusMark";

/** Ngưỡng "sắp đổi khối" — đủ sớm để đặt tay lên phím, chưa sớm tới mức nhờn. */
const BOUNDARY_WARN_S = 30;

const PHASE_LABEL: Record<Phase, string> = {
  early: "đầu phiên",
  mid: "giữa phiên",
  late: "cuối phiên",
};

/**
 * Chip plane + ink — the COLOUR channel, always paired with shape and word.
 * v2: ba trạng thái là ba MẶT THẺ khác nhau (tím điện / trung tính / sọc trôi)
 * để đọc được từ xa, không chỉ ba chip nhỏ.
 */
const CHIP: Record<StatusShape, string> = {
  on: "border-s7/60 bg-s7/15 text-on-ink",
  off: "border-hairline bg-axis text-off-ink",
  drift: "hatch-washout border-hairline text-drift-ink",
};

/** Progress-bar fill — a graphic, so 3:1 against the track is the bar to clear. */
const BAR_FILL: Record<StatusShape, string> = {
  on: "bg-s7",
  off: "bg-sec",
  drift: "bg-dim",
};

/**
 * MỘT CÂU GIẢI THÍCH dưới chữ trạng thái — trả lời thẳng "khối BẬT/TẮT nghĩa
 * là gì với tôi NGAY BÂY GIỜ" (yêu cầu hero của spec UX-FLOW e2).
 */
const EXPLAIN: Record<StatusShape, string> = {
  on: "Hệ thống đang điều khiển việc ghim sản phẩm",
  off: "Vận hành như thường lệ — nhánh đối chứng để so sánh",
  drift: "Khoảng chuyển tiếp — không tính vào kết quả",
};

/** What the desk knows about the block it is in right now. */
export interface CurrentBlockView {
  index: number;
  assignment: Assignment | null;
  washout: boolean;
  phase: Phase | null;
  remainingS: number | null;
  /** Fraction of the block already elapsed, or null when its length is unknown. */
  progress: number | null;
}

/**
 * Derive the current block from the schedule, falling back to the server's
 * snapshot. The schedule is preferred because the local 1 s clock ticks between
 * the 5 s polls, so the countdown stays smooth; the snapshot keeps the block
 * readable in the seconds before the schedule lands.
 */
export function deriveCurrentBlock(
  blocks: BlockInfo[],
  currentBlock: CurrentBlock | null,
  elapsedS: number,
): CurrentBlockView | null {
  const local = blocks.find((b) => elapsedS >= b.start_offset_s && elapsedS < b.end_offset_s);
  if (local) {
    const span = local.end_offset_s - local.start_offset_s;
    return {
      index: local.block_index,
      assignment: local.assignment,
      washout: local.is_washout,
      phase: local.phase,
      remainingS: Math.max(0, local.end_offset_s - elapsedS),
      progress:
        span > 0 ? Math.min(1, Math.max(0, (elapsedS - local.start_offset_s) / span)) : null,
    };
  }
  if (currentBlock) {
    // The snapshot carries the remainder but not the block length, so the
    // progress bar stays hidden rather than inventing a denominator.
    return {
      index: currentBlock.index,
      assignment: currentBlock.assignment,
      washout: currentBlock.is_washout,
      phase: currentBlock.phase,
      remainingS: Math.max(0, currentBlock.seconds_remaining),
      progress: null,
    };
  }
  return null;
}

export function blockShape(view: CurrentBlockView): StatusShape {
  return view.washout ? "drift" : view.assignment === "ON" ? "on" : "off";
}

interface Props {
  blocks: BlockInfo[];
  currentBlock: CurrentBlock | null;
  elapsedS: number;
  durationS: number;
  /** Name of the product pinned right now, for the strip header's meta slot. */
  pinnedName: string | null;
  /**
   * Phiên QUAN SÁT — ma trận tín hiệu của máy chủ nói `schedule` là missing
   * (gói UI-KOL). Khác hẳn "chưa tải xong lịch": ở đây lịch KHÔNG TỒN TẠI, nên
   * "NGOÀI KHỐI · chưa tới khối đầu hoặc đã qua khối cuối" là một câu sai —
   * nó ngụ ý có khối để ở ngoài. Mặc định `false`: chưa biết thì giữ nguyên
   * cách nói cũ, không đoán.
   */
  observational?: boolean;
  /**
   * Phiên ĐÃ KẾT THÚC (trạng thái từ danh sách phiên — thông tin operator,
   * không đụng làm mù): ngoài lịch thì nói "HẾT LỊCH · phiên đã kết thúc"
   * thay vì câu "chưa tới khối đầu…" mơ hồ, và rút cụm đếm ngược (không còn
   * ranh giới nào để đếm — in "—" 56px chỉ thêm nhiễu).
   */
  sessionEnded?: boolean;
}

export default function BlockClock({
  blocks,
  currentBlock,
  elapsedS,
  durationS,
  pinnedName,
  observational = false,
  sessionEnded = false,
}: Props) {
  const view = deriveCurrentBlock(blocks, currentBlock, elapsedS);
  const shape = view ? blockShape(view) : null;
  const pct = view?.progress != null ? Math.round(view.progress * 100) : null;
  const nearBoundary =
    view?.remainingS != null && view.remainingS > 0 && view.remainingS <= BOUNDARY_WARN_S;

  // Washout keeps its own word in caps: "trôi" set at display size next to
  // BẬT/TẮT would read as a different KIND of label rather than a third state.
  /** Không có lịch VÀ máy chủ đã xác nhận là phiên quan sát — không phải đang tải. */
  const noSchedule = observational && !view;
  /** Phiên đã kết thúc và đã ra ngoài lịch: mọi khối đã chạy xong. */
  const ranOut = sessionEnded && !view && !noSchedule;
  const chipWord = view && shape ? (view.washout ? "TRÔI" : STATUS_TEXT[shape]) : "NGOÀI KHỐI";
  const heroWord = noSchedule ? "QUAN SÁT" : ranOut ? "HẾT LỊCH" : chipWord;
  const heroSub = noSchedule
    ? "Buổi live gốc không có lịch gán ngẫu nhiên — số liệu chỉ mô tả, không có tác động nhân quả"
    : ranOut
      ? "Phiên đã kết thúc — mọi khối đã chạy xong; mở Báo cáo phiên để xem kết luận"
      : view && shape
        ? EXPLAIN[shape]
        : "Chưa tới khối đầu hoặc đã qua khối cuối";
  const heroMeta = view
    ? `Khối hiện tại · #${view.index + 1}/${blocks.length || "?"}${
        view.phase ? ` · ${PHASE_LABEL[view.phase]}` : ""
      }`
    : "Khối hiện tại";

  /**
   * Danh tính của trạng thái hiện tại. Đổi khoá ⇒ (a) chữ trạng thái được gắn
   * lại nên `.motion-switch` chạy lại, (b) vùng aria-live phát đúng MỘT câu,
   * (c) cả thẻ nháy nền một lần (Flash).
   */
  const switchKey = view ? `${view.index}:${shape}` : "none";
  // Câu thông báo cố ý KHÔNG chứa đồng hồ đếm ngược: nó phải đứng yên giữa hai
  // lần chuyển khối, nếu không vùng aria-live sẽ đọc lại mỗi giây.
  const announcement = useAnnounceOnChange(
    switchKey,
    view
      ? view.washout
        ? `Đã vào khoảng trôi trước khối ${view.index + 2}.`
        : `Khối ${view.index + 1} bắt đầu, trạng thái ${chipWord}.`
      : noSchedule
        ? "Phiên quan sát — không có lịch khối thí nghiệm."
        : "Phiên đã ra ngoài khung khối thí nghiệm.",
  );

  const onAir = shape === "on";

  return (
    <section
      aria-label="Đồng hồ vận hành"
      className="grid shrink-0 grid-cols-1 gap-3 xl:grid-cols-[minmax(17rem,21rem)_minmax(0,1fr)]"
    >
      {/* One screen-reader sentence up front — the display figure below is a
          role="timer", which does not announce on every tick by design. */}
      <p className="sr-only">
        {view
          ? `${view.washout ? "Đang trong khoảng trôi" : `Khối số ${view.index + 1} đang ${chipWord}`}${
              view.remainingS != null
                ? `, còn ${fmtMinSec(view.remainingS)} đến ranh giới khối kế`
                : ""
            }.`
          : noSchedule
            ? "Phiên quan sát — không có lịch khối thí nghiệm."
            : "Phiên đang ở ngoài khung khối thí nghiệm."}
      </p>

      {/* Vùng thông báo LỊCH SỰ — mỗi lần chuyển khối phát đúng một câu. Câu
          trên (không live) mô tả trạng thái tĩnh; vùng này chỉ nói lúc ĐỔI. */}
      <p className="sr-only" aria-live="polite">
        {announcement}
      </p>

      {/* ---- THẺ KHỐI HIỆN TẠI — mặt thẻ là kênh MÀU, chuyển màu 280ms là
              nửa crossfade của khoảnh khắc đổi ca (S2). Vòng on-air chỉ khi
              BẬT: chính sự có mặt của nó là tín hiệu. ---- */}
      <div
        className={`relative rounded-lg border p-4 transition-colors duration-switch ease-emphasized ${
          shape ? CHIP[shape] : "border-hairline bg-surface text-sec"
        } ${onAir ? "onair-ring shadow-[0_10px_50px_-18px_rgba(139,123,255,0.6)]" : ""}`}
      >
        {/* nháy nền MỘT lần đúng khoảnh khắc chuyển khối — không đổi bố cục */}
        <Flash value={switchKey} className="inset-0 rounded-lg" />

        <div className="relative">
          <div className="text-label uppercase text-dim">{heroMeta}</div>

          {/* …và nửa "wipe": khoá theo trạng thái nên chỉ chạy đúng lúc đổi. */}
          <span key={switchKey} className="motion-switch mt-2 flex items-center gap-3">
            {shape ? <StatusMark shape={shape} size={26} inherit /> : null}
            <span className="min-w-0">
              {/* Chữ trạng thái là CHỮ (BẬT/TẮT/TRÔI…), không phải số — font
                  display, không rơi vào JetBrains Mono của bậc num-* (v2).
                  num-m (40px) ≈ cỡ 44px của mockup; giữ hero đủ thấp để desk
                  1920×1080 không cuộn. */}
              <span className="block font-display text-num-m leading-none tracking-tight">
                {heroWord}
              </span>
            </span>
          </span>
          <p className="mt-2 max-w-[26rem] text-body leading-snug text-sec">{heroSub}</p>

          {/* đếm ngược tới ranh giới — con số vận hành liếc nhiều nhất.
              KHÔNG transition, KHÔNG animation: chỉ đổi mực khi sắp tới ranh
              giới. Phiên quan sát không có ranh giới nào để đếm: cả cụm rút đi. */}
          <div
            className={`mt-2.5 border-t border-hairline pt-2.5 ${
              noSchedule || ranOut ? "hidden" : ""
            }`}
          >
            <div className="text-label uppercase text-dim">Chuyển khối sau</div>
            {/* num-m → num-l ở màn thiết kế: 56px mono vẫn đọc được từ 2m,
                và giữ tổng chiều cao hero ≤ ~300px để desk 1920×1080 KHÔNG
                cuộn (ràng buộc f4 của spec — đo lại bằng ảnh chụp). */}
            <div
              role="timer"
              aria-label="Thời gian còn lại của khối hiện tại"
              className={`mt-1 text-num-m leading-none transition-colors duration-medium2 ease-emphasized xl:text-num-l ${
                nearBoundary ? "text-warn-ink" : "text-ink"
              }`}
            >
              {view?.remainingS != null ? fmtMinSec(view.remainingS) : "—"}
            </div>

            {/* tiến trình trong khối: cùng thông tin với đếm ngược, dạng hình.
                Ô chữ bên phải là SLOT CỐ ĐỊNH: bình thường in "đã qua %", vào
                30 giây cuối đổi thành cảnh báo ranh giới (motion-enter chạy
                MỘT lần rồi đứng yên — không nhấp nháy, không xê bố cục). */}
            <div className="mt-2 flex min-h-tap items-center gap-3">
              <div
                role="progressbar"
                aria-label="Tiến trình khối hiện tại"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={pct ?? 0}
                className="h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-axis"
              >
                {/* `scaleX` chứ không phải `width`: transform chạy trên GPU và
                    không buộc trình duyệt bố trí lại từng frame. 1000ms LINEAR
                    khớp đúng nhịp tick 1 giây, nên thanh trôi liền không giật. */}
                {pct != null && shape ? (
                  <div
                    className={`h-full w-full origin-left transition-transform duration-tick ease-linear ${BAR_FILL[shape]}`}
                    style={{ transform: `scaleX(${pct / 100})` }}
                  />
                ) : null}
              </div>
              {nearBoundary ? (
                <span className="motion-enter inline-flex shrink-0 items-center gap-1.5 rounded-full border border-warn/60 bg-warn/10 px-2.5 py-0.5 text-meta font-semibold text-warn-ink">
                  <span aria-hidden>⚠</span> Sắp đổi khối — chuẩn bị thao tác
                </span>
              ) : (
                <span className="tnum shrink-0 text-meta text-dim">
                  {pct != null ? `đã qua ${pct}%` : "chưa rõ độ dài khối"}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ---- THẺ LỊCH BẬT/TẮT — dải khối + chú giải + câu ranh giới làm mù
              (nằm trong BlockStrip). Phiên quan sát không có khối nào để vẽ,
              và thẻ trạng thái đã nói rõ lý do — dải rỗng chỉ lặp lại câu đó. */}
      {noSchedule ? null : (
        <Card as="div" padding="sm" className="flex min-w-0 flex-col">
          <SectionTitle
            className="mb-2"
            meta={
              <>
                Đang ghim: <span className="font-semibold text-ink">{pinnedName ?? "—"}</span>
              </>
            }
          >
            Lịch BẬT / TẮT — bốc thăm trước giờ lên sóng
          </SectionTitle>
          {/* Dải khối canh giữa vùng còn lại của thẻ — khối cao (tall) để đọc
              được chữ BẬT/TẮT trong từng ô từ xa, như mockup. */}
          <div className="flex min-h-0 flex-1 flex-col justify-center">
            <BlockStrip blocks={blocks} durationS={durationS} positionS={elapsedS} tall />
          </div>
        </Card>
      )}
    </section>
  );
}
