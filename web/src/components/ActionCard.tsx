"use client";

/**
 * Zone 2 action card ("Hành động gợi ý").
 *
 * E2-04 display rule (hard project rule):
 * - source="forecast"   → gray badge "Ước lượng dự báo". NEVER render any
 *   interval, even if ci fields somehow arrive populated (api.sanitizeCard
 *   already strips them; this component guards again).
 * - source="experiment" → green badge "Tác động đo được · KTC 95%" and the
 *   [ci_low, ci_high] interval.
 *
 * Mode behavior:
 * - "auto"    → execute/skip disabled, note "Tự động thực thi" (+ countdown).
 * - "suggest" → active "Thực hiện" and "Bỏ qua" buttons.
 *
 * "Thực hiện" is THE primary action of the desk, so it takes the `md` button
 * (36px tall) rather than the dense `sm` one: the operator hits it while
 * watching the stream, not while looking at the mouse.
 *
 * ---------------------------------------------------------------------------
 * CHUYỂN ĐỘNG (gói UI-3)
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

import { fmtPct } from "@/lib/format";
import type { ActionCardData, SessionMode } from "@/lib/types";

import Term from "./Term";
import Badge from "./ui/Badge";
import Button from "./ui/Button";
import Card from "./ui/Card";
import Flash from "./ui/Flash";

interface Props {
  card: ActionCardData;
  mode: SessionMode;
  executed?: boolean;
  /** Replay view: no buttons at all (actions happened in the past). */
  readOnly?: boolean;
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

export default function ActionCard({ card, mode, executed, readOnly, onExecute, onSkip }: Props) {
  // E2-04: an interval may only ever be shown for experiment-sourced cards.
  const showCi = card.source === "experiment" && card.ci_low != null && card.ci_high != null;

  return (
    <Card
      as="article"
      padding="sm"
      interactive={!executed}
      className={`motion-enter relative flex min-h-0 flex-col gap-1.5 transition-opacity duration-medium2 ease-emphasized ${
        executed ? "opacity-60" : ""
      }`}
      aria-label={`Gợi ý hạng ${card.rank}: ${card.headline}`}
    >
      <Flash value={executed === true} className="inset-0 rounded-lg" />

      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-baseline gap-2">
          <span className="tnum shrink-0 rounded bg-raised px-1.5 py-0.5 text-meta font-bold text-sec">
            #{card.rank}
          </span>
          <h3 className="truncate text-strong text-ink">{card.headline}</h3>
        </div>
        <SourceBadge card={card} />
      </div>

      <p className="line-clamp-2 text-body leading-snug text-sec">{card.rationale}</p>

      <div className="mt-auto flex items-center justify-between gap-2 pt-1">
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

        {readOnly ? (
          <span className="text-meta text-dim">Bản ghi phát lại</span>
        ) : executed ? (
          <span className="motion-enter rounded px-2 py-1 text-meta font-semibold text-good-ink">
            ✓ Đã thực hiện
          </span>
        ) : mode === "auto" ? (
          <div className="flex items-center gap-2">
            <span className="text-meta text-dim">
              Tự động thực thi
              {card.auto_execute_in_s != null && (
                <span className="tnum"> · {Math.max(0, Math.round(card.auto_execute_in_s))}s</span>
              )}
            </span>
            <Button disabled>Thực hiện</Button>
            <Button variant="ghost" disabled>
              Bỏ qua
            </Button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Button onClick={onExecute}>Thực hiện</Button>
            <Button variant="ghost" onClick={onSkip}>
              Bỏ qua
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}
