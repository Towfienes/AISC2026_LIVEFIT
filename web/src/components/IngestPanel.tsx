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
 *
 * Phản biện 17/09 (ba lỗi, sửa tận gốc ở đây — không trông vào nơi đặt panel):
 *  - MỖI PHIÊN MỘT BỘ NHỚ. Nền tảng, link đã gõ, form mở, cờ đang bận đều là
 *    của MỘT phiên. Bàn trợ live đổi phiên bằng ô chọn mà không gắn lại panel,
 *    nên link buổi live của phiên A từng được điền sẵn cho phiên B (bấm là B
 *    thu bình luận của buổi A), và ô chọn hiện "YouTube" trong khi gửi đi
 *    "mo_phong". Nay `IngestPanel` gắn phần có trạng thái theo `key={sessionId}`:
 *    đổi phiên là bộ nhớ mới hoàn toàn, và phản hồi về muộn của phiên cũ rơi vào
 *    một panel đã gỡ (bị bỏ qua, có thêm cờ `conSong`).
 *  - NỀN TẢNG ĐANG CHỌN PHẢI NẰM TRONG DANH SÁCH ĐƯỢC MỜI. `mucDangChon` chỉ trả
 *    mục khi nền tảng đó còn được phép; không thì nút khoá và nền tảng được chọn
 *    lại theo mặc định.
 *  - KHÔNG ĐỌC ĐƯỢC THÌ NÓI KHÔNG ĐỌC ĐƯỢC. Danh sách nền tảng tải hỏng từng biến
 *    thành danh sách rỗng: ô chọn trống, nút khoá, không một câu giải thích, và
 *    không bao giờ thử lại. Nay có câu lỗi + nút Thử lại + tự đọc lại; nền tảng
 *    đang chọn chưa sẵn sàng thì cũng đọc lại (người kỹ thuật vừa điền .env và
 *    khởi động lại máy chủ).
 *  - NGUỒN LUÔN ĐƯỢC NÓI TÊN khi bộ thu đã bật — nguồn Mô phỏng nói rõ là bình
 *    luận tổng hợp, không phải khách thật (luật không khai sai nguồn dữ liệu).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { getIngestStatus, getPlatforms, startIngest, stopIngest } from "@/lib/api";
import { fmtNumber } from "@/lib/format";
import type { IngestPlatform, IngestState, IngestStatus, PlatformReadiness } from "@/lib/types";

import Button from "./ui/Button";
import Callout from "./ui/Callout";
import { cx } from "./ui/cx";
import { fieldCls } from "./ui/field";

const POLL_MS = 4000;
/** Nhịp đọc lại danh sách nền tảng khi chưa đọc được / nền tảng chưa sẵn sàng. */
const POLL_NEN_TANG_MS = 8000;
const STALE_S = 120;

const THU_DUOC: readonly string[] = ["youtube", "facebook", "shopee", "mo_phong"];

const NEN_TANG_MO_PHONG = "mo_phong";

/** Tên dự phòng khi chưa đọc được danh sách nền tảng của máy chủ. */
const TEN_NGUON: Record<string, string> = {
  youtube: "YouTube Live",
  facebook: "Facebook Live",
  shopee: "Shopee Live",
  mo_phong: "Mô phỏng",
};

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

/** Nền tảng được mời chọn: nguồn mô phỏng chỉ khi phiên cho phép. */
function nenTangChoPhep(allowSimulated: boolean): readonly string[] {
  return allowSimulated ? THU_DUOC : THU_DUOC.filter((p) => p !== NEN_TANG_MO_PHONG);
}

/**
 * Mục nền tảng đang chọn — CHỈ khi nền tảng đó còn nằm trong danh sách được mời
 * chọn. Không khớp thì null: nút Bật khoá, không gửi đi một nền tảng mà ô chọn
 * không hiện.
 */
function mucDangChon(
  platforms: readonly PlatformReadiness[] | null,
  platform: string,
  choPhep: readonly string[],
): PlatformReadiness | null {
  if (!platforms || !platform || !choPhep.includes(platform)) return null;
  return platforms.find((p) => p.platform === platform) ?? null;
}

/**
 * Nền tảng chọn sẵn: của phiên nếu được phép và máy chủ có bộ thu cho nó; không
 * thì nền tảng sẵn sàng đầu tiên; không thì nền tảng được phép đầu tiên máy chủ
 * có. Chuỗi rỗng khi chưa đọc được danh sách — không đoán.
 */
function nenTangMacDinh(
  platforms: readonly PlatformReadiness[] | null,
  sessionPlatform: string | null | undefined,
  choPhep: readonly string[],
): string {
  if (!platforms) return "";
  const coTrenMayChu = platforms.filter((p) => choPhep.includes(p.platform));
  if (sessionPlatform && coTrenMayChu.some((p) => p.platform === sessionPlatform)) {
    return sessionPlatform;
  }
  return (coTrenMayChu.find((p) => p.ready) ?? coTrenMayChu[0])?.platform ?? "";
}

/**
 * Tên nguồn của bộ thu đang/đã chạy, cho dòng trạng thái. `tongHop` = bình
 * luận do máy soạn (nguồn Mô phỏng) — phải nói ra, không để người xem bàn đọc
 * nhầm thành khách thật.
 */
function nhanNguon(
  platform: string | null | undefined,
  platforms: readonly PlatformReadiness[] | null,
): { ten: string; tongHop: boolean } | null {
  if (!platform) return null;
  const tongHop = platform === NEN_TANG_MO_PHONG;
  if (tongHop) return { ten: "Mô phỏng — bình luận tổng hợp, không phải khách thật", tongHop };
  const ten = platforms?.find((p) => p.platform === platform)?.ten ?? TEN_NGUON[platform];
  return { ten: ten ?? platform, tongHop };
}

/**
 * Có đọc lại danh sách nền tảng theo nhịp không: khi chưa đọc được (lần đầu hỏng
 * hay đang hỏng), hoặc khi nền tảng đang chọn chưa sẵn sàng (người kỹ thuật có
 * thể vừa điền khoá và khởi động lại máy chủ). Lỗi một lần lúc gắn KHÔNG được là
 * lỗi vĩnh viễn.
 */
function canDocLaiNenTang(
  platforms: readonly PlatformReadiness[] | null,
  loiDoc: boolean,
  chon: PlatformReadiness | null,
): boolean {
  return platforms == null || loiDoc || (chon != null && !chon.ready);
}

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

export default function IngestPanel(props: Props) {
  if (!props.sessionId) return null;
  // Trạng thái của bộ thu thuộc về MỘT phiên: gắn theo mã phiên để đổi phiên là
  // gắn lại từ đầu — không mang nền tảng, link, form mở hay cờ bận sang phiên khác.
  return <BoThuPhien key={props.sessionId} {...props} sessionId={props.sessionId} />;
}

function BoThuPhien({
  sessionId,
  sessionPlatform,
  sessionStatus,
  compact = false,
  allowSimulated = false,
  hideTitle = false,
  className,
}: Props & { sessionId: string }) {
  const [platforms, setPlatforms] = useState<PlatformReadiness[] | null>(null);
  const [platformsErr, setPlatformsErr] = useState(false);
  const [status, setStatus] = useState<IngestStatus | null>(null);
  const [platform, setPlatform] = useState<string>("");
  const [source, setSource] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [moForm, setMoForm] = useState(false);
  /** Panel còn gắn — phản hồi về sau khi gỡ (đổi phiên) không được ghi đè gì. */
  const conSong = useRef(true);

  useEffect(() => {
    conSong.current = true;
    return () => {
      conSong.current = false;
    };
  }, []);

  const phienDong = sessionStatus === "ended" || sessionStatus === "cancelled";

  const taiNenTang = useCallback(async () => {
    try {
      const list = await getPlatforms();
      if (!conSong.current) return;
      setPlatforms(list);
      setPlatformsErr(false);
    } catch {
      if (!conSong.current) return;
      // Đã có danh sách thì giữ (lỗi thoáng qua); chưa có thì nói không đọc được.
      setPlatformsErr(true);
    }
  }, []);

  useEffect(() => {
    void taiNenTang();
  }, [taiNenTang]);

  const choPhep = useMemo(() => nenTangChoPhep(allowSimulated), [allowSimulated]);

  const chon = useMemo(
    () => mucDangChon(platforms, platform, choPhep),
    [platforms, platform, choPhep],
  );

  // Chưa chọn, hoặc nền tảng đang chọn không còn được mời (phiên hết cho phép mô
  // phỏng) hay máy chủ không có ⇒ chọn lại theo mặc định.
  useEffect(() => {
    if (!platforms || chon) return;
    const macDinh = nenTangMacDinh(platforms, sessionPlatform, choPhep);
    if (macDinh !== platform) setPlatform(macDinh);
  }, [platforms, chon, platform, sessionPlatform, choPhep]);

  // Đọc lại danh sách nền tảng khi chưa đọc được, hoặc khi nền tảng đang chọn
  // chưa sẵn sàng (máy chủ có thể vừa được điền khoá và khởi động lại).
  const canDocLai = canDocLaiNenTang(platforms, platformsErr, chon);
  useEffect(() => {
    if (!canDocLai) return;
    const t = setInterval(() => void taiNenTang(), POLL_NEN_TANG_MS);
    return () => clearInterval(t);
  }, [canDocLai, taiNenTang]);

  const refresh = useCallback(async () => {
    try {
      const st = await getIngestStatus(sessionId);
      if (conSong.current) setStatus(st);
    } catch {
      // Mất kết nối tạm thời: giữ trạng thái cũ, lần poll sau thử lại.
    }
  }, [sessionId]);

  useEffect(() => {
    void refresh();
    const t = setInterval(() => void refresh(), POLL_MS);
    return () => clearInterval(t);
  }, [refresh]);

  const batDau = async () => {
    if (!chon) return;
    setBusy(true);
    setError(null);
    try {
      const st = await startIngest(sessionId, {
        platform: chon.platform as IngestPlatform,
        source: source.trim(),
      });
      if (!conSong.current) return;
      setStatus(st);
      setMoForm(false);
    } catch (e) {
      if (!conSong.current) return;
      setError(e instanceof Error ? e.message : "Không bật được bộ thu.");
    } finally {
      if (conSong.current) setBusy(false);
    }
  };

  const tat = async () => {
    setBusy(true);
    setError(null);
    try {
      const st = await stopIngest(sessionId);
      if (conSong.current) setStatus(st);
    } catch (e) {
      if (conSong.current) setError(e instanceof Error ? e.message : "Không tắt được bộ thu.");
    } finally {
      if (conSong.current) setBusy(false);
    }
  };

  const state: IngestState = status?.state ?? "chua_bat";
  const nhan = NHAN[state] ?? NHAN.chua_bat;
  const dangChay = status?.running ?? false;
  const cu =
    dangChay &&
    state === "dang_thu" &&
    status?.seconds_since_last_event != null &&
    status.seconds_since_last_event > STALE_S;
  const nguon = status && state !== "chua_bat" ? nhanNguon(status.platform, platforms) : null;

  const dongTrangThai = (
    <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1" aria-live="polite">
      <span className={cx("inline-flex items-center gap-1.5 font-semibold", nhan.mau)}>
        <span aria-hidden>{nhan.ky_hieu}</span>
        {nhan.chu}
      </span>
      {nguon ? (
        <span
          className={cx(
            "inline-flex items-center gap-1 text-meta",
            nguon.tongHop ? "font-semibold text-warn-ink" : "text-sec",
          )}
        >
          {nguon.tongHop ? <span aria-hidden>◐</span> : null}
          Nguồn: {nguon.ten}
        </span>
      ) : null}
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
  const luaChon = (platforms ?? []).filter((p) => choPhep.includes(p.platform));

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
      {(status?.pending_writes ?? 0) > 0 && (
        <p className="mt-1 text-meta text-warn-ink">
          ⚠ Kho dữ liệu đang trục trặc: {fmtNumber(status?.pending_writes ?? 0)} bản ghi đang chờ
          ghi lại. Bộ thu vẫn đọc bình luận; đừng tắt máy chủ lúc này.
        </p>
      )}
      {(status?.dropped_writes ?? 0) > 0 && (
        <p className="mt-1 text-meta text-crit-ink">
          ✕ Đã mất {fmtNumber(status?.dropped_writes ?? 0)} bản ghi vì kho dữ liệu hỏng quá lâu —
          phần số liệu này của phiên không đầy đủ.
        </p>
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
              value={chon ? platform : ""}
              onChange={(e) => setPlatform(e.target.value)}
              disabled={luaChon.length === 0}
            >
              {chon ? null : (
                <option value="" disabled>
                  {platforms == null ? "Đang đọc…" : "Chọn nền tảng"}
                </option>
              )}
              {luaChon.map((p) => (
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

      {hienForm && platforms == null && !platformsErr && (
        <p className="mt-2 text-meta text-sec">
          <span aria-hidden>◐</span> Đang hỏi máy chủ danh sách nền tảng thu được bình luận…
        </p>
      )}
      {hienForm && platforms == null && platformsErr && (
        <Callout tone="warn" slim className="mt-2">
          <span>
            Chưa đọc được danh sách nền tảng từ máy chủ — chưa bật được bộ thu. Trang tự thử lại
            sau vài giây.{" "}
          </span>
          <Button variant="ghost" size="sm" onClick={() => void taiNenTang()}>
            Thử lại
          </Button>
        </Callout>
      )}
      {hienForm && platforms != null && luaChon.length === 0 && (
        <p className="mt-2 text-meta text-warn-ink">
          <span aria-hidden>⚠</span> Máy chủ chưa có bộ thu nào dùng được cho phiên này — chưa
          bật được bộ thu.
        </p>
      )}
      {hienForm && chon && !chon.ready && (
        <p className="mt-2 text-meta text-warn-ink">
          ⚠ Máy chủ chưa có khoá cho {chon.ten}: thiếu {chon.missing.join(", ")}. Nhờ người kỹ
          thuật điền vào tệp .env rồi khởi động lại máy chủ.
        </p>
      )}
      {hienForm && chon && chon.ready && chon.platform === NEN_TANG_MO_PHONG && (
        <p className="mt-2 text-meta text-warn-ink">
          <span aria-hidden>◐</span> {chon.note}
        </p>
      )}
      {hienForm &&
        chon &&
        chon.ready &&
        chon.mode === "du_phong" &&
        chon.platform !== NEN_TANG_MO_PHONG &&
        !compact && <p className="mt-2 text-meta text-sec">{chon.note}</p>}
      {error && (
        <Callout tone="critical" slim className="mt-2">
          {error}
        </Callout>
      )}
    </section>
  );
}
