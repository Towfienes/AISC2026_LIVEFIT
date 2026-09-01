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
 * obvious, so nobody learns the rule by hitting an error.
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  createProduct,
  createSchedule,
  createSession,
  createShortlink,
  endSession,
  listProducts,
  listSessions,
  startSession,
} from "@/lib/api";
import { fmtVnd } from "@/lib/format";
import type { BlockInfo, Product, SessionSummary } from "@/lib/types";

type Step = 1 | 2 | 3 | 4;

const PLATFORMS = [
  { value: "youtube", label: "YouTube Live" },
  { value: "facebook", label: "Facebook Live" },
] as const;

function StepHeader({
  n,
  title,
  hint,
  done,
  active,
}: {
  n: number;
  title: string;
  hint: string;
  done: boolean;
  active: boolean;
}) {
  return (
    <div className="flex items-start gap-3">
      <div
        className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
          done ? "bg-good text-page" : active ? "bg-s1 text-page" : "bg-raised text-mut"
        }`}
      >
        {done ? "✓" : n}
      </div>
      <div className="min-w-0">
        <h2 className={`text-sm font-semibold ${active || done ? "text-ink" : "text-mut"}`}>
          {title}
        </h2>
        <p className="mt-0.5 text-[12px] leading-snug text-sec">{hint}</p>
      </div>
    </div>
  );
}

const inputCls =
  "w-full rounded border border-hairline bg-page px-2.5 py-1.5 text-sm text-ink " +
  "placeholder:text-mut focus:border-s1 focus:outline-none";
const btnCls =
  "rounded bg-s1 px-3 py-1.5 text-sm font-semibold text-page transition-opacity " +
  "hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40";
const btnGhost =
  "rounded border border-hairline px-3 py-1.5 text-sm text-sec transition-colors hover:bg-surface";

export default function ChayPhienPage() {
  const [step, setStep] = useState<Step>(1);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [products, setProducts] = useState<Product[]>([]);
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

  const [links, setLinks] = useState<{ code: string; product_id: string }[]>([]);

  const refreshProducts = useCallback(async () => {
    try {
      setProducts(await listProducts());
    } catch {
      setErr("Không kết nối được máy chủ. Chạy: docker compose up -d");
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
    });

  const goLive = () =>
    run(async () => {
      if (!session) return;
      const s = await startSession(session.session_id);
      setSession(s);
      const created: { code: string; product_id: string }[] = [];
      for (const p of products.slice(0, 5)) {
        try {
          const l = await createShortlink({
            product_id: p.product_id,
            session_id: session.session_id,
            target_url: `https://shop.example/${encodeURIComponent(p.product_id)}`,
          });
          created.push({ code: l.code, product_id: p.product_id });
        } catch {
          // one bad link must not block going live
        }
      }
      setLinks(created);
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

  return (
    <main className="mx-auto max-w-3xl px-4 py-6">
      <header className="mb-5">
        <h1 className="text-xl font-bold text-ink">Chạy một phiên thí nghiệm</h1>
        <p className="mt-1 text-sm leading-relaxed text-sec">
          Bốn bước, làm theo đúng thứ tự. Thứ tự này là{" "}
          <strong className="text-ink">yêu cầu khoa học</strong>, không phải thói quen giao diện:
          lịch bốc thăm BẬT/TẮT phải được sinh và lưu <strong className="text-ink">trước khi
          lên sóng</strong> — đó là điều khiến kết quả kiểm chứng được.
        </p>
      </header>

      {err ? (
        <div className="mb-4 rounded-lg border border-critical/40 bg-critical/10 p-3 text-sm text-ink">
          {err}
        </div>
      ) : null}

      <div className="space-y-4">
        {/* ---- Step 1: products ------------------------------------------ */}
        <section className="rounded-lg border border-hairline bg-surface p-4">
          <StepHeader
            n={1}
            title="Danh mục sản phẩm"
            hint="Hệ thống cần biết bán gì để đề xuất ghim sản phẩm và đo lượt nhấp."
            done={products.length > 0}
            active={step === 1}
          />
          <div className="mt-3 pl-9">
            {products.length > 0 ? (
              <ul className="mb-3 space-y-1 text-[13px]">
                {products.map((p) => (
                  <li key={p.product_id} className="flex justify-between gap-3 text-sec">
                    <span className="truncate text-ink">{p.name}</span>
                    <span className="shrink-0 tabular-nums">{fmtVnd(p.price)}</span>
                  </li>
                ))}
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
              <button onClick={addProduct} disabled={!canAddProduct} className={btnCls}>
                Thêm sản phẩm
              </button>
              {products.length > 0 && step === 1 ? (
                <button onClick={() => setStep(2)} className={btnGhost}>
                  Xong, sang bước 2
                </button>
              ) : null}
            </div>
          </div>
        </section>

        {/* ---- Step 2: session ------------------------------------------- */}
        <section className="rounded-lg border border-hairline bg-surface p-4">
          <StepHeader
            n={2}
            title="Tạo phiên live"
            hint="Chế độ Tự động dành cho phòng live của nhóm (tuân thủ cao). Chế độ Đề xuất dành cho phòng đối tác — họ có nút bỏ qua."
            done={session != null}
            active={step === 2}
          />
          {step >= 2 && !session ? (
            <div className="mt-3 space-y-2 pl-9">
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
              <button onClick={makeSession} disabled={busy} className={btnCls}>
                Tạo phiên
              </button>
            </div>
          ) : null}
          {session ? (
            <p className="mt-2 pl-9 text-[13px] text-sec">
              {session.title || "Phiên chưa đặt tên"} · {session.planned_duration_min} phút ·{" "}
              <span className="text-ink">{session.status}</span>
            </p>
          ) : null}
        </section>

        {/* ---- Step 3: schedule ------------------------------------------ */}
        <section className="rounded-lg border border-hairline bg-surface p-4">
          <StepHeader
            n={3}
            title="Bốc thăm lịch BẬT/TẮT — TRƯỚC khi lên sóng"
            hint="Chia phiên thành các khối, mỗi khối bốc thăm 50/50. Lịch được lưu lại làm dấu vết kiểm chứng: giám khảo có thể đối chiếu để thấy không ai sửa giữa chừng."
            done={schedule != null}
            active={step === 3}
          />
          {session && step >= 3 ? (
            <div className="mt-3 pl-9">
              {!schedule ? (
                <>
                  <div className="grid grid-cols-2 gap-2 md:w-2/3">
                    <label className="text-[12px] text-sec">
                      Độ dài khối (phút)
                      <input
                        className={`${inputCls} mt-1`}
                        inputMode="numeric"
                        value={blockMin}
                        onChange={(e) => setBlockMin(e.target.value)}
                      />
                    </label>
                    <label className="text-[12px] text-sec">
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
                  <button onClick={drawSchedule} disabled={busy} className={`${btnCls} mt-2`}>
                    Bốc thăm lịch
                  </button>
                </>
              ) : (
                <>
                  <div className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-sec">
                    <span>
                      <span className="text-ink">{schedule.blocks.length}</span> khối
                    </span>
                    <span>
                      BẬT <span className="text-ink">{schedule.n_on}</span> / TẮT{" "}
                      <span className="text-ink">{schedule.n_off}</span>
                    </span>
                    <span>
                      seed <span className="tabular-nums text-ink">{schedule.seed}</span>
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
                    Tím = BẬT (hệ thống điều khiển) · Xám = TẮT (làm như thường lệ). Ghi lại seed{" "}
                    <strong className="text-sec">{schedule.seed}</strong> — sinh lại cùng seed cho
                    ra đúng lịch này.
                  </p>
                  {!live && !ended ? (
                    <button onClick={goLive} disabled={busy} className={`${btnCls} mt-3`}>
                      Bắt đầu phát sóng
                    </button>
                  ) : null}
                </>
              )}
            </div>
          ) : null}
        </section>

        {/* ---- Step 4: live ---------------------------------------------- */}
        <section className="rounded-lg border border-hairline bg-surface p-4">
          <StepHeader
            n={4}
            title="Đang phát — mở bàn điều khiển"
            hint="Mở màn hình host trên máy của người dẫn (màn hình đó cố tình không hiện khối BẬT/TẮT để không ảnh hưởng cách họ nói)."
            done={ended}
            active={step === 4}
          />
          {live || ended ? (
            <div className="mt-3 space-y-3 pl-9">
              <div className="flex flex-wrap gap-2">
                <Link href="/desk" className={btnCls}>
                  Mở bàn điều khiển
                </Link>
                <Link href="/host" className={btnGhost}>
                  Mở màn hình host
                </Link>
                {live ? (
                  <button onClick={finish} disabled={busy} className={btnGhost}>
                    Kết thúc phiên
                  </button>
                ) : null}
              </div>

              {links.length > 0 ? (
                <div>
                  <p className="text-[12px] font-semibold text-ink">
                    Link đo lượt nhấp — dán vào bình luận ghim khi giới thiệu sản phẩm
                  </p>
                  <ul className="mt-1 space-y-0.5 text-[12px] text-sec">
                    {links.map((l) => (
                      <li key={l.code} className="tabular-nums">
                        {l.product_id}:{" "}
                        <code className="text-ink">
                          http://localhost:8000/r/{l.code}
                        </code>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-1 text-[11px] leading-snug text-mut">
                    Mỗi lượt bấm được ghi lại và quy về khối đang chạy — đây chính là biến kết quả
                    chính của thí nghiệm.
                  </p>
                </div>
              ) : null}

              {ended ? (
                <div className="rounded border border-hairline bg-page p-3">
                  <p className="text-[13px] text-ink">Phiên đã kết thúc.</p>
                  <p className="mt-1 text-[12px] leading-snug text-sec">
                    Bước tiếp theo: chấm chất lượng dữ liệu bằng lệnh{" "}
                    <code className="text-ink">livelift-qc --session-id {session?.session_id}</code>{" "}
                    rồi xem{" "}
                    <Link href="/ket-qua" className="text-s1 underline underline-offset-2">
                      Kết quả thí nghiệm
                    </Link>
                    .
                  </p>
                </div>
              ) : null}
            </div>
          ) : (
            <p className="mt-2 pl-9 text-[13px] text-mut">
              Hoàn tất bước 3 rồi bấm &ldquo;Bắt đầu phát sóng&rdquo;.
            </p>
          )}
        </section>
      </div>
    </main>
  );
}
