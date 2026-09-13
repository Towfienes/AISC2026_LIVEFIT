"use client";

/**
 * Thẻ "Hành động gợi ý" (gói DESK-HOST v2 — hierarchy theo mockup mock_desk).
 *
 * E2-04 display rule (hard project rule):
 * - source="forecast"   → gray badge "Ước lượng dự báo". NEVER render any
 *   interval, even if ci fields somehow arrive populated (api.sanitizeCard
 *   already strips them; this component guards again).
 * - source="experiment" → green badge "Tác động đo được · KTC 95%" and the
 *   [ci_low, ci_high] interval.
 *
 * HIERARCHY v2: thẻ hạng 1 (`emphasized`) là VIỆC CẦN LÀM NGAY — viền gradient
 * tím-xanh TĨNH (`.border-gradient-brand`, không xoay: chuyển động xoay chỉ
 * dành cho vòng on-air của thẻ khối), con số ước lượng ở bậc hiển thị kèm nhãn
 * nguồn ("DỰ BÁO LƯỢT BẤM" / "TÁC ĐỘNG ĐO ĐƯỢC"), lý do một dòng đọc được, nút
 * chính "Ghim ngay". Các thẻ sau nhỏ hơn rõ rệt — hierarchy bằng kích thước số.
 *
 * Mode behavior:
 * - "auto"    → execute/skip disabled, đếm ngược "tự chạy sau m:ss" màu hổ
 *   phách (hệ thống sẽ tự thực hiện — người vận hành chỉ cần can thiệp).
 * - "suggest" → active "Thực hiện" and "Bỏ qua" buttons.
 *
 * "Thực hiện" is THE primary action of the desk, so it takes the `md` button
 * (36px tall) rather than the dense `sm` one: the operator hits it while
 * watching the stream, not while looking at the mouse.
 *
 * ---------------------------------------------------------------------------
 * CHUYỂN ĐỘNG (gói UI-3 — luật không đổi)
 * ---------------------------------------------------------------------------
 * Hai hiệu ứng, cả hai đều chạy đúng một lần:
 *
 *   VÀO       thẻ mới fade + trượt lên 6px trong 180ms. Chạy khi React GẮN thẻ,
 *             mà thẻ chỉ được gắn khi `card_id` chưa từng có trong danh sách —
 *             nên poll 5 giây không làm cả cột nhấp nháy lại.
 *   XÁC NHẬN  bấm "Thực hiện" xong, nền thẻ sáng lên ≤ 12% rồi tắt trong
 *             520ms. Đây là phản hồi cho một lệnh vừa gửi đi máy chủ: người
 *             vận hành cần biết cú bấm ĐÃ tới, trước cả khi thấy sản phẩm được
 *             ghim trên luồng phát.
 *
 * Không có gì ở đây đổi kích thước thẻ: đổi kích thước sẽ đẩy các thẻ bên dưới
 * trong đúng cái danh sách mà người ta đang định bấm tiếp.
 */

import { fmtMinSec, fmtPct } from "@/lib/format";
import type { ActionCardData, SessionMode } from "@/lib/types";

import Term from "./Term";
import Badge from "./ui/Badge";
import Button from "./ui/Button";
import Card from "./ui/Card";
import Flash from "./ui/Flash";
import { cx } from "./ui/cx";

interface Props {
  card: ActionCardData;
  mode: SessionMode;
  executed?: boolean;
  /** Replay view: no buttons at all (actions happened in the past). */
  readOnly?: boolean;
  /** Thẻ hạng 1 — "việc cần làm ngay": viền gradient + số ước lượng bậc hiển thị. */
  emphasized?: boolean;
  onExecute?: () => void;
  onSkip?: () => void;
}

function SourceBadge({ card }: { card: ActionCardData }) {
  if (card.source === "experiment") {
    return (
      <Term
        tip="Đo được từ các khối BẬT/TẮT trong chính phiên này — kèm khoảng tin cậy 95%."
        side="bottom"
        underline={false}
        className="shrink-0"
      >
        <Badge tone="good" dot>
          Tác động đo được · KTC 95%
        </Badge>
      </Term>
    );
  }
  return (
    <Term
      tip="Con số từ mô hình dự báo — chưa qua thí nghiệm nên không có khoảng tin cậy."
      side="bottom"
      underline={false}
      className="shrink-0"
    >
      <Badge tone="neutral">Ước lượng dự báo</Badge>
    </Term>
  );
}

/** Đếm ngược tự chạy của chế độ auto — cùng một chỗ cho thẻ to lẫn thẻ nhỏ. */
function AutoCountdown({ card }: { card: ActionCardData }) {
  return (
    <span className="text-meta text-dim">
      Tự động thực thi
      {card.auto_execute_in_s != null && (
        <span className="tnum font-num font-semibold text-warn-ink">
          {" "}
          · tự chạy sau {fmtMinSec(Math.max(0, Math.round(card.auto_execute_in_s)))}
        </span>
      )}
    </span>
  );
}

export default function ActionCard({
  card,
  mode,
  executed,
  readOnly,
  emphasized = false,
  onExecute,
  onSkip,
}: Props) {
  // E2-04: an interval may only ever be shown for experiment-sourced cards.
  const showCi = card.source === "experiment" && card.ci_low != null && card.ci_high != null;
  // Nhãn nguồn của con số — đặt NGAY DƯỚI con số to để không ai đọc nhầm một
  // dự báo thành một phép đo (nghĩa vụ E2-04 ở tầng chữ).
  const figureLabel = card.source === "experiment" ? "tác động đo được" : "dự báo lượt bấm";

  return (
    <Card
      as="article"
      padding="sm"
      interactive={!executed}
      className={cx(
        // shrink-0: trong khung cuộn của cột hành động, thẻ giữ NGUYÊN chiều
        // cao tự nhiên — khung chật thì cuộn (có dòng báo), không bóp thẻ tới
        // mức nút Thực hiện biến mất.
        "motion-enter relative flex shrink-0 flex-col gap-1.5 transition-opacity duration-medium2 ease-emphasized",
        executed && "opacity-60",
        emphasized &&
          "border-gradient-brand shadow-[0_8px_34px_-14px_rgba(124,108,255,0.55)]",
      )}
      aria-label={`Gợi ý hạng ${card.rank}: ${card.headline}`}
    >
      <Flash value={executed === true} className="inset-0 rounded-lg" />

      {/* Hàng đầu WRAP được: chip hạng + badge nguồn không bao giờ đè lên
          nhau trong cột 21–25rem — badge rơi xuống dòng khi chật. */}
      <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1">
        <div className="flex min-w-0 items-baseline gap-2">
          <span className="tnum shrink-0 rounded bg-raised px-1.5 py-0.5 text-meta font-bold text-sec">
            #{card.rank}
            {emphasized ? " · ĐỀ XUẤT MẠNH NHẤT" : ""}
          </span>
          {!emphasized && <h3 className="truncate text-strong text-ink">{card.headline}</h3>}
        </div>
        <SourceBadge card={card} />
      </div>

      {emphasized && (
        <h3 className="font-display text-title leading-snug text-ink">{card.headline}</h3>
      )}

      <p className={cx("text-body leading-snug text-sec", emphasized ? "" : "line-clamp-2")}>
        {card.rationale}
      </p>

      <div className="mt-auto flex flex-wrap items-end justify-between gap-x-3 gap-y-2 pt-1">
        {emphasized ? (
          <div className="min-w-0">
            {card.estimate != null ? (
              <>
                <div
                  className={cx(
                    "tnum text-num-s leading-none",
                    card.estimate >= 0 ? "text-good-ink" : "text-crit-ink",
                  )}
                >
                  {fmtPct(card.estimate)}
                </div>
                <div className="mt-0.5 text-meta uppercase tracking-wide text-dim">
                  {figureLabel}
                </div>
              </>
            ) : (
              <span className="text-meta text-dim">—</span>
            )}
            {showCi && (
              <div className="tnum mt-0.5 text-meta text-sec">
                KTC 95% [{fmtPct(card.ci_low as number)}, {fmtPct(card.ci_high as number)}]
              </div>
            )}
          </div>
        ) : (
          <div className="tnum text-meta text-dim">
            {card.estimate != null && (
              <span className="text-strong text-ink">{fmtPct(card.estimate)}</span>
            )}
            {showCi && (
              <span className="ml-1.5 text-sec">
                KTC 95% [{fmtPct(card.ci_low as number)}, {fmtPct(card.ci_high as number)}]
              </span>
            )}
            {card.estimate == null && !showCi && <span>—</span>}
          </div>
        )}

        {readOnly ? (
          <span className="text-meta text-dim">Bản ghi phát lại</span>
        ) : executed ? (
          <span className="motion-enter rounded px-2 py-1 text-meta font-semibold text-good-ink">
            ✓ Đã thực hiện
          </span>
        ) : mode === "auto" ? (
          <div className="flex flex-wrap items-center gap-2">
            <AutoCountdown card={card} />
            <Button disabled>{emphasized ? "Ghim ngay" : "Thực hiện"}</Button>
            <Button variant="ghost" disabled>
              Bỏ qua
            </Button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Button onClick={onExecute}>{emphasized ? "Ghim ngay" : "Thực hiện"}</Button>
            <Button variant="ghost" onClick={onSkip}>
              Bỏ qua
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}
