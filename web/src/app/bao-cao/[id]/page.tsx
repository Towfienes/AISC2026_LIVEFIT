"use client";

/**
 * "/bao-cao/[id]" — Báo cáo sau phiên cho người bán hàng (gói UI-KOL).
 *
 * Renders `GET /sessions/{id}/bao-cao` as a readable page: overview figures,
 * the signal matrix, the moment timeline, the intent distribution (with its
 * MANDATORY caveat), scrubbed-PII counts, the causal section — and honest
 * gaps everywhere a source is missing.
 *
 * The three project rules this page enforces at render time:
 * - KHÔNG BỊA SỐ: a null overview cell renders "THIẾU" + the server's reason
 *   from `tong_quan.thieu` — never the digit 0;
 * - E2-04 corollary: an observational session shows NO causal number at all,
 *   only the labeled `nhan`; the experiment section renders solely from
 *   `ket_qua_thi_nghiem` (which respects the §7 freeze server-side);
 * - the intent caveat (`phan_bo_y_dinh.caveat`) is ALWAYS displayed with the
 *   distribution — precision depends on each class's base rate.
 *
 * ĐÁNH GIÁ UI 17/09/2026 — hai sửa đổi:
 * - LỖI TẢI ĐƯỢC PHÂN LOẠI. Bản cũ gộp mọi lỗi thành một câu nghi ngờ mạng
 *   ("kiểm tra máy chủ API đã chạy chưa và phiên có tồn tại không"), kể cả
 *   khi máy chủ đang sống và trả 404 "Không tìm thấy phiên live". Ba lỗi khác
 *   nhau, ba việc cần làm khác nhau: KHÔNG CÓ PHIÊN NÀY (thử lại vô ích — đi
 *   tìm đúng phiên), MẤT KẾT NỐI (thử lại), MÁY CHỦ BÁO LỖI (in nguyên văn câu
 *   của máy chủ). Trang lỗi không còn các nút hành động của một báo cáo
 *   (mở bàn, phát lại, in PDF) — không có báo cáo nào để hành động cả.
 * - ĐƠN HÀNG (OrdersPanel): xem tổng đơn và nhập CSV ngay trên báo cáo.
 */

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import OrdersPanel from "@/components/OrdersPanel";
import PageHeader from "@/components/PageHeader";
import TomTat3Cau from "@/components/TomTat3Cau";
import TopNav from "@/components/TopNav";
import Badge from "@/components/ui/Badge";
import Button, { buttonCls } from "@/components/ui/Button";
import Callout from "@/components/ui/Callout";
import Card from "@/components/ui/Card";
import SectionTitle from "@/components/ui/SectionTitle";
import Skeleton from "@/components/ui/Skeleton";
import { getBaoCao } from "@/lib/api";
import { fmtClock, fmtNumber } from "@/lib/format";
import { CHART, INTENT_META, type BaoCao, type SignalStatus } from "@/lib/types";

/** Tên tiếng Việt cho các tín hiệu trong ma trận (khớp signals.py). */
const SIGNAL_LABEL: Record<string, string> = {
  schedule: "Lịch gán ngẫu nhiên",
  ticks: "Người xem theo thời gian",
  comments: "Bình luận (đã lọc PII)",
  clicks: "Lượt nhấp qua link đo",
  orders: "Đơn hàng đối soát",
  reactions: "Tim / quà / Super Chat",
};

/** Nhãn hiển thị cho bộ ý định mở rộng (11 lớp của live-fire). */
const INTENT_LABEL_EXT: Record<string, string> = {
  ...Object.fromEntries(Object.entries(INTENT_META).map(([k, v]) => [k, v.label])),
  chao_hoi: "Chào hỏi",
  cam_on_khen: "Cảm ơn / khen",
  hoi_sanpham: "Hỏi sản phẩm",
  hoi_daily: "Hỏi mở đại lý",
  bao_gia_shop: "Shop tự báo giá",
  hong_hoc: "Hỏng hóc / khiếu nại",
  khong_ro: "Không rõ",
};

/** Loại sự kiện tim/quà — API trả khoá tiếng Anh, màn hình phải là tiếng Việt. */
const REACTION_LABEL: Record<string, string> = {
  superchat: "Super Chat",
  gift: "Quà",
  sticker: "Sticker",
  membership: "Hội viên mới",
  like: "Tim",
};

const PII_LABEL: Record<string, string> = {
  phone: "Số điện thoại",
  email: "Email",
  order: "Mã đơn hàng",
  address: "Địa chỉ",
  name: "Tên riêng",
  social: "Tài khoản MXH",
  bank: "Số tài khoản",
};

const STATUS_BADGE: Record<SignalStatus, { tone: "good" | "warn" | "neutral"; label: string }> = {
  ok: { tone: "good", label: "CÓ" },
  degraded: { tone: "warn", label: "SUY GIẢM" },
  missing: { tone: "neutral", label: "THIẾU" },
};

/** Permutation test không nói được p nhỏ hơn 1/(số lần vẽ + 1). */
function formatP(p: number | null, draws: number | null): string {
  if (p == null) return "—";
  const floor = draws ? 1 / (draws + 1) : null;
  if (floor != null && p <= floor * 1.001) return `p < ${floor.toFixed(4)}`;
  return `p = ${p.toFixed(4)}`;
}

/**
 * Một ô tổng quan: hoặc GIÁ TRỊ đo được, hoặc chữ "THIẾU" + lý do của máy chủ.
 * Không bao giờ render 0 khi `value` là null — đó chính là luật của trang.
 */
function OverviewTile({
  label,
  value,
  hint,
  missingReason,
}: {
  label: string;
  value: React.ReactNode | null;
  hint?: React.ReactNode;
  missingReason?: string;
}) {
  return (
    <Card padding="md" className="flex min-w-0 flex-col">
      <div className="text-label uppercase text-dim">{label}</div>
      {value != null ? (
        <>
          {/* Bậc num-m (40px): đây là trang người bán đọc sau buổi live, ba
              con số đầu là thứ họ tìm trước tiên — bậc KPI 28px quá chìm. */}
          <div className="mt-1.5 text-num-m tracking-tight text-ink">{value}</div>
          {hint != null ? (
            <div className="mt-2 text-meta leading-snug text-sec">{hint}</div>
          ) : null}
        </>
      ) : (
        <>
          <div className="mt-1.5 text-strong text-dim">THIẾU</div>
          <div className="mt-2 text-meta leading-snug text-dim">
            {missingReason ?? "nguồn không cung cấp tín hiệu này"}
          </div>
        </>
      )}
    </Card>
  );
}

/**
 * Ba loại lỗi tải báo cáo — không gộp.
 *
 * `request()` của api.ts ném `Error(detail)` với câu tiếng Việt của máy chủ khi
 * máy chủ TRẢ LỜI mã lỗi (404 của `service.require_session` là "Không tìm thấy
 * phiên live…"), ném `Error("API <mã> …")` khi thân lỗi không phải JSON, và để
 * lọt `TypeError` (không nối được) hoặc `AbortError` (hết giờ) khi máy chủ
 * KHÔNG trả lời.
 *
 * Chỉ câu 404 TIẾNG VIỆT của máy chủ mới được hiểu là "không có phiên này". Một
 * 404 trần ("API 404 …" thân không phải JSON, hay "Not Found" mặc định của
 * FastAPI) nghĩa là địa chỉ đó không phục vụ đường báo cáo — phiên có thể vẫn
 * còn nguyên, nên KHÔNG được nói "không có phiên". 502/503/504 là cổng trung
 * gian đứng trước máy chủ LiveLift báo không nối được tới nó: mất kết nối.
 */
type LoiBaoCao =
  | { loai: "khong-co-phien"; maSai: boolean }
  | { loai: "mat-ket-noi" }
  | { loai: "may-chu-loi"; chiTiet: string | null };

function phanLoaiLoi(e: unknown): LoiBaoCao {
  const tenLoi =
    typeof e === "object" && e !== null ? (e as { name?: unknown }).name : undefined;
  if (e instanceof TypeError || tenLoi === "AbortError") return { loai: "mat-ket-noi" };
  const msg = e instanceof Error ? e.message.trim() : "";
  if (/^API 50[234]\b/.test(msg)) return { loai: "mat-ket-noi" };
  if (msg.startsWith("Không tìm thấy phiên")) {
    return { loai: "khong-co-phien", maSai: msg.includes("không hợp lệ") };
  }
  const kyThuat = msg === "" || msg.startsWith("API ") || msg === "Not Found";
  return { loai: "may-chu-loi", chiTiet: kyThuat ? null : msg };
}

function ReportSkeleton() {
  return (
    <div aria-busy>
      <p role="status" className="mb-3 text-body text-sec">
        Đang tải báo cáo phiên… Trang sẽ hiện ngay khi máy chủ trả dữ liệu.
      </p>
      <div className="grid gap-3 md:grid-cols-3">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <Card key={i}>
            <Skeleton className="h-3 w-24" />
            <Skeleton className="mt-2 h-7 w-28" />
            <Skeleton className="mt-2 h-3 w-36" />
          </Card>
        ))}
      </div>
      <Skeleton className="mt-3 h-40 w-full" />
    </div>
  );
}

export default function BaoCaoPage() {
  const params = useParams<{ id: string }>();
  const sessionId = typeof params?.id === "string" ? params.id : null;

  const [data, setData] = useState<BaoCao | null>(null);
  const [err, setErr] = useState<LoiBaoCao | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    setErr(null);
    try {
      setData(await getBaoCao(sessionId));
    } catch (e) {
      setData(null);
      setErr(phanLoaiLoi(e));
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void load();
  }, [load]);

  /** Đọc lại báo cáo mà không bật khung xương — sau khi nhập đơn, để ma trận
   *  tín hiệu ("Đơn hàng đối soát") khớp ngay với số đơn vừa ghi. Hỏng thì giữ
   *  bản đang hiện: bản đó vẫn đúng tới trước lúc nhập. */
  const refreshQuiet = useCallback(async () => {
    if (!sessionId) return;
    try {
      setData(await getBaoCao(sessionId));
    } catch {
      /* giữ nguyên bản đang hiển thị */
    }
  }, [sessionId]);

  const tq = data?.tong_quan ?? null;
  const observational = data?.loai_phien === "quan_sat";
  const kq = data?.ket_qua_thi_nghiem ?? null;
  const intentRows = data
    ? Object.entries(data.phan_bo_y_dinh.dem_theo_nhan).sort((a, b) => b[1] - a[1])
    : [];
  const intentMax = intentRows.reduce((m, [, n]) => Math.max(m, n), 0);
  const piiRows = data ? Object.entries(data.pii_da_che).sort((a, b) => b[1] - a[1]) : [];
  const piiTotal = piiRows.reduce((s, [, n]) => s + n, 0);

  return (
    <div className="flex min-h-screen flex-col bg-page">
      <TopNav />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        <PageHeader
          phase="sau"
          size="sm"
          className="mb-6"
          title={
            <span className="flex flex-wrap items-center gap-2">
              Báo cáo sau phiên
              {data ? (
                <Badge tone={observational ? "neutral" : "good"} dot>
                  {observational ? "PHIÊN QUAN SÁT" : "PHIÊN THÍ NGHIỆM"}
                </Badge>
              ) : null}
              {/* Chip DEMO trên MỌI số liệu sinh từ phiên demo (gói KẾT-QUẢ):
                  báo cáo phiên mẫu xem được đầy đủ nhưng không bao giờ được
                  trình bày như số đo thật. */}
              {data?.is_demo ? <Badge tone="warn">DEMO — dữ liệu mẫu</Badge> : null}
            </span>
          }
        >
          {data ? (
            <>
              <p className="mt-1 text-strong text-ink">{data.tieu_de ?? data.session_id}</p>
              {/* Nhãn nguồn của TOÀN trang — nói rõ báo cáo này được phép nói gì. */}
              <p className="mt-1 max-w-3xl text-body leading-relaxed text-sec">{data.nhan}</p>
              {/* Nút hành động CHỈ khi đã có báo cáo: trên trang lỗi không có gì để
                  mở, phát lại hay in. */}
              <div className="mt-3 flex flex-wrap items-center gap-2 print:hidden">
                <Link
                  href={`/ket-qua?phien=${data.session_id}`}
                  className={buttonCls("ghost", "sm")}
                >
                  Kết quả phiên này
                </Link>
                <Link href="/desk" className={buttonCls("ghost", "sm")}>
                  Mở bàn trợ live
                </Link>
                <Link
                  href={`/replay?session=${encodeURIComponent(data.session_id)}`}
                  className={buttonCls("ghost", "sm")}
                >
                  Xem phát lại
                </Link>
                <Button variant="ghost" size="sm" onClick={() => window.print()}>
                  In / lưu PDF
                </Button>
              </div>
            </>
          ) : null}
        </PageHeader>

        {loading ? <ReportSkeleton /> : null}

        {/* ── Lỗi tải: ba loại, ba câu, ba việc cần làm ── */}
        {!loading && err?.loai === "khong-co-phien" ? (
          <Card padding="lg" className="max-w-3xl" data-loi="khong-co-phien">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="neutral">
                <span aria-hidden className="font-bold">
                  ?
                </span>
                KHÔNG CÓ PHIÊN NÀY
              </Badge>
            </div>
            <h2 className="mt-3 font-display text-title font-bold tracking-tight text-ink">
              Máy chủ không có phiên nào mang mã này
            </h2>
            <p className="mt-2 text-body leading-relaxed text-sec">
              {err.maSai
                ? "Mã phiên trong đường dẫn không đúng định dạng — thường do link bị cắt mất một đoạn khi dán."
                : "Link có thể bị gõ nhầm, hoặc phiên thuộc một máy chủ khác."}{" "}
              Máy chủ vẫn trả lời, nên bấm thử lại cũng không ra báo cáo — hãy mở đúng phiên từ
              danh sách.
            </p>
            {sessionId ? (
              <p className="mt-2 break-all text-meta text-dim">
                Mã đã mở: <span className="font-num text-sec">{sessionId}</span>
              </p>
            ) : null}
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <Link href="/ket-qua" className={buttonCls("primary")}>
                Xem danh sách phiên
              </Link>
              <Link href="/" className={buttonCls("ghost")}>
                Về trang chính
              </Link>
            </div>
          </Card>
        ) : null}

        {!loading && err?.loai === "mat-ket-noi" ? (
          <Callout tone="critical" className="max-w-3xl">
            <strong>Mất kết nối tới máy chủ — chưa đọc được báo cáo.</strong> Nếu phiên có thật,
            dữ liệu vẫn còn nguyên trên máy chủ; bật lại máy chủ LiveLift rồi thử lại.{" "}
            <button
              type="button"
              onClick={() => void load()}
              className="focus-ring min-h-tap rounded underline underline-offset-2 transition-colors duration-short2 ease-emphasized hover:text-ink"
            >
              Thử lại
            </button>
          </Callout>
        ) : null}

        {!loading && err?.loai === "may-chu-loi" ? (
          <Callout tone="critical" className="max-w-3xl">
            <strong>Máy chủ đang chạy nhưng không lập được báo cáo.</strong>{" "}
            {err.chiTiet ? <>Máy chủ nói: “{err.chiTiet}”. </> : null}
            <button
              type="button"
              onClick={() => void load()}
              className="focus-ring min-h-tap rounded underline underline-offset-2 transition-colors duration-short2 ease-emphasized hover:text-ink"
            >
              Thử lại
            </button>
          </Callout>
        ) : null}

        {data && tq ? (
          <>
            {/* 0 — Tóm tắt 3 câu: kết luận / bằng chứng / việc nên làm —
                máy soạn câu tất định phía server (analysis/narrate.py). */}
            {data.tom_tat_3_cau && data.tom_tat_3_cau.length > 0 ? (
              <TomTat3Cau cau={data.tom_tat_3_cau} demo={data.is_demo} className="mb-6" />
            ) : null}

            {/* 1 — Tổng quan: mỗi ô hoặc có giá trị, hoặc THIẾU + lý do */}
            <section>
              <SectionTitle>Tổng quan</SectionTitle>
              <div className="grid gap-3 md:grid-cols-3">
                <OverviewTile
                  label="Thời lượng"
                  value={tq.thoi_luong_s != null ? fmtClock(tq.thoi_luong_s) : null}
                  hint="giờ:phút:giây phát sóng"
                  missingReason={tq.thieu.thoi_luong}
                />
                <OverviewTile
                  label="Bình luận"
                  value={fmtNumber(tq.tong_binh_luan)}
                  hint={
                    tq.dinh_binh_luan
                      ? `đỉnh ${fmtNumber(Math.round(tq.dinh_binh_luan.gia_tri_per_phut))} tin/phút` +
                        (tq.dinh_binh_luan.offset_s != null
                          ? ` ở phút ${Math.floor(tq.dinh_binh_luan.offset_s / 60)}`
                          : "")
                      : (tq.thieu.dinh_binh_luan ?? "chưa xác định được đỉnh")
                  }
                />
                <OverviewTile
                  label="Người xem đồng thời"
                  value={tq.nguoi_xem ? fmtNumber(Math.round(tq.nguoi_xem.dinh)) : null}
                  hint={
                    tq.nguoi_xem
                      ? `đỉnh · trung bình ${fmtNumber(Math.round(tq.nguoi_xem.trung_binh))} · ${fmtNumber(tq.nguoi_xem.n_diem_do)} điểm đo`
                      : undefined
                  }
                  missingReason={tq.thieu.nguoi_xem}
                />
                <OverviewTile
                  label="Lượt nhấp hợp lệ"
                  value={tq.luot_nhap_hop_le != null ? fmtNumber(tq.luot_nhap_hop_le) : null}
                  hint="qua link đo tự phục vụ, đã lọc click không hợp lệ"
                  missingReason={tq.thieu.luot_nhap}
                />
                <OverviewTile
                  label="Tim & quà"
                  value={tq.reactions ? fmtNumber(tq.reactions.tong) : null}
                  hint={
                    tq.reactions
                      ? Object.entries(tq.reactions.theo_loai)
                          .map(([k, n]) => `${REACTION_LABEL[k] ?? k}: ${fmtNumber(n)}`)
                          .join(" · ") +
                        (Object.keys(tq.reactions.tong_tien).length
                          ? " · " +
                            Object.entries(tq.reactions.tong_tien)
                              .map(([cur, s]) => `${fmtNumber(s)} ${cur}`)
                              .join(" · ")
                          : "")
                      : undefined
                  }
                  missingReason={tq.thieu.reactions}
                />
                <OverviewTile
                  label="PII đã che"
                  value={fmtNumber(piiTotal)}
                  hint={
                    piiRows.length
                      ? piiRows
                          .map(([k, n]) => `${PII_LABEL[k] ?? k}: ${fmtNumber(n)}`)
                          .join(" · ")
                      : "không phát hiện thông tin cá nhân nào trong chat"
                  }
                />
              </div>
            </section>

            {/* 2 — Ma trận tín hiệu: cái gì đo được, cái gì thiếu, vì sao */}
            <section className="mt-6">
              <SectionTitle>Ma trận tín hiệu</SectionTitle>
              <Card padding="none" className="divide-y divide-white/10">
                {data.tin_hieu.map((s) => (
                  <div key={s.name} className="flex flex-wrap items-start gap-x-3 gap-y-1 p-3">
                    <span className="w-56 shrink-0 text-body text-ink">
                      {SIGNAL_LABEL[s.name] ?? s.name}
                    </span>
                    <Badge tone={STATUS_BADGE[s.status].tone}>
                      {STATUS_BADGE[s.status].label}
                    </Badge>
                    <span className="min-w-0 flex-1 text-meta leading-snug text-sec">
                      {s.detail}
                    </span>
                  </div>
                ))}
              </Card>
              <div className="mt-2 flex flex-wrap gap-2">
                {data.nang_luc.map((c) => (
                  <span
                    key={c.name}
                    title={c.reason}
                    className="inline-flex items-center gap-1.5 rounded-full border border-hairline bg-surface px-2.5 py-1 text-meta text-sec"
                  >
                    <Badge tone={STATUS_BADGE[c.status].tone}>{STATUS_BADGE[c.status].label}</Badge>
                    {c.name}
                  </span>
                ))}
              </div>
            </section>

            {/* 2b — Đơn hàng: chỉ số PHỤ. Đặt ngay dưới ma trận tín hiệu, nơi dòng
                "Đơn hàng đối soát" báo THIẾU — người bán sửa được ngay tại chỗ. */}
            <OrdersPanel
              sessionId={data.session_id}
              isDemo={data.is_demo}
              onImported={() => void refreshQuiet()}
              className="mt-6"
            />

            {/* 3 — Khoảnh khắc nổi bật (câu quan sát dán nhãn, không nhân quả) */}
            <section className="mt-6">
              <SectionTitle meta="spike nhịp bình luận trên nền 5 phút">
                Khoảnh khắc nổi bật
              </SectionTitle>
              {data.khoanh_khac.length === 0 ? (
                <Card className="text-body leading-relaxed text-sec">
                  {data.khoanh_khac_ghi_chu ?? "Không có spike bình luận vượt ngưỡng trong phiên."}
                </Card>
              ) : (
                <ol className="flex flex-col gap-2">
                  {data.khoanh_khac.map((kk) => (
                    <li key={kk.offset_s}>
                      <Card padding="sm" className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
                        <span className="tnum text-num-s text-ink">
                          {String(Math.floor(kk.offset_s / 3600)).padStart(2, "0")}:
                          {String(Math.floor((kk.offset_s % 3600) / 60)).padStart(2, "0")}
                        </span>
                        <span className="tnum text-strong text-ink">
                          {fmtNumber(Math.round(kk.binh_luan_per_phut))} tin/phút
                        </span>
                        <span className="text-meta text-dim">
                          nền {fmtNumber(Math.round(kk.nen_per_phut))}
                          {kk.ty_le != null ? ` · gấp ${kk.ty_le.toFixed(1)} lần` : ""}
                        </span>
                        <span className="min-w-0 flex-1 basis-full text-body leading-snug text-sec">
                          {kk.mo_ta}
                        </span>
                      </Card>
                    </li>
                  ))}
                </ol>
              )}
            </section>

            {/* 4 — Phân bố ý định + caveat BẮT BUỘC */}
            <section className="mt-6">
              <SectionTitle meta={`${fmtNumber(data.phan_bo_y_dinh.tong)} bình luận`}>
                Phân bố ý định (nhãn tự động)
              </SectionTitle>
              <Callout tone="warn" className="mb-3">
                {data.phan_bo_y_dinh.caveat}
              </Callout>
              <Card>
                <ul className="flex flex-col gap-1.5">
                  {intentRows.map(([label, count]) => {
                    const meta = (
                      INTENT_META as Partial<Record<string, { label: string; color: string }>>
                    )[label];
                    const pct =
                      data.phan_bo_y_dinh.tong > 0
                        ? (count / data.phan_bo_y_dinh.tong) * 100
                        : 0;
                    return (
                      <li key={label} className="flex items-center gap-3">
                        <span className="w-40 shrink-0 truncate text-body text-sec">
                          {INTENT_LABEL_EXT[label] ?? label}
                        </span>
                        <span
                          aria-hidden
                          className="h-4 shrink-0 rounded-sm"
                          style={{
                            width: `${intentMax > 0 ? Math.max(1, (count / intentMax) * 100) : 1}%`,
                            maxWidth: "50%",
                            background: meta?.color ?? CHART.mut,
                          }}
                        />
                        <span className="tnum shrink-0 text-body text-ink">
                          {fmtNumber(count)}
                        </span>
                        <span className="tnum shrink-0 text-meta text-dim">
                          {pct.toFixed(1)}%
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </Card>
            </section>

            {/* 5 — Kết quả thí nghiệm HOẶC nhãn quan sát (E2-04) */}
            <section className="mt-6">
              <SectionTitle>Kết quả thí nghiệm</SectionTitle>
              {observational || kq == null ? (
                <Card className="text-body leading-relaxed text-sec">
                  <strong className="text-ink">Phiên quan sát — không có số nhân quả.</strong>{" "}
                  Buổi phát gốc không có lịch gán ngẫu nhiên nên không tồn tại phép so sánh
                  BẬT/TẮT nào để ước lượng tác động. Mọi con số ở trên là mô tả; muốn đo tác
                  động thật, hãy chạy phiên có lịch gán qua trang{" "}
                  <Link
                    href="/chay-phien"
                    className="focus-ring rounded underline underline-offset-2"
                  >
                    Chuẩn bị phiên
                  </Link>
                  .
                </Card>
              ) : (
                <>
                  {kq.khoa && kq.ly_do_khoa ? (
                    <Callout tone="warn" className="mb-3">
                      {kq.ly_do_khoa}
                    </Callout>
                  ) : null}
                  {kq.estimable && kq.estimate != null ? (
                    <Card padding="lg">
                      <div className="text-label uppercase text-dim">
                        Tác động ước lượng (nhấp/1000 giây·người xem)
                      </div>
                      <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1">
                        <span className="text-num-m text-ink">{kq.estimate.toFixed(3)}</span>
                        <span className="tnum text-strong text-sec">
                          KTC 95% [{kq.ci_low?.toFixed(3) ?? "—"} … {kq.ci_high?.toFixed(3) ?? "—"}]
                        </span>
                        <span className="tnum text-body text-sec">
                          {formatP(kq.p_value, kq.n_draws)}
                        </span>
                      </div>
                      <p className="mt-2 text-meta leading-snug text-sec">
                        {kq.n_blocks} khối đo được · {kq.n_on} BẬT / {kq.n_off} TẮT · kiểm định
                        dựa trên ngẫu nhiên hóa
                        {kq.n_draws ? ` (${fmtNumber(kq.n_draws)} lần vẽ lại)` : ""}
                      </p>
                    </Card>
                  ) : (
                    <Card className="text-body leading-relaxed text-sec">
                      <strong className="text-ink">Chưa ước lượng được tác động.</strong>{" "}
                      {kq.message ??
                        "Chưa đủ khối đo được cho phiên này — tuyên bố thiếu, không trả số."}{" "}
                      <span className="text-dim">
                        ({kq.n_blocks} khối đo được · {kq.n_on} BẬT / {kq.n_off} TẮT)
                      </span>
                    </Card>
                  )}
                </>
              )}
            </section>

            {/* 6 — Gợi ý chiến thuật: câu quan sát đã dán nhãn từ máy chủ */}
            <section className="mt-6">
              <SectionTitle>Gợi ý chiến thuật cho phiên sau</SectionTitle>
              {data.goi_y_chien_thuat.length === 0 ? (
                <Card className="text-body leading-relaxed text-sec">
                  Chưa đủ dữ liệu để rút gợi ý nào từ phiên này.
                </Card>
              ) : (
                <Card>
                  <ul className="flex list-disc flex-col gap-2 pl-5">
                    {data.goi_y_chien_thuat.map((g) => (
                      <li key={g} className="text-body leading-relaxed text-sec">
                        {g}
                      </li>
                    ))}
                  </ul>
                </Card>
              )}
              <p className="mt-3 text-meta leading-relaxed text-dim">
                Mỗi gợi ý là một QUAN SÁT có dán nhãn — chưa kiểm chứng nhân quả. Muốn biết một
                chiến thuật có thật sự tăng nhấp hay không, đưa nó vào phiên thí nghiệm có lịch
                gán ngẫu nhiên.
              </p>
            </section>
          </>
        ) : null}
      </main>
    </div>
  );
}
