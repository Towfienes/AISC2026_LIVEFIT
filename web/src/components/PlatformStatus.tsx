"use client";

/**
 * PlatformStatus — "máy chủ NÀY đang thu được bình luận từ nền tảng nào" cho
 * trang /bat-dau (đánh giá UI 17/09/2026).
 *
 * Ma trận của /bat-dau trả lời câu "loại buổi live này dùng được gì" từ tài
 * liệu. Nó không biết máy chủ người dùng đang mở có khoá YouTube hay chưa. Khối
 * này hỏi thẳng máy chủ (`GET /platforms`) và in MỖI NỀN TẢNG MỘT DÒNG:
 *
 *   tên · trạng thái (HÌNH + CHỮ) · loại đường · biến còn thiếu · ghi chú ngắn
 *
 * Luật trung thực:
 * - Trạng thái không bao giờ chỉ là màu: mỗi trạng thái một ký hiệu riêng
 *   (dấu tích / tam giác / vòng gạch chéo) kèm chữ.
 * - Máy chủ chỉ trả TÊN biến còn thiếu, không bao giờ trả giá trị khoá; khối
 *   này in đúng những tên đó, không đoán thêm.
 * - Không đọc được máy chủ thì nói KHÔNG ĐỌC ĐƯỢC — không vẽ năm dòng "thiếu
 *   khoá" giả, vì đó là một câu trả lời sai về máy chủ.
 */

import { useCallback, useEffect, useState } from "react";

import Badge, { type BadgeTone } from "@/components/ui/Badge";
import Callout from "@/components/ui/Callout";
import Card from "@/components/ui/Card";
import SectionTitle from "@/components/ui/SectionTitle";
import Skeleton from "@/components/ui/Skeleton";
import { getPlatforms } from "@/lib/api";
import type { PlatformReadiness } from "@/lib/types";

type TrangThai = "san-sang" | "thieu" | "khong-ho-tro";

const TRANG_THAI_META: Record<TrangThai, { ink: string; glyph: "tick" | "tri" | "slash" }> = {
  "san-sang": { ink: "text-good-ink", glyph: "tick" },
  thieu: { ink: "text-warn-ink", glyph: "tri" },
  "khong-ho-tro": { ink: "text-off-ink", glyph: "slash" },
};

/** Loại đường thu — đọc từ `mode` của máy chủ. */
const DUONG_META: Record<PlatformReadiness["mode"], { text: string; tone: BadgeTone }> = {
  chinh_thuc: { text: "Chính thức", tone: "good" },
  du_phong: { text: "Dự phòng", tone: "warn" },
  khong_ho_tro: { text: "Không có API", tone: "neutral" },
};

/** Mục `mo_phong` (máy chủ khai `mode: du_phong`) KHÔNG phải một đường thu bình
 *  luận khách thật: nó phát kịch bản bình luận tổng hợp. Nhãn "Dự phòng" sẽ
 *  khiến người đọc tưởng đó là cách thu dự phòng của một nền tảng — nên dòng
 *  này đeo nhãn riêng, nói thẳng dữ liệu tổng hợp, chỉ để kiểm thử. */
const NEN_TANG_MO_PHONG = "mo_phong";
const MO_PHONG_META: { text: string; tone: BadgeTone } = {
  text: "Dữ liệu tổng hợp — chỉ để kiểm thử",
  tone: "warn",
};

/** Máy chủ mới hơn web có thể thêm loại đường — không in dòng trắng nhãn. */
const DUONG_CHUA_RO: { text: string; tone: BadgeTone } = {
  text: "Loại đường chưa rõ",
  tone: "neutral",
};

/** Tên biến môi trường thật (VIẾT_HOA_GẠCH_DƯỚI) — khác với một công cụ chưa cài. */
const TEN_BIEN = /^[A-Z][A-Z0-9_]*$/;

function trangThaiCua(p: PlatformReadiness): TrangThai {
  if (p.mode === "khong_ho_tro") return "khong-ho-tro";
  return p.ready ? "san-sang" : "thieu";
}

function chuTrangThai(p: PlatformReadiness): string {
  const tt = trangThaiCua(p);
  if (tt === "san-sang") return "Sẵn sàng";
  if (tt === "khong-ho-tro") return "Không hỗ trợ";
  // Thiếu một CÔNG CỤ (vd yt-dlp chưa cài) không phải thiếu khoá — nói đúng.
  return p.missing.length > 0 && p.missing.every((m) => TEN_BIEN.test(m))
    ? "Thiếu khoá"
    : "Thiếu cài đặt";
}

function Glyph({ kind }: { kind: "tick" | "tri" | "slash" }) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 16 16"
      className="h-4 w-4 shrink-0"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {kind === "tick" ? (
        <>
          <circle cx="8" cy="8" r="6.5" />
          <path d="M5 8.2l2 2 4-4.4" />
        </>
      ) : null}
      {kind === "tri" ? (
        <>
          <path d="M8 1.8l6.4 11.4H1.6z" />
          <path d="M8 6.2v3.2M8 11.4v.1" />
        </>
      ) : null}
      {kind === "slash" ? (
        <>
          <circle cx="8" cy="8" r="6.5" />
          <path d="M3.4 12.6l9.2-9.2" />
        </>
      ) : null}
    </svg>
  );
}

function laLoiMang(e: unknown): boolean {
  if (e instanceof TypeError) return true;
  return typeof e === "object" && e !== null && (e as { name?: unknown }).name === "AbortError";
}

export default function PlatformStatus({ className }: { className?: string }) {
  const [rows, setRows] = useState<PlatformReadiness[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      setRows(await getPlatforms());
    } catch (e) {
      setRows(null);
      const msg = e instanceof Error ? e.message.trim() : "";
      setErr(
        laLoiMang(e)
          ? "Chưa hỏi được máy chủ LiveLift — trạng thái từng nền tảng đang THIẾU, không phải “không nền tảng nào dùng được”."
          : msg && !msg.startsWith("API ") && msg !== "Not Found"
            ? `Máy chủ không trả được trạng thái nền tảng: “${msg}”.`
            : "Máy chủ này chưa có mục trạng thái nền tảng (có thể là bản cũ) — trạng thái đang THIẾU.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section className={className}>
      <SectionTitle meta="hỏi trực tiếp máy chủ đang mở">
        Máy chủ này thu được bình luận từ đâu
      </SectionTitle>

      {loading && rows == null ? (
        <Card padding="none" aria-busy className="divide-y divide-white/10">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="p-3">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="mt-2 h-3 w-72 max-w-full" />
            </div>
          ))}
        </Card>
      ) : err ? (
        <Callout tone="warn">
          {err}{" "}
          <button
            type="button"
            onClick={() => void load()}
            className="focus-ring min-h-tap rounded underline underline-offset-2 transition-colors duration-short2 ease-emphasized hover:text-ink"
          >
            Thử lại
          </button>
        </Callout>
      ) : rows ? (
        <>
          <Card padding="none">
            <ul>
              {rows.map((p) => {
                const tt = trangThaiCua(p);
                const meta = TRANG_THAI_META[tt];
                const duong =
                  p.platform === NEN_TANG_MO_PHONG
                    ? MO_PHONG_META
                    : (DUONG_META[p.mode] ?? DUONG_CHUA_RO);
                return (
                  <li
                    key={p.platform}
                    data-trang-thai={tt}
                    className="flex flex-col gap-1.5 border-b border-hairline p-3 last:border-b-0 sm:p-4"
                  >
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
                      <span className="min-w-0 text-body font-semibold text-ink">{p.ten}</span>
                      <span
                        className={`inline-flex items-center gap-1.5 text-meta font-semibold ${meta.ink}`}
                      >
                        <Glyph kind={meta.glyph} />
                        {chuTrangThai(p)}
                      </span>
                      <Badge tone={duong.tone}>{duong.text}</Badge>
                    </div>
                    {p.missing.length > 0 ? (
                      <p className="flex flex-wrap items-center gap-1.5 text-meta text-sec">
                        <span>Còn thiếu:</span>
                        {p.missing.map((m) => (
                          <code
                            key={m}
                            className="rounded bg-raised px-1.5 py-0.5 font-num text-meta text-ink"
                          >
                            {m}
                          </code>
                        ))}
                      </p>
                    ) : null}
                    {p.note ? (
                      <p className="max-w-3xl text-meta leading-relaxed text-dim">{p.note}</p>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </Card>
          <p className="mt-2 text-meta leading-relaxed text-dim">
            Dòng nào “Thiếu khoá”: người quản trị máy chủ điền đúng tên biến ở trên vào tệp
            .env rồi khởi động lại máy chủ. Máy chủ chỉ báo TÊN biến còn thiếu, không bao giờ
            hiện giá trị khoá.
          </p>
        </>
      ) : null}
    </section>
  );
}
