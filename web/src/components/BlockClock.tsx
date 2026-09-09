"use client";

/**
 * "Đồng hồ vận hành" — the control desk's hero block (gói UI-2).
 *
 * OPERATOR VIEW ONLY. Block index, assignment (BẬT/TẮT) and the boundary
 * countdown are precisely the facts the blinded /host screen must never see:
 * this component may not be imported from HostView.tsx, and it must never be
 * fed a HostState.
 *
 * ---------------------------------------------------------------------------
 * Why it exists
 * ---------------------------------------------------------------------------
 * The audit of the running desk found the single most-glanced fact of a live
 * session — "is the current block BẬT or TẮT, and how long until the boundary"
 * — rendered at 11 px inside a paragraph of hint text, at the same weight and
 * the same white as the annotation around it. Two operators reported missing a
 * boundary. This block now owns the top of the screen:
 *
 *   status chip  num-l (56 px) word, on a tinted plane, behind a scaled
 *                `.status-mark` shape — so BẬT / TẮT / TRÔI separate by SHAPE,
 *                FILL and WORD, never by hue alone (WCAG 1.4.1);
 *   countdown    num-xl (72 px, tabular) inside role="timer";
 *   progress      how far through the current block we already are;
 *   vitals       viewers and clicks/min on num-s, each with a real label.
 *
 * Everything steps one notch down the scale below `xl` (1280 px) so a
 * 1366x768 laptop keeps the whole row on one line instead of clipping it.
 *
 * ---------------------------------------------------------------------------
 * CHUYỂN ĐỘNG (gói UI-3)
 * ---------------------------------------------------------------------------
 * Ba mức, đúng theo mức độ quan trọng của sự kiện:
 *
 *   ĐẾM NGƯỢC   KHÔNG hiệu ứng. Con số nhảy mỗi giây; gắn transition vào nó là
 *               làm nó không bao giờ đứng yên đủ lâu để đọc. Chỉ `tabular-nums`
 *               để các chữ số không xê dịch bề ngang.
 *   KPI         count-up 350ms ease-out, và chỉ khi lệch ≥ 5% hoặc đổi số chữ
 *               số; kèm nháy nền xác nhận. Thay đổi nhỏ thì gán thẳng.
 *   CHUYỂN KHỐI hiệu ứng "to" DUY NHẤT của phiên: mặt chip chuyển màu
 *               (`transition-colors`, 280ms) trong khi chữ trạng thái mới quét
 *               từ trái sang (`.motion-switch`) — hai nửa của một crossfade.
 *
 * Cảnh báo sắp tới ranh giới (≤ 30s) là TÍN HIỆU TĨNH: đổi mực sang hổ phách
 * và hiện một chip, vào một lần rồi đứng yên. Nhấp nháy liên tục ở đây sẽ đúng
 * lúc người vận hành cần tập trung nhất.
 */

import { fmtMinSec, fmtNumber } from "@/lib/format";
import { useAnnounceOnChange, useCountUp } from "@/lib/motion";
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

/** Chip plane + ink — the COLOUR channel, always paired with shape and word. */
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

/**
 * One labelled operating figure. Label first, then the number — never a bare digit.
 *
 * Con số chạy qua `useCountUp`: nhảy bậc thì tween 350ms ease-out để mắt nối
 * được giá trị cũ với giá trị mới, nhích một hai đơn vị thì gán thẳng. `Flash`
 * phủ lên trên xác nhận "vừa có số mới" mà không đụng tới bố cục.
 */
function Vital({
  label,
  value,
  hint,
}: {
  label: string;
  /** `null` = chưa có số liệu; hiện "—" chứ không đếm từ 0 lên. */
  value: number | null;
  hint: string;
}) {
  const shown = useCountUp(value);
  return (
    <div className="min-w-[7.5rem]">
      <div className="text-label uppercase text-dim">{label}</div>
      <span className="relative inline-flex">
        <Flash value={value} className="-inset-x-2 -inset-y-1" />
        <span className="relative text-num-s leading-none text-ink">
          {shown == null ? "—" : fmtNumber(Math.round(shown))}
        </span>
      </span>
      <div className="mt-1 text-meta text-dim">{hint}</div>
    </div>
  );
}

interface Props {
  blocks: BlockInfo[];
  currentBlock: CurrentBlock | null;
  elapsedS: number;
  durationS: number;
  viewers: number;
  /** Clicks in the last 60 s; null while no tick has landed yet. */
  clicksPerMin: number | null;
  /** Name of the product pinned right now, for the header's meta slot. */
  pinnedName: string | null;
}

export default function BlockClock({
  blocks,
  currentBlock,
  elapsedS,
  durationS,
  viewers,
  clicksPerMin,
  pinnedName,
}: Props) {
  const view = deriveCurrentBlock(blocks, currentBlock, elapsedS);
  const shape = view ? blockShape(view) : null;
  const pct = view?.progress != null ? Math.round(view.progress * 100) : null;
  const nearBoundary =
    view?.remainingS != null && view.remainingS > 0 && view.remainingS <= BOUNDARY_WARN_S;

  // Washout keeps its own word in caps: "trôi" set at 56px next to BẬT/TẮT
  // would read as a different KIND of label rather than a third state.
  const chipWord = !view || !shape ? "NGOÀI KHỐI" : view.washout ? "TRÔI" : STATUS_TEXT[shape];
  const chipSub = view
    ? view.washout
      ? "Khoảng chuyển tiếp — không tính vào kết quả"
      : `Khối #${view.index + 1}${view.phase ? ` · ${PHASE_LABEL[view.phase]}` : ""}`
    : "Chưa tới khối đầu hoặc đã qua khối cuối";

  /**
   * Danh tính của trạng thái hiện tại. Đổi khoá ⇒ (a) chữ trạng thái được gắn
   * lại nên `.motion-switch` chạy lại, (b) vùng aria-live phát đúng MỘT câu.
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
      : "Phiên đã ra ngoài khung khối thí nghiệm.",
  );

  return (
    <Card as="section" padding="sm" className="shrink-0" aria-label="Đồng hồ vận hành">
      <SectionTitle
        className="mb-2"
        meta={
          <>
            Đang ghim: <span className="font-semibold text-ink">{pinnedName ?? "—"}</span>
          </>
        }
      >
        Khối hiện tại
      </SectionTitle>

      {/* One screen-reader sentence up front — the 72px figure below is a
          role="timer", which does not announce on every tick by design. */}
      <p className="sr-only">
        {view
          ? `${view.washout ? "Đang trong khoảng trôi" : `Khối số ${view.index + 1} đang ${chipWord}`}${
              view.remainingS != null
                ? `, còn ${fmtMinSec(view.remainingS)} đến ranh giới khối kế`
                : ""
            }.`
          : "Phiên đang ở ngoài khung khối thí nghiệm."}
      </p>

      {/* Vùng thông báo LỊCH SỰ — mỗi lần chuyển khối phát đúng một câu. Câu
          trên (không live) mô tả trạng thái tĩnh; vùng này chỉ nói lúc ĐỔI. */}
      <p className="sr-only" aria-live="polite">
        {announcement}
      </p>

      <div className="flex flex-wrap items-end gap-x-6 gap-y-4">
        {/* trạng thái: hình dạng + nền + CHỮ, ba kênh độc lập với màu.
            Mặt chip chuyển màu trong 280ms — nửa "crossfade" của chuyển khối. */}
        <div
          className={`flex items-center gap-3 rounded-lg border px-4 py-2 transition-colors duration-switch ease-emphasized ${
            shape ? CHIP[shape] : "border-hairline bg-raised text-sec"
          }`}
        >
          {/* …và nửa "wipe": khoá theo trạng thái nên chỉ chạy đúng lúc đổi. */}
          <span key={switchKey} className="motion-switch flex items-center gap-3">
            {shape ? <StatusMark shape={shape} size={26} inherit /> : null}
            <span className="min-w-0">
              <span className="block text-num-m leading-none tracking-tight xl:text-num-l">
                {chipWord}
              </span>
              <span className="mt-1.5 block text-body text-sec">{chipSub}</span>
            </span>
          </span>
        </div>

        {/* đếm ngược tới ranh giới — con số vận hành liếc nhiều nhất.
            KHÔNG transition, KHÔNG animation: chỉ đổi mực khi sắp tới ranh giới. */}
        <div className="min-w-[9rem]">
          <div className="text-label uppercase text-dim">Còn đến ranh giới khối</div>
          <div
            role="timer"
            aria-label="Thời gian còn lại của khối hiện tại"
            className={`text-num-l leading-none transition-colors duration-medium2 ease-emphasized xl:text-num-xl ${
              nearBoundary ? "text-warn-ink" : "text-ink"
            }`}
          >
            {view?.remainingS != null ? fmtMinSec(view.remainingS) : "—"}
          </div>
          {/* Cảnh báo ranh giới: vào MỘT lần (180ms) rồi đứng yên. Không nhấp
              nháy — đây đúng là lúc người vận hành cần tập trung nhất. */}
          <div className="mt-1 min-h-tap">
            {nearBoundary ? (
              <span className="motion-enter inline-flex items-center gap-1.5 rounded-full border border-warn/60 bg-warn/10 px-2.5 py-0.5 text-meta font-semibold text-warn-ink">
                <span aria-hidden>⚠</span> Sắp đổi khối — chuẩn bị thao tác
              </span>
            ) : null}
          </div>
        </div>

        {/* nhịp thị trường: hai chỉ số vận hành, mỗi cái một nhãn thật */}
        {/* `items-end` + một dòng hint cho CẢ HAI: hai con số nằm đúng một
            đường ngang, nếu không cái có chú thích sẽ bị đẩy lệch lên. */}
        <div className="ml-auto flex flex-wrap items-end gap-x-6 gap-y-3">
          <Vital label="Người xem" value={viewers} hint="ngay lúc này" />
          <Vital label="Lượt bấm / phút" value={clicksPerMin} hint="60 giây gần nhất" />
        </div>
      </div>

      {/* tiến trình trong khối: cùng một thông tin với đếm ngược, dạng hình */}
      <div className="mt-3 flex items-center gap-3">
        <div
          role="progressbar"
          aria-label="Tiến trình khối hiện tại"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={pct ?? 0}
          className="h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-axis"
        >
          {/* `scaleX` chứ không phải `width`: transform chạy trên GPU và không
              buộc trình duyệt bố trí lại từng frame. 1000ms LINEAR khớp đúng
              nhịp tick 1 giây, nên thanh trôi liền chứ không giật từng nấc. */}
          {pct != null && shape ? (
            <div
              className={`h-full w-full origin-left transition-transform duration-tick ease-linear ${BAR_FILL[shape]}`}
              style={{ transform: `scaleX(${pct / 100})` }}
            />
          ) : null}
        </div>
        <span className="tnum shrink-0 text-meta text-dim">
          {pct != null ? `đã qua ${pct}% khối` : "chưa rõ độ dài khối"}
        </span>
      </div>

      <div className="mt-3">
        <BlockStrip blocks={blocks} durationS={durationS} positionS={elapsedS} />
      </div>
    </Card>
  );
}
