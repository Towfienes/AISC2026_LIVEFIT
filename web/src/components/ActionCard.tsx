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
 * dành cho vòng on-air của thẻ khối), ước lượng kèm nhãn nguồn ("THỨ HẠNG —
 * KHÔNG PHẢI % TĂNG" / "TÁC ĐỘNG ĐO ĐƯỢC"), lý do một dòng đọc được.
 * Các thẻ sau nhỏ hơn rõ rệt — hierarchy bằng kích thước số.
 *
 * MỘT ĐỘNG TỪ (gói C6): nút chính của MỌI thẻ là "Thực hiện". Thẻ #1 từng ghi
 * "Ghim ngay" còn thẻ #2–#3 ghi "Thực hiện" — một hành động hai tên, trong khi
 * hướng dẫn và thông báo lỗi đều nói "bấm Thực hiện".
 *
 * KHOÁ THEO KHỐI (gói C2 — giới hạn #6): trong khối TẮT / khoảng trôi / ngoài
 * lịch, máy chủ từ chối lệnh ghim (409). Thẻ vẫn hiện (máy chủ cố ý không ẩn
 * thẻ theo nhánh để danh sách thẻ không thành kênh lộ nhánh), nhưng nút được
 * THAY bằng lý do ngắn có HÌNH + CHỮ ("Khối TẮT — vận hành như thường lệ").
 * Được phép vì bàn trợ live vốn đã hiện BẬT/TẮT cỡ chữ lớn; màn người dẫn
 * không dùng component này.
 *
 * KHÔNG BỊA SỐ (gói C6): khi mọi thẻ dự báo có CÙNG một ước lượng, mô hình
 * chưa có dữ liệu nào để phân biệt chúng (tính chất khởi động lạnh của
 * cards.build_candidates) — in "+100%" to màu xanh là trình bày một con số
 * không mang thông tin như tin tốt. Thẻ ghi "chưa đủ dữ liệu để dự báo".
 *
 * ĐÚNG ĐƠN VỊ (sửa phản biện): `estimate` của thẻ DỰ BÁO từ máy chủ là trung
 * bình hậu nghiệm Gamma-Poisson tính bằng LƯỢT BẤM / 1000 NGƯỜI-XEM-GIÂY
 * (cards.build_candidates), KHÔNG phải mức tăng tương đối. fmtPct biến 0,17
 * thành "+17%" màu xanh — người bán đọc thành "tăng 17%". Thẻ dự báo vì vậy
 * chỉ nói THỨ HẠNG ("hạng 2/3 theo dự báo lượt bấm"), mực trung tính; chỉ thẻ
 * THÍ NGHIỆM (tác động đo được, kèm KTC 95%) mới in phần trăm. Xem
 * `estimateDisplay`.
 *
 * Mode behavior:
 * - "auto"    → KHÔNG có nút xám chết (gói C11): chỉ dòng "Tự động thực thi"
 *   + đếm ngược "tự chạy sau m:ss" màu hổ phách.
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

import { fmtMinSec, fmtNumber, fmtPct, fmtVnd } from "@/lib/format";
import type { ActionCardData, SessionMode } from "@/lib/types";

import Term from "./Term";
import Badge from "./ui/Badge";
import Button from "./ui/Button";
import Card from "./ui/Card";
import Flash from "./ui/Flash";
import StatusMark, { type StatusShape } from "./ui/StatusMark";
import { cx } from "./ui/cx";

/** Lý do khoá nút hành động — HÌNH (StatusMark) + CHỮ, không chỉ màu. */
export interface CardLock {
  shape: StatusShape;
  text: string;
}

/** Nhãn nút chính — MỘT động từ cho mọi thẻ. */
export const PRIMARY_VERB = "Thực hiện";

/** Câu thay cho con số khi dự báo chưa có cơ sở dữ liệu. */
export const NO_FORECAST_BASIS = "chưa đủ dữ liệu để dự báo";

/** Nhãn dưới thứ hạng dự báo — chặn cách đọc "thứ hạng" thành "% tăng". */
export const FORECAST_RANK_NOTE = "thứ hạng — không phải % tăng";

/** Cách hiện `estimate` của một thẻ — xem `estimateDisplay`. */
export interface EstimateDisplay {
  text: string;
  label: string;
  tone: "good" | "crit" | "neutral";
}

interface Props {
  card: ActionCardData;
  mode: SessionMode;
  executed?: boolean;
  /** Replay view: no buttons at all (actions happened in the past). */
  readOnly?: boolean;
  /** Thẻ hạng 1 — "việc cần làm ngay": viền gradient + số ước lượng bậc hiển thị. */
  emphasized?: boolean;
  /** Khối hiện tại không nhận lệnh ghim (TẮT/trôi/ngoài lịch) — null = mở. */
  locked?: CardLock | null;
  /** Dự báo chưa có cơ sở dữ liệu — xem `forecastLacksData`. */
  noForecastBasis?: boolean;
  /** Số thẻ gợi ý đang hiện — mẫu số của "hạng k/N" trên thẻ dự báo. */
  peerCount?: number | null;
  onExecute?: () => void;
  onSkip?: () => void;
}

/**
 * Dự báo của thẻ có cơ sở dữ liệu hay chưa — suy từ CHÍNH các trường của thẻ.
 *
 * - Thẻ thí nghiệm (source="experiment") là phép đo, luôn có cơ sở.
 * - Thẻ dự báo không có ước lượng hữu hạn ⇒ chưa có cơ sở.
 * - Phiên CHƯA ghi nhận lượt bấm nào (`clicksObserved === false`: không có link
 *   đo, hoặc có link mà chưa ai bấm) ⇒ mô hình lượt bấm chỉ còn phân phối tiên
 *   nghiệm (cards.build_candidates: FALLBACK_POOLED_RATE) ⇒ chưa có cơ sở — kể
 *   cả khi chỉ có MỘT thẻ, nơi luật "mọi ước lượng bằng nhau" không bắt được.
 * - Từ hai thẻ dự báo trở lên mà MỌI ước lượng bằng nhau ⇒ mô hình chưa có dữ
 *   liệu nào phân biệt được chúng (khởi động lạnh: mọi sản phẩm mang đúng phân
 *   phối tiên nghiệm) ⇒ chưa có cơ sở.
 *
 * `clicksObserved` null/thiếu = chưa biết ⇒ không kết luận từ điều kiện đó.
 */
export function forecastLacksData(
  card: ActionCardData,
  peers: readonly ActionCardData[],
  opts?: { clicksObserved?: boolean | null },
): boolean {
  if (card.source !== "forecast") return false;
  if (card.estimate == null || !Number.isFinite(card.estimate)) return true;
  if (opts?.clicksObserved === false) return true;
  const own = card.estimate;
  const forecasts = peers.filter(
    (c) => c.source === "forecast" && c.estimate != null && Number.isFinite(c.estimate),
  );
  if (forecasts.length < 2) return false;
  return forecasts.every((c) => Math.abs((c.estimate as number) - own) < 1e-9);
}

/**
 * Chữ hiển thị cho ước lượng của thẻ — KHÔNG bao giờ in "% tăng" cho dự báo.
 *
 * - Thẻ THÍ NGHIỆM: `estimate` là tác động tương đối đo được ⇒ fmtPct, mực
 *   xanh/đỏ theo dấu.
 * - Thẻ DỰ BÁO: `estimate` là tốc độ lượt bấm của mô hình (lượt bấm / 1000
 *   người-xem-giây), không phải mức tăng ⇒ chỉ nói thứ hạng của thẻ giữa
 *   `of` gợi ý đang hiện, mực trung tính.
 * - Không có ước lượng hữu hạn ⇒ null (thẻ in "—").
 */
export function estimateDisplay(card: ActionCardData, of: number | null): EstimateDisplay | null {
  if (card.estimate == null || !Number.isFinite(card.estimate)) return null;
  if (card.source === "experiment") {
    return {
      text: fmtPct(card.estimate),
      label: "tác động đo được",
      tone: card.estimate >= 0 ? "good" : "crit",
    };
  }
  // Không biết mẫu số (nơi dùng thẻ không truyền) thì chỉ nói hạng, không
  // nói "duy nhất".
  const text =
    of == null
      ? `hạng ${card.rank} theo dự báo lượt bấm`
      : of > 1
        ? `hạng ${card.rank}/${of} theo dự báo lượt bấm`
        : "gợi ý duy nhất theo dự báo lượt bấm";
  return { text, label: FORECAST_RANK_NOTE, tone: "neutral" };
}

/**
 * Chuẩn hoá số trong câu lý do của máy chủ sang định dạng vi-VN.
 *
 * Máy chủ (cards.build_cards) in "Biên lợi nhuận 53,000đ/sản phẩm" — dấu phẩy
 * nghìn kiểu Anh, lệch với "45.000 ₫" ở wizard và màn người dẫn. Tiền đi qua
 * fmtVnd, số nhóm nghìn khác đi qua fmtNumber; chuỗi đã đúng định dạng giữ
 * nguyên.
 */
export function viRationale(text: string): string {
  const toNum = (s: string) => Number(s.replace(/,/g, ""));
  return (
    text
      // tiền: "53,000đ" / "53000 ₫" → fmtVnd; "45.000 ₫" (đã đúng) không khớp
      // vì số đứng sau dấu chấm; "5 đồng" không khớp vì "đ" còn chữ theo sau.
      .replace(
        /(^|[^\d.,])(\d{1,3}(?:,\d{3})+|\d+)\s?(?:đ|₫)(?![A-Za-zÀ-ỹ])/g,
        (m, pre: string, n: string) => {
          const v = toNum(n);
          return Number.isFinite(v) ? pre + fmtVnd(v) : m;
        },
      )
      // số nhóm nghìn kiểu Anh còn lại: "1,200 trong kho" → fmtNumber
      .replace(/(^|[^\d.,])(\d{1,3}(?:,\d{3})+)(?!,?\d)/g, (m, pre: string, n: string) => {
        const v = toNum(n);
        return Number.isFinite(v) ? pre + fmtNumber(v) : m;
      })
  );
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
      {card.auto_execute_in_s != null ? (
        <span className="tnum font-num font-semibold text-warn-ink">
          {" "}
          · tự chạy sau {fmtMinSec(Math.max(0, Math.round(card.auto_execute_in_s)))}
        </span>
      ) : (
        <span> · hệ thống tự ghim trong khối BẬT</span>
      )}
    </span>
  );
}

/** Lý do khoá: ký hiệu hình dạng của trạng thái khối + câu ngắn. */
function LockNote({ lock }: { lock: CardLock }) {
  return (
    <span className="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-hairline bg-raised px-2.5 py-1 text-meta font-semibold text-sec">
      <StatusMark shape={lock.shape} />
      {lock.text}
    </span>
  );
}

/** "chưa đủ dữ liệu để dự báo" — vòng rỗng + chữ, mực trung tính (không xanh). */
function NoBasisNote() {
  return (
    <span className="inline-flex items-center gap-1.5 text-meta text-dim">
      <span aria-hidden>○</span>
      {NO_FORECAST_BASIS}
    </span>
  );
}

export default function ActionCard({
  card,
  mode,
  executed,
  readOnly,
  emphasized = false,
  locked = null,
  noForecastBasis = false,
  peerCount = null,
  onExecute,
  onSkip,
}: Props) {
  // E2-04: an interval may only ever be shown for experiment-sourced cards.
  const showCi = card.source === "experiment" && card.ci_low != null && card.ci_high != null;
  const noBasis = noForecastBasis && card.source === "forecast";
  // Nhãn nguồn của con số nằm NGAY DƯỚI nó để không ai đọc nhầm một dự báo
  // thành một phép đo (nghĩa vụ E2-04 ở tầng chữ), và thứ hạng thành "% tăng".
  const shown = noBasis ? null : estimateDisplay(card, peerCount);
  const isLocked = !readOnly && !executed && locked != null;

  return (
    <Card
      as="article"
      padding="sm"
      interactive={!executed && !isLocked}
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
            {/* "mạnh nhất" chỉ đúng khi dự báo phân biệt được các thẻ */}
            {emphasized && !noBasis ? " · ĐỀ XUẤT MẠNH NHẤT" : ""}
          </span>
          {!emphasized && <h3 className="truncate text-strong text-ink">{card.headline}</h3>}
        </div>
        <SourceBadge card={card} />
      </div>

      {emphasized && (
        <h3 className="font-display text-title leading-snug text-ink">{card.headline}</h3>
      )}

      <p className={cx("text-body leading-snug text-sec", emphasized ? "" : "line-clamp-2")}>
        {viRationale(card.rationale)}
      </p>

      <div className="mt-auto flex flex-wrap items-end justify-between gap-x-3 gap-y-2 pt-1">
        {emphasized ? (
          <div className="min-w-0">
            {noBasis ? (
              <NoBasisNote />
            ) : shown ? (
              <>
                <div
                  className={cx(
                    "tnum",
                    // Phần trăm đo được ở bậc hiển thị; thứ hạng dự báo là
                    // một câu ngắn, mực trung tính — không xanh như tin tốt.
                    shown.tone === "neutral"
                      ? "text-strong leading-snug text-ink"
                      : "text-num-s leading-none",
                    shown.tone === "good" && "text-good-ink",
                    shown.tone === "crit" && "text-crit-ink",
                  )}
                >
                  {shown.text}
                </div>
                <div className="mt-0.5 text-meta uppercase tracking-wide text-dim">
                  {shown.label}
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
            {noBasis ? (
              <NoBasisNote />
            ) : (
              <>
                {shown ? (
                  <span
                    className={shown.tone === "neutral" ? "text-sec" : "text-strong text-ink"}
                    title={shown.tone === "neutral" ? shown.label : undefined}
                  >
                    {shown.text}
                  </span>
                ) : null}
                {showCi && (
                  <span className="ml-1.5 text-sec">
                    KTC 95% [{fmtPct(card.ci_low as number)}, {fmtPct(card.ci_high as number)}]
                  </span>
                )}
                {!shown && !showCi && <span>—</span>}
              </>
            )}
          </div>
        )}

        {readOnly ? (
          <span className="text-meta text-dim">Bản ghi phát lại</span>
        ) : executed ? (
          <span className="motion-enter rounded px-2 py-1 text-meta font-semibold text-good-ink">
            ✓ Đã thực hiện
          </span>
        ) : locked ? (
          <LockNote lock={locked} />
        ) : mode === "auto" ? (
          <AutoCountdown card={card} />
        ) : (
          <div className="flex items-center gap-2">
            <Button onClick={onExecute}>{PRIMARY_VERB}</Button>
            <Button variant="ghost" onClick={onSkip}>
              Bỏ qua
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}
