"use client";

/**
 * "/replay" — Replay Engine demo (E6-06).
 *
 * Plays a finished session's recorded data back through the same three-zone
 * layout as the live desk, with transport controls and a what-if parameter
 * panel: toggling "hết hàng" on a product re-ranks / removes its action cards
 * client-side. While the recording loads, every zone shows a skeleton instead
 * of an empty panel.
 */

import Link from "next/link";

import ActionCard from "@/components/ActionCard";
import BlockStrip from "@/components/BlockStrip";
import CommentFeed from "@/components/CommentFeed";
import CommentRadar from "@/components/CommentRadar";
import ReplayControls from "@/components/ReplayControls";
import RhythmChart from "@/components/RhythmChart";
import { DemoBadge } from "@/components/StatusBar";
import { buttonCls } from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import SectionTitle from "@/components/ui/SectionTitle";
import Skeleton from "@/components/ui/Skeleton";
import { fmtDateHCM } from "@/lib/format";
import { useReplay } from "@/lib/useReplay";

export default function ReplayPage() {
  const rp = useReplay();
  const rec = rp.recording;
  const loading = rp.connection === "connecting" || (rp.sessionId != null && !rec);
  const recordedOn = rec?.session.start_ts ? fmtDateHCM(rec.session.start_ts) : "—";
  /**
   * Gói B-PROBE: dải băng vàng trước đây in "PHÁT LẠI DỮ LIỆU THẬT" trong MỌI
   * trạng thái — kể cả khi trang đang chạy bản ghi mô phỏng vì máy chủ không
   * gọi được. Trang chủ đưa người dùng sang đúng đường đó khi máy chủ chết
   * hoặc kho suy giảm, nên câu này phải nói đúng thứ đang nằm trên màn hình.
   */
  const isMock = rp.connection === "mock";

  return (
    <main className="flex h-screen flex-col gap-3 overflow-hidden bg-page p-3">
      {/* header + provenance banner */}
      <header className="flex h-bar shrink-0 items-center gap-3 rounded-lg border border-hairline bg-surface px-3">
        <Link
          href="/"
          className="focus-ring flex shrink-0 items-center rounded text-body font-bold tracking-tight text-ink"
        >
          LiveLift <span className="ml-1 font-normal text-dim">· phát lại phiên</span>
        </Link>
        {isMock && <DemoBadge />}
        <div className="ml-auto flex min-w-0 items-center gap-2 rounded-md border border-warn/60 bg-warn/10 px-3 py-1">
          <span aria-hidden className="text-warn-ink">
            ⏮
          </span>
          <span className="truncate text-meta font-bold tracking-wide text-warn-ink">
            {isMock
              ? "PHÁT LẠI DỮ LIỆU MÔ PHỎNG — không phải buổi live thật"
              : `PHÁT LẠI DỮ LIỆU THẬT — ghi ngày ${recordedOn}`}
          </span>
        </div>
        {/* Gói UI-KOL: người bán đang xem lại buổi live thường muốn biết
            "cả buổi ra sao" chứ không chỉ phút đang tua — nút này mở thẳng
            báo cáo sau phiên của ĐÚNG phiên đang phát lại. Tắt khi chưa chọn
            được phiên nào (mock/đang tải) thay vì dẫn tới trang 404. */}
        {rp.sessionId && rp.connection !== "mock" ? (
          <Link
            href={`/bao-cao/${rp.sessionId}`}
            className={`${buttonCls("ghost", "sm")} shrink-0`}
          >
            Báo cáo phiên →
          </Link>
        ) : null}
      </header>

      {/* Câu định vị trang (PageHeader d1, bản một-dòng cho màn h-screen):
          trang này để làm gì — cho ai — khi nào dùng. */}
      <p className="shrink-0 px-1 text-meta leading-snug text-dim">
        <span className="mr-1.5 font-semibold uppercase tracking-[0.08em] text-good-ink">
          Sau live
        </span>
        Xem lại phiên — tua lại một buổi đã phát theo từng phút, thử &quot;nếu-thì&quot; với tồn
        kho; không đụng gì tới dữ liệu gốc.
      </p>

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
      <Card as="section" padding="sm" className="flex min-h-0 basis-[36%] flex-col">
        <SectionTitle className="mb-1.5">Nhịp phiên (bản ghi)</SectionTitle>
        {loading ? (
          <div className="flex min-h-0 flex-1 flex-col gap-2" aria-busy>
            <Skeleton className="min-h-0 flex-1" />
            <Skeleton className="h-7 shrink-0" />
          </div>
        ) : (
          <>
            <div className="min-h-0 flex-1">
              <RhythmChart ticks={rp.visibleTicks} />
            </div>
            <div className="mt-2 shrink-0">
              <BlockStrip
                blocks={rec?.blocks ?? []}
                durationS={rec?.duration_s ?? 0}
                positionS={rp.t}
              />
            </div>
          </>
        )}
      </Card>

      <div className="grid min-h-0 flex-1 grid-cols-2 gap-3">
        {/* Zone 2 — cards + what-if parameter panel */}
        <Card as="section" padding="sm" className="flex min-h-0">
          <div className="flex min-h-0 min-w-0 flex-1 flex-col pr-3">
            <SectionTitle
              className="mb-1.5"
              meta={rec ? (rp.cardsFromServer ? "thẻ từ máy chủ" : "tổng hợp lại phía client") : undefined}
            >
              Hành động gợi ý
            </SectionTitle>
            <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
              {loading ? (
                <div className="flex flex-col gap-2" aria-busy>
                  <Skeleton className="h-24" />
                  <Skeleton className="h-24" />
                  <Skeleton className="h-24" />
                </div>
              ) : rp.cards.length === 0 ? (
                <div className="px-2 py-4 text-body text-dim">
                  Không còn thẻ nào cho thời điểm này (kiểm tra tham số bên phải).
                </div>
              ) : (
                rp.cards.map((c) => (
                  <ActionCard
                    key={c.card_id}
                    card={c}
                    mode={rec?.session.mode ?? "suggest"}
                    readOnly
                  />
                ))
              )}
            </div>
          </div>

          {/* parameter panel */}
          <aside className="flex w-60 shrink-0 flex-col border-l border-hairline pl-3">
            <SectionTitle className="mb-1.5">Tham số what-if</SectionTitle>
            <p className="mb-2 shrink-0 text-meta leading-snug text-dim">
              Đánh dấu sản phẩm <span className="font-semibold text-sec">hết hàng</span> để xem
              hệ thống xếp hạng lại thẻ hành động.
            </p>
            {loading ? (
              <div className="flex flex-col gap-1.5" aria-busy>
                <Skeleton className="h-8" />
                <Skeleton className="h-8" />
                <Skeleton className="h-8" />
                <Skeleton className="h-8" />
              </div>
            ) : (
              <ul className="min-h-0 flex-1 space-y-1 overflow-y-auto">
                {(rec?.products ?? []).map((p) => {
                  const off = rp.excluded.has(p.product_id);
                  return (
                    <li key={p.product_id}>
                      <label
                        className={`flex min-h-ctl cursor-pointer items-center gap-2 rounded-md border px-2 py-1.5 text-meta transition-colors duration-short2 ease-emphasized ${
                          off
                            ? "border-critical/60 bg-critical/10 text-sec"
                            : "border-hairline bg-raised text-ink hover:border-white/20"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={off}
                          onChange={() => rp.toggleExcluded(p.product_id)}
                          className="focus-ring accent-[#d03b3b]"
                        />
                        <span className={`min-w-0 flex-1 truncate ${off ? "line-through" : ""}`}>
                          {p.name}
                        </span>
                        {off && (
                          <span className="shrink-0 text-meta font-bold text-crit-ink">
                            HẾT HÀNG
                          </span>
                        )}
                      </label>
                    </li>
                  );
                })}
              </ul>
            )}
          </aside>
        </Card>

        {/* Zone 3 — radar + feed over the recorded comments */}
        <Card as="section" padding="sm" className="flex min-h-0 flex-col">
          <SectionTitle className="mb-1.5" meta="5 phút quanh vị trí phát">
            Radar bình luận
          </SectionTitle>
          {loading ? (
            <div className="flex min-h-0 flex-1 flex-col gap-2" aria-busy>
              <Skeleton className="min-h-0 flex-[2]" />
              <div className="flex min-h-0 flex-[3] flex-col gap-1.5 border-t border-hairline pt-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-2/3" />
                <Skeleton className="h-4 w-4/5" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            </div>
          ) : (
            <>
              <div className="min-h-0 flex-[2]">
                <CommentRadar comments={rp.visibleComments} nowS={rp.t} />
              </div>
              <div className="mt-2 flex min-h-0 flex-[3] flex-col border-t border-hairline pt-2">
                <CommentFeed comments={rp.visibleComments} />
              </div>
            </>
          )}
        </Card>
      </div>
    </main>
  );
}
