"use client";

/**
 * ModeChip — chip "KHO ĐANG CHỨA GÌ" ở góc phải thanh điều hướng (spec
 * UX-FLOW b / UI-VISUAL f).
 *
 * Người dùng LUÔN biết dữ liệu mình đang nhìn thuộc thế giới nào: kho trống,
 * kho chỉ có dữ liệu mẫu, kho có dữ liệu thật, hay kho chứa cả hai.
 *
 * Nguồn trạng thái: `GET /health` qua `probeServer()` (gói B-PROBE) — hỏi MỘT
 * lần khi gắn, 4 giây, thử lại một lần. `mode` + `mode_counts` là mô tả DỮ
 * LIỆU phía máy chủ; `mode_note` được hiển thị nguyên văn trong tooltip.
 * Khi máy chủ chưa trả trường `mode` (bản API cũ) hoặc không gọi được, chip
 * giữ nhãn DỮ LIỆU MẪU: nhãn an toàn duy nhất (web rơi về dữ liệu mô phỏng khi
 * mất máy chủ), vì không bao giờ được tự nhận dữ liệu là "thật" khi chưa có
 * nguồn xác nhận.
 *
 * ĐÁNH GIÁ UI 17/09/2026 — vì sao bỏ chip "● PHIÊN THẬT" chấm đỏ: kho RỖNG
 * cũng được máy chủ gọi là `mode=real`, nên khi KHÔNG có phiên nào chip vẫn
 * in chữ đỏ kèm chấm đỏ — đúng màu và đúng hình của đèn ĐANG PHÁT. Người vận
 * hành đọc thành "đang live". Từ nay chip chế độ dùng tông TRUNG TÍNH, chữ
 * nói đúng kho đang chứa gì, và mỗi trạng thái mang một HÌNH riêng (không chỉ
 * màu): vòng rỗng = trống, vuông đặc = thật, thoi = mẫu, vuông nửa đặc = cả
 * hai. Không hình nào là chấm tròn đặc — hình đó thuộc về đèn ĐANG PHÁT.
 *
 * SỰ CỐ 13/09/2026 — vì sao chip có thêm phần thứ hai: khi PostgreSQL chết,
 * `/health` vẫn khoe kho bền và chip vẫn thản nhiên in nhãn chế độ. Từ nay
 * chip KHÔNG ĐƯỢC im lặng khi kho suy giảm: nó đeo thêm chip cam nói thẳng.
 *
 * TĨNH tuyệt đối (nằm trong TopNav trên đường render /desk): không animation.
 */

import { useEffect, useState } from "react";

import { probeServer } from "@/lib/api";
import type { ServerStatus } from "@/lib/api";

/** Kho đang chứa gì — suy từ `mode` + `mode_counts` của `/health`. */
type KhoState = "mau" | "that" | "trong" | "ca-hai" | "chua-ro";

type Glyph = "ring" | "square" | "diamond" | "half" | "triangle" | "cross" | "dash";

const FALLBACK_NOTE =
  "Dữ liệu mẫu — dữ liệu mô phỏng và buổi live đã nạp sẵn; bấm thoải mái, không ảnh hưởng dữ liệu thật";

const DEGRADED_NOTE =
  "Kho dữ liệu đang suy giảm: máy chủ vẫn trả lời nhưng dữ liệu mới có thể không lưu lại được. " +
  "Đừng lên sóng thật cho tới khi kho trở lại bình thường.";

const DOWN_NOTE =
  "Không gọi được máy chủ (đã thử lại). Nhãn kho bên cạnh là nhãn AN TOÀN mặc định, " +
  "không phải trạng thái đã xác nhận.";

/** Chữ + hình + tông của từng trạng thái kho. Không trạng thái nào dùng đỏ. */
const KHO_META: Record<KhoState, { text: string; glyph: Glyph; cls: string }> = {
  trong: {
    text: "KHO TRỐNG",
    glyph: "ring",
    cls: "border-strong bg-transparent text-sec",
  },
  that: {
    text: "KHO: DỮ LIỆU THẬT",
    glyph: "square",
    cls: "border-strong bg-raised text-ink",
  },
  mau: {
    text: "KHO: DỮ LIỆU MẪU",
    glyph: "diamond",
    cls: "border-warn/60 bg-warn/10 text-warn-ink",
  },
  "ca-hai": {
    text: "KHO: THẬT + MẪU",
    glyph: "half",
    cls: "border-warn/60 bg-warn/10 text-warn-ink",
  },
  "chua-ro": {
    text: "KHO: CHƯA ĐẾM ĐƯỢC",
    glyph: "dash",
    cls: "border-strong bg-transparent text-sec",
  },
};

/** Ký hiệu hình dạng 10px — kênh không-màu của chip (WCAG 1.4.1). */
function ChipGlyph({ glyph }: { glyph: Glyph }) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 10 10"
      className="h-2.5 w-2.5 shrink-0"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
    >
      {glyph === "ring" ? <circle cx="5" cy="5" r="3.6" /> : null}
      {glyph === "square" ? (
        <rect x="1.5" y="1.5" width="7" height="7" rx="1" fill="currentColor" />
      ) : null}
      {glyph === "diamond" ? <path d="M5 1l4 4-4 4-4-4z" fill="currentColor" /> : null}
      {glyph === "half" ? (
        <>
          <rect x="1.5" y="1.5" width="7" height="7" rx="1" />
          <path d="M1.5 8.5V1.5L8.5 1.5z" fill="currentColor" stroke="none" />
        </>
      ) : null}
      {glyph === "triangle" ? <path d="M5 1.2l4 7.3H1z" strokeLinejoin="round" /> : null}
      {glyph === "cross" ? <path d="M2 2l6 6M8 2l-6 6" strokeLinecap="round" /> : null}
      {glyph === "dash" ? <path d="M1.5 5h7" strokeLinecap="round" /> : null}
    </svg>
  );
}

/** `/health` → kho đang chứa gì. Trả null khi máy chủ không khai (API cũ). */
function khoTu(mode: unknown, counts: unknown): KhoState | null {
  if (mode === "demo") return "mau";
  if (mode === "mixed") return "ca-hai";
  if (mode === "unknown") return "chua-ro";
  if (mode === "real") {
    const c = counts as { demo?: unknown; real?: unknown } | null | undefined;
    // Máy chủ gọi kho RỖNG là "real" (deploy thật đang chờ dữ liệu) — nói
    // đúng là TRỐNG, không được in như thể đang có dữ liệu thật.
    if (c && c.real === 0 && c.demo === 0) return "trong";
    return "that";
  }
  return null;
}

export default function ModeChip() {
  const [kho, setKho] = useState<KhoState>("mau");
  const [note, setNote] = useState<string>(FALLBACK_NOTE);
  /** "checking" = chưa biết; chưa biết thì chưa cảnh báo gì. */
  const [server, setServer] = useState<ServerStatus | "checking">("checking");
  const [warning, setWarning] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void probeServer().then((p) => {
      if (cancelled) return;
      setServer(p.status);
      setWarning(p.warning);
      const h = p.health;
      const k = h ? khoTu(h.mode, h.mode_counts) : null;
      if (h && k) {
        setKho(k);
        if (typeof h.mode_note === "string" && h.mode_note) setNote(h.mode_note);
      }
      // API cũ không có trường mode, hoặc API tắt → giữ nhãn DỮ LIỆU MẪU an toàn.
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const meta = KHO_META[kho];

  return (
    <span className="flex flex-wrap items-center justify-end gap-1.5">
      <span
        title={note}
        className={`inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-meta font-bold tracking-wide ${meta.cls}`}
      >
        <ChipGlyph glyph={meta.glyph} />
        {meta.text}
      </span>
      {/* Kho suy giảm. Chip kho vẫn đứng đó, nhưng không còn được phép là thứ
          DUY NHẤT người vận hành thấy. Hình tam giác cảnh báo, không phải chấm. */}
      {server === "degraded" && (
        <span
          title={warning ?? DEGRADED_NOTE}
          className="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border border-warn/60 bg-warn/10 px-2.5 py-0.5 text-meta font-bold tracking-wide text-warn-ink"
        >
          <ChipGlyph glyph="triangle" />
          KHO SUY GIẢM
        </span>
      )}
      {/* Máy chủ không trả lời: nhãn kho bên cạnh chỉ là mặc định an toàn, phải
          nói ra để không ai đọc nó như một xác nhận. Hình chữ X, không phải
          chấm đỏ — chấm đỏ là đèn ĐANG PHÁT. */}
      {server === "down" && (
        <span
          title={DOWN_NOTE}
          className="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border border-critical/50 bg-critical/10 px-2.5 py-0.5 text-meta font-bold tracking-wide text-crit-ink"
        >
          <ChipGlyph glyph="cross" />
          MẤT KẾT NỐI
        </span>
      )}
    </span>
  );
}
