"use client";

/**
 * "/ket-qua" — màn kết luận của dự án, VERDICT-FIRST (gói KẾT-QUẢ v2).
 *
 * Đơn đặt hàng từ phản biện khoa học (ưu tiên #6 — điều kiện bắt buộc):
 * CẢ BA trạng thái kết quả được thiết kế RIÊNG với mức công phu NGANG NHAU —
 * - DƯƠNG/ÂM: khu tuyên bố tác động với con số lớn + thanh KTC; con dấu
 *   "TÁC ĐỘNG THẬT" CHỈ hiện khi KTC 95% loại 0 và luôn đứng cạnh chính KTC;
 * - NULL: huy hiệu "KẾT QUẢ TRUNG THỰC" — vì sao null vẫn đáng tiền, và bảng
 *   "cần thêm bao nhiêu phiên" giải từ CV đo được (không phải lời an ủi);
 * - CHƯA ĐỦ ĐIỀU KIỆN / KHÓA §7: hệ thống TỪ CHỐI kết luận, in nguyên văn lý
 *   do máy chủ + checklist thiết kế cần gì để có ước lượng.
 *
 * CẤM count-up cho ước lượng nhân quả (phản biện #1): mọi con số suy diễn
 * đứng yên từ khung hình đầu — chuyển động không được phép làm một ước lượng
 * có KTC trông chắc chắn hơn mức nó là.
 *
 * Hai chế độ xem:
 * - mặc định: bản GỘP `GET /experiment/summary` (env=real; `?env=demo` xem
 *   bản gộp dữ liệu mẫu, luôn dán nhãn MÔ PHỎNG);
 * - `?phien=<id>`: verdict của MỘT phiên từ `GET /sessions/{id}/bao-cao`
 *   (đúng lối "trang kết quả của web với phiên tương ứng" trong
 *   docs/demo-vang.md) — phiên demo đeo chip DEMO trên mọi con số.
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import PageHeader from "@/components/PageHeader";
import TomTat3Cau from "@/components/TomTat3Cau";
import TopNav from "@/components/TopNav";
import Badge from "@/components/ui/Badge";
import { buttonCls } from "@/components/ui/Button";
import Callout from "@/components/ui/Callout";
import Card from "@/components/ui/Card";
import SectionTitle from "@/components/ui/SectionTitle";
import Skeleton from "@/components/ui/Skeleton";
import StatTile from "@/components/ui/StatTile";
import { getBaoCao, getExperimentSummary, listSessions } from "@/lib/api";
import { fmtDateHCM, fmtNumber, fmtPct } from "@/lib/format";
import type {
  BaoCao,
  BaoCaoKetQuaThiNghiem,
  ExperimentSummary,
  PowerRow,
  SessionSummary,
} from "@/lib/types";

/**
 * Permutation test không nói được p nhỏ hơn 1/(số lần vẽ + 1) — in sàn đó
 * một cách trung thực thay vì một con số chính-xác-giả.
 */
function formatP(p: number | null, draws: number | null): string {
  if (p == null) return "—";
  const floor = draws ? 1 / (draws + 1) : null;
  if (floor != null && p <= floor * 1.001) return `p < ${floor.toFixed(4)}`;
  return `p = ${p.toFixed(4)}`;
}

// ---------------------------------------------------------------------------
// Verdict: một hình dạng dữ liệu chung cho bản gộp và bản một-phiên
// ---------------------------------------------------------------------------

type VerdictState = "duong" | "am" | "null" | "chuadu";

interface VerdictData {
  state: VerdictState;
  /** true khi CHUA-DU đến từ khóa §7 (khác với thiếu khối/phiên). */
  khoa: boolean;
  /** Lý do tiếng Việt của máy chủ — in nguyên văn, không viết lại. */
  lyDo: string | null;
  estimate: number | null;
  ciLow: number | null;
  ciHigh: number | null;
  pValue: number | null;
  nDraws: number | null;
  nBlocks: number;
  nOn: number;
  nOff: number;
  /** null ở bản một-phiên (ngưỡng phiên không áp dụng). */
  nSessions: number | null;
  /** Mọi con số ở đây sinh từ dữ liệu mẫu — đeo chip DEMO. */
  isDemo: boolean;
}

/** Cùng luật phân loại với analysis/narrate.trang_thai_ket_luan phía server. */
function verdictState(
  estimable: boolean,
  ciLow: number | null,
  ciHigh: number | null,
): VerdictState {
  if (!estimable) return "chuadu";
  if (ciLow != null && ciLow > 0) return "duong";
  if (ciHigh != null && ciHigh < 0) return "am";
  return "null";
}

function verdictFromSummary(d: ExperimentSummary): VerdictData {
  const estimable = d.estimable !== false && d.n_blocks > 0 && d.estimate != null;
  return {
    state: verdictState(estimable, d.ci_low, d.ci_high),
    // Bản gộp không có cờ khóa riêng — nhận diện §7 qua chính câu lý do.
    khoa: d.estimable === false && (d.message ?? "").includes("§7"),
    lyDo: d.message ?? null,
    estimate: d.estimate,
    ciLow: d.ci_low,
    ciHigh: d.ci_high,
    pValue: d.p_value,
    nDraws: d.n_draws,
    nBlocks: d.n_blocks,
    nOn: d.n_on,
    nOff: d.n_off,
    nSessions: d.n_sessions,
    isDemo: d.env === "demo",
  };
}

function verdictFromKetQua(kq: BaoCaoKetQuaThiNghiem, isDemo: boolean): VerdictData {
  const estimable = kq.estimable && kq.estimate != null;
  return {
    state: verdictState(estimable, kq.ci_low, kq.ci_high),
    khoa: kq.khoa,
    lyDo: kq.khoa ? kq.ly_do_khoa : (kq.message ?? null),
    estimate: kq.estimate,
    ciLow: kq.ci_low,
    ciHigh: kq.ci_high,
    pValue: kq.p_value,
    nDraws: kq.n_draws,
    nBlocks: kq.n_blocks,
    nOn: kq.n_on,
    nOff: kq.n_off,
    nSessions: null,
    isDemo,
  };
}

// ---------------------------------------------------------------------------
// Thanh khoảng tin cậy — TĨNH (không vẽ dần, không count-up: chuyển động không
// được phép làm ước lượng nhân quả trông chắc hơn mức KTC cho phép)
// ---------------------------------------------------------------------------

function CIBar({
  lo,
  hi,
  est,
  tone,
}: {
  lo: number;
  hi: number;
  est: number;
  tone: "good" | "crit" | "neutral";
}) {
  const min = Math.min(lo, 0);
  const max = Math.max(hi, 0);
  const pad = (max - min || 1) * 0.1;
  const d0 = min - pad;
  const span = max + pad - d0;
  const pct = (x: number) => `${(((x - d0) / span) * 100).toFixed(2)}%`;
  const band =
    tone === "good" ? "bg-good/25" : tone === "crit" ? "bg-critical/25" : "bg-white/20";
  const dot = tone === "good" ? "bg-good" : tone === "crit" ? "bg-critical" : "bg-ink";
  return (
    <div aria-hidden className="mt-4">
      <div className="relative h-9">
        {/* trục nền */}
        <div className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-white/10" />
        {/* vạch 0 tham chiếu — mốc mà mọi kết luận xoay quanh */}
        <div
          className="absolute top-0 h-full w-px bg-white/40"
          style={{ left: pct(0) }}
        />
        {/* dải KTC 95% */}
        <div
          className={`absolute top-1/2 h-2.5 -translate-y-1/2 rounded-full ${band}`}
          style={{ left: pct(lo), width: `calc(${pct(hi)} - ${pct(lo)})` }}
        />
        {/* hai đầu mút */}
        <div
          className="absolute top-1/2 h-4 w-0.5 -translate-y-1/2 rounded bg-sec"
          style={{ left: pct(lo) }}
        />
        <div
          className="absolute top-1/2 h-4 w-0.5 -translate-y-1/2 rounded bg-sec"
          style={{ left: pct(hi) }}
        />
        {/* điểm ước lượng */}
        <div
          className={`absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ${dot}`}
          style={{ left: pct(est) }}
        />
      </div>
      <div className="relative h-4 text-meta text-dim">
        <span className="tnum absolute -translate-x-1/2" style={{ left: pct(lo) }}>
          {lo.toFixed(3)}
        </span>
        <span className="tnum absolute -translate-x-1/2" style={{ left: pct(0) }}>
          0
        </span>
        <span className="tnum absolute -translate-x-1/2" style={{ left: pct(hi) }}>
          {hi.toFixed(3)}
        </span>
      </div>
    </div>
  );
}

/** Hàng chỉ số phụ dưới thanh KTC — chung cho DƯƠNG/ÂM/NULL. */
function EvidenceRow({ v }: { v: VerdictData }) {
  return (
    <div className="mt-4 grid gap-3 sm:grid-cols-3">
      <div className="rounded-lg border border-hairline bg-page/40 p-3">
        <div className="text-label uppercase text-dim">Mức ý nghĩa</div>
        <div className="tnum mt-1 text-strong text-ink">{formatP(v.pValue, v.nDraws)}</div>
        <div className="mt-1 text-meta text-dim">
          kiểm định hoán vị
          {v.nDraws ? ` · ${fmtNumber(v.nDraws)} lần vẽ lại` : ""}
        </div>
      </div>
      <div className="rounded-lg border border-hairline bg-page/40 p-3">
        <div className="text-label uppercase text-dim">Cỡ mẫu</div>
        <div className="tnum mt-1 text-strong text-ink">{v.nBlocks} khối</div>
        <div className="mt-1 text-meta text-dim">
          {v.nOn} BẬT / {v.nOff} TẮT
        </div>
      </div>
      <div className="rounded-lg border border-hairline bg-page/40 p-3">
        <div className="text-label uppercase text-dim">Phạm vi</div>
        <div className="tnum mt-1 text-strong text-ink">
          {v.nSessions != null ? `${v.nSessions} phiên` : "1 phiên"}
        </div>
        <div className="mt-1 text-meta text-dim">
          {v.nSessions != null ? "gộp mọi phiên thí nghiệm đã kết thúc" : "kết quả của riêng phiên này"}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// BA TRẠNG THÁI VERDICT — ba thiết kế riêng, cùng mức công phu
// ---------------------------------------------------------------------------

/** DƯƠNG / ÂM: KTC 95% loại 0 — chỉ ở đây con dấu "TÁC ĐỘNG THẬT" được đóng. */
function VerdictCoTacDong({ v }: { v: VerdictData }) {
  const duong = v.state === "duong";
  return (
    <Card
      padding="lg"
      className={`motion-reveal relative overflow-hidden ${duong ? "border-good/40" : "border-critical/40"}`}
      data-verdict={v.state}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background: duong
            ? "radial-gradient(700px 260px at 18% -20%, rgba(61,220,122,.14), transparent 60%)"
            : "radial-gradient(700px 260px at 18% -20%, rgba(240,138,138,.12), transparent 60%)",
        }}
      />
      <div className="relative">
        <div className="flex flex-wrap items-center gap-2">
          {/* Con dấu CHỈ tồn tại trong nhánh KTC-loại-0, và KTC đứng ngay
              trong chính con dấu — không bao giờ tách điểm ước lượng khỏi
              khoảng của nó (phản biện #1). */}
          <Badge tone={duong ? "good" : "critical"} dot>
            TÁC ĐỘNG THẬT · KTC 95% không chứa 0
          </Badge>
          {v.isDemo ? <Badge tone="warn">DEMO — dữ liệu mẫu</Badge> : null}
        </div>
        <h2 className="mt-3 font-display text-title font-bold tracking-tight text-ink">
          {duong
            ? "CÓ — hệ thống làm tăng lượt nhấp sản phẩm"
            : "CÓ TÁC ĐỘNG — nhưng theo chiều GIẢM"}
        </h2>
        <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1">
          <span
            className={`tnum font-num text-num-l ${duong ? "text-good-ink" : "text-crit-ink"}`}
          >
            {v.estimate! > 0 ? "+" : ""}
            {v.estimate!.toFixed(3)}
          </span>
          <span className="tnum text-strong text-sec">
            KTC 95% [{v.ciLow!.toFixed(3)} … {v.ciHigh!.toFixed(3)}]
          </span>
        </div>
        <p className="mt-1 text-meta leading-snug text-sec">
          nhấp thêm trên mỗi 1000 giây·người xem so với khối TẮT · giá trị thật nằm trong
          khoảng trên với độ tin cậy 95%
        </p>
        <CIBar lo={v.ciLow!} hi={v.ciHigh!} est={v.estimate!} tone={duong ? "good" : "crit"} />
        <EvidenceRow v={v} />
        {!duong ? (
          <p className="mt-3 text-body leading-relaxed text-sec">
            Tác dụng ngược cũng là một phép đo thật: hệ thống báo cáo nó với đúng mức nhấn thị
            giác như một kết quả dương — xem lại chiến lược ghim trước khi chạy tiếp.
          </p>
        ) : null}
      </div>
    </Card>
  );
}

/**
 * NULL: ước lượng được nhưng KTC còn chứa 0 — trạng thái DỄ XẢY RA NHẤT với
 * MDE ~20%, nên nó được thiết kế đẹp ngang kết quả dương: đây là hệ thống
 * đang trung thực, không phải hệ thống đang thất bại.
 */
function VerdictNull({ v, powerTable }: { v: VerdictData; powerTable: PowerRow[] }) {
  return (
    <Card padding="lg" className="motion-reveal relative overflow-hidden border-s7/40" data-verdict="null">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(700px 260px at 18% -20%, rgba(139,123,255,.14), transparent 60%)",
        }}
      />
      <div className="relative">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="violet" dot>
            KẾT QUẢ TRUNG THỰC
          </Badge>
          {v.isDemo ? <Badge tone="warn">DEMO — dữ liệu mẫu</Badge> : null}
        </div>
        <h2 className="mt-3 font-display text-title font-bold tracking-tight text-ink">
          CHƯA ĐỦ BẰNG CHỨNG để kết luận — và đó là một kết quả hợp lệ
        </h2>
        <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1">
          <span className="tnum font-num text-num-l text-ink">
            {v.estimate! > 0 ? "+" : ""}
            {v.estimate!.toFixed(3)}
          </span>
          <span className="tnum text-strong text-sec">
            KTC 95% [{v.ciLow!.toFixed(3)} … {v.ciHigh!.toFixed(3)}] · còn chứa 0
          </span>
        </div>
        <p className="mt-1 text-meta leading-snug text-sec">
          nhấp thêm trên mỗi 1000 giây·người xem — khoảng tin cậy vắt qua vạch 0, nên tăng hay
          giảm đều chưa loại trừ được may rủi
        </p>
        <CIBar lo={v.ciLow!} hi={v.ciHigh!} est={v.estimate!} tone="neutral" />
        <EvidenceRow v={v} />
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <div className="rounded-lg border border-hairline bg-page/40 p-4">
            <h3 className="text-strong text-ink">Vì sao kết quả null vẫn đáng tiền</h3>
            <ul className="mt-2 flex list-disc flex-col gap-1.5 pl-5 text-body leading-relaxed text-sec">
              <li>
                Nó <strong className="text-ink">chặn một quyết định sai</strong>: không có nó,
                bạn có thể đổi cả chiến lược bán vì một chênh lệch thuần may rủi.
              </li>
              <li>
                Nó là phép đo có khoảng: hiệu ứng thật (nếu có) nằm trong chính KTC ở trên —
                nhỏ hơn ngưỡng mà lượng dữ liệu hiện tại phát hiện nổi.
              </li>
              <li>
                Đa số nền tảng chỉ khoe kết quả đẹp; một hệ thống dám in chữ
                &quot;chưa đủ bằng chứng&quot; là hệ thống mà con số dương của nó mới đáng tin.
              </li>
            </ul>
          </div>
          <div className="rounded-lg border border-hairline bg-page/40 p-4">
            <h3 className="text-strong text-ink">Cần thêm bao nhiêu phiên?</h3>
            {powerTable.length > 0 ? (
              <>
                <table className="mt-2 w-full text-body">
                  <thead className="text-label uppercase text-dim">
                    <tr>
                      <th className="py-1 text-left font-medium">Kịch bản</th>
                      <th className="py-1 text-right font-medium">Phiên</th>
                      <th className="py-1 text-right font-medium">Phát hiện được</th>
                    </tr>
                  </thead>
                  <tbody>
                    {powerTable.map((r) => (
                      <tr key={r.scenario} className="border-t border-hairline">
                        <td className="py-1.5 pr-2 text-sec">{r.scenario}</td>
                        <td className="tnum py-1.5 text-right text-ink">{r.n_sessions}</td>
                        <td className="tnum py-1.5 text-right font-semibold text-ink">
                          hiệu ứng ≥ {fmtPct(r.mde_relative).replace("+", "")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="mt-2 text-meta leading-snug text-dim">
                  tính từ CV <em>đo được</em> của chính chuỗi phiên này — không phải giả định
                  đẹp; chi tiết ở mục &quot;Chi tiết thống kê&quot; bên dưới.
                </p>
              </>
            ) : (
              <p className="mt-2 text-body leading-relaxed text-sec">
                Bảng lực thống kê được giải trên bản gộp nhiều phiên (cần CV đo được của cả
                chuỗi).{" "}
                <Link href="/ket-qua" className="focus-ring rounded underline underline-offset-2">
                  Xem kết quả gộp
                </Link>{" "}
                để biết cần thêm bao nhiêu phiên.
              </p>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}

/**
 * CHƯA ĐỦ ĐIỀU KIỆN (estimable=false) hoặc KHÓA §7: hệ thống TỪ CHỐI trả số
 * và nói rõ vì sao + thiết kế cần gì — khoảnh khắc "dám từ chối kết luận"
 * được dàn dựng công phu như hai trạng thái kia, không phải một dòng lỗi xám.
 */
function VerdictChuaDu({ v }: { v: VerdictData }) {
  // Ngưỡng THIẾT KẾ đã tiền đăng ký: bản gộp cần ≥2 phiên & ≥8 khối; báo cáo
  // một phiên cần ≥4 khối đo được (MIN_BAO_CAO_BLOCKS phía server).
  const gop = v.nSessions != null;
  const checklist = gop
    ? [
        { can: "≥ 2 phiên thí nghiệm đã kết thúc", hienCo: v.nSessions!, nguong: 2 },
        { can: "≥ 8 khối đo được", hienCo: v.nBlocks, nguong: 8 },
      ]
    : [{ can: "≥ 4 khối đo được trong phiên", hienCo: v.nBlocks, nguong: 4 }];
  return (
    <Card padding="lg" className="motion-reveal relative overflow-hidden border-warn/40" data-verdict="chuadu">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(700px 260px at 18% -20%, rgba(250,178,25,.10), transparent 60%)",
        }}
      />
      <div className="relative">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="warn" dot>
            {v.khoa ? "KHÓA THEO TIỀN ĐĂNG KÝ §7" : "CHƯA ĐỦ ĐIỀU KIỆN"}
          </Badge>
          {v.isDemo ? <Badge tone="warn">DEMO — dữ liệu mẫu</Badge> : null}
        </div>
        <h2 className="mt-3 font-display text-title font-bold tracking-tight text-ink">
          {v.khoa
            ? "Hệ thống tự khóa ước lượng — đúng hẹn mới mở"
            : "Hệ thống từ chối kết luận — và nói rõ vì sao"}
        </h2>
        <p className="mt-2 max-w-3xl text-body leading-relaxed text-sec">
          {v.lyDo ??
            "Thiết kế hiện tại chưa kiểm định được — cần thêm phiên có lịch gán ngẫu nhiên."}
        </p>
        <div className="mt-4 rounded-lg border border-hairline bg-page/40 p-4">
          <h3 className="text-strong text-ink">
            {v.khoa ? "Số liệu vận hành vẫn công khai" : "Thiết kế cần gì để có ước lượng"}
          </h3>
          <ul className="mt-2 flex flex-col gap-2">
            {checklist.map((c) => {
              const dat = c.hienCo >= c.nguong;
              return (
                <li key={c.can} className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <Badge tone={dat ? "good" : "warn"}>{dat ? "ĐẠT" : "THIẾU"}</Badge>
                  <span className="text-body text-ink">{c.can}</span>
                  <span className="tnum text-body text-sec">
                    hiện có {c.hienCo}
                    {dat ? "" : ` — còn thiếu ${c.nguong - c.hienCo}`}
                  </span>
                </li>
              );
            })}
            <li className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <Badge tone="neutral">GHI NHẬN</Badge>
              <span className="text-body text-sec">
                {v.nBlocks} khối ({v.nOn} BẬT / {v.nOff} TẮT) đã đo và được giữ nguyên — không
                con số nào bị bịa thêm cho đủ.
              </span>
            </li>
          </ul>
        </div>
        <p className="mt-3 text-body leading-relaxed text-sec">
          {v.khoa
            ? "Khóa tồn tại để không ai — kể cả đội phát triển — nhìn trộm hiệu ứng trước ngày đã đăng ký; tới ngày mở, ước lượng chạy một lần trên toàn bộ dữ liệu tích lũy."
            : "Không hạ ngưỡng, không nội suy: thiếu thì nói thiếu bằng số. Chạy thêm phiên có bốc thăm là cách duy nhất để ô này đổi trạng thái."}
        </p>
        <div className="mt-4">
          <Link href="/chay-phien" className={buttonCls("primary")}>
            Chuẩn bị phiên live có bốc thăm
          </Link>
        </div>
      </div>
    </Card>
  );
}

/** Phiên QUAN SÁT (xem qua ?phien=): không có lịch gán — không verdict nhân quả. */
function VerdictQuanSat({ isDemo }: { isDemo: boolean }) {
  return (
    <Card padding="lg" className="motion-reveal" data-verdict="quansat">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="neutral" dot>
          PHIÊN QUAN SÁT
        </Badge>
        {isDemo ? <Badge tone="warn">DEMO — dữ liệu mẫu</Badge> : null}
      </div>
      <h2 className="mt-3 font-display text-title font-bold tracking-tight text-ink">
        Không có số nhân quả cho phiên này — theo đúng thiết kế
      </h2>
      <p className="mt-2 max-w-3xl text-body leading-relaxed text-sec">
        Buổi phát gốc không có lịch bốc thăm BẬT/TẮT nên không tồn tại phép so sánh nào để ước
        lượng tác động; mọi con số trong báo cáo của phiên là mô tả. Muốn đo tác động thật, hãy
        chạy phiên có lịch gán qua trang{" "}
        <Link href="/chay-phien" className="focus-ring rounded underline underline-offset-2">
          Chuẩn bị phiên live
        </Link>
        .
      </p>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Khung xương chờ tải
// ---------------------------------------------------------------------------

function ResultSkeleton() {
  return (
    <div aria-busy>
      <Card padding="lg">
        <Skeleton className="h-5 w-56 rounded-full" />
        <Skeleton className="mt-3 h-7 w-80 max-w-full" />
        <Skeleton className="mt-3 h-14 w-64" />
        <Skeleton className="mt-4 h-9 w-full" />
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
      </Card>
      <Skeleton className="mt-3 h-28 w-full" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Danh sách báo cáo từng phiên — nhóm THẬT / DEMO theo cờ is_demo
// ---------------------------------------------------------------------------

function SessionRows({ rows }: { rows: SessionSummary[] }) {
  return (
    <Card padding="none" className="divide-y divide-white/10">
      {rows.map((s) => (
        <div key={s.session_id} className="flex flex-wrap items-center gap-x-3 gap-y-1 p-3">
          <span className="min-w-0 flex-1 truncate text-body text-ink">
            {s.title ?? s.session_id}
          </span>
          {s.is_demo ? <Badge tone="warn">DEMO</Badge> : null}
          <span className="shrink-0 text-meta text-dim">
            {s.platform}
            {s.start_ts ? ` · ${fmtDateHCM(s.start_ts)}` : ""}
          </span>
          <Link
            href={`/ket-qua?phien=${s.session_id}`}
            className={buttonCls("ghost", "sm")}
          >
            Kết quả
          </Link>
          <Link href={`/bao-cao/${s.session_id}`} className={buttonCls("ghost", "sm")}>
            Báo cáo phiên
          </Link>
        </div>
      ))}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Trang
// ---------------------------------------------------------------------------

export default function KetQuaPage() {
  /**
   * Đọc query bằng window.location (tiền lệ /desk, /bat-dau) để trang không
   * phải bọc Suspense của useSearchParams — nhưng đọc SAU khi gắn (effect),
   * vì trang được prerender không có query: khởi tạo state từ window ngay
   * trong render đầu sẽ lệch với HTML tĩnh và gây lỗi hydration.
   */
  const [phien, setPhien] = useState<string | null>(null);
  const [env, setEnv] = useState<"real" | "demo">("real");
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    setPhien(q.get("phien"));
    if (q.get("env") === "demo") setEnv("demo");
    setReady(true);
  }, []);

  const [data, setData] = useState<ExperimentSummary | null>(null);
  const [baoCao, setBaoCao] = useState<BaoCao | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  /** Phiên đã kết thúc — nhóm THẬT/DEMO cho danh sách báo cáo cuối trang. */
  const [endedSessions, setEndedSessions] = useState<SessionSummary[]>([]);
  /**
   * RỖNG khác LỖI (gói B-PROBE, sự cố 13/09/2026). Trước đây `listSessions`
   * hỏng thì danh sách bị đặt về `[]` và cả hai mục "Phiên thật"/"Phiên demo"
   * biến mất không một lời — người đọc hiểu thành "chưa có phiên nào", trong
   * khi sự thật là KHÔNG ĐỌC ĐƯỢC. Cờ này bắt trang phải nói ra.
   */
  const [sessionsErr, setSessionsErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      if (phien) {
        setBaoCao(await getBaoCao(phien));
      } else {
        setData(await getExperimentSummary(env));
      }
    } catch {
      setErr(
        phien
          ? "Không đọc được kết quả của phiên — kiểm tra máy chủ đã chạy chưa và mã phiên có đúng không."
          : "Không đọc được kết quả — kiểm tra máy chủ đã chạy chưa (docker compose up -d).",
      );
    } finally {
      setLoading(false);
    }
    // Danh sách báo cáo phiên là phần phụ: hỏng thì chỉ vắng mục đó,
    // không kéo đổ phần kết quả phía trên.
    if (!phien) {
      try {
        const sessions = await listSessions();
        setEndedSessions(sessions.filter((s) => s.status === "ended").reverse());
        setSessionsErr(null);
      } catch {
        setEndedSessions([]);
        setSessionsErr(
          "Không đọc được danh sách phiên — đây là LỖI TẢI DỮ LIỆU, không phải " +
            "“chưa có phiên nào”. Các phiên đã kết thúc (nếu có) vẫn còn nguyên trên máy chủ.",
        );
      }
    }
  }, [phien, env]);

  useEffect(() => {
    if (ready) void load();
  }, [ready, load]);

  const verdict: VerdictData | null = phien
    ? baoCao?.ket_qua_thi_nghiem
      ? verdictFromKetQua(baoCao.ket_qua_thi_nghiem, baoCao.is_demo)
      : null
    : data
      ? verdictFromSummary(data)
      : null;

  const tomTat = (phien ? baoCao?.tom_tat_3_cau : data?.tom_tat_3_cau) ?? [];
  const isDemoView = phien ? (baoCao?.is_demo ?? false) : env === "demo";
  const powerTable = data?.power_table ?? [];
  const realSessions = endedSessions.filter((s) => !s.is_demo);
  const demoSessions = endedSessions.filter((s) => s.is_demo);

  return (
    <div className="flex min-h-screen flex-col bg-page">
      <TopNav />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        <PageHeader
          phase="sau"
          title={
            <span className="flex flex-wrap items-center gap-2">
              Kết quả &amp; chiến lược
              {isDemoView && !loading ? (
                <Badge tone="warn">{phien ? "PHIÊN DEMO" : "BẢN GỘP DEMO — MÔ PHỎNG"}</Badge>
              ) : null}
            </span>
          }
          lead={
            <>
              Trả lời một câu:{" "}
              <strong className="text-ink">
                bật hệ thống lên, buổi live của bạn có thêm lượt nhấp sản phẩm không?
              </strong>
            </>
          }
        >
          {phien ? (
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="text-body text-sec">
                Đang xem kết quả của một phiên:{" "}
                <strong className="text-ink">{baoCao?.tieu_de ?? phien}</strong>
              </span>
              <Link href="/ket-qua" className={buttonCls("ghost", "sm")}>
                ← Kết quả gộp mọi phiên
              </Link>
              <Link href={`/bao-cao/${phien}`} className={buttonCls("ghost", "sm")}>
                Báo cáo đầy đủ phiên này
              </Link>
            </div>
          ) : (
            <p className="mt-2 max-w-3xl text-meta leading-relaxed text-sec">
              Cách đo: so sánh các khối <strong className="text-ink">BẬT</strong> (hệ thống
              điều khiển việc ghim sản phẩm) với các khối{" "}
              <strong className="text-ink">TẮT</strong> (đội vận hành làm như thường lệ). Vì
              mỗi khối được bốc thăm ngẫu nhiên từ trước, chênh lệch giữa hai nhánh là{" "}
              <strong className="text-ink">tác động thật</strong> của hệ thống, không phải
              trùng hợp thời điểm.
            </p>
          )}
          {!phien && env === "demo" && !loading ? (
            <p className="mt-2 max-w-3xl text-meta leading-relaxed text-warn-ink">
              {data?.label ?? "Bản gộp CHỈ dữ liệu mẫu — không phải kết quả thật."}{" "}
              <Link href="/ket-qua" className="focus-ring rounded underline underline-offset-2">
                Xem kết quả thật
              </Link>
            </p>
          ) : null}
        </PageHeader>

        {loading ? <ResultSkeleton /> : null}

        {err ? (
          <Callout tone="critical">
            {err}{" "}
            <button
              onClick={() => void load()}
              className="focus-ring rounded underline underline-offset-2 transition-colors duration-short2 ease-emphasized hover:text-ink"
            >
              Thử lại
            </button>
          </Callout>
        ) : null}

        {/* ── KHU VERDICT: một trong ba trạng thái, không trạng thái nào lép ── */}
        {!loading && !err && phien && baoCao && baoCao.loai_phien === "quan_sat" ? (
          <VerdictQuanSat isDemo={baoCao.is_demo} />
        ) : null}
        {!loading && !err && verdict ? (
          verdict.state === "duong" || verdict.state === "am" ? (
            <VerdictCoTacDong v={verdict} />
          ) : verdict.state === "null" ? (
            <VerdictNull v={verdict} powerTable={powerTable} />
          ) : (
            <VerdictChuaDu v={verdict} />
          )
        ) : null}

        {/* ── Tóm tắt 3 câu — máy soạn câu tất định phía server ── */}
        {!loading && tomTat.length > 0 ? (
          <TomTat3Cau cau={tomTat} demo={isDemoView} className="mt-3" />
        ) : null}

        {/* ── Chi tiết thống kê (MDE, CV, tuân thủ) — như cũ, sau verdict ── */}
        {!phien && data && powerTable.length > 0 ? (
          <details className="group mt-6">
            <summary className="focus-ring cursor-pointer list-none rounded-lg border border-hairline bg-surface px-4 py-3 text-body text-ink transition-colors duration-short4 ease-emphasized hover:border-white/20">
              <span className="font-display text-strong">
                Chi tiết thống kê cho giám khảo
              </span>{" "}
              <span className="text-meta text-dim">
                (bảng MDE, CV đo được, tỷ lệ tuân thủ) — bấm để mở
              </span>
            </summary>
            <div className="mt-3">
              <p className="max-w-3xl text-body leading-relaxed text-sec">
                <strong className="text-ink">MDE</strong> (hiệu ứng nhỏ nhất phát hiện được) là
                ngưỡng độ lớn tối thiểu mà thí nghiệm còn nhìn thấy được. MDE 30% nghĩa là: nếu
                hệ thống chỉ cải thiện 10%, cỡ mẫu hiện tại{" "}
                <strong className="text-ink">không đủ để chứng minh</strong> — không phải hệ
                thống vô dụng, mà là chưa đo nổi. Càng nhiều phiên, MDE càng nhỏ.
              </p>
              <div className="mt-2 overflow-x-auto rounded-lg border border-hairline">
                <table className="w-full min-w-[560px] text-body">
                  <thead className="bg-raised text-label uppercase text-dim">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium">Kịch bản</th>
                      <th className="px-3 py-2 text-right font-medium">Phiên</th>
                      <th className="px-3 py-2 text-right font-medium">Khối</th>
                      <th className="px-3 py-2 text-right font-medium">CV</th>
                      <th className="px-3 py-2 text-right font-medium">MDE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {powerTable.map((r) => (
                      <tr
                        key={r.scenario}
                        className="border-t border-hairline transition-colors duration-short2 ease-emphasized hover:bg-raised/60"
                      >
                        <td className="px-3 py-2 text-ink">{r.scenario}</td>
                        <td className="tnum px-3 py-2 text-right text-sec">{r.n_sessions}</td>
                        <td className="tnum px-3 py-2 text-right text-sec">
                          {r.n_blocks_total}
                        </td>
                        <td className="tnum px-3 py-2 text-right text-sec">{r.cv.toFixed(2)}</td>
                        <td className="tnum px-3 py-2 text-right font-semibold text-ink">
                          {fmtPct(r.mde_relative)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <StatTile
                  label="Hệ số biến thiên đo được (CV)"
                  value={data.measured_cv?.toFixed(3) ?? "—"}
                  hint="Mức dao động của kết quả giữa các khối. CV càng cao thì càng cần nhiều dữ liệu — bảng MDE ở trên tính bằng chính con số đo được này, không phải giả định."
                />
                <StatTile
                  label="Tỷ lệ tuân thủ"
                  value={
                    data.measured_compliance != null ? fmtPct(data.measured_compliance) : "—"
                  }
                  hint="Tỷ lệ khối BẬT mà hệ thống thực sự được thực thi. Tuân thủ thấp làm loãng ước lượng: con số báo cáo là ITT (theo nhóm được gán), luôn thận trọng."
                />
              </div>
              <p className="mt-3 text-meta leading-relaxed text-dim">
                Biến kết quả chính là tỷ lệ nhấp sản phẩm — chỉ báo sớm có tần suất đủ cao để
                học nhanh. Các chỉ số kinh doanh (đơn, GMV, biên lợi nhuận) được theo dõi song
                song và báo cáo riêng như kết quả khám phá; không đánh đồng hai loại.
              </p>
            </div>
          </details>
        ) : null}

        {/* ── Báo cáo từng phiên — nhóm THẬT / DEMO theo cờ is_demo ──
            Danh sách vắng vì LỖI thì phải nói là lỗi: một khu vực trống lặng
            lẽ đọc y hệt "không có gì cả", và đó là một câu trả lời sai. */}
        {!phien && sessionsErr ? (
          <Callout tone="warn" className="mt-8">
            {sessionsErr}{" "}
            <button
              onClick={() => void load()}
              className="focus-ring rounded underline underline-offset-2 transition-colors duration-short2 ease-emphasized hover:text-ink"
            >
              Thử lại
            </button>
          </Callout>
        ) : null}
        {!phien && realSessions.length > 0 ? (
          <section className="mt-8">
            <SectionTitle meta={`${realSessions.length} phiên`}>Phiên thật</SectionTitle>
            <SessionRows rows={realSessions.slice(0, 10)} />
          </section>
        ) : null}
        {!phien && demoSessions.length > 0 ? (
          <section className="mt-6">
            <SectionTitle meta={`${demoSessions.length} phiên · dữ liệu mẫu, không bao giờ vào kết quả thật`}>
              Phiên demo
            </SectionTitle>
            <SessionRows rows={demoSessions.slice(0, 10)} />
          </section>
        ) : null}
      </main>
    </div>
  );
}
