"use client";

/**
 * Zone 3 scrolling comment feed with intent chips.
 *
 * Comments arrive pre-scrubbed server-side (PII rule); rows whose text carried
 * redactions show a small "PII đã ẩn" marker.
 *
 * ---------------------------------------------------------------------------
 * TỰ CUỘN & NÚT TẠM DỪNG (WCAG 2.2.2 Pause, Stop, Hide — gói UI-3)
 * ---------------------------------------------------------------------------
 * Feed này tự cuộn theo bình luận mới, tức là nội dung TỰ ĐỘNG CẬP NHẬT và
 * chuyển động mà người dùng không bấm gì. SC 2.2.2 đòi phải có cách dừng nó
 * lại. Trước gói này, cách duy nhất là "cuộn lên rồi đừng đụng vào" — một mẹo
 * ngầm, không có nhãn, và trượt tay một cái là mất chỗ đang đọc.
 *
 * Nay có ba thứ rõ ràng:
 *   1. nút "Tạm dừng cuộn" / "Tiếp tục cuộn" — điều khiển thật, có nhãn thật;
 *   2. đếm bao nhiêu bình luận đã đến trong lúc dừng, kèm nút nhảy xuống cuối,
 *      nên tạm dừng không đồng nghĩa với bỏ lỡ;
 *   3. cuộn lên bằng tay vẫn tự ngắt bám đuôi như cũ (giữ hành vi quen thuộc).
 *
 * ---------------------------------------------------------------------------
 * CHUYỂN ĐỘNG
 * ---------------------------------------------------------------------------
 * Dòng mới vào bằng fade + translateY 6px trong 180ms ease-out, so le tối đa
 * ba bậc 60ms. KHÔNG animate `height`/`max-height`: chiều cao đổi dần sẽ đẩy
 * toàn bộ danh sách trôi trong lúc người ta đang đọc dòng khác — đúng thứ mà
 * hiệu ứng này lẽ ra phải giúp tránh.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { fmtElapsed } from "@/lib/format";
import { MOTION, useEnterStagger, usePrefersReducedMotion } from "@/lib/motion";
import { INTENT_META, type CommentItem } from "@/lib/types";

import Button from "./ui/Button";

/** Cuộn còn cách đáy dưới ngưỡng này thì coi như vẫn đang bám đuôi. */
const TAIL_SLACK_PX = 40;

function IntentChip({ intent }: { intent: CommentItem["intent_label"] }) {
  if (!intent) {
    return (
      <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-hairline px-2 py-px text-meta text-dim">
        Chưa phân loại
      </span>
    );
  }
  const meta = INTENT_META[intent];
  return (
    <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-hairline bg-raised px-2 py-px text-meta text-sec">
      <span
        aria-hidden
        className="inline-block h-1.5 w-1.5 rounded-full"
        style={{ background: meta.color }}
      />
      {meta.label}
    </span>
  );
}

export default function CommentFeed({ comments }: { comments: CommentItem[] }) {
  const boxRef = useRef<HTMLDivElement>(null);
  const stickToEnd = useRef(true);
  /** Số bình luận tại lần cuối cùng feed thực sự cuộn xuống đáy. */
  const followedCount = useRef(0);
  const [paused, setPaused] = useState(false);
  const [behind, setBehind] = useState(0);
  const reduced = usePrefersReducedMotion();
  const enter = useEnterStagger(comments, (c) => c.comment_id);

  // Track whether the operator scrolled away from the tail.
  const onScroll = () => {
    const el = boxRef.current;
    if (!el) return;
    const atEnd = el.scrollHeight - el.scrollTop - el.clientHeight < TAIL_SLACK_PX;
    stickToEnd.current = atEnd;
    if (atEnd && !paused) {
      followedCount.current = comments.length;
      setBehind(0);
    }
  };

  const scrollToEnd = useCallback(() => {
    const el = boxRef.current;
    if (!el) return;
    el.scrollTo({
      top: el.scrollHeight,
      behavior: reduced ? "auto" : "smooth",
    });
  }, [reduced]);

  useEffect(() => {
    if (!boxRef.current) return;
    if (paused || !stickToEnd.current) {
      setBehind(Math.max(0, comments.length - followedCount.current));
      return;
    }
    scrollToEnd();
    followedCount.current = comments.length;
    setBehind(0);
  }, [comments, paused, scrollToEnd]);

  /** Bắt kịp: bỏ tạm dừng, bám đuôi lại và nhảy xuống bình luận mới nhất. */
  const catchUp = () => {
    setPaused(false);
    stickToEnd.current = true;
    followedCount.current = comments.length;
    setBehind(0);
    scrollToEnd();
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="mb-1 flex shrink-0 flex-wrap items-center gap-2">
        <span className="text-meta text-dim">
          Bình luận trực tiếp
          {comments.length > 0 ? ` · ${comments.length} dòng` : ""}
        </span>
        {behind > 0 ? (
          <Button size="sm" variant="ghost" onClick={catchUp} className="motion-enter">
            ↓ {behind} bình luận mới
          </Button>
        ) : null}
        <Button
          size="sm"
          variant="ghost"
          className="ml-auto"
          aria-pressed={paused}
          onClick={() => setPaused((p) => !p)}
          title={
            paused
              ? "Cho feed tự cuộn theo bình luận mới nhất trở lại"
              : "Dừng tự cuộn để đọc kỹ — bình luận mới vẫn được đếm"
          }
        >
          {paused ? "Tiếp tục cuộn" : "Tạm dừng cuộn"}
        </Button>
      </div>

      {/* Thông báo LỊCH SỰ, chỉ phát khi người dùng bật/tắt tạm dừng — không
          phải mỗi bình luận. Đọc từng dòng bình luận sẽ khiến người dùng trình
          đọc màn hình tắt hẳn vùng này. */}
      <p className="sr-only" aria-live="polite">
        {paused ? "Đã tạm dừng tự cuộn feed bình luận." : ""}
      </p>

      {/* Khung cuộn được ĐỊNH VỊ TUYỆT ĐỐI trong một hộp co giãn.
          Không phải để làm dáng: `overflow-y-auto` thường vẫn đóng góp chiều
          cao nội dung của nó cho phần tử cha, và bàn điều khiển dựng trên một
          lưới có hàng tỉ lệ (`3fr`/`2fr`) trong hộp cao KHÔNG XÁC ĐỊNH. 14 dòng
          bình luận vì thế từng đội hàng radar lên 699px, kéo theo hàng biểu đồ
          1049px và đẩy cả trang thành 2182px trên màn 1080px — bàn phải cuộn
          hai màn hình ở đúng kích thước nó được thiết kế cho. Nội dung của một
          lớp `absolute` không đóng góp gì vào chiều cao cha, nên vòng lặp
          "nội dung quyết định chiều cao, chiều cao quyết định nội dung" bị cắt
          tại đây. */}
      <div className="relative min-h-0 flex-1">
        <div
          ref={boxRef}
          onScroll={onScroll}
          // aria-live="off" là CÓ CHỦ Ý: một feed trực tiếp đọc lên liên tục thì
          // che mất mọi thông báo khác của bàn điều khiển.
          aria-live="off"
          className="absolute inset-0 overflow-y-auto pr-1"
        >
          {comments.length === 0 ? (
            <div className="px-2 py-4 text-body text-dim">
              Chưa có bình luận nào. Bình luận sẽ tự hiện ở đây ngay khi người xem gõ — bạn không
              cần làm gì.
            </div>
          ) : (
            // Nhãn nằm trên chính danh sách, không trên khung cuộn: `aria-label`
            // trên một <div> không mang vai trò nào sẽ bị trình đọc màn hình bỏ
            // qua, còn <ul> có vai trò `list` nên đặt tên được.
            <ul aria-label="Danh sách bình luận" className="flex flex-col gap-1">
              {comments.map((c) => {
                const step = enter.get(c.comment_id);
                return (
                  <li
                    key={c.comment_id}
                    className={`flex items-start gap-2 rounded border border-transparent px-2 py-1 transition-colors duration-short2 ease-emphasized hover:border-hairline hover:bg-raised ${
                      step == null ? "" : "motion-enter"
                    }`}
                    style={
                      step == null ? undefined : { animationDelay: `${step * MOTION.staggerMs}ms` }
                    }
                  >
                    <span className="tnum mt-0.5 shrink-0 text-meta text-dim">
                      {fmtElapsed(c.offset_s)}
                    </span>
                    <span className="min-w-0 flex-1 break-words text-body leading-snug text-ink">
                      {c.text_scrubbed}
                      {c.pii_kinds.length > 0 && (
                        <span className="ml-1.5 rounded bg-axis px-1.5 py-px align-middle text-meta font-semibold text-off-ink">
                          PII đã ẩn
                        </span>
                      )}
                    </span>
                    <IntentChip intent={c.intent_label} />
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
