"use client";

/**
 * "/desk" — Bàn điều khiển (control desk).
 *
 * Three zones, no scroll at 1920x1080:
 * - Zone 1 (top ~40%): session rhythm chart + switchback block strip.
 * - Zone 2 (bottom-left): up to 3 action cards.
 * - Zone 3 (bottom-right): comment radar (last 5 min) + scrolling feed.
 *
 * First-time-user rules: an empty state instead of a blank screen when no
 * session is running, plain-Vietnamese labels, jargon explained in-context
 * via <Term> tooltips.
 */

import { useState } from "react";
import Link from "next/link";
import ActionCard from "@/components/ActionCard";
import BlockStrip from "@/components/BlockStrip";
import CommentFeed from "@/components/CommentFeed";
import CommentRadar from "@/components/CommentRadar";
import RhythmChart from "@/components/RhythmChart";
import StatusBar from "@/components/StatusBar";
import TopNav from "@/components/TopNav";
import { useDesk } from "@/lib/useDesk";

function ZoneTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-1.5 shrink-0 text-[11px] font-bold uppercase tracking-widest text-mut">
      {children}
    </h2>
  );
}

/** Never a blank screen: friendly guidance when nothing is running (NN/g empty states). */
function EmptyDesk({
  hasEndedSessions,
  onDemo,
  onShowAnyway,
}: {
  hasEndedSessions: boolean;
  onDemo: () => void;
  onShowAnyway: () => void;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-6 text-center">
      <div className="text-5xl" aria-hidden>
        📭
      </div>
      <h2 className="text-2xl font-bold text-ink">Chưa có phiên nào đang chạy</h2>
      <p className="max-w-md text-sm leading-relaxed text-sec">
        Bàn điều khiển sẽ hiển thị nhịp phiên, thẻ gợi ý và bình luận khi một phiên live bắt đầu.
        Trong lúc chờ, bạn có thể xem thử với dữ liệu mô phỏng.
      </p>
      <div className="flex flex-wrap items-center justify-center gap-3">
        <button
          type="button"
          onClick={onDemo}
          className="rounded-lg bg-s1 px-5 py-2.5 text-sm font-semibold text-ink transition-colors hover:bg-[#5099ea]"
        >
          Xem thử với dữ liệu mô phỏng
        </button>
        <Link
          href="/"
          className="rounded-lg border border-hairline bg-raised px-5 py-2.5 text-sm font-semibold text-sec transition-colors hover:border-mut hover:text-ink"
        >
          Về trang chính
        </Link>
      </div>
      {hasEndedSessions && (
        <button
          type="button"
          onClick={onShowAnyway}
          className="text-xs text-mut underline decoration-dotted underline-offset-2 hover:text-sec"
        >
          Vẫn mở bàn điều khiển với phiên đã kết thúc
        </button>
      )}
    </div>
  );
}

export default function DeskPage() {
  const [demoMode, setDemoMode] = useState(false);
  const [showAnyway, setShowAnyway] = useState(false);
  const desk = useDesk({ forceMock: demoMode });

  const hasLive = desk.sessions.some((s) => s.status === "live");
  const showEmpty =
    desk.connection !== "connecting" &&
    !showAnyway &&
    (desk.sessionId == null || (desk.connection === "live" && !hasLive));

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-page">
      <TopNav />
      {desk.connection === "connecting" ? (
        <div className="flex flex-1 items-center justify-center text-sm text-mut">
          Đang kết nối…
        </div>
      ) : showEmpty ? (
        <EmptyDesk
          hasEndedSessions={desk.sessions.length > 0}
          onDemo={() => setDemoMode(true)}
          onShowAnyway={() => setShowAnyway(true)}
        />
      ) : (
        <main className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden p-3">
          <StatusBar
            connection={desk.connection}
            wsStatus={desk.wsStatus}
            sessions={desk.sessions}
            sessionId={desk.sessionId}
            onSelectSession={desk.setSessionId}
            elapsedS={desk.elapsedS}
            durationS={desk.durationS}
            viewers={desk.viewers}
            mode={desk.mode}
            onSetMode={desk.setMode}
            canToggleMode={desk.canToggleMode}
          />

          {/* Zone 1 — nhịp phiên + dải khối switchback */}
          <section className="flex min-h-0 basis-[40%] flex-col rounded-lg border border-hairline bg-surface p-3">
            <div className="flex shrink-0 items-baseline justify-between">
              <ZoneTitle>Nhịp phiên</ZoneTitle>
              <span className="text-[11px] text-sec">
                Đang ghim:{" "}
                <span className="font-semibold text-ink">{desk.pinned?.name ?? "—"}</span>
              </span>
            </div>
            <div className="min-h-0 flex-1">
              <RhythmChart ticks={desk.ticks} />
            </div>
            <div className="mt-2 shrink-0">
              <BlockStrip
                blocks={desk.blocks}
                durationS={desk.durationS}
                positionS={desk.elapsedS}
              />
            </div>
          </section>

          <div className="grid min-h-0 flex-1 grid-cols-2 gap-3">
            {/* Zone 2 — action cards */}
            <section className="flex min-h-0 flex-col rounded-lg border border-hairline bg-surface p-3">
              <ZoneTitle>
                Hành động gợi ý{" "}
                <span className="normal-case tracking-normal text-sec">
                  · chế độ {desk.mode === "auto" ? "tự động" : "gợi ý"}
                </span>
              </ZoneTitle>
              <div className="flex min-h-0 flex-1 flex-col justify-start gap-2 overflow-y-auto">
                {desk.cards.length === 0 ? (
                  <div className="px-2 py-4 text-xs text-mut">
                    Chưa có gợi ý cho thời điểm này — hệ thống sẽ tự thêm thẻ khi đủ dữ liệu.
                  </div>
                ) : (
                  desk.cards.map((c) => (
                    <ActionCard
                      key={c.card_id}
                      card={c}
                      mode={desk.mode}
                      executed={desk.executedCardIds.has(c.card_id)}
                      onExecute={() => void desk.execute(c)}
                      onSkip={() => desk.skip(c.card_id)}
                    />
                  ))
                )}
              </div>
            </section>

            {/* Zone 3 — comment radar + feed */}
            <section className="flex min-h-0 flex-col rounded-lg border border-hairline bg-surface p-3">
              <ZoneTitle>Radar bình luận · 5 phút gần nhất</ZoneTitle>
              <div className="min-h-0 flex-[2]">
                <CommentRadar comments={desk.comments} nowS={desk.elapsedS} />
              </div>
              <div className="mt-2 flex min-h-0 flex-[3] flex-col border-t border-hairline pt-2">
                <CommentFeed comments={desk.comments} />
              </div>
            </section>
          </div>
        </main>
      )}
    </div>
  );
}
