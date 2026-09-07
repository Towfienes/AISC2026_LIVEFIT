"use client";

/**
 * "/chay-phien" — run a real experiment session without touching a terminal.
 *
 * Until now the whole lifecycle (product -> session -> schedule -> start ->
 * end) was curl-only. That is workable for the team's own Live Lab, where an
 * engineer sits at the desk, and impossible for a seller.
 *
 * The screen is a linear stepper because the ORDER IS THE SCIENCE, not a UI
 * preference: the randomization schedule must be drawn and persisted BEFORE
 * the broadcast starts. The API enforces this with a 409; the UI makes it
 * obvious — a vertical rail connects the steps, done steps get a green check,
 * the active step a blue ring — so nobody learns the rule by hitting an error.
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import TopNav from "@/components/TopNav";
import Button, { buttonCls } from "@/components/ui/Button";
import Callout from "@/components/ui/Callout";
import Card from "@/components/ui/Card";
import { cx } from "@/components/ui/cx";
import { fieldCls } from "@/components/ui/field";
import Skeleton from "@/components/ui/Skeleton";
import {
  createProduct,
  createSchedule,
  createSession,
  createShortlink,
  endSession,
  listProducts,
  listSessions,
  PUBLIC_API_BASE,
  startSession,
} from "@/lib/api";
import { fmtVnd } from "@/lib/format";
import type { BlockInfo, Product, SessionSummary } from "@/lib/types";

type Step = 1 | 2 | 3 | 4;
type StepState = "done" | "active" | "upcoming";

const PLATFORMS = [
  { value: "youtube", label: "YouTube Live" },
  { value: "facebook", label: "Facebook Live" },
] as const;

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

/**
 * One stepper row: state circle + vertical rail on the left, card on the
 * right. done = green check · active = blue ring · upcoming = muted.
 */
function StepItem({
  n,
  state,
  last,
  title,
  hint,
  children,
}: {
  n: number;
  state: StepState;
  last?: boolean;
  title: string;
  hint: string;
  children?: React.ReactNode;
}) {
  return (
    <li className="flex gap-4">
      {/* rail */}
      <div className="flex w-7 shrink-0 flex-col items-center">
        <div
          aria-hidden
          className={cx(
            "mt-3 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold transition-colors duration-150",
            state === "done" && "bg-good text-page",
            state === "active" && "border border-s1 bg-s1/15 text-s1 ring-2 ring-s1/30",
            state === "upcoming" && "border border-hairline bg-raised text-mut",
          )}
        >
          {state === "done" ? <CheckIcon /> : n}
        </div>
        {!last && (
          <div
            aria-hidden
            className={cx("my-1.5 w-px flex-1", state === "done" ? "bg-good/40" : "bg-white/10")}
          />
        )}
      </div>

      {/* card */}
      <Card
        as="section"
        className={cx(
          "mb-4 min-w-0 flex-1 transition-colors duration-150",
          state === "active" && "border-s1/40",
          state === "upcoming" && "opacity-70",
        )}
      >
        <h2
          className={cx(
            "text-sm font-semibold",
            state === "upcoming" ? "text-mut" : "text-ink",
          )}
        >
          {title}
        </h2>
        <p className="mt-0.5 text-xs leading-snug text-sec">{hint}</p>
        {children}
      </Card>
    </li>
  );
}

const inputCls = `${fieldCls} w-full px-2.5 py-1.5 text-sm`;

/**
 * Only an absolute http(s) URL is a usable product link: the /r/{code}
 * shortlink 302s a VIEWER's browser there, so a relative path, a bare domain
 * without scheme, or a typo would break the measured click at the worst
 * possible moment (mid-broadcast).
 */
function isValidProductUrl(value: string): boolean {
  try {
    const u = new URL(value);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

export default function ChayPhienPage() {
  const [step, setStep] = useState<Step>(1);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [products, setProducts] = useState<Product[]>([]);
  const [productsLoading, setProductsLoading] = useState(true);
  const [newProduct, setNewProduct] = useState({
    product_id: "",
    name: "",
    cost: "",
    price: "",
    stock: "",
  });

  const [session, setSession] = useState<SessionSummary | null>(null);
  const [form, setForm] = useState({
    title: "",
    platform: "youtube" as string,
    minutes: "60",
    mode: "auto" as "auto" | "suggest",
  });

  const [blockMin, setBlockMin] = useState("5");
  const [seed, setSeed] = useState("");
  const [schedule, setSchedule] = useState<{
    seed: number;
    n_on: number;
    n_off: number;
    n_redraws: number;
    blocks: BlockInfo[];
  } | null>(null);
  /** ScheduleOut.warning — the API's honest note when the drawn layout could
   * not meet the balance guarantee. Scientifically meaningful: show it. */
  const [schedWarning, setSchedWarning] = useState<string | null>(null);

  const [links, setLinks] = useState<{ code: string; product_id: string }[]>([]);
  /** URL trang sản phẩm thật, nhập ở bước 1 — đích của link đo /r/{code}. */
  const [productUrls, setProductUrls] = useState<Record<string, string>>({});
  /** Ghi chú sau khi lên sóng: bao nhiêu link đo được tạo / bị bỏ qua. */
  const [linkNote, setLinkNote] = useState<string | null>(null);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const copyLink = async (code: string) => {
    try {
      await navigator.clipboard.writeText(`${PUBLIC_API_BASE}/r/${code}`);
      setCopiedCode(code);
      setTimeout(() => setCopiedCode((c) => (c === code ? null : c)), 2000);
    } catch {
      setErr("Không chép được link — trình duyệt chặn quyền bộ nhớ tạm, hãy chọn và chép thủ công.");
    }
  };

  const refreshProducts = useCallback(async () => {
    try {
      setProducts(await listProducts());
    } catch {
      setErr("Không kết nối được máy chủ. Chạy: docker compose up -d");
    } finally {
      setProductsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshProducts();
  }, [refreshProducts]);

  const run = useCallback(async (fn: () => Promise<void>) => {
    setBusy(true);
    setErr(null);
    try {
      await fn();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Có lỗi xảy ra — thử lại.");
    } finally {
      setBusy(false);
    }
  }, []);

  const addProduct = () =>
    run(async () => {
      await createProduct({
        product_id: newProduct.product_id.trim(),
        name: newProduct.name.trim(),
        cost: Number(newProduct.cost) || 0,
        price: Number(newProduct.price) || 0,
        stock: Number(newProduct.stock) || 0,
      });
      setNewProduct({ product_id: "", name: "", cost: "", price: "", stock: "" });
      await refreshProducts();
    });

  const makeSession = () =>
    run(async () => {
      const s = await createSession({
        platform: form.platform,
        title: form.title.trim() || undefined,
        mode: form.mode,
        planned_duration_min: Number(form.minutes) || 60,
      });
      setSession(s);
      setStep(3);
    });

  const drawSchedule = () =>
    run(async () => {
      if (!session) return;
      const res = await createSchedule(session.session_id, {
        block_min: Number(blockMin) || 5,
        washout_min: 0,
        jitter_s: 30,
        seed: seed.trim() ? Number(seed) : undefined,
      });
      setSchedule(res);
      // The API's ScheduleOut carries an optional Vietnamese `warning` when the
      // layout cannot meet the design's balance guarantee. api.ts types stay
      // untouched (contract-guarded), so read it defensively here.
      setSchedWarning((res as { warning?: string | null }).warning ?? null);
    });

  const goLive = () =>
    run(async () => {
      if (!session) return;
      const s = await startSession(session.session_id);
      setSession(s);
      // Chỉ tạo link đo cho sản phẩm đã có URL thật hợp lệ (nhập ở bước 1):
      // một link trỏ về đích giả sẽ làm hỏng đúng khoảnh khắc người xem bấm.
      const withUrl = products
        .map((p) => ({ product_id: p.product_id, url: (productUrls[p.product_id] ?? "").trim() }))
        .filter((x) => isValidProductUrl(x.url))
        .slice(0, 5);
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
          // one bad link must not block going live
        }
      }
      setLinks(created);
      const skipped = products.length - created.length;
      setLinkNote(
        created.length === 0
          ? "Chưa tạo được link đo nào — bạn chưa nhập link trang sản phẩm hợp lệ ở bước 1. " +
              "Phiên vẫn chạy nhưng sẽ không đo được lượt nhấp (biến kết quả chính)."
          : skipped > 0
            ? `Đã tạo ${created.length} link đo; ${skipped} sản phẩm bị bỏ qua vì thiếu link trang sản phẩm hợp lệ.`
            : null,
      );
      setStep(4);
    });

  const finish = () =>
    run(async () => {
      if (!session) return;
      setSession(await endSession(session.session_id));
      await listSessions().catch(() => []);
    });

  const canAddProduct =
    newProduct.product_id.trim() !== "" && newProduct.name.trim() !== "" && !busy;
  const ended = session?.status === "ended";
  const live = session?.status === "live";

  const stateOf = (n: Step, done: boolean): StepState =>
    done ? "done" : step === n ? "active" : "upcoming";

  return (
    <div className="flex min-h-screen flex-col bg-page">
      <TopNav />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-8">
        <header className="mb-6">
          <h1 className="text-xl font-bold tracking-tight text-ink">
            Chạy một phiên thí nghiệm
          </h1>
          <p className="mt-1 text-sm leading-relaxed text-sec">
            Bốn bước, làm theo đúng thứ tự. Thứ tự này là{" "}
            <strong className="text-ink">yêu cầu khoa học</strong>, không phải thói quen giao
            diện: lịch bốc thăm BẬT/TẮT phải được sinh và lưu{" "}
            <strong className="text-ink">trước khi lên sóng</strong> — đó là điều khiến kết quả
            kiểm chứng được.
          </p>
        </header>

        {err ? (
          <Callout tone="critical" className="mb-4">
            {err}
          </Callout>
        ) : null}

        <ol>
          {/* ---- Step 1: products ---------------------------------------- */}
          <StepItem
            n={1}
            state={stateOf(1, products.length > 0)}
            title="Danh mục sản phẩm"
            hint="Hệ thống cần biết bán gì để đề xuất ghim sản phẩm và đo lượt nhấp. Nhập thêm link trang sản phẩm thật — link đo dán vào bình luận ghim sẽ chuyển hướng người xem tới đó."
          >
            <div className="mt-3">
              {productsLoading ? (
                <div className="mb-3 space-y-1.5" aria-busy>
                  <Skeleton className="h-5 w-full" />
                  <Skeleton className="h-5 w-5/6" />
                  <Skeleton className="h-5 w-2/3" />
                </div>
              ) : products.length > 0 ? (
                <ul className="mb-3 space-y-2 text-[13px]">
                  {products.map((p) => {
                    const url = productUrls[p.product_id] ?? "";
                    const invalid = url.trim() !== "" && !isValidProductUrl(url.trim());
                    return (
                      <li
                        key={p.product_id}
                        className="rounded px-1 py-1 text-sec transition-colors duration-150 hover:bg-raised"
                      >
                        <div className="flex justify-between gap-3">
                          <span className="truncate text-ink">{p.name}</span>
                          <span className="tnum shrink-0">{fmtVnd(p.price)}</span>
                        </div>
                        <input
                          className={`${inputCls} mt-1 text-xs ${invalid ? "border-critical/60" : ""}`}
                          type="url"
                          inputMode="url"
                          placeholder="Link trang sản phẩm thật (vd https://shop.cua-ban.vn/ao-thun)"
                          value={url}
                          aria-invalid={invalid}
                          aria-label={`Link trang sản phẩm cho ${p.name}`}
                          onChange={(e) =>
                            setProductUrls((prev) => ({
                              ...prev,
                              [p.product_id]: e.target.value,
                            }))
                          }
                        />
                        {invalid ? (
                          <p className="mt-0.5 text-[11px] text-critical">
                            Link không hợp lệ — cần URL đầy đủ bắt đầu bằng http:// hoặc
                            https://.
                          </p>
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="mb-3 text-[13px] text-mut">Chưa có sản phẩm nào.</p>
              )}
              <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
                <input
                  className={inputCls}
                  placeholder="Mã SP"
                  value={newProduct.product_id}
                  onChange={(e) => setNewProduct({ ...newProduct, product_id: e.target.value })}
                />
                <input
                  className={inputCls}
                  placeholder="Tên"
                  value={newProduct.name}
                  onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })}
                />
                <input
                  className={inputCls}
                  placeholder="Giá vốn"
                  inputMode="numeric"
                  value={newProduct.cost}
                  onChange={(e) => setNewProduct({ ...newProduct, cost: e.target.value })}
                />
                <input
                  className={inputCls}
                  placeholder="Giá bán"
                  inputMode="numeric"
                  value={newProduct.price}
                  onChange={(e) => setNewProduct({ ...newProduct, price: e.target.value })}
                />
                <input
                  className={inputCls}
                  placeholder="Tồn kho"
                  inputMode="numeric"
                  value={newProduct.stock}
                  onChange={(e) => setNewProduct({ ...newProduct, stock: e.target.value })}
                />
              </div>
              <div className="mt-2 flex gap-2">
                <Button onClick={addProduct} disabled={!canAddProduct} className="px-3 py-1.5">
                  Thêm sản phẩm
                </Button>
                {products.length > 0 && step === 1 ? (
                  <Button variant="ghost" onClick={() => setStep(2)} className="px-3 py-1.5">
                    Xong, sang bước 2
                  </Button>
                ) : null}
              </div>
            </div>
          </StepItem>

          {/* ---- Step 2: session ------------------------------------------ */}
          <StepItem
            n={2}
            state={stateOf(2, session != null)}
            title="Tạo phiên live"
            hint="Chế độ Tự động dành cho phòng live của nhóm (tuân thủ cao). Chế độ Đề xuất dành cho phòng đối tác — họ có nút bỏ qua."
          >
            {step >= 2 && !session ? (
              <div className="mt-3 space-y-2">
                <input
                  className={inputCls}
                  placeholder="Tên phiên (tuỳ chọn)"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                />
                <div className="grid grid-cols-3 gap-2">
                  <select
                    className={inputCls}
                    value={form.platform}
                    onChange={(e) => setForm({ ...form, platform: e.target.value })}
                  >
                    {PLATFORMS.map((p) => (
                      <option key={p.value} value={p.value}>
                        {p.label}
                      </option>
                    ))}
                  </select>
                  <select
                    className={inputCls}
                    value={form.mode}
                    onChange={(e) =>
                      setForm({ ...form, mode: e.target.value as "auto" | "suggest" })
                    }
                  >
                    <option value="auto">Tự động</option>
                    <option value="suggest">Đề xuất</option>
                  </select>
                  <input
                    className={inputCls}
                    inputMode="numeric"
                    value={form.minutes}
                    onChange={(e) => setForm({ ...form, minutes: e.target.value })}
                    placeholder="Số phút"
                  />
                </div>
                <Button onClick={makeSession} disabled={busy} className="px-3 py-1.5">
                  Tạo phiên
                </Button>
              </div>
            ) : null}
            {session ? (
              <p className="mt-2 text-[13px] text-sec">
                {session.title || "Phiên chưa đặt tên"} · {session.planned_duration_min} phút ·{" "}
                <span className="text-ink">{session.status}</span>
              </p>
            ) : null}
          </StepItem>

          {/* ---- Step 3: schedule ----------------------------------------- */}
          <StepItem
            n={3}
            state={stateOf(3, schedule != null)}
            title="Bốc thăm lịch BẬT/TẮT — TRƯỚC khi lên sóng"
            hint="Chia phiên thành các khối, mỗi khối bốc thăm 50/50. Lịch được lưu lại làm dấu vết kiểm chứng: giám khảo có thể đối chiếu để thấy không ai sửa giữa chừng."
          >
            {session && step >= 3 ? (
              <div className="mt-3">
                {!schedule ? (
                  <>
                    <div className="grid grid-cols-2 gap-2 md:w-2/3">
                      <label className="text-xs text-sec">
                        Độ dài khối (phút)
                        <input
                          className={`${inputCls} mt-1`}
                          inputMode="numeric"
                          value={blockMin}
                          onChange={(e) => setBlockMin(e.target.value)}
                        />
                      </label>
                      <label className="text-xs text-sec">
                        Seed (để trống = ngẫu nhiên)
                        <input
                          className={`${inputCls} mt-1`}
                          inputMode="numeric"
                          value={seed}
                          onChange={(e) => setSeed(e.target.value)}
                          placeholder="vd 42"
                        />
                      </label>
                    </div>
                    <Button onClick={drawSchedule} disabled={busy} className="mt-2 px-3 py-1.5">
                      Bốc thăm lịch
                    </Button>
                  </>
                ) : (
                  <>
                    <div className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-sec">
                      <span>
                        <span className="tnum text-ink">{schedule.blocks.length}</span> khối
                      </span>
                      <span>
                        BẬT <span className="tnum text-ink">{schedule.n_on}</span> / TẮT{" "}
                        <span className="tnum text-ink">{schedule.n_off}</span>
                      </span>
                      <span>
                        seed <span className="tnum text-ink">{schedule.seed}</span>
                      </span>
                    </div>
                    <div className="flex h-6 overflow-hidden rounded border border-hairline">
                      {schedule.blocks
                        .filter((b) => !b.is_washout)
                        .map((b, i) => (
                          <div
                            key={i}
                            title={`Khối ${i + 1}: ${b.assignment}`}
                            className={`flex-1 ${b.assignment === "ON" ? "bg-s7" : "bg-axis"}`}
                          />
                        ))}
                    </div>
                    <p className="mt-1 text-[11px] text-mut">
                      Tím = BẬT (hệ thống điều khiển) · Xám = TẮT (làm như thường lệ). Ghi lại
                      seed <strong className="text-sec">{schedule.seed}</strong> — sinh lại cùng
                      seed cho ra đúng lịch này.
                    </p>
                    {schedWarning ? (
                      <Callout tone="warn" className="mt-2">
                        <strong>Lưu ý về lịch vừa bốc:</strong> {schedWarning}
                      </Callout>
                    ) : null}
                    {!live && !ended ? (
                      <Button onClick={goLive} disabled={busy} className="mt-3 px-3 py-1.5">
                        Bắt đầu phát sóng
                      </Button>
                    ) : null}
                  </>
                )}
              </div>
            ) : null}
          </StepItem>

          {/* ---- Step 4: live --------------------------------------------- */}
          <StepItem
            n={4}
            state={stateOf(4, ended)}
            last
            title="Đang phát — mở bàn điều khiển"
            hint="Mở màn hình host trên máy của người dẫn (màn hình đó cố tình không hiện khối BẬT/TẮT để không ảnh hưởng cách họ nói)."
          >
            {live || ended ? (
              <div className="mt-3 space-y-3">
                <div className="flex flex-wrap gap-2">
                  <Link href="/desk" className={`${buttonCls("primary")} px-3 py-1.5`}>
                    Mở bàn điều khiển
                  </Link>
                  <Link href="/host" className={`${buttonCls("ghost")} px-3 py-1.5`}>
                    Mở màn hình host
                  </Link>
                  {live ? (
                    <Button
                      variant="danger"
                      onClick={finish}
                      disabled={busy}
                      className="px-3 py-1.5"
                    >
                      Kết thúc phiên
                    </Button>
                  ) : null}
                </div>

                {linkNote ? <Callout tone="warn">{linkNote}</Callout> : null}

                {links.length > 0 ? (
                  <div>
                    <p className="text-xs font-semibold text-ink">
                      Link đo lượt nhấp — dán vào bình luận ghim khi giới thiệu sản phẩm
                    </p>
                    <ul className="mt-1 space-y-1 text-xs text-sec">
                      {links.map((l) => (
                        <li key={l.code} className="flex flex-wrap items-center gap-2">
                          <span className="tnum">
                            {l.product_id}:{" "}
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
                    <p className="mt-1 text-[11px] leading-snug text-mut">
                      Mỗi lượt bấm được ghi lại và quy về khối đang chạy — đây chính là biến kết
                      quả chính của thí nghiệm. Người xem phải mở được địa chỉ này từ ngoài: đặt
                      biến <code>NEXT_PUBLIC_PUBLIC_API_BASE</code> thành domain công khai (xem{" "}
                      <code>web/.env.example</code>) nếu link đang trỏ về localhost.
                    </p>
                  </div>
                ) : null}

                {ended ? (
                  <div className="rounded-md border border-hairline bg-page p-3">
                    <p className="text-[13px] text-ink">Phiên đã kết thúc.</p>
                    <p className="mt-1 text-xs leading-snug text-sec">
                      Bước tiếp theo: chấm chất lượng dữ liệu bằng lệnh{" "}
                      <code className="text-ink">
                        livelift-qc --session-id {session?.session_id}
                      </code>{" "}
                      rồi xem{" "}
                      <Link
                        href="/ket-qua"
                        className="focus-ring rounded text-s1 underline underline-offset-2"
                      >
                        Kết quả thí nghiệm
                      </Link>
                      .
                    </p>
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="mt-2 text-[13px] text-mut">
                Hoàn tất bước 3 rồi bấm &ldquo;Bắt đầu phát sóng&rdquo;.
              </p>
            )}
          </StepItem>
        </ol>
      </main>
    </div>
  );
}
