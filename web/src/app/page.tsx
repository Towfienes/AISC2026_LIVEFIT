"use client";

/**
 * "/" — calm start screen for first-time users.
 *
 * Three guided cards in priority order (Hick's law: few, prioritized choices;
 * one primary action per card). The API is probed once; when unreachable the
 * cards degrade gracefully: card 1 switches to the offline mock demo, card 2
 * is disabled with an honest note.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import TopNav from "@/components/TopNav";
import Button, { buttonCls } from "@/components/ui/Button";
import Callout from "@/components/ui/Callout";
import Card from "@/components/ui/Card";
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

function CardShell({
  step,
  children,
  dimmed,
}: {
  step: string;
  children: React.ReactNode;
  dimmed?: boolean;
}) {
  return (
    <Card
      as="section"
      padding="lg"
      interactive={!dimmed}
      className={`relative ${dimmed ? "opacity-60" : ""}`}
    >
      <span className="absolute -left-2.5 -top-2.5 flex h-6 w-6 items-center justify-center rounded-full border border-hairline bg-raised text-[11px] font-bold text-sec">
        {step}
      </span>
      {children}
    </Card>
  );
}

export default function HomePage() {
  const router = useRouter();
  const [api, setApi] = useState<ApiProbe>("checking");

  // Card 1 state
  const [demoBusy, setDemoBusy] = useState(false);
  const [demoErr, setDemoErr] = useState<string | null>(null);

  // Card 2 state
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

  // ---- Card 1: one-click demo -------------------------------------------
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

  // ---- Card 2: analyze an existing YouTube live --------------------------
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

  return (
    <div className="flex min-h-screen flex-col bg-page">
      <TopNav />
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-6 py-10">
        {/* brand + one-line promise */}
        <header className="text-center">
          <h1 className="text-4xl font-extrabold tracking-tight text-ink">LiveLift</h1>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-sec">
            Biến mỗi quyết định trong phiên live thành thí nghiệm đo được.
          </p>
          {api === "down" && (
            <Callout tone="warn" slim className="mx-auto mt-3 inline-flex text-left">
              Chưa kết nối được máy chủ — bạn vẫn xem thử được bằng dữ liệu mô phỏng.
            </Callout>
          )}
        </header>

        <div className="flex flex-col gap-4">
          {/* Card 1 — one-click demo */}
          <CardShell step="1">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-base font-semibold text-ink">🔬 Xem thử ngay (30 giây)</h2>
                <p className="mt-1 text-xs leading-relaxed text-sec">
                  Tạo dữ liệu mô phỏng và mở bản phát lại — không cần cài gì thêm.
                </p>
              </div>
              <Button
                onClick={() => void startDemo()}
                disabled={demoBusy || api === "checking"}
                className="shrink-0"
              >
                {demoBusy
                  ? "Đang tạo dữ liệu…"
                  : api === "checking"
                    ? "Đang kiểm tra máy chủ…"
                    : api === "down"
                      ? "Xem thử với dữ liệu mô phỏng"
                      : "Bắt đầu xem thử"}
              </Button>
            </div>
            {demoErr && <p className="mt-2 text-xs text-critical">{demoErr}</p>}
          </CardShell>

          {/* Card 2 — analyze an existing YouTube live */}
          <CardShell step="2" dimmed={api === "down"}>
            <h2 className="text-base font-semibold text-ink">
              🎬 Phân tích một video live có sẵn
            </h2>
            <p className="mt-1 text-xs leading-relaxed text-sec">
              Dán đường dẫn một buổi live YouTube <strong>đã kết thúc</strong> — hệ thống tải
              phần chat và dựng lại nhịp bình luận cùng radar ý định.
            </p>
            <form
              className="mt-3 flex flex-col gap-2 sm:flex-row"
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
                className={`${fieldCls} min-w-0 flex-1 px-3 py-2 text-sm`}
              />
              <Button type="submit" disabled={api !== "ok" || jobRunning || url.trim() === ""}>
                {jobRunning ? "Đang xử lý…" : "Phân tích"}
              </Button>
            </form>

            {/* job progress */}
            {(job || jobRunning) && (
              <div className="mt-3 flex items-center gap-2 rounded-md border border-hairline bg-raised px-3 py-2 text-xs text-sec">
                {job?.status !== "error" && (
                  <span
                    aria-hidden
                    className="inline-block h-2 w-2 animate-pulse rounded-full bg-s1"
                  />
                )}
                <span className={job?.status === "error" ? "text-critical" : undefined}>
                  {job
                    ? job.status === "error"
                      ? (job.detail ?? JOB_STATUS_VI.error)
                      : JOB_STATUS_VI[job.status]
                    : "Đang gửi yêu cầu…"}
                  {job?.video_title && job.status !== "error" && (
                    <span className="text-mut"> · {job.video_title}</span>
                  )}
                </span>
              </div>
            )}
            {jobErr && <p className="mt-2 text-xs text-critical">{jobErr}</p>}

            <p className="mt-3 border-t border-hairline pt-2 text-[11px] leading-relaxed text-mut">
              Chỉ phân tích được video YouTube còn chat replay. Video của người khác chỉ cho kết
              quả <strong className="text-sec">QUAN SÁT</strong> (radar ý định, nhịp bình luận) —
              không phải thí nghiệm.
            </p>
            {api === "down" && (
              <p className="mt-2 text-[11px] font-semibold text-warn">
                Cần máy chủ LiveLift đang chạy để phân tích video — hiện chưa kết nối được.
              </p>
            )}
          </CardShell>

          {/* Card 3 — run your own live session */}
          <CardShell step="3">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-base font-semibold text-ink">
                  📡 Chạy phiên live thật của bạn
                </h2>
                <p className="mt-1 text-xs leading-relaxed text-sec">
                  Khi đã sẵn sàng lên sóng: chuẩn bị theo 4 bước bên dưới rồi mở Bàn điều khiển.
                </p>
              </div>
              <Link href="/desk" className={`${buttonCls("ghost")} bg-raised text-ink`}>
                Mở Bàn điều khiển
              </Link>
            </div>
            <details className="mt-3 border-t border-hairline pt-2">
              <summary className="focus-ring cursor-pointer select-none rounded text-xs font-semibold text-sec transition-colors duration-150 hover:text-ink">
                Xem 4 bước chuẩn bị (tạo sản phẩm → tạo phiên → sinh lịch gán → bắt đầu)
              </summary>
              <ol className="mt-2 space-y-2 text-xs leading-relaxed text-sec">
                <li>
                  <strong className="text-ink">1. Tạo sản phẩm</strong> — thêm từng sản phẩm sẽ
                  lên sóng bằng lệnh{" "}
                  <code className="rounded bg-raised px-1 py-0.5 text-[11px]">POST /products</code>{" "}
                  (hoặc bấm &quot;Bắt đầu xem thử&quot; ở bước 1 để có sẵn dữ liệu mẫu).
                </li>
                <li>
                  <strong className="text-ink">2. Tạo phiên</strong> — đặt tên, nền tảng và thời
                  lượng buổi live bằng{" "}
                  <code className="rounded bg-raised px-1 py-0.5 text-[11px]">POST /sessions</code>.
                </li>
                <li>
                  <strong className="text-ink">3. Sinh lịch gán</strong> — hệ thống tự chia phiên
                  thành các khối BẬT/TẮT xen kẽ bằng{" "}
                  <code className="rounded bg-raised px-1 py-0.5 text-[11px]">
                    POST /sessions/{"{id}"}/schedule
                  </code>{" "}
                  (bạn không phải tự chọn gì).
                </li>
                <li>
                  <strong className="text-ink">4. Bắt đầu</strong> — phát lệnh{" "}
                  <code className="rounded bg-raised px-1 py-0.5 text-[11px]">
                    POST /sessions/{"{id}"}/start
                  </code>
                  , mở Bàn điều khiển và bấm nút &quot;Thực hiện&quot; trên thẻ gợi ý khi muốn ghim
                  sản phẩm; màn hình cho host đặt ở trang &quot;Màn hình host&quot;.
                </li>
              </ol>
            </details>
          </CardShell>
        </div>

        {/* slim footer: version + quick links */}
        <footer className="mt-auto flex flex-col items-center gap-2 border-t border-hairline pt-4 text-[11px] text-mut sm:flex-row sm:justify-between">
          <span>
            LiveLift <span className="tnum">v0.1.0</span> · thí nghiệm switchback cho
            live-commerce · AISC&apos;26
          </span>
          <span className="flex items-center gap-3">
            <Link
              href="/chay-phien"
              className="focus-ring rounded transition-colors duration-150 hover:text-sec"
            >
              Chạy phiên
            </Link>
            <Link
              href="/replay"
              className="focus-ring rounded transition-colors duration-150 hover:text-sec"
            >
              Phát lại
            </Link>
            <Link
              href="/ket-qua"
              className="focus-ring rounded transition-colors duration-150 hover:text-sec"
            >
              Kết quả
            </Link>
          </span>
        </footer>
      </main>
    </div>
  );
}
