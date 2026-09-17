"use client";

/**
 * IngestPanel — bật/tắt bộ thu bình luận của một phiên ngay trên trình duyệt.
 *
 * Kiểm toán 17/09/2026: trước đây đưa bình luận vào LiveLift cần một cửa sổ
 * terminal chạy `python -m livelift.ingest.runner …`, nên mọi phiên tạo trên web
 * hiện "THIẾU nguồn". Máy chủ nay chạy bộ thu NỀN (`POST /sessions/{id}/ingest`);
 * khung này là nút bấm cho nó.
 *
 * Nguyên tắc cho màn hình đang live:
 *  - MỘT dòng trạng thái đọc được khi liếc: ký hiệu + chữ + số bình luận.
 *  - Trạng thái có HÌNH (● ◐ ↻ ✕ ○) chứ không chỉ màu (WCAG 1.4.1).
 *  - Không bao giờ bịa số: chưa có dữ liệu thì nói chưa có.
 *  - Thiếu khoá trên máy chủ ⇒ nói tên biến còn thiếu, khoá nút, không để người
 *    dùng bấm rồi mới nhận lỗi.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import { getIngestStatus, getPlatforms, startIngest, stopIngest } from "@/lib/api";
import { fmtNumber } from "@/lib/format";
import type { IngestPlatform, IngestState, IngestStatus, PlatformReadiness } from "@/lib/types";

import Button from "./ui/Button";
import Callout from "./ui/Callout";
import { cx } from "./ui/cx";
import { fieldCls } from "./ui/field";

const POLL_MS = 4000;
const STALE_S = 120;

const THU_DUOC: readonly string[] = ["youtube", "facebook", "shopee", "mo_phong"];

const NHAN: Record<IngestState, { ky_hieu: string; chu: string; mau: string }> = {
  chua_bat: { ky_hieu: "○", chu: "Chưa bật bộ thu", mau: "text-sec" },
  dang_khoi_dong: { ky_hieu: "◐", chu: "Đang kết nối", mau: "text-info-ink" },
  dang_thu: { ky_hieu: "●", chu: "Đang thu bình luận", mau: "text-good-ink" },
  dang_thu_lai: { ky_hieu: "↻", chu: "Mất kết nối — đang thử lại", mau: "text-warn-ink" },
  cho_len_song: { ky_hieu: "◐", chu: "Chờ buổi live bắt đầu", mau: "text-warn-ink" },
  da_dung: { ky_hieu: "○", chu: "Đã tắt bộ thu", mau: "text-sec" },
  phien_ket_thuc: { ky_hieu: "○", chu: "Phiên đã kết thúc — bộ thu tự dừng", mau: "text-sec" },
  nguon_ket_thuc: { ky_hieu: "○", chu: "Buổi live đã tắt — bộ thu dừng", mau: "text-sec" },
  loi: { ky_hieu: "✕", chu: "Bộ thu dừng vì lỗi", mau: "text-crit-ink" },
};

interface Props {
  sessionId: string | null;
  /** Nền tảng của phiên — chọn sẵn nếu nền tảng đó có bộ thu. */
  sessionPlatform?: string | null;
  sessionStatus?: string | null;
  /** Một dòng gọn cho thanh trạng thái bàn trợ live. */
  compact?: boolean;
  /** Phiên chạy thử hoặc phiên mẫu: chỉ khi đó mới cho chọn nguồn mô phỏng
   *  (máy chủ cũng chặn bằng 422 — đây là lớp thứ hai, để không mời bấm nhầm). */
  allowSimulated?: boolean;
  /** Ẩn tiêu đề "Nguồn bình luận" khi nơi đặt panel đã có tiêu đề riêng. */
  hideTitle?: boolean;
  className?: string;
}

export default function IngestPanel({
  sessionId,
  sessionPlatform,
  sessionStatus,
  compact = false,
  allowSimulated = false,
  hideTitle = false,
  className,
}: Props) {
  const [platforms, setPlatforms] = useState<PlatformReadiness[] | null>(null);
  const [status, setStatus] = useState<IngestStatus | null>(null);
  const [platform, setPlatform] = useState<string>("");
  const [source, setSource] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [moForm, setMoForm] = useState(false);

  const phienDong = sessionStatus === "ended" || sessionStatus === "cancelled";

  useEffect(() => {
    let alive = true;
    getPlatforms()
      .then((list) => alive && setPlatforms(list))
      .catch(() => alive && setPlatforms([]));
    return () => {
      alive = false;
    };
  }, []);

  const choPhep = useMemo(
    () => (allowSimulated ? THU_DUOC : THU_DUOC.filter((p) => p !== "mo_phong")),
    [allowSimulated],
  );

  useEffect(() => {
    if (platform || !platforms) return;
    const macDinh =
      sessionPlatform && choPhep.includes(sessionPlatform)
        ? sessionPlatform
        : (platforms.find((p) => p.ready && choPhep.includes(p.platform))?.platform ?? "youtube");
    setPlatform(macDinh);
  }, [platforms, platform, sessionPlatform, choPhep]);

  const refresh = useCallback(async () => {
    if (!sessionId) return;
    try {
      setStatus(await getIngestStatus(sessionId));
    } catch {
      // Mất kết nối tạm thời: giữ trạng thái cũ, lần poll sau thử lại.
    }
  }, [sessionId]);

  useEffect(() => {
    setStatus(null);
    setError(null);
    if (!sessionId) return;
    void refresh();
    const t = setInterval(() => void refresh(), POLL_MS);
    return () => clearInterval(t);
  }, [sessionId, refresh]);

  const chon = useMemo(
    () => platforms?.find((p) => p.platform === platform) ?? null,
    [platforms, platform],
  );

  const batDau = async () => {
    if (!sessionId || !platform) return;
    setBusy(true);
    setError(null);
    try {
      const st = await startIngest(sessionId, {
        platform: platform as IngestPlatform,
        source: source.trim(),
      });
      setStatus(st);
      setMoForm(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không bật được bộ thu.");
    } finally {
      setBusy(false);
    }
  };

  const tat = async () => {
    if (!sessionId) return;
    setBusy(true);
    setError(null);
    try {
      setStatus(await stopIngest(sessionId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tắt được bộ thu.");
    } finally {
      setBusy(false);
    }
  };

  if (!sessionId) return null;

  const state: IngestState = status?.state ?? "chua_bat";
  const nhan = NHAN[state] ?? NHAN.chua_bat;
  const dangChay = status?.running ?? false;
  const cu =
    dangChay &&
    state === "dang_thu" &&
    status?.seconds_since_last_event != null &&
    status.seconds_since_last_event > STALE_S;

  const dongTrangThai = (
    <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1" aria-live="polite">
      <span className={cx("inline-flex items-center gap-1.5 font-semibold", nhan.mau)}>
        <span aria-hidden>{nhan.ky_hieu}</span>
        {nhan.chu}
      </span>
      {status && state !== "chua_bat" && (
        <span className="text-meta text-sec">
          {fmtNumber(status.comments_posted)} bình luận
          {status.last_viewers != null && ` · ${fmtNumber(status.last_viewers)} người xem`}
          {status.seconds_since_last_event != null &&
            ` · mới nhất ${fmtNumber(Math.round(status.seconds_since_last_event))} giây trước`}
        </span>
      )}
    </div>
  );

  const hienForm = !dangChay && !phienDong && (!compact || moForm || state === "chua_bat");

  return (
    <section
      aria-label="Bộ thu bình luận"
      className={cx(
        "rounded-lg border border-hairline bg-surface",
        compact ? "px-3 py-2" : "p-4",
        className,
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          {!compact && !hideTitle && (
            <p className="text-label uppercase text-sec">Nguồn bình luận</p>
          )}
          {dongTrangThai}
        </div>
        <div className="flex items-center gap-2">
          {dangChay && (
            <Button variant="ghost" size="sm" onClick={() => void tat()} disabled={busy}>
              Tắt bộ thu
            </Button>
          )}
          {!dangChay && !phienDong && compact && state !== "chua_bat" && !moForm && (
            <Button variant="ghost" size="sm" onClick={() => setMoForm(true)}>
              Bật lại
            </Button>
          )}
        </div>
      </div>

      {cu && (
        <p className="mt-1 text-meta text-warn-ink">
          ⚠ Hai phút không có bình luận mới — kiểm tra buổi live còn phát và còn người bình luận.
        </p>
      )}
      {status?.last_error && state !== "dang_thu" && (
        <p className="mt-1 text-meta text-sec">{status.last_error}</p>
      )}

      {hienForm && (
        <form
          className="mt-2 flex flex-wrap items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            void batDau();
          }}
        >
          <label className="flex flex-col gap-1 text-meta text-sec">
            Nền tảng
            <select
              className={cx(fieldCls, "px-2 text-body")}
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
            >
              {(platforms ?? [])
                .filter((p) => choPhep.includes(p.platform))
                .map((p) => (
                  <option key={p.platform} value={p.platform}>
                    {p.ten}
                    {p.ready ? "" : " — chưa sẵn sàng"}
                  </option>
                ))}
            </select>
          </label>
          <label className="flex min-w-[16rem] flex-1 flex-col gap-1 text-meta text-sec">
            Link hoặc mã buổi live
            <input
              className={cx(fieldCls, "px-3 text-body")}
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder={chon?.source_hint || "Dán link buổi live"}
              spellCheck={false}
              autoComplete="off"
            />
          </label>
          <Button type="submit" disabled={busy || !chon?.ready}>
            {busy ? "Đang bật…" : "Bật bộ thu"}
          </Button>
        </form>
      )}

      {hienForm && chon && !chon.ready && (
        <p className="mt-2 text-meta text-warn-ink">
          ⚠ Máy chủ chưa có khoá cho {chon.ten}: thiếu {chon.missing.join(", ")}. Nhờ người kỹ
          thuật điền vào tệp .env rồi khởi động lại máy chủ.
        </p>
      )}
      {hienForm && chon && chon.ready && chon.mode === "du_phong" && !compact && (
        <p className="mt-2 text-meta text-sec">{chon.note}</p>
      )}
      {error && (
        <Callout tone="critical" slim className="mt-2">
          {error}
        </Callout>
      )}
    </section>
  );
}
