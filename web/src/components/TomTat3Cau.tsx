/**
 * TomTat3Cau — "tóm tắt 3 câu" từ máy soạn câu TẤT ĐỊNH phía server
 * (analysis/narrate.py, AI-LAYER lớp 0 — gói KẾT-QUẢ).
 *
 * Ba câu: kết luận đúng trạng thái → bằng chứng chính → việc nên làm. Client
 * chỉ HIỂN THỊ nguyên văn: không viết lại câu, không chế thêm số — mọi con số
 * đã được server chép từ chính payload, và `refs` (đường dẫn JSON của từng
 * số) được đưa vào tooltip để ai cũng truy được nguồn ngay trên văn xuôi.
 *
 * Huy hiệu bằng chứng theo spec AI-LAYER N2: THÍ NGHIỆM (xanh — số từ
 * analyze_outer, có KTC) · QUAN SÁT (xám — số đếm mô tả) · THIẾU DỮ LIỆU
 * (vàng — tuyên bố thiếu kèm con số cần thêm). Server là nơi duy nhất quyết
 * định huy hiệu; client vẽ đúng màu, không suy diễn lại.
 */

import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";
import type { CauBadge, CauTomTat } from "@/lib/types";

const BADGE_META: Record<CauBadge, { tone: "good" | "neutral" | "warn"; label: string; hint: string }> =
  {
    thi_nghiem: {
      tone: "good",
      label: "THÍ NGHIỆM",
      hint: "Số trong câu đến từ ước lượng nhân quả tiền đăng ký (có khoảng tin cậy).",
    },
    quan_sat: {
      tone: "neutral",
      label: "QUAN SÁT",
      hint: "Số đếm mô tả — chưa kiểm chứng nhân quả.",
    },
    thieu_du_lieu: {
      tone: "warn",
      label: "THIẾU DỮ LIỆU",
      hint: "Tuyên bố thiếu kèm con số cần thêm — không hạ ngưỡng, không nội suy.",
    },
  };

interface Props {
  cau: CauTomTat[];
  /** Câu sinh từ dữ liệu mẫu — đeo chip DEMO ngay trên khối. */
  demo?: boolean;
  className?: string;
}

export default function TomTat3Cau({ cau, demo = false, className }: Props) {
  if (!cau || cau.length === 0) return null;
  return (
    <Card padding="lg" className={className}>
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="font-display text-strong text-ink">Tóm tắt 3 câu</h2>
        {demo ? <Badge tone="warn">DEMO — dữ liệu mẫu</Badge> : null}
        {/* Không lẫn thuật ngữ tiếng Anh ("template") trên giao diện người bán. */}
        <span className="text-meta text-dim">
          máy soạn theo mẫu câu cố định, không dùng AI viết chữ — rê chuột lên từng câu để xem
          nguồn của các con số
        </span>
      </div>
      <ol className="mt-3 flex flex-col gap-3">
        {cau.map((c, i) => {
          const meta = BADGE_META[c.badge] ?? BADGE_META.quan_sat;
          return (
            <li
              key={c.text}
              className="flex flex-wrap items-baseline gap-x-3 gap-y-1"
              title={`Nguồn số: ${c.refs.length ? c.refs.join(" · ") : "không có con số trong câu"}`}
            >
              <span aria-hidden className="tnum w-4 shrink-0 text-right text-meta text-dim">
                {i + 1}
              </span>
              <span title={meta.hint} className="shrink-0">
                <Badge tone={meta.tone}>{meta.label}</Badge>
              </span>
              <p className="min-w-0 flex-1 basis-64 text-body leading-relaxed text-ink">
                {c.text}
              </p>
            </li>
          );
        })}
      </ol>
    </Card>
  );
}
