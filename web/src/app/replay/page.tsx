"use client";

/**
 * "/replay" — Replay Engine demo (E6-06).
 *
 * Plays a finished session's recorded data back through the same three-zone
 * layout as the live desk, with transport controls and a what-if parameter
 * panel: toggling "hết hàng" on a product re-ranks / removes its action cards
 * client-side.
 */

import ActionCard from "@/components/ActionCard";
import BlockStrip from "@/components/BlockStrip";
import CommentFeed from "@/components/CommentFeed";
import CommentRadar from "@/components/CommentRadar";
import ReplayControls from "@/components/ReplayControls";
import RhythmChart from "@/components/RhythmChart";
import { DemoBadge } from "@/components/StatusBar";
import { fmtDateHCM } from "@/lib/format";
import { useReplay } from "@/lib/useReplay";

function ZoneTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-1.5 shrink-0 text-[11px] font-bold uppercase tracking-widest text-mut">
      {children}
    </h2>
  );
}

export default function ReplayPage() {
  const rp = useReplay();
  const rec = rp.recording;
  const recordedOn = rec?.session.start_ts ? fmtDateHCM(rec.session.start_ts) : "—";

  return (
    <main className="flex h-screen flex-col gap-3 overflow-hidden p-3">
      {/* header + provenance banner */}
      <header className="flex h-11 shrink-0 items-center gap-3 rounded-lg border border-hairline bg-surface px-3">
        <span className="text-sm font-bold tracking-tight text-ink">
          LiveLift <span className="font-normal text-mut">· phát lại phiên</span>
        </span>
        {rp.connection === "mock" && <DemoBadge />}
        <div className="ml-auto flex min-w-0 items-center gap-2 rounded border border-warn/60 bg-warn/10 px-3 py-1">
          <span aria-hidden className="text-warn">⏮</span>
          <span className="truncate text-xs font-bold tracking-wide text-warn">
            PHÁT LẠI DỮ LIỆU THẬT — ghi ngày {recordedOn}
          </span>
        </div>
      </header>

      <ReplayControls
        sessions={rp.sessions}
        sessionId={rp.sessionId}
        onSelectSession={rp.setSessionId}
        t={rp.t}
        durationS={rec?.duration_s ?? 0}
        playing={rp.playing}
        onTogglePlay={rp.togglePlay}
        speed={rp.speed}
        onSetSpeed={rp.setSpeed}
        onSeek={rp.seek}
        disabled={!rec}
      />

      {/* Zone 1 — same rhythm + block strip as the live desk */}
      <section className="flex min-h-0 basis-[36%] flex-col rounded-lg border border-hairline bg-surface p-3">
        <ZoneTitle>Nhịp phiên (bản ghi)</ZoneTitle>
        <div className="min-h-0 flex-1">
          <RhythmChart ticks={rp.visibleTicks} />
        </div>
        <div className="mt-2 shrink-0">
          <BlockStrip blocks={rec?.blocks ?? []} durationS={rec?.duration_s ?? 0} positionS={rp.t} />
        </div>
      </section>

      <div className="grid min-h-0 flex-1 grid-cols-2 gap-3">
        {/* Zone 2 — cards + what-if parameter panel */}
        <section className="flex min-h-0 rounded-lg border border-hairline bg-surface p-3">
          <div className="flex min-h-0 min-w-0 flex-1 flex-col pr-3">
            <ZoneTitle>
              Hành động gợi ý{" "}
              <span className="normal-case tracking-normal text-sec">
                · {rp.cardsFromServer ? "thẻ từ máy chủ" : "tổng hợp lại phía client"}
              </span>
            </ZoneTitle>
            <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
              {rp.cards.length === 0 ? (
                <div className="px-2 py-4 text-xs text-mut">
                  Không còn thẻ nào cho thời điểm này (kiểm tra tham số bên phải).
                </div>
              ) : (
                rp.cards.map((c) => (
                  <ActionCard key={c.card_id} card={c} mode={rec?.session.mode ?? "suggest"} readOnly />
                ))
              )}
            </div>
          </div>

          {/* parameter panel */}
          <aside className="flex w-60 shrink-0 flex-col border-l border-hairline pl-3">
            <ZoneTitle>Tham số what-if</ZoneTitle>
            <p className="mb-2 shrink-0 text-[11px] leading-snug text-mut">
              Đánh dấu sản phẩm <span className="font-semibold text-sec">hết hàng</span> để xem hệ
              thống xếp hạng lại thẻ hành động.
            </p>
            <ul className="min-h-0 flex-1 space-y-1 overflow-y-auto">
              {(rec?.products ?? []).map((p) => {
                const off = rp.excluded.has(p.product_id);
                return (
                  <li key={p.product_id}>
                    <label
                      className={`flex cursor-pointer items-center gap-2 rounded border px-2 py-1.5 text-xs transition-colors ${
                        off
                          ? "border-critical/60 bg-critical/10 text-sec"
                          : "border-hairline bg-raised text-ink hover:border-mut"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={off}
                        onChange={() => rp.toggleExcluded(p.product_id)}
                        className="accent-[#d03b3b]"
                      />
                      <span className={`min-w-0 flex-1 truncate ${off ? "line-through" : ""}`}>
                        {p.name}
                      </span>
                      {off && (
                        <span className="shrink-0 text-[10px] font-bold text-critical">
                          HẾT HÀNG
                        </span>
                      )}
                    </label>
                  </li>
                );
              })}
            </ul>
          </aside>
        </section>

        {/* Zone 3 — radar + feed over the recorded comments */}
        <section className="flex min-h-0 flex-col rounded-lg border border-hairline bg-surface p-3">
          <ZoneTitle>Radar bình luận · 5 phút quanh vị trí phát</ZoneTitle>
          <div className="min-h-0 flex-[2]">
            <CommentRadar comments={rp.visibleComments} nowS={rp.t} />
          </div>
          <div className="mt-2 flex min-h-0 flex-[3] flex-col border-t border-hairline pt-2">
            <CommentFeed comments={rp.visibleComments} />
          </div>
        </section>
      </div>
    </main>
  );
}
