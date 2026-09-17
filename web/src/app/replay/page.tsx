"use client";

/**
 * "/replay" — Replay Engine demo (E6-06).
 *
 * Plays a finished session's recorded data back through the same three-zone
 * layout as the live desk, with transport controls and a what-if parameter
 * panel: toggling "hết hàng" on a product re-ranks / removes its action cards
 * client-side. While the recording loads, every zone shows a skeleton instead
 * of an empty panel.
 *
 * ---------------------------------------------------------------------------
 * GÓI D — những gì trang này phải nói ĐÚNG
 * ---------------------------------------------------------------------------
 * - NHÃN NGUỒN DỮ LIỆU: dải băng từng chỉ xét `connection === "mock"` nên phiên
 *   gieo mẫu (`is_demo=true`, lấy từ máy chủ) bị in "PHÁT LẠI DỮ LIỆU THẬT" —
 *   đúng lúc giám khảo bấm "Bắt đầu xem thử". Nay nhãn đọc `session.is_demo`:
 *   mẫu → "DỮ LIỆU MẪU", mất máy chủ → "MÔ PHỎNG", chỉ phiên thật mới "THẬT";
 *   đang tải thì không khẳng định gì.
 * - MỞ ĐÚNG BUỔI: `?session=<id>` đọc bằng `useSearchParams` (bọc Suspense —
 *   build production của Next 14 bắt buộc) và ưu tiên tuyệt đối; chọn buổi
 *   khác trong ô chọn thì URL đổi theo, để link chép ra mở lại đúng buổi.
 * - KHÔNG CÒN KHUNG CHẾT: thẻ gợi ý + khung "nếu hết hàng" có nội dung khi có
 *   sản phẩm; rỗng thì câu rỗng nói đúng lý do (không còn "kiểm tra tham số
 *   bên phải" khi bên phải cũng trống).
 * - NGỮ CẢNH PHÁT LẠI: có TopNav như mọi trang; khung đầu đã tua sẵn tới phút
 *   có số liệu + một dòng nhắc bấm Phát; không mượn câu "bạn không cần bấm gì"
 *   của màn live; feed rỗng không hiện nút "Tạm dừng cuộn".
 *
 * KIỂM TOÁN 17/09:
 * - BUỔI CHẠY THỬ KHÔNG BAO GIỜ LÀ "THẬT": nguồn bình luận mô phỏng chỉ được
 *   ghi vào phiên `dry_run` hoặc `is_demo` (ingest_jobs.cho_phep_mo_phong), và
 *   payload bình luận không mang nền tảng — web không phân biệt được câu AI
 *   soạn với bình luận thật. Nên phiên `dry_run` luôn in "CHẠY THỬ", nói rõ
 *   bình luận/người xem CÓ THỂ là mô phỏng, kèm huy hiệu riêng.
 * - "Bắt đầu xem thử" (`?session=mock-…`) là bản mô phỏng ngoại tuyến kể cả
 *   khi máy chủ sống (useReplay, lý do `"sample"`).
 */

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback } from "react";

import ActionCard from "@/components/ActionCard";
import BlockStrip from "@/components/BlockStrip";
import CommentFeed from "@/components/CommentFeed";
import CommentRadar from "@/components/CommentRadar";
import ReplayControls from "@/components/ReplayControls";
import RhythmChart from "@/components/RhythmChart";
import TopNav from "@/components/TopNav";
import Badge from "@/components/ui/Badge";
import Button, { buttonCls } from "@/components/ui/Button";
import Callout from "@/components/ui/Callout";
import Card from "@/components/ui/Card";
import SectionTitle from "@/components/ui/SectionTitle";
import Skeleton from "@/components/ui/Skeleton";
import { fmtDateHCM, fmtElapsed } from "@/lib/format";
import type { SessionSummary } from "@/lib/types";
import { useReplay, type ReplayState } from "@/lib/useReplay";

export default function ReplayPage() {
  return (
    <div className="flex min-h-screen flex-col bg-page">
      <TopNav />
      {/* useSearchParams cần một ranh giới Suspense để `next build` không
          từ chối prerender trang này. */}
      <Suspense fallback={<ReplayLoading />}>
        <ReplayScreen />
      </Suspense>
    </div>
  );
}

function ReplayLoading() {
  return (
    <main className="flex flex-1 flex-col gap-3 p-3" aria-busy>
      <p role="status" className="px-1 text-body text-sec">
        Đang mở bản ghi phát lại…
      </p>
      <Skeleton className="h-bar" />
      <Skeleton className="h-[22rem]" />
    </main>
  );
}

/** Câu trên dải băng nguồn dữ liệu — chọn theo thứ ĐANG nằm trên màn hình. */
function provenanceText(rp: ReplayState, shown: SessionSummary | null): string {
  const isMock = rp.connection === "mock";
  if (isMock) {
    if (rp.mockReason === "no_ended") {
      return "PHÁT LẠI DỮ LIỆU MÔ PHỎNG — chưa có buổi nào kết thúc để xem lại";
    }
    if (rp.mockReason === "server") {
      return "PHÁT LẠI DỮ LIỆU MÔ PHỎNG — chưa kết nối được máy chủ, không phải buổi live thật";
    }
    if (rp.mockReason === "sample") {
      return "PHÁT LẠI DỮ LIỆU MÔ PHỎNG — bản xem thử ngoại tuyến, không phải buổi live thật";
    }
    return "PHÁT LẠI DỮ LIỆU MÔ PHỎNG — không phải buổi live thật";
  }
  if (!shown) return "Đang tải danh sách buổi đã phát…";
  if (shown.is_demo) {
    return "PHÁT LẠI DỮ LIỆU MẪU — phiên mô phỏng, không phải buổi live thật";
  }
  if (shown.dry_run) {
    return "PHÁT LẠI BUỔI CHẠY THỬ — không tính vào kết quả; bình luận và người xem có thể là mô phỏng";
  }
  const recordedOn = shown.start_ts ? fmtDateHCM(shown.start_ts) : "—";
  return `PHÁT LẠI DỮ LIỆU THẬT — ghi ngày ${recordedOn}`;
}

/** Link `?session=` không mở được đúng buổi: nói lý do, không lặng lẽ đổi buổi. */
function requestNotice(rp: ReplayState): string | null {
  if (rp.requestedStatus === "none" || rp.requestedStatus === "ok") return null;
  if (rp.connection === "mock") {
    if (rp.mockReason === "sample") {
      return "Không có bản xem thử này — đang phát bản mô phỏng gần nhất.";
    }
    return rp.mockReason === "no_ended"
      ? "Chưa có buổi nào kết thúc — đang phát bản mô phỏng thay cho buổi trong link."
      : "Chưa kết nối được máy chủ — đang phát bản mô phỏng thay cho buổi trong link.";
  }
  if (rp.requestedStatus === "not_ended") {
    return "Buổi trong link chưa kết thúc nên chưa xem lại được — đang mở buổi đã kết thúc gần nhất.";
  }
  return "Không tìm thấy buổi trong link — đang mở buổi đã kết thúc gần nhất.";
}

function ReplayScreen() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const requestedId = searchParams.get("session");
  const rp = useReplay(requestedId);
  const rec = rp.recording;
  const loading = rp.connection === "connecting" || (rp.sessionId != null && !rec);

  const { setSessionId } = rp;
  const selectSession = useCallback(
    (id: string) => {
      setSessionId(id);
      router.replace(`/replay?session=${encodeURIComponent(id)}`, { scroll: false });
    },
    [router, setSessionId],
  );

  const shown: SessionSummary | null =
    rec?.session ?? rp.sessions.find((s) => s.session_id === rp.sessionId) ?? null;
  /**
   * Gói B-PROBE: dải băng trước đây in "PHÁT LẠI DỮ LIỆU THẬT" trong MỌI
   * trạng thái — kể cả khi trang đang chạy bản ghi mô phỏng vì máy chủ không
   * gọi được. Gói D: và cả khi phiên lấy từ máy chủ là DỮ LIỆU MẪU
   * (`is_demo`) — nhãn nay xét cả hai.
   */
  const isMock = rp.connection === "mock";
  const isSample = isMock || shown?.is_demo === true;
  const isDryRun = !isSample && shown?.dry_run === true;
  const notice = requestNotice(rp);

  return (
    <main className="flex flex-1 flex-col gap-3 p-3">
      {/* tiêu đề + dải băng nguồn dữ liệu */}
      <header className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <div className="min-w-0 flex-1 basis-72">
          <p className="text-meta font-semibold uppercase tracking-[0.08em] text-good-ink">
            Sau live
          </p>
          <h1 className="font-display text-title text-ink">Xem lại phiên</h1>
          <p className="text-meta leading-snug text-dim">
            Tua lại một buổi đã phát theo từng phút, thử &quot;nếu hết hàng&quot; — không đụng gì
            tới dữ liệu gốc.
          </p>
        </div>
        {isSample ? <Badge tone="warn">DEMO — dữ liệu mẫu</Badge> : null}
        {isDryRun ? <Badge tone="warn">CHẠY THỬ — không tính kết quả</Badge> : null}
        <div className="flex min-w-0 items-center gap-2 rounded-md border border-warn/60 bg-warn/10 px-3 py-1">
          <span aria-hidden className="text-warn-ink">
            ⏮
          </span>
          <span className="text-meta font-bold tracking-wide text-warn-ink">
            {provenanceText(rp, shown)}
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

      {notice ? <Callout slim>{notice}</Callout> : null}

      <ReplayControls
        sessions={rp.sessions}
        sessionId={rp.sessionId}
        onSelectSession={selectSession}
        t={rp.t}
        durationS={rec?.duration_s ?? 0}
        playing={rp.playing}
        onTogglePlay={rp.togglePlay}
        speed={rp.speed}
        onSetSpeed={rp.setSpeed}
        onSeek={rp.seek}
        disabled={!rec}
      />

      {/* Dòng nhắc việc cần làm — LUÔN chiếm chỗ (đổi chữ, không đổi chiều
          cao) để bấm Phát/Tạm dừng không làm cả trang giật xuống. */}
      <p className="flex min-h-tap items-center gap-2 px-1 text-body text-sec">
        <span aria-hidden className="text-brand-ink">
          {rp.playing ? "❚❚" : "▶"}
        </span>
        {playPrompt(rp)}
      </p>

      {/* Zone 1 — same rhythm + block strip as the live desk */}
      <Card as="section" padding="sm" className="flex h-[22rem] flex-col">
        <SectionTitle className="mb-1.5">Nhịp phiên (bản ghi)</SectionTitle>
        {loading ? (
          <div className="flex min-h-0 flex-1 flex-col gap-2" aria-busy>
            <Skeleton className="min-h-0 flex-1" />
            <Skeleton className="h-7 shrink-0" />
          </div>
        ) : (
          <>
            <div className="min-h-0 flex-1">
              <RhythmChart
                ticks={rp.visibleTicks}
                viewersMissing={rp.viewersMissing}
                clicksMissing={rp.clicksMissing}
                blocks={rec?.blocks}
                replay
              />
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

      <div className="grid gap-3 lg:grid-cols-2">
        {/* Zone 2 — cards + "nếu hết hàng" panel */}
        <Card as="section" padding="sm" className="flex min-h-[26rem] flex-col sm:flex-row">
          <div className="flex min-w-0 flex-1 flex-col sm:pr-3">
            <SectionTitle className="mb-1.5" meta={rec ? "xếp lại từ bản ghi" : undefined}>
              Hành động gợi ý
            </SectionTitle>
            <div className="flex flex-col gap-2">
              {loading ? (
                <div className="flex flex-col gap-2" aria-busy>
                  <Skeleton className="h-24" />
                  <Skeleton className="h-24" />
                  <Skeleton className="h-24" />
                </div>
              ) : rp.cards.length === 0 ? (
                <div className="flex flex-col items-start gap-2 px-2 py-4">
                  <p className="text-body text-dim">{cardsEmptyReason(rp)}</p>
                  {!rp.analysis && (rec?.products.length ?? 0) === 0 && !rp.catalogFailed ? (
                    <Link href="/chay-phien" className={buttonCls("ghost", "sm")}>
                      Chuẩn bị phiên →
                    </Link>
                  ) : null}
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

          {/* khung "nếu hết hàng" */}
          <aside className="mt-3 flex shrink-0 flex-col border-t border-hairline pt-3 sm:mt-0 sm:w-60 sm:border-l sm:border-t-0 sm:pl-3 sm:pt-0">
            <SectionTitle className="mb-1.5">Thử: nếu hết hàng</SectionTitle>
            <p className="mb-2 shrink-0 text-meta leading-snug text-dim">
              Đánh dấu sản phẩm <span className="font-semibold text-sec">hết hàng</span> để xem thẻ
              gợi ý xếp lại thế nào.
            </p>
            {loading ? (
              <div className="flex flex-col gap-1.5" aria-busy>
                <Skeleton className="h-8" />
                <Skeleton className="h-8" />
                <Skeleton className="h-8" />
                <Skeleton className="h-8" />
              </div>
            ) : (rec?.products.length ?? 0) === 0 ? (
              <p className="text-body text-dim">{productsEmptyReason(rp)}</p>
            ) : (
              <ul className="space-y-1">
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
        <Card as="section" padding="sm" className="flex h-[30rem] flex-col">
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
          ) : rp.visibleComments.length === 0 ? (
            // Feed rỗng: KHÔNG dựng CommentFeed (nút "Tạm dừng cuộn" vô nghĩa
            // khi chưa có gì cuộn, và câu "bạn không cần làm gì" là của màn live).
            <NoCommentsYet rp={rp} />
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

/**
 * Số phút có số liệu tới vị trí đang phát — CÙNG cách gộp với RhythmChart
 * (`Math.floor(offset_s / 60)`), nên ≥ 2 nghĩa là biểu đồ thật sự vẽ được đường.
 */
function minutesWithData(ticks: readonly { offset_s: number }[]): number {
  return new Set(ticks.map((x) => Math.floor(x.offset_s / 60))).size;
}

/** Dòng nhắc dưới thanh điều khiển: đang làm gì và bấm gì tiếp. */
function playPrompt(rp: ReplayState): string {
  const rec = rp.recording;
  if (!rec) return "Đang tải bản ghi…";
  if (rp.playing) return `Đang phát ở tốc độ ${rp.speed}x — bấm Tạm dừng để dừng lại.`;
  if (rp.t >= rec.duration_s) return "Đã phát hết bản ghi — bấm Phát để xem lại từ đầu.";
  if (rp.t > 0 && rp.t === rp.firstFrameS) {
    // Khung đầu có thể được tua tới bình luận đầu tiên khi bản ghi CHƯA có phút
    // số liệu thứ hai — lúc đó không được nói "đủ hai phút số liệu" (kiểm toán 17/09).
    return minutesWithData(rp.visibleTicks) >= 2
      ? `Đã tua sẵn tới ${fmtElapsed(rp.t)}, đủ hai phút số liệu để vẽ nhịp — bấm Phát để xem tiếp.`
      : `Đã tua sẵn tới ${fmtElapsed(rp.t)}, lúc có bình luận đầu tiên — bấm Phát để xem tiếp.`;
  }
  return `Đang dừng ở ${fmtElapsed(rp.t)} — bấm Phát để xem tiếp.`;
}

/** Vì sao cột thẻ trống — nói đúng lý do, không đẩy người dùng đi tìm. */
function cardsEmptyReason(rp: ReplayState): string {
  const products = rp.recording?.products ?? [];
  if (rp.analysis) {
    return "Phiên phân tích video của người khác không có thẻ gợi ý — đây không phải buổi bạn vận hành.";
  }
  if (products.length === 0) {
    return rp.catalogFailed
      ? "Không tải được danh mục sản phẩm từ máy chủ nên chưa xếp được thẻ. Tải lại trang để thử lại."
      : "Chưa có sản phẩm nào trong danh mục nên không có thẻ để xếp.";
  }
  if (products.every((p) => rp.excluded.has(p.product_id))) {
    return "Bạn đã đánh dấu hết hàng mọi sản phẩm — bỏ bớt một dấu để thấy thẻ.";
  }
  return "Bản ghi chưa có thẻ nào cho thời điểm này.";
}

/** Vì sao khung "nếu hết hàng" không có sản phẩm nào để đánh dấu. */
function productsEmptyReason(rp: ReplayState): string {
  if (rp.analysis) return "Phiên phân tích video của người khác không có sản phẩm của bạn.";
  if (rp.catalogFailed) return "Không tải được danh mục sản phẩm từ máy chủ.";
  return "Danh mục chưa có sản phẩm nào.";
}

/** Khung bình luận khi tới vị trí đang phát vẫn chưa có bình luận nào. */
function NoCommentsYet({ rp }: { rp: ReplayState }) {
  const comments = rp.recording?.comments ?? [];
  if (comments.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-1.5 px-4 text-center">
        <p className="text-body text-sec">Buổi này không ghi lại bình luận nào.</p>
        <p className="text-meta text-dim">Nhịp phiên và thẻ gợi ý vẫn xem lại được bình thường.</p>
      </div>
    );
  }
  let first = Number.POSITIVE_INFINITY;
  for (const c of comments) first = Math.min(first, c.offset_s);
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-2 px-4 text-center">
      <p className="text-body text-sec">
        Chưa tới bình luận đầu tiên — bản ghi có bình luận từ {fmtElapsed(first)}.
      </p>
      <Button size="sm" variant="ghost" onClick={() => rp.seek(Math.ceil(first))}>
        Tua tới {fmtElapsed(first)}
      </Button>
    </div>
  );
}
