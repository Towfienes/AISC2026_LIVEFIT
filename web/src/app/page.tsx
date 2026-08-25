"use client";

/**
 * "/" — Bàn trung control (control desk).
 *
 * Three zones, no scroll at 1920x1080:
 * - Zone 1 (top ~40%): session rhythm chart + switchback block strip.
 * - Zone 2 (bottom-left): up to 3 action cards.
 * - Zone 3 (bottom-right): comment radar (last 5 min) + scrolling feed.
 */

import ActionCard from "@/components/ActionCard";
import BlockStrip from "@/components/BlockStrip";
import CommentFeed from "@/components/CommentFeed";
import CommentRadar from "@/components/CommentRadar";
import RhythmChart from "@/components/RhythmChart";
import StatusBar from "@/components/StatusBar";
import { useDesk } from "@/lib/useDesk";

function ZoneTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-1.5 shrink-0 text-[11px] font-bold uppercase tracking-widest text-mut">
      {children}
    </h2>
  );
}

export default function DeskPage() {
  const desk = useDesk();

  return (
    <main className="flex h-screen flex-col gap-3 overflow-hidden p-3">
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
          <BlockStrip blocks={desk.blocks} durationS={desk.durationS} positionS={desk.elapsedS} />
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
              <div className="px-2 py-4 text-xs text-mut">Chưa có gợi ý cho thời điểm này.</div>
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
  );
}
