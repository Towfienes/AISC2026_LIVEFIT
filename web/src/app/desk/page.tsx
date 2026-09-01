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
 * session is running, skeletons instead of a blank screen while connecting,
 * plain-Vietnamese labels, jargon explained in-context via <Term> tooltips.
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
import Button, { buttonCls } from "@/components/ui/Button";
import Callout from "@/components/ui/Callout";
import Card from "@/components/ui/Card";
import EmptyState from "@/components/ui/EmptyState";
import SectionTitle from "@/components/ui/SectionTitle";
import Skeleton from "@/components/ui/Skeleton";
import { useDesk } from "@/lib/useDesk";

/** Mirror of the three-zone layout while the first connection is racing. */
function DeskSkeleton() {
  return (
    <main className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden p-3" aria-busy>
      <Skeleton className="h-11 shrink-0 rounded-lg" />
      <Card padding="sm" className="flex min-h-0 basis-[40%] flex-col gap-2">
        <div className="flex items-center justify-between">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-3 w-40" />
        </div>
        <Skeleton className="min-h-0 flex-1" />
        <Skeleton className="h-7 shrink-0" />
      </Card>
      <div className="grid min-h-0 flex-1 grid-cols-2 gap-3">
        <Card padding="sm" className="flex min-h-0 flex-col gap-2">
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </Card>
        <Card padding="sm" className="flex min-h-0 flex-col gap-2">
          <Skeleton className="h-3 w-40" />
          <Skeleton className="min-h-0 flex-[2]" />
          <div className="flex min-h-0 flex-[3] flex-col gap-1.5 border-t border-hairline pt-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-4 w-4/5" />
          </div>
        </Card>
      </div>
    </main>
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
    <div className="flex flex-1 flex-col items-center justify-center">
      <EmptyState
        icon="📭"
        title="Chưa có phiên nào đang chạy"
        hint="Bàn điều khiển sẽ hiển thị nhịp phiên, thẻ gợi ý và bình luận khi một phiên live bắt đầu. Trong lúc chờ, bạn có thể xem thử với dữ liệu mô phỏng."
        action={
          <>
            <Button onClick={onDemo}>Xem thử với dữ liệu mô phỏng</Button>
            <Link href="/" className={buttonCls("ghost")}>
              Về trang chính
            </Link>
          </>
        }
      />
      {hasEndedSessions && (
        <button
          type="button"
          onClick={onShowAnyway}
          className="focus-ring rounded text-xs text-mut underline decoration-dotted underline-offset-2 transition-colors duration-150 hover:text-sec"
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
        <DeskSkeleton />
      ) : showEmpty ? (
        <EmptyDesk
          hasEndedSessions={desk.sessions.length > 0}
          onDemo={() => setDemoMode(true)}
          onShowAnyway={() => setShowAnyway(true)}
        />
      ) : (
        <main className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden p-3">
          {/* compact toolbar: picker · status · vitals · mode */}
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

          {/* degraded-data banner: slim, amber, right under the toolbar */}
          {desk.degraded && (
            <Callout tone="warn" slim className="shrink-0">
              <strong>Dữ liệu suy giảm</strong> — {desk.degraded}. Bàn vẫn chạy với các nguồn còn
              lại.
            </Callout>
          )}

          {/* Zone 1 — nhịp phiên + dải khối switchback */}
          <Card as="section" padding="sm" className="flex min-h-0 basis-[40%] flex-col">
            <SectionTitle
              className="mb-1.5"
              meta={
                <>
                  Đang ghim:{" "}
                  <span className="font-semibold text-ink">{desk.pinned?.name ?? "—"}</span>
                </>
              }
            >
              Nhịp phiên
            </SectionTitle>
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
          </Card>

          <div className="grid min-h-0 flex-1 grid-cols-2 gap-3">
            {/* Zone 2 — action cards */}
            <Card as="section" padding="sm" className="flex min-h-0 flex-col">
              <SectionTitle
                className="mb-1.5"
                meta={<>chế độ {desk.mode === "auto" ? "tự động" : "gợi ý"}</>}
              >
                Hành động gợi ý
              </SectionTitle>
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
            </Card>

            {/* Zone 3 — comment radar + feed */}
            <Card as="section" padding="sm" className="flex min-h-0 flex-col">
              <SectionTitle className="mb-1.5" meta="5 phút gần nhất">
                Radar bình luận
              </SectionTitle>
              <div className="min-h-0 flex-[2]">
                <CommentRadar comments={desk.comments} nowS={desk.elapsedS} />
              </div>
              <div className="mt-2 flex min-h-0 flex-[3] flex-col border-t border-hairline pt-2">
                <CommentFeed comments={desk.comments} />
              </div>
            </Card>
          </div>
        </main>
      )}
    </div>
  );
}
