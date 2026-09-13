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
 *   Bước 3  Bốc thăm lịch BẬT/TẮT — một nút to; dải khối trực quan; mã bằng
 *            chứng (design hash) giải thích bằng lời thường; seed nằm sau
 *            "Tuỳ chọn nâng cao".
 *   Bước 4  Lên sóng — checklist trước giờ G (link đo, lịch niêm phong, màn
 *            hình người dẫn, ma trận tín hiệu) rồi MỘT nút Bắt đầu phát sóng,
 *            xong tự chuyển /desk?session=ID.
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
import type { BlockInfo, Product, SessionMode, SessionSummary, SignalCoverage } from "@/lib/types";

// ---------------------------------------------------------------------------
// Kiểu + hằng
// ---------------------------------------------------------------------------

type Step = 1 | 2 | 3 | 4;

/** Khoá localStorage — đổi tên là đổi phiên bản trạng thái (v1). */
const LS_KEY = "ll.chayphien.v1";

/** Tối đa 5 link đo mỗi phiên — đủ cho một buổi live, tránh spam shortlink. */
const MAX_LINKS = 5;

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

/** Trạng thái wizard được lưu để refresh không mất (yêu cầu #3 của gói). */
interface SavedWizard {
  v: 1;
  step: Step;
  productUrls: Record<string, string>;
  form: { title: string; platform: string; minutes: string; mode: SessionMode };
  blockMin: string;
  sessionId: string | null;
  links: { code: string; product_id: string }[];
  daDanLink: boolean;
  daMoHost: boolean;
}

/** Nhãn tiếng người cho ma trận tín hiệu ở checklist bước 4. */
const SIGNAL_LABEL: Record<string, string> = {
  schedule: "Lịch gán khối",
  ticks: "Người xem theo thời gian",
  comments: "Bình luận",
  clicks: "Lượt nhấp link đo",
  orders: "Đơn hàng",
  reactions: "Tim & quà tặng",
};

const inputCls = `${fieldCls} w-full px-2.5 py-1.5 text-body`;

// ---------------------------------------------------------------------------
// Helpers thuần
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

/** Một dòng checklist bước 4: dấu trạng thái + nội dung. */
function CheckRow({
  state,
  title,
  children,
}: {
  state: "ok" | "warn" | "todo";
  title: React.ReactNode;
  children?: React.ReactNode;
}) {
  const glyph = state === "ok" ? "✓" : state === "warn" ? "⚠" : "○";
  const cls =
    state === "ok" ? "text-good-ink" : state === "warn" ? "text-warn-ink" : "text-dim";
  const srText = state === "ok" ? "đã sẵn sàng" : state === "warn" ? "cần chú ý" : "chưa làm";
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
  const [links, setLinks] = useState<{ code: string; product_id: string }[]>([]);
  const [linkNote, setLinkNote] = useState<string | null>(null);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [daDanLink, setDaDanLink] = useState(false);
  const [daMoHost, setDaMoHost] = useState(false);
  const [signals, setSignals] = useState<SignalCoverage | null>(null);
  const [signalsErr, setSignalsErr] = useState(false);
  const linksEnsured = useRef(false);

  const live = session?.status === "live";

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

    if (saved) {
      setProductUrls(saved.productUrls ?? {});
      if (saved.form) setForm(saved.form);
      if (saved.blockMin) setBlockMin(saved.blockMin);
      setLinks(saved.links ?? []);
      setDaDanLink(Boolean(saved.daDanLink));
      setDaMoHost(Boolean(saved.daMoHost));
    }

    const sid = urlSession ?? saved?.sessionId ?? null;
    const wantStep = (
      urlStep >= 1 && urlStep <= 4 ? urlStep : (saved?.step ?? 1)
    ) as Step;

    const clearSessionBits = () => {
      setSession(null);
      setSchedule(null);
      setDesignHash(null);
      setLinks([]);
      setDaDanLink(false);
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
      daMoHost,
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
  }, [hydrated, step, productUrls, form, blockMin, session, links, daDanLink, daMoHost]);

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

  /** Điền sẵn một sản phẩm mẫu để xem thử — vẫn phải bấm "Thêm sản phẩm". */
  const fillSample = () =>
    setNewProduct({
      name: "Áo khoác dù 2 lớp",
      url: "https://shopee.vn/ao-khoac-du-2-lop-mau",
      price: "179000",
      cost: "96000",
      stock: "40",
    });

  const readyLinkCount = products.filter((p) =>
    isValidProductUrl((productUrls[p.product_id] ?? "").trim()),
  ).length;

  // -------------------------------------------------------------------------
  // Bước 2: tạo phiên
  // -------------------------------------------------------------------------
  const makeSession = () =>
    run(async () => {
      const s = await createSession({
        platform: form.platform,
        title: form.title.trim() || undefined,
        mode: form.mode,
        planned_duration_min: Number(form.minutes) || 90,
      });
      setSession(s);
      setStepState(3);
    });

  /** Huỷ phiên nháp để sửa thông tin — backend cố ý không có API sửa phiên. */
  const cancelAndEdit = () =>
    run(async () => {
      if (!session) return;
      await cancelSession(session.session_id);
      setSession(null);
      setSchedule(null);
      setDesignHash(null);
      setSchedWarning(null);
      setLinks([]);
      setDaDanLink(false);
      linksEnsured.current = false;
      setStepState(2);
    });

  // -------------------------------------------------------------------------
  // Bước 3: bốc thăm lịch
  // -------------------------------------------------------------------------
  const drawSchedule = () =>
    run(async () => {
      if (!session) return;
      const res = await createSchedule(session.session_id, {
        block_min: Number(blockMin) || 5,
        washout_min: 0,
        jitter_s: 30,
        seed: seed.trim() ? Number(seed) : undefined,
      });
      setSchedule({ blocks: res.blocks, nOn: res.n_on, nOff: res.n_off, seed: res.seed });
      setDesignHash(res.design_hash);
      setSchedWarning(res.warning ?? null);
      setSession((s) => (s ? { ...s, status: "scheduled" } : s));
    });

  // -------------------------------------------------------------------------
  // Bước 4: link đo + ma trận tín hiệu + lên sóng
  // -------------------------------------------------------------------------

  /** Tạo link đo cho các sản phẩm đã có URL hợp lệ — chưa có thì thôi, không chặn. */
  const ensureLinks = useCallback(async () => {
    if (!session) return;
    const have = new Set(links.map((l) => l.product_id));
    const withUrl = products
      .map((p) => ({ product_id: p.product_id, url: (productUrls[p.product_id] ?? "").trim() }))
      .filter((x) => isValidProductUrl(x.url) && !have.has(x.product_id))
      .slice(0, Math.max(0, MAX_LINKS - links.length));
    const created: { code: string; product_id: string }[] = [];
    for (const { product_id, url } of withUrl) {
      try {
        const l = await createShortlink({
          product_id,
          session_id: session.session_id,
          target_url: url,
        });
        created.push({ code: l.code, product_id });
      } catch {
        // một link hỏng không được chặn các link còn lại
      }
    }
    const all = [...links, ...created];
    setLinks(all);
    const skipped = products.length - all.length;
    setLinkNote(
      all.length === 0
        ? "Chưa tạo được link đo nào — chưa sản phẩm nào có link trang sản phẩm hợp lệ ở bước 1. " +
            "Phiên vẫn chạy được nhưng sẽ không đo được lượt nhấp (con số quyết định kết quả)."
        : skipped > 0
          ? `Đã tạo ${all.length} link đo; ${skipped} sản phẩm bị bỏ qua vì thiếu link trang sản phẩm hợp lệ.`
          : null,
    );
  }, [session, links, products, productUrls]);

  useEffect(() => {
    if (step !== 4 || !session) return;
    setSignalsErr(false);
    getSignalCoverage(session.session_id)
      .then(setSignals)
      .catch(() => setSignalsErr(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, session?.session_id]);

  // Tạo link đo khi vào bước 4 — CHỜ danh mục sản phẩm tải xong (refresh
  // thẳng vào bước 4 thì products tới sau), và chỉ chạy một lần mỗi lần mở
  // trang (ref guard; các lần sau link đã lưu trong trạng thái khôi phục).
  useEffect(() => {
    if (step !== 4 || !session || productsLoading) return;
    if (!linksEnsured.current) {
      linksEnsured.current = true;
      void ensureLinks();
    }
    // ensureLinks đổi theo links → ref guard giữ cho hiệu ứng chạy đúng 1 lần.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, session?.session_id, productsLoading]);

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
  /**
   * Độ dài khối đọc từ CHÍNH lịch đã bốc (đúng cả khi khôi phục từ máy chủ).
   * Lấy TRUNG VỊ vì thiết kế cố ý cho khối biên dài hơn (khối 0 là burn-in
   * ~10 phút) và ranh giới có jitter — khối đầu tiên KHÔNG đại diện.
   */
  const blockLens = (schedule?.blocks ?? [])
    .filter((b) => !b.is_washout)
    .map((b) => (b.end_offset_s - b.start_offset_s) / 60)
    .sort((a, b) => a - b);
  const blockLenMin = blockLens.length
    ? Math.max(1, Math.round(blockLens[Math.floor(blockLens.length / 2)]))
    : Number(blockMin) || 5;

  return (
    <div className="flex min-h-screen flex-col bg-page">
      <TopNav />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-8">
        <PageHeader
          phase="truoc"
          title="Chuẩn bị buổi live"
          lead={
            <>
              Bốn bước nhỏ, mỗi lần một việc: khai sản phẩm, tạo phiên, bốc thăm lịch BẬT/TẮT rồi
              lên sóng. Thứ tự là <strong className="text-ink">yêu cầu khoa học</strong> — lịch
              phải bốc và niêm phong <strong className="text-ink">trước</strong> giờ phát, đó là
              điều làm kết quả kiểm chứng được.
            </>
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

                {productsLoading ? (
                  <div className="mt-4 space-y-1.5" aria-busy>
                    <Skeleton className="h-5 w-full" />
                    <Skeleton className="h-5 w-5/6" />
                  </div>
                ) : products.length > 0 ? (
                  <ul className="mt-4 space-y-2">
                    {products.map((p) => {
                      const url = (productUrls[p.product_id] ?? "").trim();
                      const valid = isValidProductUrl(url);
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
                              {valid ? (
                                <span className="rounded-full border border-good/30 bg-good/10 px-2 py-0.5 text-meta font-semibold text-good-ink">
                                  ✓ link đo sẵn sàng
                                </span>
                              ) : (
                                <span className="rounded-full border border-warn/40 bg-warn/10 px-2 py-0.5 text-meta font-semibold text-warn-ink">
                                  ⚠ chưa có link
                                </span>
                              )}
                            </span>
                          </div>
                          <label className="mt-1.5 block">
                            <span className="text-meta text-dim">
                              Link trang sản phẩm thật (Shopee / website của bạn)
                            </span>
                            <input
                              className={`${inputCls} mt-0.5 text-meta ${invalid ? "border-critical/60" : ""}`}
                              type="url"
                              inputMode="url"
                              placeholder="https://shopee.vn/ten-san-pham"
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
                          ) : !valid ? (
                            <p className="mt-0.5 text-meta text-warn-ink">
                              Chưa có link — sản phẩm này sẽ không đo được lượt nhấp.
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
                      placeholder="https://shopee.vn/ao-khoac-du-2-lop"
                      value={newProduct.url}
                      onChange={(e) => setNewProduct({ ...newProduct, url: e.target.value })}
                    />
                  </label>
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
                    {session.planned_duration_min} phút · {session.platform}) đã được tạo. Muốn đổi
                    nền tảng/thời lượng/chế độ thì huỷ phiên nháp này rồi tạo lại — thông số phiên
                    là một phần của thiết kế thí nghiệm nên không sửa tại chỗ được.
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Button variant="ghost" size="sm" onClick={cancelAndEdit} disabled={busy}>
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
                        placeholder="Phiên live tối thứ Bảy"
                        value={form.title}
                        onChange={(e) => setForm({ ...form, title: e.target.value })}
                      />
                    </label>

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
                          {m === "90" ? (
                            <span className="ml-1.5 text-meta font-normal text-good-ink">
                              khuyên dùng
                            </span>
                          ) : null}
                        </button>
                      ))}
                    </div>
                    {minutesNum > 0 && minutesNum < 90 ? (
                      <Callout tone="warn" className="mt-2">
                        Phiên {minutesNum} phút vẫn chạy được, nhưng ít khối hơn nên kết luận sẽ
                        kém chắc — từ 90 phút trở lên mới đủ khối cho kết luận đáng tin. Khi bốc
                        thăm, máy chủ sẽ nói rõ mức đảm bảo thật của lịch.
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
                <p className="mt-1 text-body leading-snug text-sec">{CAU_MOT_DONG.batTat}</p>
                <p className="mt-2 text-body leading-snug text-sec">
                  Bốc <strong className="text-ink">trước</strong> khi lên sóng để không ai sửa
                  được giữa chừng — đây là thứ làm kết quả đáng tin.
                </p>

                {!schedule ? (
                  <>
                    <div className="mt-5 flex justify-center">
                      <Button onClick={drawSchedule} disabled={busy || !session}>
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
                            <Term tip="Số khởi tạo bốc thăm — cùng seed cho ra đúng lịch đó, để kiểm chứng lại.">
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
                  <div className="mt-4">
                    <p className="mb-2 text-body text-sec">
                      <span className="tnum font-semibold text-ink">{measBlocks}</span> khối, phần
                      lớn ~<span className="tnum text-ink">{blockLenMin}</span> phút · BẬT{" "}
                      <span className="tnum font-semibold text-ink">{schedule.nOn}</span> / TẮT{" "}
                      <span className="tnum font-semibold text-ink">{schedule.nOff}</span>
                    </p>
                    <BlockStrip
                      blocks={schedule.blocks}
                      durationS={(session?.planned_duration_min ?? 90) * 60}
                      positionS={null}
                    />
                    {designHash ? (
                      <div className="mt-3 rounded-md border border-hairline bg-page/60 p-3">
                        <p className="text-body text-ink">
                          Mã bằng chứng:{" "}
                          <code className="tnum break-all text-brand-ink" title={designHash}>
                            {designHash.slice(0, 16)}…
                          </code>
                        </p>
                        <p className="mt-1 text-meta leading-snug text-sec">
                          Đây là dấu kiểm chứng của lịch vừa bốc, chốt <strong>trước</strong> giờ
                          phát sóng: ai cũng có thể sinh lại lịch và đối chiếu mã này — khớp nghĩa
                          là không ai sửa lịch giữa chừng.
                        </p>
                        {schedule.seed != null ? (
                          <p className="mt-1 text-meta text-dim">
                            <Term tip="Số khởi tạo bốc thăm — cùng seed cho ra đúng lịch đó, để kiểm chứng lại.">
                              Mã kiểm chứng lịch
                            </Term>
                            : <span className="tnum text-sec">{schedule.seed}</span>
                          </p>
                        ) : null}
                      </div>
                    ) : null}
                    {schedWarning ? (
                      <Callout tone="warn" className="mt-3">
                        <strong>Máy chủ lưu ý về lịch vừa bốc:</strong> {schedWarning}
                      </Callout>
                    ) : null}
                    {!live ? (
                      <div className="mt-3">
                        <Button variant="ghost" size="sm" onClick={drawSchedule} disabled={busy}>
                          Bốc lại lịch khác
                        </Button>
                      </div>
                    ) : null}
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

                {linkNote ? (
                  <Callout tone="warn" className="mt-3">
                    {linkNote}
                  </Callout>
                ) : null}

                <ul className="mt-4">
                  <CheckRow
                    state={
                      readyLinkCount === 0
                        ? "warn"
                        : readyLinkCount < products.length
                          ? "warn"
                          : "ok"
                    }
                    title={
                      <>
                        <span className="tnum">{products.length}</span> sản phẩm,{" "}
                        <span className="tnum">{readyLinkCount}</span> link trang sản phẩm hợp lệ
                      </>
                    }
                  >
                    {readyLinkCount < products.length ? (
                      <p className="mt-0.5 text-meta leading-snug text-sec">
                        Sản phẩm thiếu link sẽ không đo được lượt nhấp —{" "}
                        <button
                          type="button"
                          onClick={() => goStep(1)}
                          className="focus-ring rounded text-brand-ink underline underline-offset-2"
                        >
                          bổ sung ở bước 1
                        </button>{" "}
                        nếu muốn đo đủ.
                      </p>
                    ) : null}
                  </CheckRow>

                  <CheckRow
                    state={schedule ? "ok" : "warn"}
                    title={
                      schedule ? (
                        <>
                          Lịch <span className="tnum">{measBlocks}</span> khối đã bốc và niêm
                          phong
                          {designHash ? (
                            <>
                              {" "}
                              · mã bằng chứng{" "}
                              <code className="tnum text-brand-ink" title={designHash ?? undefined}>
                                {designHash.slice(0, 10)}…
                              </code>
                            </>
                          ) : null}
                        </>
                      ) : (
                        "Chưa có lịch BẬT/TẮT — quay lại bước 3 để bốc thăm"
                      )
                    }
                  />

                  <CheckRow
                    state={links.length === 0 ? "warn" : daDanLink ? "ok" : "todo"}
                    title={
                      links.length === 0
                        ? "Chưa có link đo cho phiên này"
                        : `Link đo (${links.length}) — chép rồi dán vào bình luận ghim khi giới thiệu sản phẩm`
                    }
                  >
                    {links.length > 0 ? (
                      <>
                        <ul className="mt-1.5 space-y-1 text-meta text-sec">
                          {links.map((l) => (
                            <li key={l.code} className="flex flex-wrap items-center gap-2">
                              <span className="tnum min-w-0">
                                {products.find((p) => p.product_id === l.product_id)?.name ??
                                  l.product_id}
                                :{" "}
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
                            Link đang trỏ về localhost — chỉ mở được trên máy này. Muốn khách xem
                            bấm được từ điện thoại của họ, cần một địa chỉ công khai (nhờ người kỹ
                            thuật của nhóm, xem hướng dẫn mục 8).
                          </p>
                        ) : null}
                        <label className="mt-2 flex min-h-tap cursor-pointer items-center gap-2 text-body text-sec">
                          <input
                            type="checkbox"
                            className="focus-ring h-4 w-4 shrink-0 accent-brand"
                            checked={daDanLink}
                            onChange={(e) => setDaDanLink(e.target.checked)}
                          />
                          Tôi đã dán (hoặc sẽ dán ngay khi lên sóng) link đo vào bình luận ghim
                        </label>
                      </>
                    ) : (
                      <p className="mt-0.5 text-meta leading-snug text-sec">
                        Không có link đo thì phiên vẫn chạy, nhưng không có con số lượt nhấp để
                        kết luận.
                      </p>
                    )}
                  </CheckRow>

                  <CheckRow
                    state={daMoHost ? "ok" : "todo"}
                    title="Màn hình người dẫn đã mở trên màn phụ/TV"
                  >
                    <p className="mt-0.5 text-meta leading-snug text-sec">
                      {CAU_MOT_DONG.manNguoiDan}
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <Link
                        href="/host"
                        target="_blank"
                        onClick={() => setDaMoHost(true)}
                        className={buttonCls("ghost", "sm")}
                      >
                        Mở màn hình người dẫn ↗
                      </Link>
                      <span className="text-meta text-dim">
                        kéo cửa sổ sang màn phụ/TV, bấm F11 để toàn màn hình
                      </span>
                    </div>
                  </CheckRow>

                  <CheckRow
                    state={
                      signalsErr
                        ? "warn"
                        : signals == null
                          ? "todo"
                          : signals.signals.some((s) => s.status === "missing")
                            ? "warn"
                            : "ok"
                    }
                    title="Nguồn dữ liệu (ma trận tín hiệu)"
                  >
                    {signalsErr ? (
                      <p className="mt-0.5 text-meta leading-snug text-sec">
                        Chưa đọc được ma trận tín hiệu từ máy chủ — thử tải lại trang.
                      </p>
                    ) : signals == null ? (
                      <p className="mt-0.5 text-meta text-dim">Đang đọc ma trận tín hiệu…</p>
                    ) : (
                      <>
                        <ul className="mt-1.5 space-y-1">
                          {signals.signals.map((s) => (
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
                                  {SIGNAL_LABEL[s.name] ?? s.name}
                                </span>
                                {s.status === "ok" ? null : (
                                  <> — {s.detail}</>
                                )}
                              </span>
                            </li>
                          ))}
                        </ul>
                        {!live ? (
                          <p className="mt-1.5 text-meta leading-snug text-dim">
                            Trước giờ phát, các nguồn “người xem / bình luận / lượt nhấp” chưa
                            chảy là bình thường — chúng bắt đầu được thu khi buổi live lên sóng.
                            Ô nào THIẾU kèm lý do là trạng thái thật lúc này, không phải lỗi của
                            bạn.
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
                      href="/host"
                      target="_blank"
                      className={buttonCls("ghost")}
                      onClick={() => setDaMoHost(true)}
                    >
                      Mở màn hình người dẫn ↗
                    </Link>
                  </div>
                ) : (
                  <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-hairline pt-4">
                    <Button variant="ghost" onClick={() => goStep(3)} disabled={busy}>
                      ← Quay lại
                    </Button>
                    <Button
                      onClick={goLive}
                      disabled={busy || !session || !schedule}
                      className="uppercase tracking-wide"
                    >
                      <span aria-hidden>▶</span> Bắt đầu phát sóng
                    </Button>
                  </div>
                )}

                <WhyStep>
                  Checklist là 60 giây rẻ nhất của cả buổi: link đo chưa dán nghĩa là không có số
                  lượt nhấp; màn hình người dẫn chưa mở nghĩa là người dẫn không thấy sản phẩm cần
                  giới thiệu. Bấm “Bắt đầu phát sóng” xong, trang sẽ tự đưa bạn sang bàn trợ live
                  đúng phiên này; kết thúc phiên ở đó là báo cáo tự có, không phải chạy thêm gì.
                </WhyStep>
              </Card>
            ) : null}
          </>
        )}
      </main>
    </div>
  );
}
