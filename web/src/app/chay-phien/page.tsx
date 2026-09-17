"use client";

/**
 * "/chay-phien" — wizard TỪNG-BƯỚC-MỘT chuẩn bị một buổi live thí nghiệm
 * (gói WIZARD, spec UX-FLOW e1 + critic sản phẩm ưu tiên #5).
 *
 * Vì sao đập stepper cũ: bản trước trải cả 4 thẻ + 10 ô nhập cùng lúc, bắt
 * người bán tự nghĩ "Mã SP", đọc placeholder không nhãn, hiểu chữ "seed", và
 * kết thúc bằng một lệnh terminal — người thật nhìn màn hình nói thẳng
 * "không hiểu làm gì". Bản này mỗi lần chỉ hỏi MỘT việc:
 *
 *   Bước 1  Sản phẩm sẽ bán   — tên + link thật + giá; mã hệ thống TỰ SINH.
 *   Bước 2  Thông tin buổi live — nền tảng/thời lượng/chế độ là thẻ bấm,
 *            cảnh báo TRƯỚC khi tạo nếu cấu hình yếu (dưới 90 phút).
 *   Bước 3  Bốc thăm lịch BẬT/TẮT — một nút to; MỘT câu tóm tắt lấy số từ
 *            lịch thật máy chủ trả về + lời khuyên hành động; mã bằng chứng,
 *            mã bốc thăm, lưu ý cân bằng và nút bốc lại nằm sau "Chi tiết kỹ
 *            thuật".
 *   Bước 4  Lên sóng — checklist trước giờ G (lịch, link đo, nguồn bình luận,
 *            màn hình người dẫn, dữ liệu sẽ ghi lại) rồi MỘT nút Bắt đầu phát
 *            sóng, cạnh nút đếm "còn N việc" (không chặn bấm), xong tự chuyển
 *            /desk?session=ID.
 *
 * Gói H (đánh giá UI 17/09, luồng B): đoạn dẫn chỉ ở bước 1; cảnh báo thiếu
 * link gộp về MỘT chỗ mỗi bước; bước 3 hết mâu thuẫn độ dài khối và hết tường
 * thuật ngữ; bước 4 có bộ thu bình luận ngay trong checklist (nguồn mô phỏng
 * chỉ mở cho phiên chạy thử / dữ liệu mẫu) và link màn người dẫn mang
 * ?session=; phiên không đặt tên được đặt tên mặc định đọc được.
 *
 * THỨ TỰ LÀ KHOA HỌC, không phải sở thích UI: lịch bốc thăm phải sinh và
 * niêm phong TRƯỚC giờ phát (API chặn bằng 409) — wizard làm điều đó thành
 * đường đi duy nhất thay vì một quy tắc phải học qua lỗi.
 *
 * Trạng thái sống sót qua refresh: lưu localStorage (ll.chayphien.v1) + URL
 * (?buoc=&phien=); mở lại một phiên đang planned/scheduled thì wizard đọc
 * trạng thái THẬT từ máy chủ và nhảy về đúng bước. Lỗi 400 của máy chủ (cấu
 * hình không khả thi) hiện NGUYÊN VĂN tiếng Việt kèm gợi ý của máy chủ —
 * không bao giờ hiện chuỗi lỗi kỹ thuật.
 *
 * KHÔNG còn lệnh terminal ở bất kỳ đâu trên trang này: chấm chất lượng dữ
 * liệu chạy phía máy chủ khi đọc báo cáo phiên — người bán chỉ bấm nút.
 */

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import BlockStrip from "@/components/BlockStrip";
import IngestPanel from "@/components/IngestPanel";
import PageHeader from "@/components/PageHeader";
import Term from "@/components/Term";
import TopNav from "@/components/TopNav";
import Button, { buttonCls } from "@/components/ui/Button";
import Callout from "@/components/ui/Callout";
import Card from "@/components/ui/Card";
import { cx } from "@/components/ui/cx";
import { fieldCls } from "@/components/ui/field";
import Skeleton from "@/components/ui/Skeleton";
import {
  cancelSession,
  createProduct,
  createSchedule,
  createSession,
  createShortlink,
  getIngestStatus,
  getSchedule,
  getSignalCoverage,
  getState,
  listProducts,
  listSessions,
  PUBLIC_API_BASE,
  startSession,
} from "@/lib/api";
import { CAU_MOT_DONG } from "@/lib/copy";
import { fmtVnd } from "@/lib/format";
import type {
  BlockInfo,
  IngestState,
  Product,
  SessionMode,
  SessionSummary,
  SignalCoverage,
  SignalStateItem,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Kiểu + hằng
// ---------------------------------------------------------------------------

type Step = 1 | 2 | 3 | 4;

/** Khoá localStorage — đổi tên là đổi phiên bản trạng thái (v1). */
const LS_KEY = "ll.chayphien.v1";

/** Tối đa 5 link đo mỗi phiên — đủ cho một buổi live, tránh spam shortlink. */
const MAX_LINKS = 5;

/**
 * Thời lượng khuyên dùng — cùng mốc với lưu ý cân bằng của máy chủ ("cân nhắc
 * phiên dài hơn (từ 90 phút)") và thẻ "khuyên dùng" ở bước 2.
 */
const PHUT_KHUYEN_DUNG = 90;

const STEP_META: { n: Step; label: string; time: string }[] = [
  { n: 1, label: "Sản phẩm", time: "chừng 2 phút" },
  { n: 2, label: "Buổi live", time: "chừng 1 phút" },
  { n: 3, label: "Bốc thăm", time: "chừng 30 giây" },
  { n: 4, label: "Lên sóng", time: "chừng 1 phút" },
];

interface WizardSchedule {
  blocks: BlockInfo[];
  nOn: number;
  nOff: number;
  /** null khi khôi phục từ máy chủ (GET lịch không trả seed). */
  seed: number | null;
}

/**
 * Một link đo của phiên. `target_url` là đích THẬT máy chủ lưu lúc tạo link —
 * máy chủ không có API sửa đích, nên đổi link trang sản phẩm sau đó KHÔNG đổi
 * nơi link đo dẫn tới. null = trạng thái lưu từ bản trang cũ chưa giữ đích
 * (không đoán: coi là không rõ và tạo lại khi vào bước 4).
 */
interface LinkDo {
  code: string;
  product_id: string;
  target_url: string | null;
}

/** Trạng thái wizard được lưu để refresh không mất (yêu cầu #3 của gói). */
interface SavedWizard {
  v: 1;
  step: Step;
  productUrls: Record<string, string>;
  form: { title: string; platform: string; minutes: string; mode: SessionMode };
  blockMin: string;
  sessionId: string | null;
  links: LinkDo[];
  daDanLink: boolean;
  /**
   * Mã phiên mà màn người dẫn đã được mở cho. Link màn người dẫn ghim cứng
   * ?session=<id> nên tab đã mở KHÔNG tự sang phiên mới — một cờ true/false
   * chung sẽ báo ✓ sai sau khi huỷ phiên nháp hoặc bắt đầu phiên khác.
   */
  daMoHostFor: string | null;
}

/** Tên nền tảng viết như người bán vẫn viết — không in mã "youtube" trần. */
const TEN_NEN_TANG: Record<string, string> = {
  youtube: "YouTube",
  facebook: "Facebook",
  shopee: "Shopee",
  tiktok: "TikTok",
};

/**
 * Mục "Dữ liệu hệ thống sẽ ghi lại" ở bước 4, bằng lời thường. Chỉ gồm các
 * nguồn KHÔNG có dòng checklist riêng: lịch (dòng Lịch), bình luận (dòng
 * Nguồn bình luận) và lượt bấm (dòng Link đo) đã được nói một lần ở dòng của
 * chúng — lặp lại ở đây chính là lỗi "một thiếu sót báo ba lần".
 */
const TIN_HIEU_THUONG: Record<string, { ten: string; thieu: string }> = {
  ticks: {
    ten: "Số người xem theo thời gian",
    thieu:
      "chưa có — số này chỉ có khi buổi live đã lên sóng và bộ thu đọc được số người xem",
  },
  orders: {
    ten: "Đơn hàng",
    thieu: "chưa ghi nhận đơn nào — chưa đối chiếu được doanh thu",
  },
  reactions: {
    ten: "Tim và quà tặng",
    thieu:
      "hệ thống chưa thu được loại dữ liệu này từ nền tảng — ô này sẽ hiện THIẾU, không hiện số 0",
  },
};

/** Nguồn đã có dòng checklist riêng — không liệt kê lại ở mục dữ liệu. */
const TIN_HIEU_CO_DONG_RIENG = ["schedule", "comments", "clicks"];

const inputCls = `${fieldCls} w-full px-2.5 py-1.5 text-body`;

// ---------------------------------------------------------------------------
// Helpers thuần (không JSX — tests/test_web_wizard_v3.py chạy thử chúng bằng node)
// ---------------------------------------------------------------------------

/**
 * Chỉ URL http(s) tuyệt đối mới dùng được: link đo /r/{code} chuyển hướng
 * trình duyệt NGƯỜI XEM tới đó — một đường dẫn tương đối hay thiếu scheme sẽ
 * làm hỏng đúng khoảnh khắc khách bấm giữa buổi live.
 */
function isValidProductUrl(value: string): boolean {
  try {
    const u = new URL(value);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

/**
 * Link MẪU để chạy thử: chỉ dùng tên miền example.com (dành riêng cho ví dụ,
 * RFC 2606) — không bao giờ bịa địa chỉ một cửa hàng có thật. Trang đánh dấu
 * rõ "link mẫu" ở mọi chỗ nó xuất hiện.
 */
function isSampleUrl(value: string): boolean {
  try {
    const host = new URL(value).hostname;
    return host === "example.com" || host.endsWith(".example.com");
  } catch {
    return false;
  }
}

function sampleUrlFor(productId: string): string {
  return `https://example.com/${productId}`;
}

function tenNenTang(platform: string): string {
  return TEN_NEN_TANG[platform] ?? platform;
}

/**
 * Tên mặc định khi người bán để trống ô tên (gói H5): "Live 17/09 07:38 ·
 * YouTube · 30 phút", giờ Việt Nam. Không có tên thì ô chọn phiên ở nơi khác
 * chỉ còn in UUID — người bán không nhận ra buổi nào là buổi nào.
 */
function tenPhienMacDinh(now: Date, platform: string, minutes: number): string {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Ho_Chi_Minh",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(now);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "00";
  return `Live ${get("day")}/${get("month")} ${get("hour")}:${get("minute")} · ${tenNenTang(platform)} · ${minutes} phút`;
}

/**
 * Phiên được phép chọn nguồn MÔ PHỎNG ở Bộ thu bình luận: chỉ phiên chạy thử
 * (`dry_run`) hoặc phiên dữ liệu mẫu (`is_demo`). Phiên thật mà nhận bình luận
 * mô phỏng là trộn dữ liệu giả vào kết quả thật — máy chủ chặn bằng 422, đây là
 * lớp thứ hai để khỏi mời bấm nhầm. Máy chủ trả `dry_run` trong SessionOut
 * nhưng SessionSummary chưa khai trường này, nên đọc có kiểm tra: thiếu cờ thì
 * coi là phiên THẬT (không mở mô phỏng).
 */
function choPhepMoPhong(s: SessionSummary & { dry_run?: boolean }): boolean {
  return s.dry_run === true || s.is_demo === true;
}

/**
 * Màn người dẫn tính là "đã mở" chỉ khi đã mở cho ĐÚNG phiên đang chuẩn bị
 * (link mang ?session=<id>, tab đó không bao giờ tự đổi phiên).
 */
function daMoDungPhien(daMoHostFor: string | null, sessionId: string | null | undefined): boolean {
  return sessionId != null && daMoHostFor === sessionId;
}

/**
 * Link đo phải tạo lại khi link trang sản phẩm hiện tại hợp lệ mà KHÁC đích
 * thật của link đo (hoặc đích không rõ). Link trang sản phẩm bị xoá hay chưa
 * hợp lệ thì giữ link cũ — không có đích mới nào để tạo.
 */
function canTaoLaiLink(link: LinkDo, urlHienTai: string): boolean {
  return isValidProductUrl(urlHienTai) && link.target_url !== urlHienTai;
}

/**
 * Việc cần làm với link đo khi vào bước 4: tạo lại link lệch đích (thay đúng
 * chỗ, không tăng số link) và tạo mới cho sản phẩm có link hợp lệ mà chưa có
 * link đo, trong trần `max`.
 */
function keHoachLinkDo(
  links: LinkDo[],
  urls: { product_id: string; url: string }[],
  max: number,
): { product_id: string; url: string; thay: boolean }[] {
  const cuaSp = (pid: string) => links.find((l) => l.product_id === pid);
  const thay = urls
    .filter((x) => {
      const l = cuaSp(x.product_id);
      return l != null && canTaoLaiLink(l, x.url);
    })
    .map((x) => ({ product_id: x.product_id, url: x.url, thay: true }));
  const moi = urls
    .filter((x) => cuaSp(x.product_id) == null && isValidProductUrl(x.url))
    .slice(0, Math.max(0, max - links.length))
    .map((x) => ({ product_id: x.product_id, url: x.url, thay: false }));
  return [...thay, ...moi];
}

/** Gộp link vừa tạo vào danh sách hiện có: cùng sản phẩm thì THAY, không nhân đôi. */
function ganLinkMoi(prev: LinkDo[], created: LinkDo[]): LinkDo[] {
  const next = [...prev];
  for (const c of created) {
    const i = next.findIndex((l) => l.product_id === c.product_id);
    if (i >= 0) next[i] = c;
    else next.push(c);
  }
  return next;
}

/**
 * Dòng "Nguồn bình luận" theo trạng thái THẬT của Bộ thu bình luận, không chỉ
 * cờ đang chạy: bộ thu dừng vì lỗi mà ghi "chưa bật" là trái với IngestPanel
 * ngay bên dưới và khiến người bán bấm bật lại mãi. Chỉ trạng thái "chua_bat"
 * mới được nói là chưa bật.
 */
function dongNguonBinhLuan(
  ingest: { state: string; running: boolean } | null,
): { state: RowState; title: string } {
  if (ingest == null) return { state: "todo", title: "Nguồn bình luận: đang hỏi máy chủ…" };
  switch (ingest.state) {
    case "chua_bat":
      return { state: "todo", title: "Nguồn bình luận: chưa bật Bộ thu bình luận" };
    case "dang_khoi_dong":
      return { state: "ok", title: "Nguồn bình luận: Bộ thu bình luận đang kết nối" };
    case "dang_thu":
      return { state: "ok", title: "Nguồn bình luận: Bộ thu bình luận đang chạy" };
    case "cho_len_song":
      return {
        state: "ok",
        title: "Nguồn bình luận: Bộ thu bình luận đã bật, chờ buổi live bắt đầu",
      };
    case "dang_thu_lai":
      return {
        state: "warn",
        title: "Nguồn bình luận: Bộ thu bình luận mất kết nối, đang tự thử lại",
      };
    case "loi":
      return {
        state: "warn",
        title: "Nguồn bình luận: Bộ thu bình luận dừng vì lỗi — xem lý do bên dưới",
      };
    case "da_dung":
      return {
        state: "todo",
        title: "Nguồn bình luận: Bộ thu bình luận đã tắt — bật lại bên dưới nếu cần",
      };
    case "nguon_ket_thuc":
      return {
        state: "warn",
        title: "Nguồn bình luận: buổi live ở link đã dán đã tắt nên Bộ thu bình luận dừng — kiểm tra lại link",
      };
    case "phien_ket_thuc":
      return {
        state: "info",
        title: "Nguồn bình luận: phiên đã kết thúc, Bộ thu bình luận tự dừng",
      };
    default:
      return ingest.running
        ? { state: "ok", title: "Nguồn bình luận: Bộ thu bình luận đang chạy" }
        : { state: "todo", title: "Nguồn bình luận: Bộ thu bình luận không chạy" };
  }
}

/** Tên do tenPhienMacDinh đặt — để "sửa lại phiên" không giữ giờ cũ trong ô tên. */
function laTenMacDinh(title: string): boolean {
  return /^Live \d{2}\/\d{2} \d{2}:\d{2} · .+ · \d+ phút$/.test(title);
}

/**
 * Mã bốc thăm chỉ được in khi trình duyệt giữ nó CHÍNH XÁC. Máy chủ bốc seed
 * 63 bit; số vượt 2^53 bị JSON.parse làm tròn (…918767123 thành …918767000) —
 * in số đã tròn kèm lời hứa "cùng số này sinh lại đúng lịch" là hứa sai.
 */
function seedHienThi(seed: number | null): string | null {
  return seed != null && Number.isSafeInteger(seed) ? String(seed) : null;
}

function trungVi(xs: number[]): number {
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/**
 * MỘT câu thường ngày tóm tắt lịch, lấy số từ CHÍNH các khối máy chủ trả về
 * (gói H3). Bản cũ in "~5 phút" (câu chuẩn), "phần lớn ~10 phút" (trung vị
 * lệch vì khối đầu/cuối dài gấp đôi) và "khối 2 phút" (lưu ý máy chủ) trong
 * cùng một thẻ. Thiết kế cố ý cho khối đầu và khối cuối dài hơn, nên câu nói
 * thẳng điều đó thay vì gộp thành một con số sai.
 */
function tomTatLich(blocks: BlockInfo[], durationMin: number): string {
  const meas = blocks.filter((b) => !b.is_washout);
  if (meas.length === 0) return "Lịch chưa có khối nào.";
  const nOn = meas.filter((b) => b.assignment === "ON").length;
  const nOff = meas.filter((b) => b.assignment === "OFF").length;
  const phut = meas.map((b) => (b.end_offset_s - b.start_offset_s) / 60);
  const giua = phut.length >= 3 ? phut.slice(1, -1) : phut;
  const thuong = trungVi(giua);
  const dau = phut[0];
  const cuoi = phut[phut.length - 1];
  const bienDai = phut.length >= 3 && dau >= 1.5 * thuong && cuoi >= 1.5 * thuong;
  const doDai = bienDai
    ? `khối đầu và khối cuối dài khoảng ${Math.max(1, Math.round((dau + cuoi) / 2))} phút, các khối còn lại khoảng ${Math.max(1, Math.round(thuong))} phút`
    : `mỗi khối khoảng ${Math.max(1, Math.round(thuong))} phút`;
  return `Buổi live ${durationMin} phút được chia thành ${meas.length} khối (${nOn} khối BẬT, ${nOff} khối TẮT), ${doDai}.`;
}

/**
 * Lý do máy chủ gửi kèm tín hiệu có lúc là ghi chú nội bộ của đội kỹ thuật
 * (tên bộ phân tích, tên bộ lọc, số mục tiền đăng ký). Nguồn THIẾU đã biết thì nói
 * bằng câu thường ở TIN_HIEU_THUONG; các trường hợp khác giữ lời máy chủ
 * nhưng bỏ phần ngoặc chứa thuật ngữ kỹ thuật — trạng thái THIẾU vẫn giữ.
 */
function lyDoThuong(s: SignalStateItem): string {
  const known = TIN_HIEU_THUONG[s.name];
  if (s.status === "missing" && known) return known.thieu;
  return s.detail
    .replace(
      /\s*\((?=[^)]*(parser|ingest|GIVT|PII|schema|telemetry|pipeline|§))[^)]*\)/gi,
      "",
    )
    .replace(/telemetry/gi, "dữ liệu đo")
    .trim();
}

/**
 * Mã sản phẩm TỰ SINH từ tên (spec e1: bỏ ô "Mã SP" — người bán không phải
 * nghĩ mã). "Áo khoác dù 2 lớp" → "ao-khoac-du-2-lop".
 */
function slugify(name: string): string {
  const s = name
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48)
    .replace(/-+$/g, "");
  return s || "san-pham";
}

/** Slug + hậu tố -2/-3… khi trùng với sản phẩm đã có. */
function uniqueSlug(name: string, existing: Product[]): string {
  const base = slugify(name);
  const taken = new Set(existing.map((p) => p.product_id));
  if (!taken.has(base)) return base;
  for (let i = 2; i < 100; i++) {
    if (!taken.has(`${base}-${i}`)) return `${base}-${i}`;
  }
  return `${base}-${Date.now() % 100000}`;
}

/**
 * Lỗi cho NGƯỜI THƯỜNG đọc (yêu cầu #4): thông báo tiếng Việt của máy chủ
 * (đã được api.ts lấy từ `detail`) hiện nguyên văn; chuỗi kỹ thuật hoặc lỗi
 * mạng được dịch thành một câu hành động được.
 */
function viError(e: unknown): string {
  const msg = e instanceof Error ? e.message : "";
  if (/^API \d/.test(msg)) {
    return "Máy chủ từ chối yêu cầu nhưng không nói rõ lý do — thử lại; nếu vẫn lỗi, báo người kỹ thuật của nhóm.";
  }
  if (!msg || /fetch|network|abort|load failed/i.test(msg)) {
    return "Không kết nối được máy chủ dữ liệu — kiểm tra máy chủ đã bật chưa rồi thử lại.";
  }
  return msg;
}

// ---------------------------------------------------------------------------
// Mảnh giao diện nhỏ
// ---------------------------------------------------------------------------

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
      <path
        d="M2.5 6.5 5 9l4.5-6"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Icon SVG stroke thống nhất — CẤM emoji làm icon (spec UI-VISUAL). */
function IconYouTube() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden className="shrink-0">
      <rect x="2" y="5" width="20" height="14" rx="4" stroke="currentColor" strokeWidth="1.8" />
      <path d="m10 9 5 3-5 3z" fill="currentColor" />
    </svg>
  );
}

function IconFacebook() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden className="shrink-0">
      <circle cx="12" cy="12" r="9.5" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M13.5 8.5h2v-2.4h-2a3.1 3.1 0 0 0-3.1 3.1v1.8H8.5v2.4h1.9v6h2.5v-6h2.1l.5-2.4h-2.6V9.6c0-.6.5-1.1 1.1-1.1Z"
        fill="currentColor"
      />
    </svg>
  );
}

/** Dòng "Vì sao cần bước này?" — mỗi bước một cái (yêu cầu #2 của gói). */
function WhyStep({ children }: { children: React.ReactNode }) {
  return (
    <details className="mt-4 rounded-md border border-hairline bg-page/60 px-3 py-2">
      <summary className="focus-ring flex min-h-tap cursor-pointer select-none items-center gap-1 rounded text-meta font-semibold text-dim">
        <span aria-hidden>▸</span> Vì sao cần bước này?
      </summary>
      <div className="mt-1.5 text-meta leading-snug text-sec">{children}</div>
    </details>
  );
}

/** Thanh tiến độ 4 chấm — bước xong bấm lại được, bước chưa mở thì khoá. */
function StepRail({
  step,
  maxStep,
  onJump,
}: {
  step: Step;
  maxStep: Step;
  onJump: (n: Step) => void;
}) {
  return (
    <ol className="mb-5 flex items-start" aria-label="Tiến độ chuẩn bị buổi live — 4 bước">
      {STEP_META.map((s, i) => {
        const state = s.n < step ? "done" : s.n === step ? "active" : "upcoming";
        const reachable = s.n <= maxStep;
        return (
          <li key={s.n} className="flex min-w-0 flex-1 flex-col items-center">
            <div className="flex w-full items-center">
              <div
                aria-hidden
                className={cx(
                  "h-px flex-1",
                  i === 0 ? "bg-transparent" : s.n <= step ? "bg-brand/50" : "bg-white/10",
                )}
              />
              <button
                type="button"
                onClick={() => onJump(s.n)}
                disabled={!reachable}
                aria-current={state === "active" ? "step" : undefined}
                aria-label={`Bước ${s.n}: ${s.label}${reachable ? "" : " — chưa mở được, hoàn tất bước trước đã"}`}
                className={cx(
                  "focus-ring flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                  "text-meta font-bold transition-colors duration-short2 ease-emphasized",
                  state === "done" && "bg-good text-page",
                  state === "active" &&
                    "border border-brand bg-brand/15 text-brand-ink ring-2 ring-brand/30",
                  state === "upcoming" && "border border-hairline bg-raised text-dim",
                  !reachable && "cursor-not-allowed opacity-60",
                )}
              >
                {state === "done" ? <CheckIcon /> : s.n}
              </button>
              <div
                aria-hidden
                className={cx(
                  "h-px flex-1",
                  i === STEP_META.length - 1
                    ? "bg-transparent"
                    : s.n < step
                      ? "bg-brand/50"
                      : "bg-white/10",
                )}
              />
            </div>
            <span
              className={cx(
                "mt-1 max-w-full truncate text-meta",
                state === "active" ? "font-semibold text-ink" : "text-dim",
              )}
            >
              {s.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

/** Thẻ lựa chọn to (nền tảng / chế độ) — radio bằng nút, có aria-pressed. */
function ChoiceCard({
  selected,
  onClick,
  title,
  note,
  badge,
  icon,
}: {
  selected: boolean;
  onClick: () => void;
  title: string;
  note?: string;
  badge?: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={cx(
        "focus-ring min-h-ctl flex-1 rounded-lg border p-3 text-left",
        "transition-colors duration-short2 ease-emphasized",
        selected
          ? "border-brand/70 bg-brand/10"
          : "border-hairline bg-raised hover:border-white/20",
      )}
    >
      <span className="flex items-start gap-2.5">
        {icon ? <span className={cx("mt-0.5", selected ? "text-brand-ink" : "text-dim")}>{icon}</span> : null}
        <span className="min-w-0">
          <span className="flex flex-wrap items-center gap-2">
            <span
              aria-hidden
              className={cx(
                "inline-block h-3 w-3 shrink-0 rounded-full border",
                selected ? "border-brand bg-brand" : "border-strong bg-transparent",
              )}
            />
            <span className="text-body font-semibold text-ink">{title}</span>
            {badge}
          </span>
          {note ? <span className="mt-1 block text-meta leading-snug text-sec">{note}</span> : null}
        </span>
      </span>
    </button>
  );
}

type RowState = "ok" | "warn" | "todo" | "info";

/** Một dòng checklist bước 4: dấu trạng thái (HÌNH + chữ ẩn) + nội dung. */
function CheckRow({
  state,
  title,
  children,
}: {
  state: RowState;
  title: React.ReactNode;
  children?: React.ReactNode;
}) {
  const glyph = { ok: "✓", warn: "⚠", todo: "○", info: "ℹ" }[state];
  const cls = { ok: "text-good-ink", warn: "text-warn-ink", todo: "text-dim", info: "text-info-ink" }[
    state
  ];
  const srText = { ok: "đã sẵn sàng", warn: "cần chú ý", todo: "chưa làm", info: "để biết" }[state];
  return (
    <li className="flex gap-2.5 border-t border-hairline py-3 first:border-t-0 first:pt-0 last:pb-0">
      <span aria-hidden className={cx("w-5 shrink-0 text-center text-body font-bold", cls)}>
        {glyph}
      </span>
      <span className="sr-only">{srText}:</span>
      <div className="min-w-0 flex-1">
        <p className="text-body text-ink">{title}</p>
        {children}
      </div>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Trang
// ---------------------------------------------------------------------------

export default function ChayPhienPage() {
  const [step, setStepState] = useState<Step>(1);
  const [hydrated, setHydrated] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Bước 1 — sản phẩm
  const [products, setProducts] = useState<Product[]>([]);
  const [productsLoading, setProductsLoading] = useState(true);
  const [newProduct, setNewProduct] = useState({
    name: "",
    url: "",
    price: "",
    cost: "",
    stock: "",
  });
  /** URL trang sản phẩm thật theo mã sản phẩm — đích của link đo /r/{code}. */
  const [productUrls, setProductUrls] = useState<Record<string, string>>({});

  // Bước 2 — phiên
  const [session, setSession] = useState<SessionSummary | null>(null);
  const [form, setForm] = useState({
    title: "",
    platform: "youtube" as string,
    minutes: "90",
    mode: "auto" as SessionMode,
  });

  // Bước 3 — lịch
  const [blockMin, setBlockMin] = useState("5");
  const [seed, setSeed] = useState("");
  const [schedule, setSchedule] = useState<WizardSchedule | null>(null);
  const [schedWarning, setSchedWarning] = useState<string | null>(null);
  /** Mã bằng chứng (SHA-256 tham số + seed) — công bố trước giờ phát. */
  const [designHash, setDesignHash] = useState<string | null>(null);

  // Bước 4 — lên sóng
  const [links, setLinks] = useState<LinkDo[]>([]);
  /** Số sản phẩm có link hợp lệ nhưng máy chủ không tạo được link đo. */
  const [linkFailed, setLinkFailed] = useState(0);
  /** Số link đo vừa được tạo lại vì lệch đích — báo tới khi người bán tick đã dán. */
  const [linkThay, setLinkThay] = useState(0);
  /** Đang tạo link đo — khoá chống chạy chồng (tạo trùng, ghi đè danh sách). */
  const [linksBusy, setLinksBusy] = useState(false);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [daDanLink, setDaDanLink] = useState(false);
  const [daMoHostFor, setDaMoHostFor] = useState<string | null>(null);
  const [signals, setSignals] = useState<SignalCoverage | null>(null);
  const [signalsErr, setSignalsErr] = useState(false);
  /** Trạng thái Bộ thu bình luận. null = chưa đọc được từ máy chủ. */
  const [ingest, setIngest] = useState<{ state: IngestState; running: boolean } | null>(null);
  const linksEnsured = useRef(false);
  /** Cờ tức thời (state cập nhật trễ một nhịp) — lời gọi ensureLinks đang chạy. */
  const linksInFlight = useRef(false);
  /** Phiên hiện tại cho lời gọi bất đồng bộ đối chiếu khi xong — phiên có thể đã bị huỷ. */
  const sessionIdRef = useRef<string | null>(null);

  const live = session?.status === "live";

  useEffect(() => {
    sessionIdRef.current = session?.session_id ?? null;
  }, [session?.session_id]);

  // -------------------------------------------------------------------------
  // Khung chạy lệnh + lỗi tiếng người
  // -------------------------------------------------------------------------
  const run = useCallback(async (fn: () => Promise<void>) => {
    setBusy(true);
    setErr(null);
    try {
      await fn();
    } catch (e) {
      setErr(viError(e));
    } finally {
      setBusy(false);
    }
  }, []);

  const refreshProducts = useCallback(async () => {
    try {
      setProducts(await listProducts());
    } catch {
      setErr("Không kết nối được máy chủ dữ liệu — kiểm tra máy chủ đã bật chưa rồi tải lại trang.");
    } finally {
      setProductsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshProducts();
  }, [refreshProducts]);

  // -------------------------------------------------------------------------
  // Khôi phục trạng thái: localStorage + URL, rồi hỏi máy chủ trạng thái THẬT
  // của phiên đã lưu (planned → bước 3, scheduled → bước 3/4, live → bước 4).
  // -------------------------------------------------------------------------
  useEffect(() => {
    let saved: SavedWizard | null = null;
    try {
      const raw = localStorage.getItem(LS_KEY);
      const parsed = raw ? (JSON.parse(raw) as SavedWizard) : null;
      if (parsed && parsed.v === 1) saved = parsed;
    } catch {
      saved = null;
    }
    const q = new URLSearchParams(window.location.search);
    const urlStep = Number(q.get("buoc"));
    const urlSession = q.get("phien");

    const sid = urlSession ?? saved?.sessionId ?? null;
    const wantStep = (
      urlStep >= 1 && urlStep <= 4 ? urlStep : (saved?.step ?? 1)
    ) as Step;

    if (saved) {
      setProductUrls(saved.productUrls ?? {});
      if (saved.form) setForm(saved.form);
      if (saved.blockMin) setBlockMin(saved.blockMin);
      // Link đo + các dấu đã-làm thuộc về MỘT phiên: URL trỏ phiên khác thì
      // không mang sang (link của phiên cũ dán vào phiên mới là đếm nhầm lượt bấm).
      if (sid != null && saved.sessionId === sid) {
        setLinks(
          (saved.links ?? []).map((l) => ({
            code: l.code,
            product_id: l.product_id,
            target_url: typeof l.target_url === "string" ? l.target_url : null,
          })),
        );
        setDaDanLink(Boolean(saved.daDanLink));
        setDaMoHostFor(typeof saved.daMoHostFor === "string" ? saved.daMoHostFor : null);
      }
    }

    const clearSessionBits = () => {
      setSession(null);
      setSchedule(null);
      setDesignHash(null);
      setLinks([]);
      setDaDanLink(false);
      setDaMoHostFor(null);
      try {
        localStorage.removeItem(LS_KEY);
      } catch {
        // localStorage bị chặn — trạng thái chỉ sống trong phiên trình duyệt
      }
    };

    if (!sid) {
      setStepState(wantStep <= 2 ? wantStep : 1);
      setHydrated(true);
      return;
    }

    void (async () => {
      try {
        const list = await listSessions();
        const s = list.find((x) => x.session_id === sid) ?? null;
        if (!s || s.status === "ended" || s.status === "cancelled") {
          // Phiên đã đóng: wizard bắt đầu lại từ đầu, không giữ xác cũ.
          clearSessionBits();
          setStepState(1);
          return;
        }
        setSession(s);
        setForm((f) => ({
          ...f,
          title: s.title ?? f.title,
          platform: s.platform,
          minutes: String(s.planned_duration_min),
          mode: s.mode,
        }));
        if (s.status === "planned") {
          setStepState(3);
          return;
        }
        // scheduled / live: khôi phục lịch + mã bằng chứng từ máy chủ
        const [blocksR, stateR] = await Promise.allSettled([getSchedule(sid), getState(sid)]);
        if (blocksR.status === "fulfilled" && blocksR.value.length > 0) {
          const bs = blocksR.value;
          setSchedule({
            blocks: bs,
            nOn: bs.filter((b) => !b.is_washout && b.assignment === "ON").length,
            nOff: bs.filter((b) => !b.is_washout && b.assignment === "OFF").length,
            seed: null,
          });
        }
        if (stateR.status === "fulfilled") {
          setDesignHash(stateR.value.design_hash ?? null);
        }
        setStepState(s.status === "live" || wantStep === 4 ? 4 : 3);
      } catch {
        setErr(
          "Không kết nối được máy chủ dữ liệu — phiên đã lưu sẽ hiện lại đúng bước khi máy chủ chạy.",
        );
        setStepState(wantStep <= 2 ? wantStep : 1);
      } finally {
        setHydrated(true);
      }
    })();
    // Chạy đúng một lần lúc mở trang — các setState bên trong là khôi phục.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Ghi trạng thái xuống localStorage + URL sau mỗi thay đổi (refresh không mất).
  useEffect(() => {
    if (!hydrated) return;
    const state: SavedWizard = {
      v: 1,
      step,
      productUrls,
      form,
      blockMin,
      sessionId: session?.session_id ?? null,
      links,
      daDanLink,
      daMoHostFor,
    };
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(state));
    } catch {
      // localStorage bị chặn — URL vẫn giữ được bước + phiên
    }
    const q = new URLSearchParams();
    q.set("buoc", String(step));
    if (session) q.set("phien", session.session_id);
    window.history.replaceState(null, "", `?${q.toString()}`);
  }, [hydrated, step, productUrls, form, blockMin, session, links, daDanLink, daMoHostFor]);

  // -------------------------------------------------------------------------
  // Điều hướng bước
  // -------------------------------------------------------------------------
  const maxStep: Step = session ? (schedule ? 4 : 3) : 2;
  const goStep = (n: Step) => {
    if (n <= maxStep) {
      setErr(null);
      setStepState(n);
    }
  };

  // -------------------------------------------------------------------------
  // Bước 1: sản phẩm
  // -------------------------------------------------------------------------
  const canAddProduct = newProduct.name.trim() !== "" && !busy;
  const slugPreview = newProduct.name.trim() ? uniqueSlug(newProduct.name.trim(), products) : null;

  const addProduct = () =>
    run(async () => {
      const name = newProduct.name.trim();
      const pid = uniqueSlug(name, products);
      await createProduct({
        product_id: pid,
        name,
        cost: Number(newProduct.cost) || 0,
        price: Number(newProduct.price) || 0,
        stock: Number(newProduct.stock) || 0,
      });
      const url = newProduct.url.trim();
      if (url) setProductUrls((prev) => ({ ...prev, [pid]: url }));
      setNewProduct({ name: "", url: "", price: "", cost: "", stock: "" });
      await refreshProducts();
    });

  /**
   * Điền sẵn một sản phẩm mẫu để xem thử — vẫn phải bấm "Thêm sản phẩm".
   * Link là LINK MẪU example.com (không bịa địa chỉ cửa hàng có thật) và được
   * ghi rõ là link mẫu ngay dưới ô.
   */
  const fillSample = () =>
    setNewProduct({
      name: "Áo khoác dù 2 lớp",
      url: sampleUrlFor("ao-khoac-du-2-lop"),
      price: "179000",
      cost: "96000",
      stock: "40",
    });

  /** Điền link mẫu cho các sản phẩm còn thiếu link — chỉ để chạy thử. */
  const fillSampleLinks = () =>
    setProductUrls((prev) => {
      const next = { ...prev };
      for (const p of products) {
        if (!isValidProductUrl((next[p.product_id] ?? "").trim())) {
          next[p.product_id] = sampleUrlFor(p.product_id);
        }
      }
      return next;
    });

  const urlOf = (productId: string) => (productUrls[productId] ?? "").trim();
  const missingLinkProducts = products.filter((p) => !isValidProductUrl(urlOf(p.product_id)));

  // -------------------------------------------------------------------------
  // Bước 2: tạo phiên
  // -------------------------------------------------------------------------
  const makeSession = () =>
    run(async () => {
      const minutes = Number(form.minutes) || PHUT_KHUYEN_DUNG;
      const s = await createSession({
        platform: form.platform,
        // Để trống tên thì đặt tên mặc định đọc được — nơi khác khỏi in UUID.
        title: form.title.trim() || tenPhienMacDinh(new Date(), form.platform, minutes),
        mode: form.mode,
        planned_duration_min: minutes,
      });
      setSession(s);
      setStepState(3);
    });

  /**
   * Huỷ phiên nháp để sửa thông tin — backend cố ý không có API sửa phiên.
   * `minutes` chọn sẵn thời lượng mới (nút "Đổi thời lượng" ở bước 3).
   */
  const cancelAndEdit = (minutes?: string) =>
    run(async () => {
      if (!session) return;
      await cancelSession(session.session_id);
      setSession(null);
      setSchedule(null);
      setDesignHash(null);
      setSchedWarning(null);
      setLinks([]);
      setLinkFailed(0);
      setLinkThay(0);
      setDaDanLink(false);
      // Tab màn người dẫn đã mở ghim vào phiên vừa huỷ — không còn là "đã mở".
      setDaMoHostFor(null);
      linksEnsured.current = false;
      setForm((f) => ({
        ...f,
        title: laTenMacDinh(f.title) ? "" : f.title,
        minutes: minutes ?? f.minutes,
      }));
      setStepState(2);
    });

  // -------------------------------------------------------------------------
  // Bước 3: bốc thăm lịch
  // -------------------------------------------------------------------------
  const drawSchedule = (boLai = false) =>
    run(async () => {
      if (!session) return;
      // Bốc lại là bốc NGẪU NHIÊN mới: giữ mã bốc thăm đã gõ ở tuỳ chọn nâng
      // cao thì "lịch khác" sẽ ra y hệt lịch vừa bốc.
      const seedGo = boLai ? "" : seed.trim();
      if (boLai) setSeed("");
      const res = await createSchedule(session.session_id, {
        block_min: Number(blockMin) || 5,
        washout_min: 0,
        jitter_s: 30,
        seed: seedGo ? Number(seedGo) : undefined,
      });
      setSchedule({ blocks: res.blocks, nOn: res.n_on, nOff: res.n_off, seed: res.seed });
      setDesignHash(res.design_hash);
      setSchedWarning(res.warning ?? null);
      setSession((s) => (s ? { ...s, status: "scheduled" } : s));
    });

  // -------------------------------------------------------------------------
  // Bước 4: link đo + nguồn bình luận + dữ liệu + lên sóng
  // -------------------------------------------------------------------------

  /**
   * Tạo link đo cho các sản phẩm đã có URL hợp lệ (chưa có thì thôi, không
   * chặn) và TẠO LẠI link đo có đích khác link trang sản phẩm hiện tại — máy
   * chủ không sửa được đích của link cũ. Một lời gọi mỗi lúc (linksInFlight):
   * ra rồi vào lại bước 4 nhanh không được sinh bộ link trùng.
   */
  const ensureLinks = useCallback(async () => {
    if (!session || linksInFlight.current) return;
    linksInFlight.current = true;
    setLinksBusy(true);
    const sid = session.session_id;
    try {
      const viec = keHoachLinkDo(
        links,
        products.map((p) => ({
          product_id: p.product_id,
          url: (productUrls[p.product_id] ?? "").trim(),
        })),
        MAX_LINKS,
      );
      const created: LinkDo[] = [];
      let failed = 0;
      let thay = 0;
      for (const v of viec) {
        try {
          const l = await createShortlink({
            product_id: v.product_id,
            session_id: sid,
            target_url: v.url,
          });
          created.push({ code: l.code, product_id: v.product_id, target_url: l.target_url });
          if (v.thay) thay += 1;
        } catch {
          // một link hỏng không được chặn các link còn lại — nhưng phải được đếm
          failed += 1;
        }
      }
      // Phiên đã bị huỷ/đổi trong lúc chờ: link vừa tạo thuộc phiên cũ, bỏ.
      if (sessionIdRef.current !== sid) return;
      setLinks((prev) => ganLinkMoi(prev, created));
      setLinkFailed(failed);
      if (thay > 0) {
        setLinkThay(thay);
        // link cũ (có thể đã dán vào bình luận ghim) vẫn dẫn tới đích cũ
        setDaDanLink(false);
      }
    } finally {
      linksInFlight.current = false;
      setLinksBusy(false);
    }
  }, [session, links, products, productUrls]);

  useEffect(() => {
    if (step !== 4 || !session) return;
    setSignalsErr(false);
    getSignalCoverage(session.session_id)
      .then(setSignals)
      .catch(() => setSignalsErr(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, session?.session_id]);

  // Trạng thái bộ thu cho dòng "Nguồn bình luận" và bộ đếm "còn N việc".
  // IngestPanel tự hỏi máy chủ nhưng không báo ra ngoài, nên trang hỏi riêng
  // (thưa hơn) — chỉ khi đang ở bước 4.
  useEffect(() => {
    if (step !== 4 || !session) return;
    let alive = true;
    const sid = session.session_id;
    setIngest(null);
    const hoi = () =>
      getIngestStatus(sid)
        .then((st) => {
          if (alive) setIngest({ state: st.state, running: st.running });
        })
        .catch(() => {
          // mất kết nối tạm thời: giữ trạng thái cũ, lần sau hỏi lại
        });
    void hoi();
    const t = setInterval(() => void hoi(), 5000);
    return () => {
      alive = false;
      clearInterval(t);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, session?.session_id]);

  // Tạo link đo MỖI LẦN vào bước 4 — CHỜ danh mục sản phẩm tải xong (refresh
  // thẳng vào bước 4 thì products tới sau). Rời bước 4 thì mở khoá lại: người
  // bán bấm "bổ sung ở bước 1" rồi quay lại phải thấy link mới (hoặc link tạo
  // lại vì đổi đích). Lời gọi trước CHƯA XONG thì chờ: linksBusy nằm trong
  // deps nên khi nó xong hiệu ứng chạy lại với danh sách link đã cập nhật —
  // không chạy chồng, không tạo trùng.
  useEffect(() => {
    if (step !== 4) {
      linksEnsured.current = false;
      return;
    }
    if (!session || productsLoading || linksBusy) return;
    if (!linksEnsured.current) {
      linksEnsured.current = true;
      void ensureLinks();
    }
    // ensureLinks đổi theo links → ref guard giữ cho hiệu ứng chạy đúng 1 lần.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, session?.session_id, productsLoading, linksBusy]);

  const copyLink = async (code: string) => {
    try {
      await navigator.clipboard.writeText(`${PUBLIC_API_BASE}/r/${code}`);
      setCopiedCode(code);
      setTimeout(() => setCopiedCode((c) => (c === code ? null : c)), 2000);
    } catch {
      setErr("Không chép được link — trình duyệt chặn quyền bộ nhớ tạm, hãy chọn và chép thủ công.");
    }
  };

  const goLive = () =>
    run(async () => {
      if (!session) return;
      const s = await startSession(session.session_id);
      setSession(s);
      // Lên sóng xong, chỗ làm việc là bàn trợ live — chuyển thẳng tới ĐÚNG
      // phiên vừa tạo (deep link ?session=, spec UX-FLOW luồng 3).
      // window.location thay vì router.push: wizard ghi trạng thái bước lên
      // URL bằng history.replaceState, App Router vì thế lệch nhịp với
      // history và nuốt lệnh push (kiểm chứng bằng đường bấm thật 13/09);
      // một lần tải trang đầy đủ khi rời wizard là chấp nhận được.
      window.location.assign(`/desk?session=${encodeURIComponent(s.session_id)}`);
    });

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  const meta = STEP_META[step - 1];
  const minutesNum = Number(form.minutes) || 0;
  const measBlocks = schedule ? schedule.blocks.filter((b) => !b.is_washout).length : 0;
  const plannedMin = session?.planned_duration_min ?? (minutesNum || PHUT_KHUYEN_DUNG);
  const phienNgan = plannedMin < PHUT_KHUYEN_DUNG;

  /** Màn người dẫn mở ĐÚNG phiên này, kể cả khi kho có phiên live khác. */
  const hostHref = session ? `/host?session=${encodeURIComponent(session.session_id)}` : "/host";

  // Checklist bước 4 — mỗi việc một cờ; bộ đếm cạnh nút lên sóng đọc từ đây.
  const daMoHost = daMoDungPhien(daMoHostFor, session?.session_id);
  const ingestRunning = ingest?.running ?? null;
  const dongNguon = dongNguonBinhLuan(ingest);
  // Link đo vẫn dẫn tới đích cũ, khác link trang sản phẩm hiện tại (tạo lại
  // thất bại). Đang tạo link thì chưa kết luận.
  const linkLechDich = linksBusy
    ? 0
    : links.filter((l) => canTaoLaiLink(l, urlOf(l.product_id))).length;
  const linkXong = links.length > 0 && daDanLink && linkLechDich === 0;
  const viecChuaXong = [!schedule, !linkXong, ingestRunning !== true, !daMoHost].filter(
    Boolean,
  ).length;
  const tinHieuHienThi = (signals?.signals ?? []).filter(
    (s) => !TIN_HIEU_CO_DONG_RIENG.includes(s.name),
  );
  const tenSanPham = (productId: string) =>
    products.find((p) => p.product_id === productId)?.name ?? productId;
  // Đọc ĐÍCH THẬT của link đo, không đọc link trang sản phẩm hiện tại: thay
  // link mẫu bằng link thật ở bước 1 không làm link đo cũ hết trỏ example.com.
  const linkMauDangDung = links.filter(
    (l) => l.target_url != null && isSampleUrl(l.target_url),
  ).length;
  // Chỉ nói "vượt giới hạn" khi đã chạm trần MAX_LINKS — trước khi link được
  // tạo xong, sản phẩm có URL mà chưa có link là chuyện đang chờ, không phải trần.
  const vuotGioiHan =
    links.length >= MAX_LINKS
      ? products.filter(
          (p) =>
            isValidProductUrl(urlOf(p.product_id)) &&
            !links.some((l) => l.product_id === p.product_id),
        ).length
      : 0;

  return (
    <div className="flex min-h-screen flex-col bg-page">
      <TopNav />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-8">
        <PageHeader
          phase="truoc"
          title="Chuẩn bị buổi live"
          lead={
            // Đoạn dẫn chỉ ở bước 1 (gói H1): các bước sau người bán đã đọc
            // rồi — lặp lại là đẩy việc cần làm xuống dưới ~230 px chữ cũ.
            hydrated && step === 1 ? (
              <>
                Bốn bước nhỏ, mỗi lần một việc: khai sản phẩm, tạo phiên, bốc thăm lịch BẬT/TẮT
                rồi lên sóng. Thứ tự là <strong className="text-ink">yêu cầu khoa học</strong> —
                lịch phải bốc và niêm phong <strong className="text-ink">trước</strong> giờ phát,
                đó là điều làm kết quả kiểm chứng được.
              </>
            ) : undefined
          }
        />

        {!hydrated ? (
          <div className="space-y-3" aria-busy>
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-48 w-full rounded-lg" />
          </div>
        ) : (
          <>
            <StepRail step={step} maxStep={live ? 4 : maxStep} onJump={goStep} />
            <p className="mb-2 text-meta text-dim">
              Bước <span className="tnum text-sec">{step}/4</span> · {meta.label} · {meta.time}
              {session?.is_demo ? (
                <>
                  {" "}
                  ·{" "}
                  <span className="font-semibold text-warn-ink">
                    <span aria-hidden>◐</span> Phiên dữ liệu mẫu — không tính vào kết quả thật
                  </span>
                </>
              ) : null}
            </p>

            {err ? (
              <Callout tone="critical" className="mb-4">
                {err}
              </Callout>
            ) : null}

            {/* ============================= BƯỚC 1 ============================= */}
            {step === 1 ? (
              <Card as="section" padding="lg">
                <h2 className="text-title text-ink">Bạn sẽ bán gì trong buổi live này?</h2>
                <p className="mt-1 text-body leading-snug text-sec">
                  {CAU_MOT_DONG.linkDo}
                </p>

                {/* MỘT chỗ duy nhất nói về link còn thiếu (gói H2) — trước đây
                    mỗi sản phẩm tự in hai dòng cảnh báo giống hệt nhau. */}
                {!productsLoading && missingLinkProducts.length > 0 ? (
                  <Callout tone="warn" className="mt-4">
                    <strong>
                      <span className="tnum">{missingLinkProducts.length}</span>/
                      <span className="tnum">{products.length}</span> sản phẩm chưa có link trang
                      sản phẩm
                    </strong>{" "}
                    — những sản phẩm này sẽ không đo được lượt bấm. Mở trang sản phẩm trên Shopee,
                    TikTok Shop hay website của bạn, chép địa chỉ trên thanh trình duyệt rồi dán vào
                    ô “Link trang sản phẩm thật” của từng sản phẩm.
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <Button variant="ghost" size="sm" onClick={fillSampleLinks} disabled={busy}>
                        Điền link mẫu để chạy thử
                      </Button>
                      <span className="text-meta text-dim">
                        link mẫu dạng https://example.com/… — khách bấm sẽ tới trang ví dụ, không
                        phải trang bán hàng
                      </span>
                    </div>
                  </Callout>
                ) : null}

                {productsLoading ? (
                  <div className="mt-4 space-y-1.5" aria-busy>
                    <Skeleton className="h-5 w-full" />
                    <Skeleton className="h-5 w-5/6" />
                  </div>
                ) : products.length > 0 ? (
                  <ul className="mt-4 space-y-2">
                    {products.map((p) => {
                      const url = urlOf(p.product_id);
                      const valid = isValidProductUrl(url);
                      const sample = valid && isSampleUrl(url);
                      const invalid = url !== "" && !valid;
                      return (
                        <li
                          key={p.product_id}
                          className="rounded-md border border-hairline bg-raised px-3 py-2"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                            <span className="truncate text-body font-semibold text-ink">
                              {p.name}
                            </span>
                            <span className="flex items-center gap-2">
                              <span className="tnum shrink-0 text-body text-sec">
                                {fmtVnd(p.price)}
                              </span>
                              {sample ? (
                                <span className="rounded-full border border-warn/40 bg-warn/10 px-2 py-0.5 text-meta font-semibold text-warn-ink">
                                  ◐ link mẫu
                                </span>
                              ) : valid ? (
                                <span className="rounded-full border border-good/30 bg-good/10 px-2 py-0.5 text-meta font-semibold text-good-ink">
                                  ✓ có link
                                </span>
                              ) : (
                                <span className="rounded-full border border-hairline px-2 py-0.5 text-meta text-dim">
                                  ○ chưa có link
                                </span>
                              )}
                            </span>
                          </div>
                          <label className="mt-1.5 block">
                            <span className="text-meta text-dim">Link trang sản phẩm thật</span>
                            <input
                              className={`${inputCls} mt-0.5 text-meta ${invalid ? "border-critical/60" : ""}`}
                              type="url"
                              inputMode="url"
                              placeholder="Dán link trang sản phẩm (bắt đầu bằng https://)"
                              value={productUrls[p.product_id] ?? ""}
                              aria-invalid={invalid}
                              onChange={(e) =>
                                setProductUrls((prev) => ({
                                  ...prev,
                                  [p.product_id]: e.target.value,
                                }))
                              }
                            />
                          </label>
                          {invalid ? (
                            <p className="mt-0.5 text-meta text-crit-ink">
                              Link chưa hợp lệ — cần địa chỉ đầy đủ bắt đầu bằng http:// hoặc
                              https://.
                            </p>
                          ) : null}
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <p className="mt-4 text-body text-dim">
                    Chưa có sản phẩm nào — thêm sản phẩm đầu tiên bên dưới, hoặc bấm “Dùng sản
                    phẩm mẫu” để xem thử.
                  </p>
                )}

                {/* form thêm sản phẩm — MỌI ô có nhãn, KHÔNG có ô "Mã SP" */}
                <div className="mt-4 rounded-md border border-hairline bg-page/60 p-3">
                  <p className="text-body font-semibold text-ink">Thêm sản phẩm mới</p>
                  <div className="mt-2 grid gap-2 md:grid-cols-2">
                    <label className="block">
                      <span className="text-meta font-semibold text-sec">Tên sản phẩm *</span>
                      <input
                        className={`${inputCls} mt-0.5`}
                        placeholder="Áo khoác dù 2 lớp"
                        value={newProduct.name}
                        onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })}
                      />
                    </label>
                    <label className="block">
                      <span className="text-meta font-semibold text-sec">Giá bán (đ)</span>
                      <input
                        className={`${inputCls} mt-0.5`}
                        inputMode="numeric"
                        placeholder="179000"
                        value={newProduct.price}
                        onChange={(e) => setNewProduct({ ...newProduct, price: e.target.value })}
                      />
                    </label>
                  </div>
                  <label className="mt-2 block">
                    <span className="text-meta font-semibold text-sec">
                      Link trang sản phẩm thật
                    </span>
                    <input
                      className={`${inputCls} mt-0.5`}
                      type="url"
                      inputMode="url"
                      placeholder="Dán link trang sản phẩm (bắt đầu bằng https://)"
                      value={newProduct.url}
                      onChange={(e) => setNewProduct({ ...newProduct, url: e.target.value })}
                    />
                  </label>
                  {isSampleUrl(newProduct.url.trim()) ? (
                    <p className="mt-1 text-meta text-warn-ink">
                      <span aria-hidden>◐</span> Đây là link mẫu để xem thử — thay bằng link trang
                      sản phẩm thật của bạn trước khi lên sóng.
                    </p>
                  ) : (
                    <p className="mt-1 text-meta text-dim">
                      Mở trang sản phẩm trên Shopee, TikTok Shop hay website của bạn rồi chép địa
                      chỉ trên thanh trình duyệt.
                    </p>
                  )}
                  {slugPreview ? (
                    <p className="mt-1 text-meta text-dim">
                      Mã hệ thống tự đặt: <code className="text-sec">{slugPreview}</code> — bạn
                      không phải nghĩ mã.
                    </p>
                  ) : null}
                  <details className="mt-2">
                    <summary className="focus-ring flex min-h-tap cursor-pointer select-none items-center gap-1 rounded text-meta font-semibold text-dim">
                      <span aria-hidden>▸</span> Thêm chi tiết (giá vốn, tồn kho) — tuỳ chọn
                    </summary>
                    <div className="mt-1.5 grid gap-2 md:grid-cols-2">
                      <label className="block">
                        <span className="text-meta font-semibold text-sec">Giá vốn (đ)</span>
                        <input
                          className={`${inputCls} mt-0.5`}
                          inputMode="numeric"
                          placeholder="96000"
                          value={newProduct.cost}
                          onChange={(e) => setNewProduct({ ...newProduct, cost: e.target.value })}
                        />
                      </label>
                      <label className="block">
                        <span className="text-meta font-semibold text-sec">Tồn kho (cái)</span>
                        <input
                          className={`${inputCls} mt-0.5`}
                          inputMode="numeric"
                          placeholder="40"
                          value={newProduct.stock}
                          onChange={(e) => setNewProduct({ ...newProduct, stock: e.target.value })}
                        />
                      </label>
                    </div>
                  </details>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button onClick={addProduct} disabled={!canAddProduct}>
                      + Thêm sản phẩm
                    </Button>
                    <Button variant="ghost" onClick={fillSample} disabled={busy}>
                      Dùng sản phẩm mẫu
                    </Button>
                  </div>
                </div>

                <WhyStep>
                  Hệ thống cần biết bán gì để gợi ý ghim sản phẩm đúng lúc, và cần link trang sản
                  phẩm thật để tạo <Term tip={CAU_MOT_DONG.linkDo}>link đo</Term> — không có link
                  thì buổi live vẫn chạy, nhưng không đo được lượt nhấp, tức là không có con số để
                  kết luận.
                </WhyStep>

                <div className="mt-4 flex items-center justify-end gap-3 border-t border-hairline pt-4">
                  {products.length === 0 ? (
                    <p className="mr-auto text-meta text-dim">
                      Thêm ít nhất một sản phẩm để tiếp tục.
                    </p>
                  ) : null}
                  <Button onClick={() => goStep(2)} disabled={products.length === 0 || busy}>
                    Xong, sang bước 2 →
                  </Button>
                </div>
              </Card>
            ) : null}

            {/* ============================= BƯỚC 2 ============================= */}
            {step === 2 ? (
              <Card as="section" padding="lg">
                <h2 className="text-title text-ink">Thông tin buổi live</h2>
                <p className="mt-1 text-body leading-snug text-sec">
                  Ba lựa chọn bấm là xong — không có ô nào bắt buộc phải gõ.
                </p>

                {session ? (
                  <Callout tone="warn" className="mt-4">
                    Phiên <strong>{session.title || "chưa đặt tên"}</strong> (
                    {session.planned_duration_min} phút · {tenNenTang(session.platform)}) đã được
                    tạo. Muốn đổi nền tảng/thời lượng/chế độ thì huỷ phiên nháp này rồi tạo lại —
                    thông số phiên là một phần của thiết kế thí nghiệm nên không sửa tại chỗ được.
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => cancelAndEdit()}
                        disabled={busy}
                      >
                        Huỷ phiên nháp, sửa lại
                      </Button>
                      <Button size="sm" onClick={() => goStep(3)} disabled={busy}>
                        Giữ nguyên, sang bước 3 →
                      </Button>
                    </div>
                  </Callout>
                ) : (
                  <>
                    <label className="mt-4 block">
                      <span className="text-meta font-semibold text-sec">
                        Tên buổi live (tuỳ chọn)
                      </span>
                      <input
                        className={`${inputCls} mt-0.5`}
                        placeholder={tenPhienMacDinh(
                          new Date(),
                          form.platform,
                          minutesNum || PHUT_KHUYEN_DUNG,
                        )}
                        value={form.title}
                        onChange={(e) => setForm({ ...form, title: e.target.value })}
                      />
                    </label>
                    <p className="mt-1 text-meta text-dim">
                      Để trống thì hệ thống đặt tên theo giờ tạo, nền tảng và thời lượng như gợi ý
                      trong ô.
                    </p>

                    <p className="mt-4 text-meta font-semibold text-sec">Phát trên nền tảng nào?</p>
                    <div className="mt-1.5 flex flex-col gap-2 sm:flex-row">
                      <ChoiceCard
                        selected={form.platform === "youtube"}
                        onClick={() => setForm({ ...form, platform: "youtube" })}
                        title="YouTube Live"
                        note="Đọc được bình luận + người xem trực tiếp — đo đầy đủ nhất."
                        icon={<IconYouTube />}
                      />
                      <ChoiceCard
                        selected={form.platform === "facebook"}
                        onClick={() => setForm({ ...form, platform: "facebook" })}
                        title="Facebook Live"
                        note="Cần kết nối Trang (Page) để đọc bình luận — thiếu thì hệ thống sẽ nói rõ."
                        icon={<IconFacebook />}
                      />
                    </div>

                    <p className="mt-4 text-meta font-semibold text-sec">
                      Dự kiến live bao lâu?
                    </p>
                    <div className="mt-1.5 flex flex-wrap gap-2">
                      {["30", "60", "90", "120"].map((m) => (
                        <button
                          key={m}
                          type="button"
                          aria-pressed={form.minutes === m}
                          onClick={() => setForm({ ...form, minutes: m })}
                          className={cx(
                            "focus-ring min-h-ctl rounded-md border px-4 text-body font-semibold",
                            "transition-colors duration-short2 ease-emphasized",
                            form.minutes === m
                              ? "border-brand/70 bg-brand/10 text-brand-ink"
                              : "border-hairline bg-raised text-sec hover:border-white/20",
                          )}
                        >
                          {m} phút
                          {Number(m) === PHUT_KHUYEN_DUNG ? (
                            <span className="ml-1.5 text-meta font-normal text-good-ink">
                              khuyên dùng
                            </span>
                          ) : null}
                        </button>
                      ))}
                    </div>
                    {minutesNum > 0 && minutesNum < PHUT_KHUYEN_DUNG ? (
                      <Callout tone="warn" className="mt-2">
                        Phiên {minutesNum} phút vẫn chạy được, nhưng ít khối hơn nên kết luận sẽ
                        kém chắc — từ {PHUT_KHUYEN_DUNG} phút trở lên mới đủ khối cho kết luận đáng
                        tin. Khi bốc thăm, máy chủ sẽ nói rõ mức đảm bảo thật của lịch.
                      </Callout>
                    ) : null}

                    <p className="mt-4 text-meta font-semibold text-sec">
                      Ai bấm nút ghim sản phẩm?
                    </p>
                    <div className="mt-1.5 flex flex-col gap-2 sm:flex-row">
                      <ChoiceCard
                        selected={form.mode === "auto"}
                        onClick={() => setForm({ ...form, mode: "auto" })}
                        title="Tự ghim"
                        badge={
                          <span className="rounded-full border border-good/30 bg-good/10 px-2 py-0.5 text-meta font-semibold text-good-ink">
                            khuyên dùng
                          </span>
                        }
                        note="Hệ thống tự ghim sản phẩm tốt nhất khi đến lượt; bạn chỉ theo dõi trên bàn trợ live."
                      />
                      <ChoiceCard
                        selected={form.mode === "suggest"}
                        onClick={() => setForm({ ...form, mode: "suggest" })}
                        title="Chỉ gợi ý"
                        note="Hệ thống chỉ đề xuất; sản phẩm chỉ được ghim khi bạn bấm Thực hiện — dùng khi live nhờ phòng đối tác."
                      />
                    </div>
                  </>
                )}

                <WhyStep>
                  Nền tảng quyết định hệ thống đọc được tín hiệu gì; thời lượng quyết định số{" "}
                  <Term tip={CAU_MOT_DONG.batTat}>khối BẬT/TẮT</Term> — càng nhiều khối kết luận
                  càng chắc; chế độ quyết định ai bấm nút ghim. Ba thứ này phải chốt trước khi bốc
                  thăm nên hệ thống hỏi một lần ở đây.
                </WhyStep>

                {!session ? (
                  <div className="mt-4 flex items-center justify-between gap-3 border-t border-hairline pt-4">
                    <Button variant="ghost" onClick={() => goStep(1)} disabled={busy}>
                      ← Quay lại
                    </Button>
                    <Button onClick={makeSession} disabled={busy}>
                      Tạo phiên, sang bước 3 →
                    </Button>
                  </div>
                ) : (
                  <div className="mt-4 flex items-center justify-start gap-3 border-t border-hairline pt-4">
                    <Button variant="ghost" onClick={() => goStep(1)} disabled={busy}>
                      ← Quay lại
                    </Button>
                  </div>
                )}
              </Card>
            ) : null}

            {/* ============================= BƯỚC 3 ============================= */}
            {step === 3 ? (
              <Card as="section" padding="lg">
                <h2 className="text-title text-ink">Bốc thăm lịch BẬT/TẮT</h2>

                {!schedule ? (
                  <>
                    <p className="mt-1 text-body leading-snug text-sec">{CAU_MOT_DONG.batTat}</p>
                    <p className="mt-2 text-body leading-snug text-sec">
                      Bốc <strong className="text-ink">trước</strong> khi lên sóng để không ai sửa
                      được giữa chừng — đây là thứ làm kết quả đáng tin.
                    </p>
                    <div className="mt-5 flex justify-center">
                      <Button onClick={() => drawSchedule()} disabled={busy || !session}>
                        Bốc thăm lịch BẬT/TẮT
                      </Button>
                    </div>
                    <details className="mt-4">
                      <summary className="focus-ring flex min-h-tap cursor-pointer select-none items-center gap-1 rounded text-meta font-semibold text-dim">
                        <span aria-hidden>▸</span> Tuỳ chọn nâng cao (độ dài khối, mã bốc thăm) —
                        mặc định là đủ
                      </summary>
                      <div className="mt-1.5 grid gap-2 md:w-2/3 md:grid-cols-2">
                        <label className="block">
                          <span className="text-meta font-semibold text-sec">
                            Độ dài khối (phút)
                          </span>
                          <input
                            className={`${inputCls} mt-0.5`}
                            inputMode="numeric"
                            value={blockMin}
                            onChange={(e) => setBlockMin(e.target.value)}
                          />
                        </label>
                        <label className="block">
                          <span className="text-meta font-semibold text-sec">
                            <Term tip="Số khởi tạo bốc thăm — cùng số này cho ra đúng lịch đó, để kiểm chứng lại.">
                              Mã bốc thăm (seed)
                            </Term>{" "}
                            — để trống là ngẫu nhiên
                          </span>
                          <input
                            className={`${inputCls} mt-0.5`}
                            inputMode="numeric"
                            value={seed}
                            onChange={(e) => setSeed(e.target.value)}
                            placeholder="vd 42"
                          />
                        </label>
                      </div>
                    </details>
                  </>
                ) : (
                  <div className="mt-1">
                    {/* MỘT câu thường ngày, số lấy từ lịch thật máy chủ trả về. */}
                    <p className="text-body leading-snug text-sec">
                      {tomTatLich(schedule.blocks, plannedMin)}
                    </p>
                    {/* positionS={null}: chưa lên sóng nên không có vạch vị trí, và
                        BlockStrip bỏ luôn chú giải "Vị trí hiện tại". */}
                    <div className="mt-3">
                      <BlockStrip
                        blocks={schedule.blocks}
                        durationS={plannedMin * 60}
                        positionS={null}
                      />
                    </div>

                    {/* Khuyến nghị hành động — một việc, một nút. */}
                    {!live && phienNgan ? (
                      <Callout tone="warn" className="mt-4">
                        <strong>
                          Phiên <span className="tnum">{plannedMin}</span> phút chỉ có{" "}
                          <span className="tnum">{measBlocks}</span> khối —{" "}
                          {/* "quá ngắn" chỉ khi máy chủ xác nhận lịch thiếu cân bằng. */}
                          {schedWarning
                            ? "quá ngắn để kết luận chắc."
                            : "hơi ngắn nên kết luận sẽ kém chắc hơn."}
                        </strong>{" "}
                        Nên chọn {PHUT_KHUYEN_DUNG} phút.
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          <Button
                            size="sm"
                            onClick={() => cancelAndEdit(String(PHUT_KHUYEN_DUNG))}
                            disabled={busy}
                          >
                            Đổi thời lượng
                          </Button>
                          <span className="text-meta text-dim">
                            huỷ phiên nháp này, chọn sẵn {PHUT_KHUYEN_DUNG} phút ở bước 2 để bạn
                            tạo lại
                          </span>
                        </div>
                      </Callout>
                    ) : !live && schedWarning ? (
                      <Callout tone="warn" className="mt-4">
                        <strong>Lịch này chưa cân bằng đủ như thiết kế yêu cầu</strong> nên kết luận
                        sẽ kém chắc hơn. Lý do và gợi ý sửa của máy chủ nằm trong “Chi tiết kỹ
                        thuật”.
                      </Callout>
                    ) : schedule.seed != null && !schedWarning && !phienNgan ? (
                      <p className="mt-4 text-body text-good-ink">
                        <span aria-hidden>✓</span> Lịch đủ cân bằng theo thiết kế — sang bước 4 được
                        rồi.
                      </p>
                    ) : null}

                    {/* Mọi chi tiết kỹ thuật gom một chỗ, đóng sẵn. */}
                    <details className="mt-4 rounded-md border border-hairline bg-page/60 px-3 py-2">
                      <summary className="focus-ring flex min-h-tap cursor-pointer select-none items-center gap-1 rounded text-meta font-semibold text-dim">
                        <span aria-hidden>▸</span> Chi tiết kỹ thuật (mã bằng chứng, mã bốc thăm,
                        bốc lại lịch)
                      </summary>
                      <div className="mt-2 space-y-3 pb-1 text-meta leading-snug text-sec">
                        {designHash ? (
                          <div>
                            <p className="text-ink">
                              Mã bằng chứng:{" "}
                              <code className="tnum break-all text-brand-ink">{designHash}</code>
                            </p>
                            <p className="mt-0.5">
                              Dấu kiểm chứng của lịch vừa bốc, chốt <strong>trước</strong> giờ phát
                              sóng: ai cũng có thể sinh lại lịch và đối chiếu mã này — khớp nghĩa là
                              không ai sửa lịch giữa chừng.
                            </p>
                          </div>
                        ) : null}
                        {schedule.seed != null && seedHienThi(schedule.seed) != null ? (
                          <div>
                            <p className="text-ink">
                              Mã bốc thăm (seed):{" "}
                              <span className="tnum text-sec">{seedHienThi(schedule.seed)}</span>
                            </p>
                            <p className="mt-0.5">
                              Con số khởi đầu của lần bốc này — cùng số này và cùng thông số thì
                              sinh lại đúng lịch trên. Khác mã bằng chứng ở chỗ: mã bốc thăm dùng
                              để sinh lại lịch, mã bằng chứng dùng để đối chiếu.
                            </p>
                          </div>
                        ) : schedule.seed != null ? (
                          <div>
                            <p className="text-ink">Mã bốc thăm (seed): máy chủ đã lưu cùng lịch</p>
                            <p className="mt-0.5">
                              Mã này dài hơn mức trình duyệt giữ được chính xác nên trang không in
                              ra — in ra sẽ là một số đã bị làm tròn, không sinh lại được lịch. Để
                              đối chiếu, dùng mã bằng chứng ở trên.
                            </p>
                          </div>
                        ) : null}
                        {schedWarning ? (
                          <div>
                            <p className="text-ink">Lưu ý của máy chủ về độ cân bằng:</p>
                            <p className="mt-0.5">{schedWarning}</p>
                          </div>
                        ) : null}
                        {!live ? (
                          <div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => drawSchedule(true)}
                              disabled={busy}
                            >
                              Bốc lại lịch khác
                            </Button>
                            <p className="mt-1">
                              Mỗi lần bốc lại đều được lưu vết kèm mã bằng chứng của lần đó — lịch
                              cũ không bị xoá khỏi nhật ký, nên bốc lại không che được lần bốc
                              trước.
                            </p>
                          </div>
                        ) : null}
                      </div>
                    </details>
                  </div>
                )}

                <WhyStep>
                  Nếu hệ thống được ghim lúc nào tuỳ thích, không ai phân biệt được “nhờ hệ thống”
                  hay “nhờ may”. Bốc thăm sẵn từng khối rồi niêm phong bằng mã bằng chứng nghĩa là
                  lịch không đổi được sau khi thấy số liệu — kết quả so BẬT/TẮT vì thế mới đáng
                  tin.
                </WhyStep>

                <div className="mt-4 flex items-center justify-between gap-3 border-t border-hairline pt-4">
                  <Button variant="ghost" onClick={() => goStep(2)} disabled={busy}>
                    ← Quay lại
                  </Button>
                  <Button onClick={() => goStep(4)} disabled={!schedule || busy}>
                    Xong, sang bước 4 →
                  </Button>
                </div>
              </Card>
            ) : null}

            {/* ============================= BƯỚC 4 ============================= */}
            {step === 4 ? (
              <Card as="section" padding="lg">
                <h2 className="text-title text-ink">
                  {live ? "Đang phát sóng" : "Trước giờ lên sóng"}
                </h2>
                <p className="mt-1 text-body leading-snug text-sec">
                  {live
                    ? "Phiên đã lên sóng — chỗ làm việc bây giờ là bàn trợ live."
                    : "Soát nhanh checklist rồi bấm một nút — hệ thống lo phần còn lại."}
                </p>

                <ul className="mt-4">
                  {/* 1. Lịch */}
                  <CheckRow
                    state={schedule ? "ok" : "warn"}
                    title={
                      schedule ? (
                        <>
                          Lịch BẬT/TẮT đã bốc và niêm phong:{" "}
                          <span className="tnum">{measBlocks}</span> khối
                        </>
                      ) : (
                        "Chưa có lịch BẬT/TẮT — quay lại bước 3 để bốc thăm"
                      )
                    }
                  />

                  {/* 2. Link đo — MỘT chỗ duy nhất nói về link (gói H2). */}
                  <CheckRow
                    state={
                      links.length === 0
                        ? linksBusy
                          ? "todo"
                          : "warn"
                        : linkLechDich > 0
                          ? "warn"
                          : linkXong
                            ? "ok"
                            : "todo"
                    }
                    title={
                      links.length === 0
                        ? linksBusy
                          ? "Link đo: đang tạo link cho phiên này…"
                          : "Link đo: chưa có link nào cho phiên này"
                        : `Link đo (${links.length}) — chép rồi dán vào bình luận ghim khi giới thiệu sản phẩm`
                    }
                  >
                    {missingLinkProducts.length > 0 ? (
                      <p className="mt-0.5 text-meta leading-snug text-sec">
                        <span className="tnum">{missingLinkProducts.length}</span>/
                        <span className="tnum">{products.length}</span> sản phẩm chưa có link trang
                        sản phẩm nên không đo được lượt bấm (
                        {missingLinkProducts.map((p) => p.name).join(", ")}) —{" "}
                        <button
                          type="button"
                          onClick={() => goStep(1)}
                          className="focus-ring rounded text-brand-ink underline underline-offset-2"
                        >
                          bổ sung ở bước 1
                        </button>
                        .
                      </p>
                    ) : null}
                    {linkFailed > 0 ? (
                      <p className="mt-0.5 text-meta leading-snug text-warn-ink">
                        Máy chủ không tạo được link đo cho <span className="tnum">{linkFailed}</span>{" "}
                        sản phẩm — tải lại trang để thử lại.
                      </p>
                    ) : null}
                    {vuotGioiHan > 0 ? (
                      <p className="mt-0.5 text-meta leading-snug text-sec">
                        Mỗi phiên tối đa {MAX_LINKS} link đo —{" "}
                        <span className="tnum">{vuotGioiHan}</span> sản phẩm còn lại chưa có link
                        đo.
                      </p>
                    ) : null}
                    {linkThay > 0 ? (
                      <p className="mt-0.5 text-meta leading-snug text-warn-ink">
                        <span aria-hidden>↻</span> Link trang sản phẩm đã khác nơi link đo cũ dẫn
                        tới, nên đã tạo link đo mới cho <span className="tnum">{linkThay}</span>{" "}
                        sản phẩm. Link đo cũ vẫn dẫn tới địa chỉ cũ — nếu đã dán link cũ vào bình
                        luận ghim, hãy thay bằng link mới trong danh sách dưới.
                      </p>
                    ) : null}
                    {linkLechDich > 0 ? (
                      <p className="mt-0.5 text-meta leading-snug text-warn-ink">
                        <span aria-hidden>⚠</span> <span className="tnum">{linkLechDich}</span> link
                        đo vẫn dẫn tới địa chỉ cũ, khác link trang sản phẩm hiện tại — đừng dán
                        link đó vào bình luận ghim.
                      </p>
                    ) : null}
                    {linkMauDangDung > 0 ? (
                      <p className="mt-0.5 text-meta leading-snug text-warn-ink">
                        <span aria-hidden>◐</span> <span className="tnum">{linkMauDangDung}</span>{" "}
                        link đo đang dẫn tới link mẫu (example.com) — khách bấm sẽ tới trang ví dụ,
                        chỉ dùng để chạy thử.
                      </p>
                    ) : null}
                    {links.length > 0 ? (
                      <>
                        <ul className="mt-1.5 space-y-1 text-meta text-sec">
                          {links.map((l) => (
                            <li key={l.code} className="flex flex-wrap items-center gap-2">
                              <span className="tnum min-w-0">
                                {tenSanPham(l.product_id)}:{" "}
                                <code className="break-all text-ink">
                                  {PUBLIC_API_BASE}/r/{l.code}
                                </code>
                              </span>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => void copyLink(l.code)}
                                title="Chép link vào bộ nhớ tạm"
                              >
                                {copiedCode === l.code ? "Đã chép ✓" : "Chép link"}
                              </Button>
                            </li>
                          ))}
                        </ul>
                        {PUBLIC_API_BASE.includes("localhost") ||
                        PUBLIC_API_BASE.includes("127.0.0.1") ? (
                          <p className="mt-1.5 text-meta leading-snug text-warn-ink">
                            Link đang trỏ về máy này — chỉ mở được trên máy này. Muốn khách xem bấm
                            được từ điện thoại của họ, cần một địa chỉ công khai (nhờ người kỹ thuật
                            của nhóm, xem hướng dẫn mục 8).
                          </p>
                        ) : null}
                        <label className="mt-2 flex min-h-tap cursor-pointer items-center gap-2 text-body text-sec">
                          <input
                            type="checkbox"
                            className="focus-ring h-4 w-4 shrink-0 accent-brand"
                            checked={daDanLink}
                            onChange={(e) => {
                              setDaDanLink(e.target.checked);
                              if (e.target.checked) setLinkThay(0);
                            }}
                          />
                          Tôi đã dán (hoặc sẽ dán ngay khi lên sóng) link đo vào bình luận ghim
                        </label>
                      </>
                    ) : null}
                  </CheckRow>

                  {/* 3. Nguồn bình luận — bật Bộ thu bình luận ngay tại đây. */}
                  <CheckRow state={dongNguon.state} title={dongNguon.title}>
                    <p className="mt-0.5 text-meta leading-snug text-sec">
                      Dán link buổi live để Bộ thu bình luận đọc bình luận (và số người xem, nếu
                      nền tảng cho đọc). Bật trước giờ phát cũng được — bộ thu sẽ chờ buổi live bắt
                      đầu.
                    </p>
                    {session ? (
                      <IngestPanel
                        sessionId={session.session_id}
                        sessionPlatform={session.platform}
                        sessionStatus={session.status}
                        allowSimulated={choPhepMoPhong(session)}
                        hideTitle
                        className="mt-2"
                      />
                    ) : null}
                  </CheckRow>

                  {/* 4. Màn người dẫn — mở ĐÚNG phiên này. */}
                  <CheckRow
                    state={daMoHost ? "ok" : "todo"}
                    title="Màn hình người dẫn đã mở trên màn phụ/TV"
                  >
                    <p className="mt-0.5 text-meta leading-snug text-sec">
                      {CAU_MOT_DONG.manNguoiDan}
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <Link
                        href={hostHref}
                        target="_blank"
                        onClick={() => setDaMoHostFor(session?.session_id ?? null)}
                        className={buttonCls("ghost", "sm")}
                      >
                        Mở màn hình người dẫn ↗
                      </Link>
                      <span className="text-meta text-dim">
                        kéo cửa sổ sang màn phụ/TV, bấm F11 để toàn màn hình
                      </span>
                    </div>
                  </CheckRow>

                  {/* 5. Dữ liệu sẽ ghi lại — lời thường, không lặp các dòng trên. */}
                  <CheckRow
                    state={
                      signalsErr
                        ? "warn"
                        : live && tinHieuHienThi.some((s) => s.status !== "ok")
                          ? "warn"
                          : "info"
                    }
                    title="Dữ liệu hệ thống sẽ ghi lại"
                  >
                    {signalsErr ? (
                      <p className="mt-0.5 text-meta leading-snug text-sec">
                        Chưa đọc được tình trạng dữ liệu từ máy chủ — thử tải lại trang.
                      </p>
                    ) : signals == null ? (
                      <p className="mt-0.5 text-meta text-dim">Đang hỏi máy chủ…</p>
                    ) : (
                      <>
                        <ul className="mt-1.5 space-y-1">
                          {tinHieuHienThi.map((s) => (
                            <li key={s.name} className="flex gap-2 text-meta leading-snug">
                              <span
                                aria-hidden
                                className={cx(
                                  "w-4 shrink-0 text-center font-bold",
                                  s.status === "ok"
                                    ? "text-good-ink"
                                    : s.status === "degraded"
                                      ? "text-warn-ink"
                                      : "text-dim",
                                )}
                              >
                                {s.status === "ok" ? "✓" : s.status === "degraded" ? "⚠" : "○"}
                              </span>
                              <span className="text-sec">
                                <span className="font-semibold text-ink">
                                  {TIN_HIEU_THUONG[s.name]?.ten ?? s.name}
                                </span>
                                <span className="sr-only">
                                  {s.status === "ok"
                                    ? " (có)"
                                    : s.status === "degraded"
                                      ? " (thiếu một phần)"
                                      : " (THIẾU)"}
                                </span>{" "}
                                — {lyDoThuong(s)}
                              </span>
                            </li>
                          ))}
                        </ul>
                        {!live ? (
                          <p className="mt-1.5 text-meta leading-snug text-dim">
                            Trước giờ phát, các dữ liệu này chưa có là bình thường — chúng bắt đầu
                            được ghi khi buổi live lên sóng. Dòng nào ghi THIẾU là tình trạng thật
                            lúc này, không phải lỗi của bạn.
                          </p>
                        ) : null}
                      </>
                    )}
                  </CheckRow>
                </ul>

                {live ? (
                  <div className="mt-4 flex flex-wrap gap-2 border-t border-hairline pt-4">
                    <Link
                      href={
                        session
                          ? `/desk?session=${encodeURIComponent(session.session_id)}`
                          : "/desk"
                      }
                      className={buttonCls("primary")}
                    >
                      Mở bàn trợ live →
                    </Link>
                    <Link
                      href={hostHref}
                      target="_blank"
                      className={buttonCls("ghost")}
                      onClick={() => setDaMoHostFor(session?.session_id ?? null)}
                    >
                      Mở màn hình người dẫn ↗
                    </Link>
                  </div>
                ) : (
                  <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-hairline pt-4">
                    <Button variant="ghost" onClick={() => goStep(3)} disabled={busy}>
                      ← Quay lại
                    </Button>
                    <div className="flex flex-wrap items-center justify-end gap-3">
                      {/* Không chặn bấm — chỉ nói thật còn bao nhiêu việc. */}
                      <p className="text-meta text-sec" aria-live="polite">
                        {viecChuaXong > 0 ? (
                          <>
                            <span aria-hidden className="text-dim">
                              ○
                            </span>{" "}
                            Còn <span className="tnum font-semibold text-ink">{viecChuaXong}</span>{" "}
                            việc chưa xong
                          </>
                        ) : (
                          <>
                            <span aria-hidden className="text-good-ink">
                              ✓
                            </span>{" "}
                            Đã soát xong checklist
                          </>
                        )}
                      </p>
                      <Button onClick={goLive} disabled={busy || !session || !schedule}>
                        <span aria-hidden>▶</span> Bắt đầu phát sóng
                      </Button>
                    </div>
                  </div>
                )}

                <WhyStep>
                  Checklist là 60 giây rẻ nhất của cả buổi: link đo chưa dán nghĩa là không có số
                  lượt nhấp; bộ thu bình luận chưa bật nghĩa là không đọc được người xem nói gì; màn
                  hình người dẫn chưa mở nghĩa là người dẫn không thấy sản phẩm cần giới thiệu. Bấm
                  “Bắt đầu phát sóng” xong, trang sẽ tự đưa bạn sang bàn trợ live đúng phiên này;
                  kết thúc phiên ở đó là báo cáo tự có, không phải chạy thêm gì.
                </WhyStep>
              </Card>
            ) : null}
          </>
        )}
      </main>
    </div>
  );
}
