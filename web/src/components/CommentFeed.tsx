"use client";

/**
 * Zone 3 scrolling comment feed with intent chips.
 *
 * Comments arrive pre-scrubbed server-side (PII rule); rows whose text carried
 * redactions show a small "PII đã ẩn" marker. Auto-follows the newest comment
 * unless the operator has scrolled up; scroll is instant when the viewer
 * prefers reduced motion.
 */

import { useEffect, useRef } from "react";

import { fmtElapsed } from "@/lib/format";
import { INTENT_META, type CommentItem } from "@/lib/types";

function IntentChip({ intent }: { intent: CommentItem["intent_label"] }) {
  if (!intent) {
    return (
      <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-hairline px-1.5 py-px text-[11px] text-mut">
        Chưa phân loại
      </span>
    );
  }
  const meta = INTENT_META[intent];
  return (
    <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-hairline bg-raised px-1.5 py-px text-[11px] text-sec">
      <span aria-hidden className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: meta.color }} />
      {meta.label}
    </span>
  );
}

export default function CommentFeed({ comments }: { comments: CommentItem[] }) {
  const boxRef = useRef<HTMLDivElement>(null);
  const stickToEnd = useRef(true);

  // Track whether the operator scrolled away from the tail.
  const onScroll = () => {
    const el = boxRef.current;
    if (!el) return;
    stickToEnd.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
  };

  useEffect(() => {
    const el = boxRef.current;
    if (!el || !stickToEnd.current) return;
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    el.scrollTo({ top: el.scrollHeight, behavior: reduced ? "auto" : "smooth" });
  }, [comments]);

  return (
    <div
      ref={boxRef}
      onScroll={onScroll}
      className="min-h-0 flex-1 overflow-y-auto pr-1"
      aria-label="Bình luận trực tiếp"
    >
      {comments.length === 0 ? (
        <div className="px-2 py-4 text-xs text-mut">Chưa có bình luận trong phiên.</div>
      ) : (
        <ul className="flex flex-col gap-1">
          {comments.map((c) => (
            <li
              key={c.comment_id}
              className="flex items-start gap-2 rounded border border-transparent px-2 py-1 text-xs transition-colors duration-150 hover:border-hairline hover:bg-raised"
            >
              <span className="tnum mt-px shrink-0 text-[11px] text-mut">
                {fmtElapsed(c.offset_s)}
              </span>
              <span className="min-w-0 flex-1 break-words leading-snug text-ink">
                {c.text_scrubbed}
                {c.pii_kinds.length > 0 && (
                  <span className="ml-1.5 rounded bg-axis px-1 py-px text-[10px] font-semibold text-sec align-middle">
                    PII đã ẩn
                  </span>
                )}
              </span>
              <IntentChip intent={c.intent_label} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
