"use client";

/**
 * GÓI WIZARD — ô dán link YouTube VOD, hiện NGAY TẠI CHỖ trong ô kết quả.
 *
 * Lý do tồn tại: trang /bat-dau trả lời "bạn làm được gì", và với tổ hợp đông
 * người dùng nhất (buổi YouTube đã kết thúc) câu trả lời là "dán link là xong".
 * Bắt người dùng đọc câu đó rồi tự đi tìm ô dán ở trang khác là đánh mất đúng
 * khoảnh khắc họ đang sẵn sàng hành động — nên ô dán nằm luôn dưới câu trả lời.
 *
 * Dùng lại NGUYÊN VẸN hợp đồng API của trang chủ (POST /replays/youtube →
 * GET /replays/jobs/{id}), không thêm đường dẫn mới nào vào api.ts.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Button from "@/components/ui/Button";
import { fieldCls } from "@/components/ui/field";
import { getReplayJob, submitYoutubeReplay } from "@/lib/api";
import type { ServerStatus } from "@/lib/api";
import type { ReplayJob } from "@/lib/types";

const JOB_STATUS_VI: Record<ReplayJob["status"], string> = {
  queued: "Đang xếp hàng…",
  downloading: "Đang tải chat replay…",
  ingesting: "Đang phân tích bình luận…",
  done: "Xong — đang mở kết quả…",
  error: "Có lỗi xảy ra.",
};

interface Props {
  /** Nhãn nút, do từng tổ hợp đặt (mỗi tổ hợp có một câu riêng). */
  label: string;
  /** API có với tới được không — khi không thì ô bị khoá kèm lý do thật. */
  apiUp: boolean;
  /**
   * Vì sao ô bị khoá (gói B-PROBE). Trước đây chỉ có `apiUp`, nên MỌI lý do
   * đều in ra cùng một câu "hiện chưa kết nối được" — kể cả khi máy chủ đang
   * chạy và chỉ có kho dữ liệu suy giảm. Khoá thì được, nói sai thì không.
   */
  server?: "checking" | ServerStatus;
}

export default function BatDauVod({ label, apiUp, server = "checking" }: Props) {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<ReplayJob | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const analyze = useCallback(async () => {
    const u = url.trim();
    if (!u) return;
    setErr(null);
    setJob(null);
    setSubmitting(true);
    try {
      const { job_id } = await submitYoutubeReplay(u);
      setJobId(job_id);
    } catch {
      setErr("Không gửi được yêu cầu — kiểm tra lại đường dẫn video và máy chủ LiveLift.");
      setSubmitting(false);
    }
  }, [url]);

  // Theo dõi tiến trình nạp mỗi 2 giây cho tới khi xong hoặc lỗi.
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
          setErr("Mất kết nối tới máy chủ khi đang theo dõi tiến trình nạp.");
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

  const running = useMemo(
    () => submitting || (job != null && job.status !== "error" && job.status !== "done"),
    [submitting, job],
  );

  return (
    <div className="mt-3 rounded-md border border-hairline bg-raised p-3">
      <label
        htmlFor="batdau-vod-url"
        className="block text-label uppercase text-dim"
      >
        {label}
      </label>
      <form
        className="mt-2 flex flex-col gap-2 sm:flex-row"
        onSubmit={(e) => {
          e.preventDefault();
          void analyze();
        }}
      >
        <input
          id="batdau-vod-url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=…"
          disabled={!apiUp || running}
          className={`${fieldCls} min-w-0 flex-1 px-3 py-2 text-body`}
        />
        <Button type="submit" disabled={!apiUp || running || url.trim() === ""}>
          {running ? "Đang xử lý…" : "Phân tích ngay"}
        </Button>
      </form>

      {(job || running) && (
        <div className="mt-2 flex items-center gap-2 rounded-md border border-hairline bg-surface px-3 py-2 text-meta text-sec">
          {job?.status !== "error" && (
            <span aria-hidden className="inline-block h-2 w-2 animate-pulse rounded-full bg-s1" />
          )}
          <span className={job?.status === "error" ? "font-semibold text-crit-ink" : undefined}>
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
      {err && <p className="mt-2 text-meta text-crit-ink">{err}</p>}
      {!apiUp && (
        <p className="mt-2 text-meta font-semibold text-warn-ink">
          {server === "degraded"
            ? "Máy chủ VẪN CHẠY nhưng kho dữ liệu đang suy giảm — kết quả nạp video sẽ không lưu lại được, nên tạm khoá."
            : server === "checking"
              ? "Đang kiểm tra máy chủ…"
              : "Cần máy chủ LiveLift đang chạy để nạp video — hiện chưa kết nối được."}
        </p>
      )}
    </div>
  );
}
