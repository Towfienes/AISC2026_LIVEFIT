"use client";

/**
 * Switchback block timeline — OPERATOR VIEW ONLY (the host screen is blinded
 * and must never render this component). Shows ON/OFF blocks, washout hatch,
 * the current position marker and — new in gói UI-2 — a ring around the block
 * the session is in right now.
 *
 * Four redundant channels per block, so the state survives colour blindness, a
 * washed-out projector and a 1366 px laptop alike:
 *   1. the Vietnamese word (BẬT / TẮT) printed inside the block;
 *   2. the fill (violet / neutral / 45° hatch);
 *   3. the shape convention in the legend (chấm đặc / vòng rỗng / nửa đặc);
 *   4. a text summary for screen readers, since the strip itself is a graphic.
 *
 * Responsive notes: the strip is percentage-scaled so it never overflows, but
 * the word inside a block disappears below ~44 px of block width — the legend,
 * the ring and the `title` tooltip are what carry the meaning there. The legend
 * WRAPS instead of truncating: the operator-only warning used to be cut to
 * "Chỉ hiển thị cho bàn điều…" on a 1366 px screen, which is exactly the line
 * that must never be half-read.
 *
 * ---------------------------------------------------------------------------
 * CHUYỂN ĐỘNG (gói UI-3)
 * ---------------------------------------------------------------------------
 * Playhead là thứ DUY NHẤT ở đây chuyển động liên tục, và nó chạy bằng
 * `transform: translateX` trên một lớp phủ rộng bằng cả dải, với
 * `transition-transform 1000ms linear` khớp đúng nhịp tick 1 giây. Lý do không
 * animate `left`: `left` buộc trình duyệt bố trí lại (layout) mỗi frame, ngay
 * bên cạnh một biểu đồ đang vẽ; `transform` thì tổng hợp trên GPU.
 *
 * Khi phiên bước sang khối khác, ô khối hiện tại nháy nền một lần (≤ 12% alpha,
 * 520ms) — cùng khoảnh khắc với hiệu ứng chuyển BẬT/TẮT trên đồng hồ khối, nên
 * hai chỗ kể cùng một câu chuyện thay vì hai sự kiện rời rạc.
 */

import { fmtElapsed } from "@/lib/format";
import { BLOCK_OFF_COLOR, BLOCK_ON_COLOR } from "@/lib/palette";
import { BlockInfo } from "@/lib/types";

import Term from "./Term";
import Flash from "./ui/Flash";
import StatusMark, { STATUS_TEXT, type StatusShape } from "./ui/StatusMark";

interface Props {
  blocks: BlockInfo[];
  /** Total planned duration in seconds (defines the strip's scale). */
  durationS: number;
  /** Current position in seconds (marker); null hides the marker. */
  positionS: number | null;
  /**
   * Dải cao 56px cho hàng hero của desk v2 (mockup mock_desk) — chữ BẬT/TẮT
   * trong ô đọc được từ xa. Mặc định giữ 36px cho các chỗ chật (replay…).
   */
  tall?: boolean;
}

function shapeOf(b: BlockInfo): StatusShape {
  return b.is_washout ? "drift" : b.assignment === "ON" ? "on" : "off";
}

export default function BlockStrip({ blocks, durationS, positionS, tall = false }: Props) {
  if (durationS <= 0 || blocks.length === 0) {
    // Never a blank bar: say why it is empty instead of showing a grey slab.
    return (
      <div className="flex h-9 items-center rounded border border-hairline bg-surface px-3 text-meta text-dim">
        Chưa nhận được lịch khối cho phiên này.
      </div>
    );
  }
  const pctNum = (s: number) => Math.min(100, Math.max(0, (s / durationS) * 100));
  const pct = (s: number) => `${pctNum(s)}%`;

  const current =
    positionS == null
      ? null
      : (blocks.find((b) => positionS >= b.start_offset_s && positionS < b.end_offset_s) ?? null);

  const nOn = blocks.filter((b) => !b.is_washout && b.assignment === "ON").length;
  const nOff = blocks.filter((b) => !b.is_washout && b.assignment === "OFF").length;

  return (
    <div>
      <div
        role="img"
        aria-label={
          `Dải khối switchback: ${blocks.length} khối, ${nOn} khối BẬT, ${nOff} khối TẮT.` +
          (current
            ? ` Vị trí hiện tại: khối ${current.block_index + 1}, ${STATUS_TEXT[shapeOf(current)]}.`
            : "")
        }
        className={`relative w-full overflow-hidden rounded border border-edge bg-surface ${
          tall ? "h-16" : "h-9"
        }`}
      >
        {blocks.map((b) => {
          const left = pct(b.start_offset_s);
          const width = pct(b.end_offset_s - b.start_offset_s);
          const isOn = b.assignment === "ON";
          const shape = shapeOf(b);
          const isCurrent = current?.block_index === b.block_index;
          // Khối ĐÃ QUA mờ đi (mockup): mắt rơi vào hiện tại và phần còn lại
          // của lịch. Chỉ là kênh phụ — chữ và vị trí playhead vẫn đầy đủ.
          const isPast = !isCurrent && positionS !== null && b.end_offset_s <= positionS;
          return (
            <div
              key={b.block_index}
              aria-hidden
              className={`absolute top-0 flex h-full items-center justify-center overflow-hidden text-meta font-semibold ${
                b.is_washout ? "hatch-washout" : ""
              } ${isCurrent ? "ring-2 ring-inset ring-ink" : ""} ${isPast ? "opacity-50" : ""}`}
              style={{
                left,
                width: `calc(${width} - 2px)`, // 2px surface gap between blocks
                background: b.is_washout ? undefined : isOn ? BLOCK_ON_COLOR : BLOCK_OFF_COLOR,
                // v2: #a6acbb on the hatch (7.4:1 on s3), #0c0d12 on violet
                // (5.9:1), #c3c5cc on the neutral fill (6.1:1) — all clear AA.
                color: b.is_washout ? "#a6acbb" : isOn ? "#0c0d12" : "#c3c5cc",
              }}
              title={`Khối ${b.block_index + 1} · ${STATUS_TEXT[shape]} · ${fmtElapsed(
                b.start_offset_s,
              )}–${fmtElapsed(b.end_offset_s)}`}
            >
              {/* Nháy MỘT lần đúng lúc phiên bước vào khối này. */}
              {isCurrent ? <Flash value={b.block_index} /> : null}
              {b.is_washout ? "" : STATUS_TEXT[shape]}
            </div>
          );
        })}
        {/* Playhead. Lớp phủ rộng bằng cả dải rồi dịch theo % CHÍNH NÓ — đó là
            cách duy nhất để một phần tử rộng 4px đi được quãng đường tính theo
            % của dải mà vẫn chỉ dùng `transform`. */}
        {positionS != null && (
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 transition-transform duration-tick ease-linear will-change-transform"
            style={{ transform: `translate3d(${pctNum(positionS)}%, 0, 0)` }}
          >
            <div className="absolute left-0 top-0 h-full w-1 -translate-x-1/2 rounded-full bg-ink" />
          </div>
        )}
      </div>

      {/* Chú giải: ký hiệu hình dạng đi trước ô màu — chấm đặc / vòng rỗng /
          nửa đặc phân biệt được ba trạng thái ngay cả khi không thấy màu.
          `flex-wrap`: xuống dòng chứ không cắt chữ trên màn hình hẹp. */}
      <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 px-0.5 text-meta text-dim">
        <span className="flex items-center gap-1.5">
          <StatusMark shape="on" />
          <span
            className="inline-block h-2.5 w-3 rounded-sm"
            style={{ background: BLOCK_ON_COLOR }}
          />
          <Term tip="Hệ thống điều khiển việc ghim sản phẩm trong khối này.">Khối BẬT</Term>
        </span>
        <span className="flex items-center gap-1.5">
          <StatusMark shape="off" />
          <span
            className="inline-block h-2.5 w-3 rounded-sm border border-edge"
            style={{ background: BLOCK_OFF_COLOR }}
          />
          <Term tip="Đội vận hành làm như thường lệ (nhánh đối chứng).">Khối TẮT</Term>
        </span>
        <span className="flex items-center gap-1.5">
          <StatusMark shape="drift" />
          <span className="hatch-washout inline-block h-2.5 w-3 rounded-sm border border-edge" />
          <Term tip="Phút chuyển tiếp giữa hai khối — không tính vào kết quả đo.">
            Khoảng trôi
          </Term>
        </span>
        {/* Chưa có vị trí (bước bốc thăm của wizard — chưa lên sóng) thì
            không có vạch nào để chú giải. */}
        {positionS != null ? (
          <span className="flex items-center gap-1.5">
            <span aria-hidden className="inline-block h-3 w-1 rounded-full bg-ink" />
            Vị trí hiện tại
          </span>
        ) : null}
        {/* Câu cảnh báo ranh giới làm mù: `ml-auto` để nằm cùng dòng khi còn
            chỗ, và KHÔNG `truncate` — đây là dòng không bao giờ được đọc dở. */}
        <span className="ml-auto">Chỉ hiện trên bàn trợ live — màn người dẫn không thấy khối</span>
      </div>
    </div>
  );
}
