"use client";

/**
 * "/" — trang Bắt đầu (gói SKIN, theo mockup mock_home.png đã duyệt).
 *
 * MÀN KỂ CHUYỆN (loại B) — được phép sân khấu: đèn studio + lưới kỹ thuật
 * (D1), MỘT cụm gradient-text trong H1 (G2), bento 3 cửa vào, reveal một lần
 * khi vào trang. Nội dung theo spec UX-FLOW: 3 LỐI ĐI không đánh số bước,
 * hàng số bằng chứng CHỈ dùng số đếm mô tả kiểm chứng được (không effect size
 * mô phỏng — điều chỉnh bắt buộc của phản biện khoa học), dải CHẾ ĐỘ giải
 * thích DEMO vs THẬT, và lối vào /bat-dau ("3 câu hỏi") giữ nguyên.
 *
 * Icon: SVG inline stroke 1.8 — CẤM emoji (spec UI-VISUAL).
 *
 * The API is probed once; when unreachable the doors degrade gracefully:
 * demo switches to the offline mock replay, VOD analysis is disabled with an
 * honest note.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import TopNav from "@/components/TopNav";
import Button from "@/components/ui/Button";
import Callout from "@/components/ui/Callout";
import { fieldCls } from "@/components/ui/field";
import { getReplayJob, listSessions, seedDemo, submitYoutubeReplay } from "@/lib/api";
import type { ReplayJob } from "@/lib/types";

type ApiProbe = "checking" | "ok" | "down";

const JOB_STATUS_VI: Record<ReplayJob["status"], string> = {
  queued: "Đang xếp hàng…",
  downloading: "Đang tải chat…",
  ingesting: "Đang phân tích…",
  done: "Xong — đang mở kết quả…",
  error: "Có lỗi xảy ra.",
};

/**
 * HÀNG SỐ BẰNG CHỨNG — chỉ số đếm mô tả có nguồn kiểm chứng được (nguyên tắc
 * không-bịa-số + điều chỉnh của phản biện khoa học: không effect size mô
 * phỏng trên trang mặt tiền):
 *   48.000 bình luận — 6 buổi live thật đã ingest (docs/HUONG-DAN-SU-DUNG.md)
 *   30+ buổi live    — tổng số buổi đã phân tích qua pipeline replay
 *   735 kiểm thử     — `grep -c "def test_" tests/*.py` ngày 12/09/2026
 */
const PROOF: { value: string; label: string }[] = [
  { value: "48.000", label: "bình luận thật đã phân tích" },
  { value: "30+", label: "buổi live đã xử lý" },
  { value: "735", label: "kiểm thử tự động đang xanh" },
];

/* ---- icon SVG inline, stroke 1.8, style Lucide (CẤM emoji toàn app) ------ */

function IconLive() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 10l4.55-2.27A1 1 0 0 1 21 8.62v6.76a1 1 0 0 1-1.45.9L15 14M3 8a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
    </svg>
  );
}

function IconPlay() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <path d="M10 9l5 3-5 3z" />
    </svg>
  );
}

function IconAnalyze() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12a9 9 0 1 1-9-9" />
      <path d="M21 3l-9 9" />
      <path d="M15 3h6v6" />
    </svg>
  );
}

/** Ô icon 38px viền hairline trên plane cao — DNA của cửa vào bento. */
function DoorIcon({ children }: { children: React.ReactNode }) {
  return (
    <span className="mb-3 grid h-10 w-10 place-items-center rounded-[10px] border border-strong bg-axis text-brand-hi">
      {children}
    </span>
  );
}

export default function HomePage() {
  const router = useRouter();
  const [api, setApi] = useState<ApiProbe>("checking");

  // Cửa 2 — demo 30 giây
  const [demoBusy, setDemoBusy] = useState(false);
  const [demoErr, setDemoErr] = useState<string | null>(null);

  // Cửa 3 — phân tích VOD
  const [url, setUrl] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<ReplayJob | null>(null);
  const [jobErr, setJobErr] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Probe the API once (2.5 s) — same probe the hooks use.
  useEffect(() => {
    let cancelled = false;
    listSessions(2500)
      .then(() => !cancelled && setApi("ok"))
      .catch(() => !cancelled && setApi("down"));
    return () => {
      cancelled = true;
    };
  }, []);

  // ---- Cửa 2: one-click demo --------------------------------------------
  const startDemo = useCallback(async () => {
    setDemoErr(null);
    if (api !== "ok") {
      // Offline: open the deterministic mock replay directly.
      router.push("/replay?session=mock-ended-01");
      return;
    }
    setDemoBusy(true);
    try {
      const seed = await seedDemo(3);
      const sessions = await listSessions(6000);
      const ended = new Set(
        sessions.filter((s) => s.status === "ended").map((s) => s.session_id),
      );
      const preferred =
        [seed.replay_session_id, ...seed.session_ids].find((id) => ended.has(id)) ??
        sessions.find((s) => s.status === "ended")?.session_id ??
        null;
      router.push(preferred ? `/replay?session=${encodeURIComponent(preferred)}` : "/replay");
    } catch {
      setDemoErr("Không tạo được dữ liệu mô phỏng — kiểm tra máy chủ rồi thử lại.");
      setDemoBusy(false);
    }
  }, [api, router]);

  // ---- Cửa 3: analyze an existing YouTube live ---------------------------
  const analyze = useCallback(async () => {
    const u = url.trim();
    if (!u) return;
    setJobErr(null);
    setJob(null);
    setSubmitting(true);
    try {
      const { job_id } = await submitYoutubeReplay(u);
      setJobId(job_id);
    } catch {
      setJobErr("Không gửi được yêu cầu — kiểm tra đường dẫn video và máy chủ.");
      setSubmitting(false);
    }
  }, [url]);

  // Poll the job every 2 s until done/error.
  const stopped = useRef(false);
  useEffect(() => {
    if (!jobId) return;
    stopped.current = false;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      try {
        const j = await getReplayJob(jobId);
        if (stopped.current) return;
        setJob(j);
        if (j.status === "done" && j.session_id) {
          router.push(`/replay?session=${encodeURIComponent(j.session_id)}&mode=analysis`);
          return;
        }
        if (j.status === "error") {
          setSubmitting(false);
          return;
        }
        timer = setTimeout(tick, 2000);
      } catch {
        if (!stopped.current) {
          setJobErr("Mất kết nối tới máy chủ khi đang theo dõi tiến trình.");
          setSubmitting(false);
        }
      }
    };
    timer = setTimeout(tick, 400);
    return () => {
      stopped.current = true;
      clearTimeout(timer);
    };
  }, [jobId, router]);

  const jobRunning = useMemo(
    () => submitting || (job != null && job.status !== "error" && job.status !== "done"),
    [submitting, job],
  );

  /** Reveal một lần khi vào trang — chỉ trang kể chuyện, tối đa 6 bậc so le.
   *  Trả về `style` thôi; lớp `motion-reveal` được ghi thẳng trong className
   *  của từng phần tử (spread className sẽ bị className literal đè mất). */
  const reveal = (i: number) => ({
    style: { animationDelay: `${Math.min(i, 6) * 60}ms` },
  });

  return (
    <div className="flex min-h-screen flex-col bg-page">
      <TopNav />
      <main className="hero-stage flex-1">
        <div className="relative mx-auto flex w-full max-w-5xl flex-col items-center px-6 pb-16 pt-14 text-center">
          {/* eyebrow: đèn live pulse — quy ước phát sóng, ngoại lệ lặp duy nhất */}
          <span
            {...reveal(0)}
            className="motion-reveal inline-flex items-center gap-2 rounded-full border border-s7/40 bg-s7/10 px-4 py-1.5 text-meta font-semibold uppercase tracking-[0.14em] text-brand-ink"
          >
            <span aria-hidden className="live-dot" />
            Nền tảng thí nghiệm cho livestream bán hàng
          </span>

          <h1
            {...reveal(1)}
            className="motion-reveal mt-6 font-display text-[clamp(40px,6vw,68px)] font-bold leading-[1.06] tracking-[-0.03em] text-ink"
          >
            Mỗi quyết định trên sóng
            <br />
            <span className="text-grad-brand">là một thí nghiệm đo được</span>
          </h1>

          <p {...reveal(2)} className="motion-reveal mx-auto mt-4 max-w-2xl text-[17px] leading-relaxed text-sec">
            LiveLift bốc thăm <strong className="text-ink">BẬT/TẮT</strong> từng khối thời gian
            trước khi lên sóng, gợi ý sản phẩm nên ghim theo thời gian thực, rồi chứng minh tác
            động bằng <strong className="text-ink">kiểm định nhân quả</strong> — không phải cảm
            giác.
          </p>

          {/* hàng số bằng chứng — chỉ số đếm có nguồn, font số JetBrains Mono */}
          <div
            {...reveal(3)}
            className="motion-reveal mt-6 flex flex-wrap items-baseline justify-center gap-x-8 gap-y-2 text-meta text-mut"
          >
            {PROOF.map((p) => (
              <span key={p.label}>
                <strong className="font-num text-body font-bold tabular-nums text-ink">
                  {p.value}
                </strong>{" "}
                {p.label}
              </span>
            ))}
          </div>

          {api === "down" && (
            <Callout tone="warn" slim className="mt-5 inline-flex text-left">
              Chưa kết nối được máy chủ — bạn vẫn xem thử được bằng dữ liệu mô phỏng.
            </Callout>
          )}

          {/* ---- bento 3 cửa vào ------------------------------------------ */}
          <div className="mt-9 grid w-full grid-cols-1 gap-3.5 text-left md:grid-cols-[1.25fr_1fr_1fr]">
            {/* Cửa 1 — primary: tôi có buổi live → 3 câu hỏi */}
            <Link
              href="/bat-dau"
              {...reveal(4)}
              className="focus-ring group motion-reveal relative overflow-hidden rounded-2xl border border-s7/40 bg-gradient-to-b from-s7/15 to-s7/[0.03] p-6 transition-all duration-short4 ease-emphasized hover:-translate-y-0.5 hover:border-s7/60 hover:shadow-[0_12px_40px_-12px_rgba(124,108,255,0.35)]"
            >
              <span className="absolute right-4 top-4 rounded-full bg-brand-hi px-2.5 py-0.5 text-meta font-bold text-[#0c0d12]">
                BẮT ĐẦU Ở ĐÂY
              </span>
              <DoorIcon>
                <IconLive />
              </DoorIcon>
              <span className="font-num text-meta tracking-[0.1em] text-dim">01</span>
              <h2 className="mt-1 font-display text-strong tracking-tight text-ink">
                Tôi có buổi live
              </h2>
              <p className="mt-1 min-h-10 text-meta leading-relaxed text-sec">
                Trả lời 3 câu hỏi — hệ thống nói ngay bạn dùng được gì với buổi live của mình,
                kèm cả thứ không làm được và vì sao.
              </p>
              <span className="mt-4 inline-flex items-center gap-1.5 text-meta font-semibold text-brand-hi">
                Trả lời 3 câu hỏi →
              </span>
            </Link>

            {/* Cửa 2 — demo 30 giây */}
            <div
              {...reveal(5)}
              className="group motion-reveal relative overflow-hidden rounded-2xl border border-hairline bg-gradient-to-b from-raised to-surface p-6 transition-all duration-short4 ease-emphasized hover:-translate-y-0.5 hover:border-s7/40 hover:shadow-[0_12px_40px_-12px_rgba(124,108,255,0.25)]"
            >
              <DoorIcon>
                <IconPlay />
              </DoorIcon>
              <span className="font-num text-meta tracking-[0.1em] text-dim">02</span>
              <h2 className="mt-1 font-display text-strong tracking-tight text-ink">
                Xem demo 30 giây
              </h2>
              <p className="mt-1 min-h-10 text-meta leading-relaxed text-sec">
                Một phiên mô phỏng chạy sẵn — xem bàn trợ live vận hành mà không cần cài gì.
              </p>
              <Button
                onClick={() => void startDemo()}
                disabled={demoBusy || api === "checking"}
                size="sm"
                className="mt-3"
              >
                {/* Nhãn "Bắt đầu xem thử" được docs/HUONG-DAN-SU-DUNG.md trích
                    nguyên văn (gate test_docs_huong_dan) — đổi nhãn là phải đổi
                    docs cùng lúc. */}
                {demoBusy
                  ? "Đang tạo dữ liệu…"
                  : api === "checking"
                    ? "Đang kiểm tra máy chủ…"
                    : api === "down"
                      ? "Xem thử với dữ liệu mô phỏng"
                      : "Bắt đầu xem thử"}
              </Button>
              {demoErr && <p className="mt-2 text-meta text-crit-ink">{demoErr}</p>}
            </div>

            {/* Cửa 3 — phân tích VOD có sẵn */}
            <div
              {...reveal(6)}
              className={`group motion-reveal relative overflow-hidden rounded-2xl border border-hairline bg-gradient-to-b from-raised to-surface p-6 transition-all duration-short4 ease-emphasized hover:-translate-y-0.5 hover:border-s7/40 hover:shadow-[0_12px_40px_-12px_rgba(124,108,255,0.25)] ${
                api === "down" ? "opacity-60" : ""
              }`}
            >
              <DoorIcon>
                <IconAnalyze />
              </DoorIcon>
              <span className="font-num text-meta tracking-[0.1em] text-dim">03</span>
              <h2 className="mt-1 font-display text-strong tracking-tight text-ink">
                Phân tích video có sẵn
              </h2>
              <p className="mt-1 min-h-10 text-meta leading-relaxed text-sec">
                Dán link YouTube <strong className="text-ink">đã kết thúc</strong> — dựng lại
                nhịp bình luận và radar ý định mua.
              </p>
              <form
                className="mt-3 flex flex-col gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  void analyze();
                }}
              >
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v=…"
                  disabled={api !== "ok" || jobRunning}
                  aria-label="Đường dẫn video YouTube"
                  className={`${fieldCls} min-w-0 px-3 py-1.5 text-meta`}
                />
                <Button
                  type="submit"
                  size="sm"
                  variant="ghost"
                  disabled={api !== "ok" || jobRunning || url.trim() === ""}
                >
                  {jobRunning ? "Đang xử lý…" : "Phân tích →"}
                </Button>
              </form>
              {(job || jobRunning) && (
                <div className="mt-2 flex items-center gap-2 rounded-md border border-hairline bg-axis px-2.5 py-1.5 text-meta text-sec">
                  {job?.status !== "error" && (
                    <span
                      aria-hidden
                      className="inline-block h-2 w-2 animate-pulse rounded-full bg-s1"
                    />
                  )}
                  <span
                    className={job?.status === "error" ? "font-semibold text-crit-ink" : undefined}
                  >
                    {job
                      ? job.status === "error"
                        ? (job.detail ?? JOB_STATUS_VI.error)
                        : JOB_STATUS_VI[job.status]
                      : "Đang gửi yêu cầu…"}
                    {job?.video_title && job.status !== "error" && (
                      <span className="text-dim"> · {job.video_title}</span>
                    )}
                  </span>
                </div>
              )}
              {jobErr && <p className="mt-2 text-meta text-crit-ink">{jobErr}</p>}
              <p className="mt-3 border-t border-hairline pt-2 text-meta leading-relaxed text-dim">
                Video của người khác chỉ cho kết quả{" "}
                <strong className="text-sec">QUAN SÁT</strong> — không phải thí nghiệm.
              </p>
            </div>
          </div>

          {/* ---- dải CHẾ ĐỘ: DEMO vs THẬT --------------------------------- */}
          <div className="mt-4 flex w-full flex-col items-start gap-3 rounded-xl border border-dashed border-warn/40 bg-warn/5 px-5 py-3.5 text-left sm:flex-row sm:items-center">
            <span className="shrink-0 rounded-md bg-warn px-2.5 py-0.5 text-meta font-bold tracking-[0.1em] text-[#0c0d12]">
              CHẾ ĐỘ
            </span>
            <span className="text-meta leading-relaxed text-sec">
              <strong className="text-ink">DEMO</strong> dùng dữ liệu mô phỏng và buổi live đã
              nạp sẵn — để xem và tập, bấm thoải mái.{" "}
              <strong className="text-ink">PHIÊN THẬT</strong> nối thẳng vào buổi live của bạn.
              Chip chế độ ở góc phải thanh điều hướng cho biết bạn đang ở thế giới nào.
            </span>
          </div>

          {/* footer mảnh: nguồn gốc dự án */}
          <p className="mt-10 text-meta text-dim">
            LiveLift <span className="tnum">v0.1.0</span> · thí nghiệm switchback cho
            live-commerce · AISC&apos;26
          </p>
        </div>
      </main>
    </div>
  );
}
