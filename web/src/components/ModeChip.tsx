"use client";

/**
 * ModeChip — chip chế độ dữ liệu ở góc phải nav (spec UX-FLOW b / UI-VISUAL f).
 *
 * Người dùng LUÔN biết mình đang ở thế giới dữ liệu nào: DEMO (vàng — dữ liệu
 * mô phỏng và buổi live đã nạp sẵn, bấm thoải mái) hay PHIÊN THẬT (chấm đỏ).
 *
 * Nguồn trạng thái: `GET /health` (gói DEMO-THẬT thêm mode/mode_counts/
 * mode_note) — hỏi MỘT lần khi gắn. Khi máy chủ chưa trả trường `mode` (bản
 * API cũ) hoặc không gọi được, chip rơi về nhãn DEMO: nhãn an toàn duy nhất,
 * vì theo nguyên tắc không-bịa của repo thì không bao giờ được tự nhận dữ
 * liệu là "THẬT" khi chưa có nguồn xác nhận. `mode_note` của máy chủ được
 * hiển thị nguyên văn trong tooltip.
 *
 * TĨNH tuyệt đối (nằm trong TopNav trên đường render /desk): không animation.
 */

import { useEffect, useState } from "react";

import { getHealth } from "@/lib/api";

type Mode = "demo" | "real" | "mixed";

const FALLBACK_NOTE =
  "Chế độ DEMO — dữ liệu mô phỏng và buổi live đã nạp sẵn; bấm thoải mái, không ảnh hưởng dữ liệu thật";

export default function ModeChip() {
  const [mode, setMode] = useState<Mode>("demo");
  const [note, setNote] = useState<string>(FALLBACK_NOTE);

  useEffect(() => {
    let cancelled = false;
    getHealth(2500)
      .then((h) => {
        if (cancelled) return;
        if (h.mode === "real" || h.mode === "mixed" || h.mode === "demo") {
          setMode(h.mode);
          if (typeof h.mode_note === "string" && h.mode_note) setNote(h.mode_note);
        }
        // API cũ không có trường mode → giữ nhãn DEMO an toàn.
      })
      .catch(() => {
        // API tắt → giữ nhãn DEMO an toàn.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (mode === "real") {
    return (
      <span
        title={note}
        className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-live/40 bg-live/10 px-2.5 py-0.5 text-meta font-bold tracking-wide text-crit-ink"
      >
        <span aria-hidden className="inline-block h-2 w-2 rounded-full bg-live" />
        PHIÊN THẬT
      </span>
    );
  }
  if (mode === "mixed") {
    // Kho đang chứa CẢ dữ liệu mẫu lẫn phiên thật — nói thẳng, không giấu.
    return (
      <span
        title={note}
        className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-warn/60 bg-warn/10 px-2.5 py-0.5 text-meta font-bold tracking-wide text-warn-ink"
      >
        THẬT + DEMO
      </span>
    );
  }
  return (
    <span
      title={note}
      className="inline-flex shrink-0 items-center rounded-full bg-warn px-2.5 py-0.5 text-meta font-bold tracking-wide text-[#0c0d12]"
    >
      DEMO
    </span>
  );
}
