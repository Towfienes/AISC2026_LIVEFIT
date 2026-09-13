"use client";

/**
 * ModeChip — chip chế độ dữ liệu ở góc phải nav (spec UX-FLOW b / UI-VISUAL f).
 *
 * Người dùng LUÔN biết mình đang ở thế giới dữ liệu nào: DEMO (vàng — dữ liệu
 * mô phỏng và buổi live đã nạp sẵn, bấm thoải mái) hay PHIÊN THẬT (chấm đỏ).
 *
 * Nguồn trạng thái: `GET /health` qua `probeServer()` (gói B-PROBE) — hỏi MỘT
 * lần khi gắn, 4 giây, thử lại một lần. Khi máy chủ chưa trả trường `mode`
 * (bản API cũ) hoặc không gọi được, chip rơi về nhãn DEMO: nhãn an toàn duy
 * nhất, vì theo nguyên tắc không-bịa của repo thì không bao giờ được tự nhận
 * dữ liệu là "THẬT" khi chưa có nguồn xác nhận. `mode_note` của máy chủ được
 * hiển thị nguyên văn trong tooltip.
 *
 * SỰ CỐ 13/09/2026 — vì sao chip có thêm phần thứ hai: khi PostgreSQL chết,
 * `/health` vẫn khoe `storage_mode=postgres, durable=true` và chip vẫn thản
 * nhiên in "PHIÊN THẬT". Người vận hành nhìn thanh nav thấy mọi thứ bình
 * thường trong khi hệ thống không lưu được gì. Từ nay chip KHÔNG ĐƯỢC im lặng
 * khoe DEMO/THẬT khi kho suy giảm: nó phải đeo thêm một chấm cam nói thẳng.
 *
 * TĨNH tuyệt đối (nằm trong TopNav trên đường render /desk): không animation.
 */

import { useEffect, useState } from "react";

import { probeServer } from "@/lib/api";
import type { ServerStatus } from "@/lib/api";

type Mode = "demo" | "real" | "mixed";

const FALLBACK_NOTE =
  "Chế độ DEMO — dữ liệu mô phỏng và buổi live đã nạp sẵn; bấm thoải mái, không ảnh hưởng dữ liệu thật";

const DEGRADED_NOTE =
  "Kho dữ liệu đang suy giảm: máy chủ vẫn trả lời nhưng dữ liệu mới có thể không lưu lại được. " +
  "Đừng lên sóng thật cho tới khi kho trở lại bình thường.";

const DOWN_NOTE =
  "Không gọi được máy chủ (đã thử lại). Nhãn chế độ bên cạnh là nhãn AN TOÀN mặc định, " +
  "không phải trạng thái đã xác nhận.";

export default function ModeChip() {
  const [mode, setMode] = useState<Mode>("demo");
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
      if (h && (h.mode === "real" || h.mode === "mixed" || h.mode === "demo")) {
        setMode(h.mode);
        if (typeof h.mode_note === "string" && h.mode_note) setNote(h.mode_note);
      }
      // API cũ không có trường mode, hoặc API tắt → giữ nhãn DEMO an toàn.
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const modeChip =
    mode === "real" ? (
      <span
        title={note}
        className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-live/40 bg-live/10 px-2.5 py-0.5 text-meta font-bold tracking-wide text-crit-ink"
      >
        <span aria-hidden className="inline-block h-2 w-2 rounded-full bg-live" />
        PHIÊN THẬT
      </span>
    ) : mode === "mixed" ? (
      // Kho đang chứa CẢ dữ liệu mẫu lẫn phiên thật — nói thẳng, không giấu.
      <span
        title={note}
        className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-warn/60 bg-warn/10 px-2.5 py-0.5 text-meta font-bold tracking-wide text-warn-ink"
      >
        THẬT + DEMO
      </span>
    ) : (
      <span
        title={note}
        className="inline-flex shrink-0 items-center rounded-full bg-warn px-2.5 py-0.5 text-meta font-bold tracking-wide text-[#0c0d12]"
      >
        DEMO
      </span>
    );

  return (
    <span className="flex shrink-0 items-center gap-1.5">
      {modeChip}
      {/* Chấm cam: kho suy giảm. Chip chế độ vẫn đứng đó, nhưng không còn được
          phép là thứ DUY NHẤT người vận hành thấy. */}
      {server === "degraded" && (
        <span
          title={warning ?? DEGRADED_NOTE}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-warn/60 bg-warn/10 px-2.5 py-0.5 text-meta font-bold tracking-wide text-warn-ink"
        >
          <span aria-hidden className="inline-block h-2 w-2 rounded-full bg-warn" />
          KHO SUY GIẢM
        </span>
      )}
      {/* Máy chủ không trả lời: nhãn chế độ bên cạnh chỉ là mặc định an toàn,
          phải nói ra để không ai đọc nó như một xác nhận. */}
      {server === "down" && (
        <span
          title={DOWN_NOTE}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-critical/50 bg-critical/10 px-2.5 py-0.5 text-meta font-bold tracking-wide text-crit-ink"
        >
          <span aria-hidden className="inline-block h-2 w-2 rounded-full bg-critical" />
          MẤT KẾT NỐI
        </span>
      )}
    </span>
  );
}
