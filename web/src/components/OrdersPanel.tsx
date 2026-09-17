"use client";

/**
 * OrdersPanel — đơn hàng của MỘT phiên trên trang báo cáo (/bao-cao/[id]).
 *
 * Vì sao có khối này (đánh giá UI 17/09/2026): máy chủ đã có đường ghi đơn
 * (`GET /sessions/{id}/orders`, `POST .../orders/import`) nhưng web không có
 * chỗ nào dùng — báo cáo luôn ghi "đơn hàng đối soát: THIẾU" và người bán không
 * có cách nào sửa điều đó ngoài gõ lệnh.
 *
 * Bốn luật của khối:
 * 1. ĐƠN LÀ CHỈ SỐ PHỤ. Chỉ số chính của thí nghiệm là lượt nhấp link đo — câu
 *    này đứng ngay dưới tiêu đề, không chìm trong chú thích.
 * 2. KHÔNG BỊA SỐ. Chưa nhập đơn nào thì doanh thu là THIẾU, không phải "0 ₫";
 *    không đọc được máy chủ thì nói không đọc được, không vẽ ô số rỗng.
 * 3. KHÔNG LỘ NHÁNH. Đơn được máy chủ gán vào khối theo thời điểm đặt, nhưng
 *    khối nào BẬT hay TẮT không phải việc của ô nhập đơn — khối này không đọc
 *    trường khối của đơn.
 * 4. KHÔNG GỬI TỆP. Chọn tệp chỉ để trình duyệt ĐỌC CHỮ trong tệp (FileReader)
 *    rồi đổ vào ô dán — thứ gửi đi luôn là nội dung CSV người dùng nhìn thấy,
 *    đúng hợp đồng `importOrdersCsv(sessionId, csv)`.
 */

import { useCallback, useEffect, useState } from "react";

import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import Callout from "@/components/ui/Callout";
import Card from "@/components/ui/Card";
import SectionTitle from "@/components/ui/SectionTitle";
import Skeleton from "@/components/ui/Skeleton";
import { fieldCls } from "@/components/ui/field";
import { getOrders, importOrdersCsv } from "@/lib/api";
import { fmtNumber, fmtVnd } from "@/lib/format";
import type { OrderImportResult, OrderSummary } from "@/lib/types";

/** Trần nội dung CSV phía máy chủ (routes/orders.py MAX_CSV_BYTES). */
const MAX_CSV_CHARS = 2_000_000;
/**
 * Máy chủ cắt danh sách lỗi còn 50 dòng đầu (routes/orders.py `loi[:50]`) và
 * trả tổng thật ở `tong_loi` (từ 17/09/2026). Máy chủ cũ không có trường đó:
 * khi đó nhận đủ 50 dòng thì chỉ biết "ít nhất 50" — in "50" như một con số
 * chính xác là bịa.
 */
const MAX_LOI_HIEN = 50;

function soLoi(result: OrderImportResult): { so: number; chiCanDuoi: boolean } {
  if (typeof result.tong_loi === "number") return { so: result.tong_loi, chiCanDuoi: false };
  return { so: result.loi.length, chiCanDuoi: result.loi.length >= MAX_LOI_HIEN };
}

/**
 * Tên cột máy chủ NHẬN ĐƯỢC — mỗi tên phải là một bí danh trong `_COT` của
 * routes/orders.py (kiểm thử đối chiếu từng tên). Phản biện gói E: gợi ý cũ in
 * đậm "thời gian đặt đơn", một tên máy chủ không nhận, nên người làm đúng
 * theo màn hình vẫn bị từ chối cả tệp. Chữ mô tả (`y`) KHÔNG phải tên cột.
 */
interface CotGoiY {
  /** Khoá cột phía máy chủ (`_COT`). */
  khoa: string;
  batBuoc: boolean;
  /** Tên cột viết đúng như máy chủ nhận. */
  ten: readonly string[];
  /** Mô tả cho người đọc — không phải tên cột. */
  y: string;
}

const COT_GOI_Y: readonly CotGoiY[] = [
  {
    khoa: "ts",
    batBuoc: true,
    ten: ["thời gian", "thời gian đặt hàng", "ts"],
    y: "lúc khách đặt đơn",
  },
  {
    khoa: "gross",
    batBuoc: true,
    ten: ["tổng tiền", "doanh thu", "gross"],
    y: "số tiền của đơn",
  },
  {
    khoa: "order_id",
    batBuoc: false,
    ten: ["mã đơn", "order_id"],
    y: "để nhập lại cùng tệp không bị tính trùng",
  },
];

const GHI_CHU_CHI_SO_PHU = "Đơn hàng là chỉ số phụ; chỉ số chính là lượt nhấp link đo.";

/** Lỗi mạng (không nối được / hết giờ) khác lỗi máy chủ trả lời. */
function laLoiMang(e: unknown): boolean {
  if (e instanceof TypeError) return true;
  return typeof e === "object" && e !== null && (e as { name?: unknown }).name === "AbortError";
}

/** Câu tiếng Việt của máy chủ nếu có; chuỗi kỹ thuật "API 4xx …" thì thay bằng câu dự phòng. */
function cauLoi(e: unknown, duPhong: string): string {
  if (laLoiMang(e)) return "Mất kết nối tới máy chủ — kiểm tra máy chủ LiveLift rồi thử lại.";
  const msg = e instanceof Error ? e.message.trim() : "";
  return msg && !msg.startsWith("API ") ? msg : duPhong;
}

interface Props {
  sessionId: string;
  /** Phiên dữ liệu mẫu — đeo nhãn DEMO trên khối số. */
  isDemo?: boolean;
  /** Gọi sau khi nhập xong để trang báo cáo đọc lại ma trận tín hiệu. */
  onImported?: () => void;
  className?: string;
}

export default function OrdersPanel({ sessionId, isDemo = false, onImported, className }: Props) {
  const [summary, setSummary] = useState<OrderSummary | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [csv, setCsv] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [importErr, setImportErr] = useState<string | null>(null);
  const [result, setResult] = useState<OrderImportResult | null>(null);

  const loadOrders = useCallback(async () => {
    setLoading(true);
    setLoadErr(null);
    try {
      setSummary(await getOrders(sessionId));
    } catch (e) {
      setSummary(null);
      setLoadErr(
        cauLoi(e, "Máy chủ không trả được danh sách đơn của phiên này.") +
          " Số đơn đang THIẾU — không phải bằng 0.",
      );
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void loadOrders();
  }, [loadOrders]);

  /** Đọc CHỮ trong tệp ngay trên trình duyệt rồi đổ vào ô dán — không tải tệp lên. */
  const onFile = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    // Xoá lựa chọn để chọn lại đúng tệp đó (sau khi sửa) vẫn kích hoạt onChange.
    e.target.value = "";
    if (!f) return;
    setImportErr(null);
    setResult(null);
    if (f.size > MAX_CSV_CHARS) {
      setImportErr(
        `Tệp "${f.name}" lớn hơn 2 MB — chia nhỏ tệp (tối đa 5.000 đơn mỗi lần) rồi nhập từng phần.`,
      );
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setCsv(typeof reader.result === "string" ? reader.result : "");
      setFileName(f.name);
    };
    reader.onerror = () => {
      setImportErr(
        `Không đọc được tệp "${f.name}" — mở tệp bằng Excel, lưu lại dạng CSV UTF-8 rồi chọn lại.`,
      );
    };
    reader.readAsText(f, "utf-8");
  }, []);

  const submit = useCallback(async () => {
    const noiDung = csv.trim();
    if (!noiDung) return;
    setImportErr(null);
    setResult(null);
    if (noiDung.length > MAX_CSV_CHARS) {
      setImportErr("Nội dung dài hơn 2 MB — chia nhỏ tệp rồi nhập từng phần.");
      return;
    }
    setBusy(true);
    try {
      setResult(await importOrdersCsv(sessionId, noiDung));
      await loadOrders();
      onImported?.();
    } catch (e) {
      setImportErr(cauLoi(e, "Máy chủ không nhận nội dung này — chưa có đơn nào được ghi."));
    } finally {
      setBusy(false);
    }
  }, [csv, sessionId, loadOrders, onImported]);

  const coDon = summary != null && summary.tong_don > 0;

  return (
    <section className={className}>
      <SectionTitle meta="chỉ số phụ">Đơn hàng của phiên</SectionTitle>
      <Card padding="lg">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-body leading-relaxed text-sec">
            {/* Câu trung thực bắt buộc — giữ liền một dòng để cổng kiểm thử tìm thấy. */}
            <strong className="text-ink">{GHI_CHU_CHI_SO_PHU}</strong>
          </p>
          {isDemo ? <Badge tone="warn">DEMO — dữ liệu mẫu</Badge> : null}
        </div>

        {/* ---- tổng đơn: có số, hoặc nói rõ vì sao chưa có số ---------------- */}
        {loading && summary == null ? (
          <div aria-busy className="mt-4 grid gap-3 sm:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-20" />
            ))}
          </div>
        ) : loadErr ? (
          <Callout tone="warn" className="mt-4">
            {loadErr}{" "}
            <button
              type="button"
              onClick={() => void loadOrders()}
              className="focus-ring min-h-tap rounded underline underline-offset-2 transition-colors duration-short2 ease-emphasized hover:text-ink"
            >
              Thử lại
            </button>
          </Callout>
        ) : coDon && summary ? (
          <dl className="mt-4 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-hairline bg-page/40 p-3">
              <dt className="text-label uppercase text-dim">Tổng đơn</dt>
              <dd className="mt-1 font-num text-num-s text-ink">{fmtNumber(summary.tong_don)}</dd>
            </div>
            <div className="rounded-lg border border-hairline bg-page/40 p-3">
              <dt className="text-label uppercase text-dim">Tổng sản phẩm</dt>
              <dd className="mt-1 font-num text-num-s text-ink">
                {fmtNumber(summary.tong_san_pham)}
              </dd>
            </div>
            <div className="rounded-lg border border-hairline bg-page/40 p-3">
              <dt className="text-label uppercase text-dim">Doanh thu</dt>
              <dd className="mt-1 font-num text-num-s text-ink">
                {fmtVnd(summary.tong_doanh_thu)}
              </dd>
            </div>
          </dl>
        ) : (
          <p className="mt-4 rounded-lg border border-dashed border-strong px-4 py-3 text-body leading-relaxed text-sec">
            <strong className="text-ink">Chưa nhập đơn nào cho phiên này.</strong> Doanh thu đang
            THIẾU — không phải bằng 0. Nhập tệp đơn xuất từ trang quản lý shop ở ngay dưới.
          </p>
        )}

        {/* ---- nhập CSV: dán nội dung HOẶC chọn tệp (chỉ đọc chữ, không gửi tệp) --- */}
        <div className="mt-5 border-t border-hairline pt-4 print:hidden">
          <h3 className="text-strong text-ink">Nhập đơn từ tệp CSV</h3>
          <p className="mt-1 text-meta leading-relaxed text-sec">
            Dòng đầu của tệp là tên cột. Mỗi cột dưới đây đặt tên đúng{" "}
            <strong className="text-ink">một</strong> trong các tên được liệt kê (không phân biệt
            hoa thường):
          </p>
          <ul className="mt-1.5 flex flex-col gap-1 text-meta leading-relaxed text-sec">
            {COT_GOI_Y.map((c) => (
              <li key={c.khoa} className="flex flex-wrap items-baseline gap-x-1.5 gap-y-0.5">
                <strong className={c.batBuoc ? "text-ink" : "text-sec"}>
                  {c.batBuoc ? "Bắt buộc:" : "Nên có:"}
                </strong>
                {c.ten.map((t, i) => (
                  <span key={t}>
                    {i > 0 ? <span className="mr-1.5">hoặc</span> : null}
                    <code className="rounded bg-raised px-1 font-num text-ink">{t}</code>
                  </span>
                ))}
                <span className="text-dim">— {c.y}</span>
              </li>
            ))}
          </ul>
          <p className="mt-1.5 text-meta leading-relaxed text-sec">
            Không cần cột tên, số điện thoại hay địa chỉ người mua — có cũng bị bỏ qua, không lưu.
          </p>

          <div className="mt-3 flex flex-col gap-2">
            <label htmlFor={`don-tep-${sessionId}`} className="text-meta font-semibold text-sec">
              Chọn tệp CSV trên máy
            </label>
            <input
              id={`don-tep-${sessionId}`}
              type="file"
              accept=".csv,text/csv,text/plain"
              onChange={onFile}
              disabled={busy}
              className="focus-ring block w-full min-w-0 rounded-md text-meta text-sec file:mr-3 file:min-h-ctl file:cursor-pointer file:rounded-md file:border file:border-solid file:border-white/10 file:bg-transparent file:px-3 file:text-meta file:font-semibold file:text-sec hover:file:bg-raised disabled:cursor-not-allowed"
            />
            {fileName ? (
              <p className="text-meta text-dim">
                Đã đọc tệp <span className="text-sec">{fileName}</span> vào ô bên dưới — kiểm tra
                rồi bấm Nhập đơn.
              </p>
            ) : null}

            <label
              htmlFor={`don-csv-${sessionId}`}
              className="mt-2 text-meta font-semibold text-sec"
            >
              Hoặc dán nội dung CSV
            </label>
            <textarea
              id={`don-csv-${sessionId}`}
              value={csv}
              onChange={(e) => {
                setCsv(e.target.value);
                setFileName(null);
              }}
              rows={6}
              spellCheck={false}
              disabled={busy}
              placeholder={"mã đơn,thời gian,tổng tiền\nDH001,17/09/2026 20:05,125000"}
              className={`${fieldCls} w-full px-3 py-2 font-num text-meta leading-relaxed`}
            />
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-3">
            <Button onClick={() => void submit()} disabled={busy || csv.trim() === ""}>
              {busy ? "Đang nhập…" : "Nhập đơn"}
            </Button>
            {csv ? (
              <Button
                variant="ghost"
                disabled={busy}
                onClick={() => {
                  setCsv("");
                  setFileName(null);
                  setResult(null);
                  setImportErr(null);
                }}
              >
                Xoá nội dung
              </Button>
            ) : null}
          </div>

          {importErr ? (
            <Callout tone="critical" className="mt-3">
              {importErr}
            </Callout>
          ) : null}

          {/* Kết quả nhập: mỗi loại một HÌNH + một CHỮ, không chỉ màu. */}
          {result ? (
            <div role="status" className="mt-3 rounded-lg border border-hairline bg-page/40 p-3">
              <ul className="flex flex-wrap gap-x-5 gap-y-1 text-body">
                <li className="flex items-center gap-1.5 text-ink">
                  <span aria-hidden className="font-bold text-good-ink">
                    ✓
                  </span>
                  Nhập mới <span className="tnum font-semibold">{fmtNumber(result.nhap_moi)}</span>{" "}
                  đơn
                </li>
                <li className="flex items-center gap-1.5 text-sec">
                  <span aria-hidden className="font-bold text-dim">
                    =
                  </span>
                  Trùng mã, bỏ qua{" "}
                  <span className="tnum font-semibold">{fmtNumber(result.trung_bo_qua)}</span> đơn
                </li>
                <li
                  className={`flex items-center gap-1.5 ${soLoi(result).so ? "text-warn-ink" : "text-sec"}`}
                >
                  <span aria-hidden className="font-bold">
                    ⚠
                  </span>
                  {/* Danh sách lỗi đã bị máy chủ cắt ở MAX_LOI_HIEN: đủ trần thì
                      chỉ biết cận dưới, không biết số thật. */}
                  {soLoi(result).chiCanDuoi ? "Lỗi ít nhất" : "Lỗi"}{" "}
                  <span className="tnum font-semibold">{fmtNumber(soLoi(result).so)}</span> dòng
                </li>
              </ul>
              {result.loi.length > 0 ? (
                <>
                  <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto border-t border-hairline pt-2 text-meta leading-snug text-sec">
                    {result.loi.map((l, i) => (
                      <li key={`${l.dong}-${i}`}>
                        <span className="tnum font-semibold text-ink">Dòng {l.dong}:</span>{" "}
                        {l.ly_do}
                      </li>
                    ))}
                  </ul>
                  {soLoi(result).so > result.loi.length || soLoi(result).chiCanDuoi ? (
                    <p className="mt-1 text-meta text-dim">
                      Máy chủ chỉ trả tối đa {MAX_LOI_HIEN} lỗi đầu tiên, nên có thể còn dòng lỗi
                      khác chưa được liệt kê — sửa các dòng này rồi nhập lại để kiểm tra tiếp.
                    </p>
                  ) : null}
                </>
              ) : null}
            </div>
          ) : null}
        </div>
      </Card>
    </section>
  );
}
