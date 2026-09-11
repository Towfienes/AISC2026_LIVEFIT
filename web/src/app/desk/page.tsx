"use client";

/**
 * "/desk" — Bàn điều khiển (control desk). OPERATOR screen: it is the one view
 * that is allowed to see the assignment. Nothing here may import HostView,
 * useHost or HostState — the blinding boundary (rule L6) runs along this file.
 *
 * ---------------------------------------------------------------------------
 * LAYOUT (rebuilt in gói UI-2)
 * ---------------------------------------------------------------------------
 * The previous layout was a fixed three-zone fit for 1920x1080 with two nested
 * `overflow-hidden` planes and NOT ONE breakpoint. On the 1366x768 laptop most
 * operators actually use, the "lượt bấm/phút" panel — the primary outcome of
 * the experiment — collapsed to about 4 px and the action-card column was
 * clipped to a third of a card, with no scrollbar to say so. At 1920x1080 the
 * same rigid split left ~141 px of dead space under the cards.
 *
 * The desk is now a flowing document with a priority order, not a fitted
 * dashboard (gói UI-KOL adds the media row — video + signal tiles — WITHOUT
 * touching priority 1: the block clock stays the desk's scientific identity,
 * the video is auxiliary context and is the FIRST thing to give way):
 *
 *   1. đồng hồ khối  — sticky at the top, never scrolls away;
 *   2. thẻ hành động — own column from `xl` up, first panel below `xl`;
 *   3. dải thẻ tín hiệu + khung video — tiles are honest (a source that
 *      cannot measure renders "THIẾU nguồn" with the matrix reason, never 0);
 *      the video defaults to a collapsed button below `xl`;
 *   4. biểu đồ nhịp  — `min-h` floors so it can never collapse again;
 *   5. radar + feed  — the data panel that gives way first (video gives first).
 *
 * When the content no longer fits, the page SCROLLS (the browser scrollbar is
 * the indicator, and the card list adds its own "cuộn để xem hết" line) instead
 * of silently cutting content off.
 *
 * First-time-user rules: an empty state instead of a blank screen when no
 * session is running, skeletons instead of a blank screen while connecting,
 * plain-Vietnamese labels, jargon explained in-context via <Term> tooltips.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import ActionCard from "@/components/ActionCard";
import BlockClock from "@/components/BlockClock";
import CommentFeed from "@/components/CommentFeed";
import CommentRadar from "@/components/CommentRadar";
import LiveVideo from "@/components/LiveVideo";
import RhythmChart from "@/components/RhythmChart";
import SignalTiles, { buildSignalTiles } from "@/components/SignalTiles";
import StatusBar from "@/components/StatusBar";
import TopNav from "@/components/TopNav";
import Button, { buttonCls } from "@/components/ui/Button";
import Callout from "@/components/ui/Callout";
import Card from "@/components/ui/Card";
import EmptyState from "@/components/ui/EmptyState";
import SectionTitle from "@/components/ui/SectionTitle";
import Skeleton from "@/components/ui/Skeleton";
import { getReactions, getSessionDetail, getSignalCoverage, youtubeVideoId } from "@/lib/api";
import type { ActionCardData, SessionDetail, SignalCoverage } from "@/lib/types";
import { useDesk } from "@/lib/useDesk";

/** Clicks landed in the last 60 s — ticks are 30 s buckets, so this is the tail. */
function clicksInLastMinute(
  ticks: { offset_s: number; click_count: number }[],
  nowS: number,
): number | null {
  const recent = ticks.filter((t) => t.offset_s > nowS - 60 && t.offset_s <= nowS);
  if (recent.length === 0) return null;
  return recent.reduce((sum, t) => sum + t.click_count, 0);
}

/**
 * True while a scroll container has more content than it shows. Drives the
 * explicit "cuộn để xem hết" line: a 8 px recessive scrollbar is not a strong
 * enough signal on a desk the operator only glances at.
 */
function useIsOverflowing(key: unknown) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [overflowing, setOverflowing] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const check = () => setOverflowing(el.scrollHeight - el.clientHeight > 4);
    check();
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(check);
    ro.observe(el);
    return () => ro.disconnect();
  }, [key]);
  return { ref, overflowing };
}

/**
 * Mirror of the layout while the first connection is racing.
 *
 * Khung xám không nói được là đang TẢI hay đã HỎNG, nên có thêm một dòng
 * `role="status"`: nó cũng là chỗ trình đọc màn hình biết bàn đang bận.
 */
function DeskSkeleton() {
  return (
    <main className="flex flex-1 flex-col p-3" aria-busy>
      <p role="status" className="mb-2 shrink-0 text-body text-sec">
        Đang kết nối tới máy chủ và tải phiên đang phát… Bàn sẽ hiện ngay khi có dữ liệu, bạn không
        cần tải lại trang.
      </p>
      <div className="mb-3 flex flex-col gap-3">
        <Skeleton className="h-bar shrink-0 rounded-lg" />
        <Card padding="sm" className="flex flex-col gap-3">
          <Skeleton className="h-4 w-32" />
          <div className="flex flex-wrap items-end gap-6">
            <Skeleton className="h-20 w-56" />
            <Skeleton className="h-16 w-40" />
            <Skeleton className="ml-auto h-14 w-32" />
            <Skeleton className="h-14 w-32" />
          </div>
          <Skeleton className="h-2 w-full rounded-full" />
          <Skeleton className="h-9 w-full" />
        </Card>
      </div>
      <div className="grid flex-1 grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(22rem,30rem)] xl:grid-rows-[auto_minmax(20rem,3fr)_minmax(16rem,2fr)]">
        <Card
          padding="sm"
          className="flex min-h-[16rem] flex-col gap-2 xl:col-start-2 xl:row-span-3 xl:row-start-1"
        >
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </Card>
        {/* dải media: khung video + 4 thẻ tín hiệu (gói UI-KOL) */}
        <div className="flex flex-col gap-3 lg:flex-row xl:col-start-1 xl:row-start-1">
          <Skeleton className="h-40 rounded-lg lg:basis-[24rem] lg:shrink-0" />
          {/* hai cột minmax — không dùng grid-cols-2 cứng (gate bố cục UI-2) */}
          <div className="grid flex-1 grid-cols-[repeat(2,minmax(0,1fr))] gap-2">
            <Skeleton className="h-[4.5rem]" />
            <Skeleton className="h-[4.5rem]" />
            <Skeleton className="h-[4.5rem]" />
            <Skeleton className="h-[4.5rem]" />
          </div>
        </div>
        <Card
          padding="sm"
          className="flex min-h-[20rem] flex-col gap-2 xl:col-start-1 xl:row-start-2"
        >
          <Skeleton className="h-4 w-24" />
          <Skeleton className="min-h-[14rem] flex-1" />
        </Card>
        <Card
          padding="sm"
          className="flex min-h-[16rem] flex-col gap-2 xl:col-start-1 xl:row-start-3"
        >
          <Skeleton className="h-4 w-40" />
          <Skeleton className="min-h-[6rem] flex-[2]" />
          <div className="flex min-h-[6rem] flex-[3] flex-col gap-1.5 border-t border-hairline pt-2">
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-5 w-2/3" />
            <Skeleton className="h-5 w-4/5" />
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
          className="focus-ring flex min-h-ctl items-center rounded px-3 text-body text-dim underline decoration-dotted underline-offset-2 transition-colors duration-short2 ease-emphasized hover:text-sec"
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
  const [endBusy, setEndBusy] = useState(false);
  /**
   * Lỗi vận hành đang chờ người xử lý. Một ô duy nhất trên StatusBar cho cả
   * lệnh Thực hiện lẫn Kết thúc phiên: hai chỗ báo lỗi khác nhau là hai chỗ có
   * thể bỏ sót.
   */
  const [alert, setAlert] = useState<string | null>(null);
  const desk = useDesk({ forceMock: demoMode });

  const clicksPerMin = useMemo(
    () => clicksInLastMinute(desk.ticks, desk.elapsedS),
    [desk.ticks, desk.elapsedS],
  );
  const cardList = useIsOverflowing(desk.cards.length);

  /**
   * Gói UI-KOL: session detail (video id for the embed), the signal matrix
   * (what this session can honestly measure) and the paid-event count. The
   * matrix is the AUTHORITY for the signal tiles: a tile whose source is
   * missing renders "THIẾU nguồn" with the server's reason — never a fake 0.
   */
  const [videoDetail, setVideoDetail] = useState<SessionDetail | null>(null);
  const [signalCov, setSignalCov] = useState<SignalCoverage | null>(null);
  const [reactionsTotal, setReactionsTotal] = useState<number | null>(null);

  useEffect(() => {
    setVideoDetail(null);
    setSignalCov(null);
    setReactionsTotal(null);
    if (desk.connection !== "live" || !desk.sessionId) return;
    const sid = desk.sessionId;
    let cancelled = false;
    getSessionDetail(sid)
      .then((d) => {
        if (!cancelled) setVideoDetail(d);
      })
      .catch(() => {
        // không tải được chi tiết phiên: khung video hiện trạng thái thiếu
      });
    const pullMatrix = () => {
      getSignalCoverage(sid)
        .then((c) => {
          if (!cancelled) setSignalCov(c);
        })
        .catch(() => {
          // ma trận chưa tải được: ô tín hiệu giữ trạng thái "—", không đoán
        });
      getReactions(sid)
        .then((rs) => {
          if (!cancelled) setReactionsTotal(rs.length);
        })
        .catch(() => {
          // thiếu số đếm thì ô Tim & quà hiện "—" thay vì một số bịa
        });
    };
    pullMatrix();
    // Ma trận đổi chậm (nguồn xuất hiện/mất theo phút) — 30 giây là đủ tươi.
    const timer = setInterval(pullMatrix, 30000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [desk.connection, desk.sessionId]);

  const tiles = useMemo(
    () =>
      buildSignalTiles({
        signals: signalCov,
        connection: desk.connection,
        viewers: desk.viewers,
        ticks: desk.ticks,
        clicksPerMin,
        reactionsTotal,
      }),
    [signalCov, desk.connection, desk.viewers, desk.ticks, clicksPerMin, reactionsTotal],
  );

  /** Phiên replay không còn lộ CCU quá khứ — số 0 trong tick là chỗ trống,
   * KHÔNG phải phép đo (signals.py), nên đồng hồ khối hiện "—" thay vì 0. */
  const isReplaySession = desk.session?.platform === "replay";

  /**
   * Cùng luật cho lượt bấm: khi ma trận tín hiệu nói phiên KHÔNG có link đo
   * (clicks = missing), tổng click_count của các tick chỉ là chỗ trống — đồng
   * hồ khối phải hiện "—" như ô THIẾU bên dưới, không phải một số 0 giả.
   * Chưa có ma trận (mock/đang tải) thì giữ số đo hiện có.
   */
  const clicksUnmeasured =
    signalCov?.signals.some((s) => s.name === "clicks" && s.status === "missing") ?? false;
  const honestClicksPerMin = clicksUnmeasured ? null : clicksPerMin;

  /**
   * Cùng ma trận, cùng luật, áp cho BIỂU ĐỒ NHỊP PHIÊN — khung lớn nhất của
   * bàn. Trước gói UI-KOL nó luôn vẽ hai đường "người xem" và "lượt bấm/phút";
   * trên phiên replay cả hai nguồn đều không tồn tại nên biểu đồ vẽ hai đường
   * phẳng ở mức 0, mâu thuẫn thẳng với ô "THIẾU nguồn" ngay phía trên. Nay
   * panel nào không có nguồn thì hiện dải THIẾU kèm lý do của máy chủ.
   */
  const missingReason = (name: string): string | null => {
    const s = signalCov?.signals.find((x) => x.name === name);
    return s && s.status === "missing" ? s.detail : null;
  };
  const viewersMissingReason = missingReason("ticks");
  const clicksMissingReason = missingReason("clicks");
  /**
   * Phiên QUAN SÁT: máy chủ nói không có lịch gán ngẫu nhiên. Hai chỗ trên bàn
   * phải nói thật thay vì hứa hão — đồng hồ khối (không có khối nào để ở
   * "ngoài") và cột thẻ hành động (sẽ KHÔNG BAO GIỜ có thẻ, nên câu "thẻ mới
   * sẽ tự hiện trong vài phút đầu phiên" là một lời hứa sai).
   */
  const observational = missingReason("schedule") != null;

  /**
   * `useDesk.execute` THROWS when the API refuses the command (and rolls the
   * card back out of the executed set). The old call site was
   * `onExecute={() => void desk.execute(c)}`: the rejection went to an unhandled
   * promise, the card quietly un-executed itself, and the operator was never
   * told the pin had not happened.
   */
  const runCard = (card: ActionCardData) => {
    setAlert(null);
    desk.execute(card).catch((e: unknown) => {
      const detail = e instanceof Error ? e.message : "Máy chủ không nhận lệnh.";
      setAlert(
        `Không thực hiện được thẻ “${card.headline}”: ${detail} ` +
          "Thẻ đã được trả lại danh sách — kiểm tra kết nối rồi bấm Thực hiện lại.",
      );
    });
  };

  const endSession = () => {
    if (
      !window.confirm(
        "Kết thúc phiên ngay bây giờ? Các khối chưa chạy sẽ không được tính vào kết quả.",
      )
    ) {
      return;
    }
    setEndBusy(true);
    setAlert(null);
    desk
      .endSession()
      .catch((e: unknown) => {
        setAlert(e instanceof Error ? e.message : "Không kết thúc được phiên — thử lại.");
      })
      .finally(() => setEndBusy(false));
  };

  const hasLive = desk.sessions.some((s) => s.status === "live");
  const showEmpty =
    desk.connection !== "connecting" &&
    !showAnyway &&
    (desk.sessionId == null || (desk.connection === "live" && !hasLive));

  return (
    <div className="flex min-h-screen flex-col bg-page">
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
        <main className="flex flex-1 flex-col p-3">
          {/* Ưu tiên 1 — thanh trạng thái, cảnh báo và ĐỒNG HỒ KHỐI dính đầu
              màn hình: khi trang phải cuộn (1366x768) đây là những thứ người
              vận hành không được phép mất khỏi tầm mắt. */}
          <div className="sticky top-0 z-20 -mx-3 -mt-3 mb-3 flex flex-col gap-3 bg-page px-3 pb-3 pt-3">
            <StatusBar
              connection={desk.connection}
              wsStatus={desk.wsStatus}
              sessions={desk.sessions}
              sessionId={desk.sessionId}
              onSelectSession={desk.setSessionId}
              elapsedS={desk.elapsedS}
              durationS={desk.durationS}
              mode={desk.mode}
              onSetMode={desk.setMode}
              canToggleMode={desk.canToggleMode}
              onEndSession={endSession}
              canEndSession={desk.canEndSession}
              endBusy={endBusy}
              designHash={desk.designHash}
              alert={alert}
              onDismissAlert={() => setAlert(null)}
            />

            {/* degraded-data banner: amber, right under the toolbar */}
            {desk.degraded && (
              <Callout tone="warn" className="shrink-0">
                <strong>Dữ liệu suy giảm</strong> — {desk.degraded}. Bàn vẫn chạy với các nguồn còn
                lại.
              </Callout>
            )}

            <BlockClock
              blocks={desk.blocks}
              currentBlock={desk.currentBlock}
              elapsedS={desk.elapsedS}
              durationS={desk.durationS}
              viewers={isReplaySession ? null : desk.viewers}
              clicksPerMin={honestClicksPerMin}
              pinnedName={desk.pinned?.name ?? null}
              observational={observational}
            />
          </div>

          {/* Cột phải giữ nguyên bề rộng thẻ hành động ở mọi màn ≥ xl; cột trái
              co giãn. Các `minmax(...)` là sàn chiều cao — lý do biểu đồ không
              còn sập được về 4px. Hàng đầu (`auto`) là dải media của gói
              UI-KOL: video + thẻ tín hiệu — không có sàn vì video là vùng
              NHƯỜNG CHỖ ĐẦU TIÊN khi màn chật (ưu tiên G của spec). */}
          <div className="grid flex-1 grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(22rem,30rem)] xl:grid-rows-[auto_minmax(20rem,3fr)_minmax(16rem,2fr)]">
            {/* Ưu tiên 2 — thẻ hành động */}
            <Card
              as="section"
              padding="sm"
              className="flex min-h-[16rem] min-w-0 flex-col xl:col-start-2 xl:row-span-3 xl:row-start-1"
            >
              <SectionTitle
                className="mb-1.5"
                meta={<>chế độ {desk.mode === "auto" ? "tự động" : "gợi ý"}</>}
              >
                Hành động gợi ý
              </SectionTitle>
              {/* Khung cuộn `absolute` trong hộp `relative` — cùng lý do với
                  feed bình luận: nội dung của một lớp absolute không đóng góp
                  chiều cao cho lưới `3fr`/`2fr` cao không xác định, nên 10 thẻ
                  không thể tự kéo dài hàng lưới và đẩy cả trang phải cuộn. */}
              <div className="relative min-h-0 flex-1">
                <div
                  ref={cardList.ref}
                  className="absolute inset-0 flex flex-col justify-start gap-2 overflow-y-auto pr-1"
                >
                  {desk.cards.length === 0 ? (
                    <div className="px-2 py-4">
                      <p className="text-body text-sec">
                        {observational
                          ? "Phiên quan sát — không có thẻ hành động."
                          : "Chưa có gợi ý cho thời điểm này."}
                      </p>
                      <p className="mt-1 text-body leading-snug text-dim">
                        {observational
                          ? "Đây là buổi live của người khác, nạp lại để phân tích: hệ thống không " +
                            "ghim được sản phẩm nào và cũng không có link đo để xếp hạng, nên sẽ " +
                            "không có thẻ nào xuất hiện. Dải tín hiệu và nhịp bình luận bên trái " +
                            "vẫn là số liệu thật của buổi đó."
                          : "Thẻ mới sẽ tự hiện khi hệ thống đủ số liệu — thường trong vài phút " +
                            "đầu phiên. Trong lúc đó cứ vận hành như thường lệ; bạn không cần chờ " +
                            "thẻ để ghim sản phẩm."}
                      </p>
                    </div>
                  ) : (
                    desk.cards.map((c) => (
                      <ActionCard
                        key={c.card_id}
                        card={c}
                        mode={desk.mode}
                        executed={desk.executedCardIds.has(c.card_id)}
                        onExecute={() => runCard(c)}
                        onSkip={() => desk.skip(c.card_id)}
                      />
                    ))
                  )}
                </div>
              </div>
              {cardList.overflowing && (
                <p className="mt-2 shrink-0 text-body text-warn-ink">
                  ↓ Danh sách dài hơn khung — cuộn để xem hết {desk.cards.length} thẻ.
                </p>
              )}
              <p className="mt-2 shrink-0 border-t border-hairline pt-2 text-body leading-snug text-dim">
                {desk.mode === "auto"
                  ? "Chế độ tự động: hệ thống tự ghim thẻ hạng 1 khi đếm ngược về 0."
                  : "Chế độ gợi ý: hệ thống chỉ đề xuất — sản phẩm chỉ được ghim khi bạn bấm Thực hiện."}
              </p>
            </Card>

            {/* Ưu tiên 3 (gói UI-KOL) — dải media: khung video (bối cảnh, thu
                gọn được và mặc định thu gọn dưới xl) + 4 thẻ tín hiệu trung
                thực. Dưới lg các thẻ tín hiệu đứng TRƯỚC video (thứ tự nhường
                chỗ G: dữ liệu là nhiệm vụ, video là tiện nghi). */}
            <div className="flex min-w-0 flex-col gap-3 lg:flex-row xl:col-start-1 xl:row-start-1">
              <LiveVideo
                videoId={youtubeVideoId(videoDetail)}
                platform={desk.session?.platform ?? null}
                className="order-2 min-w-0 lg:order-1 lg:basis-[24rem] lg:shrink-0 2xl:basis-[34rem]"
              />
              <SignalTiles
                tiles={tiles}
                className="order-1 min-w-0 flex-1 lg:order-2"
                meta={
                  desk.sessionId ? (
                    <Link
                      href={`/bao-cao/${desk.sessionId}`}
                      className="focus-ring rounded underline decoration-dotted underline-offset-2 transition-colors duration-short2 ease-emphasized hover:text-ink"
                    >
                      Báo cáo phiên →
                    </Link>
                  ) : undefined
                }
              />
            </div>

            {/* Ưu tiên 4 — nhịp phiên (chỉ số đầu ra chính của thí nghiệm) */}
            <Card
              as="section"
              padding="sm"
              className="flex min-h-[20rem] min-w-0 flex-col xl:col-start-1 xl:row-start-2"
            >
              <SectionTitle className="mb-1.5" meta="gộp theo phút">
                Nhịp phiên
              </SectionTitle>
              {/* Trạng thái rỗng nằm TRONG RhythmChart: nó biết cần mấy phút
                  số liệu mới vẽ được đường, trang thì không. */}
              <div className="min-h-[14rem] flex-1">
                <RhythmChart
                  ticks={desk.ticks}
                  viewersMissing={viewersMissingReason}
                  clicksMissing={clicksMissingReason}
                />
              </div>
            </Card>

            {/* Ưu tiên 5 — radar bình luận + feed */}
            <Card
              as="section"
              padding="sm"
              className="flex min-h-[16rem] min-w-0 flex-col xl:col-start-1 xl:row-start-3"
            >
              <SectionTitle className="mb-1.5" meta="5 phút gần nhất">
                Radar bình luận
              </SectionTitle>
              <div className="min-h-[6rem] flex-[2]">
                <CommentRadar comments={desk.comments} nowS={desk.elapsedS} />
              </div>
              <div className="mt-2 flex min-h-[6rem] flex-[3] flex-col border-t border-hairline pt-2">
                <CommentFeed comments={desk.comments} />
              </div>
            </Card>
          </div>
        </main>
      )}
    </div>
  );
}
