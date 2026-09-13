/**
 * Typed client for the LiveLift FastAPI backend.
 *
 * Base URL comes from NEXT_PUBLIC_API_URL (default http://localhost:8000).
 * Every call has a short timeout so an unreachable API fails fast and the UI
 * can fall back to mock mode.
 */

import type {
  ActionCardData,
  BaoCao,
  BlockInfo,
  CommentItem,
  DemoSeedResult,
  ExperimentSummary,
  HealthInfo,
  HostState,
  OverrideReason,
  Product,
  ReactionItem,
  ReplayJob,
  SessionDetail,
  SessionMode,
  SessionState,
  SessionSummary,
  SignalCoverage,
  Tick,
} from "./types";
import { OVERRIDE_REASONS } from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

/**
 * Base URL for links VIEWERS must reach (the /r/{code} measurement links
 * pasted into the pinned comment). On a laptop demo API_BASE is localhost —
 * correct for the operator's browser, useless for a viewer's phone — so the
 * public base is its own variable (real domain or tunnel), falling back to
 * NEXT_PUBLIC_API_BASE, then to API_BASE (NEXT_PUBLIC_API_URL / localhost).
 */
export const PUBLIC_API_BASE = (
  process.env.NEXT_PUBLIC_PUBLIC_API_BASE ??
  process.env.NEXT_PUBLIC_API_BASE ??
  API_BASE
).replace(/\/$/, "");

/** http(s) base -> ws(s) URL for /ws/{sessionId}. */
export function wsUrl(sessionId: string): string {
  return `${API_BASE.replace(/^http/, "ws")}/ws/${sessionId}`;
}

async function request<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const { timeoutMs = 3500, ...rest } = init ?? {};
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...rest,
      signal: ctrl.signal,
      headers: { "Content-Type": "application/json", ...(rest.headers ?? {}) },
      cache: "no-store",
    });
    if (!res.ok) {
      // Gói WIZARD: máy chủ trả lỗi 400/409 kèm `detail` TIẾNG VIỆT có gợi ý
      // sửa (vd "phiên 50 phút, khối 10 phút…"). Nuốt nó đi và ném ra chuỗi
      // kỹ thuật "API 400 Bad Request" là vứt câu trả lời tốt nhất mà người
      // dùng có thể nhận — nên đọc body trước, chuỗi kỹ thuật chỉ là fallback.
      let detail: string | null = null;
      try {
        const body = (await res.json()) as { detail?: unknown } | null;
        if (typeof body?.detail === "string" && body.detail.trim()) {
          detail = body.detail.trim();
        }
      } catch {
        // body không phải JSON — giữ fallback kỹ thuật
      }
      throw new Error(detail ?? `API ${res.status} ${res.statusText} — ${path}`);
    }
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * E2-04 enforcement (hard rule 2): a card whose numbers come from a forecast
 * model must NEVER carry a confidence interval. Strip intervals defensively on
 * every card that crosses into the UI, regardless of what the API sent.
 */
export function sanitizeCard(raw: ActionCardData): ActionCardData {
  if (raw.source === "forecast" && (raw.ci_low != null || raw.ci_high != null)) {
    // eslint-disable-next-line no-console
    console.warn(
      `[E2-04] Card ${raw.card_id}: source="forecast" arrived with a CI — stripped before display.`,
    );
    return { ...raw, ci_low: null, ci_high: null };
  }
  return raw;
}

/**
 * Chuẩn hoá danh sách thẻ trước khi vào UI.
 *
 * Ngoài luật E2-04 ở trên, hàm này còn BÙ HẠNG. `/sessions/{id}/state` không
 * trả trường `rank` (chỉ dữ liệu mô phỏng mới có), nên trên bàn thật huy hiệu
 * hạng in ra đúng một chữ "#" trống và nhãn trợ năng đọc thành "Gợi ý hạng
 * undefined". Thứ tự API trả về CHÍNH LÀ thứ hạng, nên lấy luôn vị trí làm
 * hạng thay vì để giao diện hiển thị một ô rỗng.
 */
export function sanitizeCards(cards: ActionCardData[]): ActionCardData[] {
  return cards
    .slice(0, 3)
    .map((raw, i) => sanitizeCard(raw.rank == null ? { ...raw, rank: i + 1 } : raw));
}

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------

/**
 * List sessions. `env` (gói DEMO-THẬT, UX spec B-3/L-B) lọc theo nguồn dữ
 * liệu phía server — "real": chỉ phiên thật, "demo": chỉ dữ liệu mẫu. Bỏ
 * trống trả cả hai, mỗi dòng đã mang cờ `is_demo` để UI dán nhãn.
 */
export function listSessions(
  timeoutMs?: number,
  env?: "real" | "demo",
): Promise<SessionSummary[]> {
  return request<SessionSummary[]>(env ? `/sessions?env=${env}` : "/sessions", { timeoutMs });
}

/**
 * `GET /health` — trạng thái an toàn dữ liệu + chế độ dữ liệu tổng hợp
 * (mode/mode_counts/mode_note) cho chip DEMO/THẬT trên nav.
 */
export function getHealth(timeoutMs?: number): Promise<HealthInfo> {
  return request<HealthInfo>("/health", { timeoutMs });
}

// ---------------------------------------------------------------------------
// THĂM DÒ MÁY CHỦ — SỐNG / SUY GIẢM / CHẾT (gói B-PROBE)
//
// Sự cố 13/09/2026: trang chủ hỏi "máy chủ còn sống không" bằng `listSessions`,
// tức bằng một truy vấn ĐỌC KHO. Khi PostgreSQL chết, `GET /sessions` treo 30
// giây rồi trả 500, nên probe 2,5 giây LUÔN hết giờ và trang in "Chưa kết nối
// được máy chủ" TRONG KHI API vẫn đang chạy và trả lời. Ba lỗi trong một:
//   (a) hỏi sai câu hỏi — một endpoint nặng không trả lời được câu "còn sống
//       không"; câu đó thuộc về `/health`, endpoint rẻ nhất và là nơi máy chủ
//       TỰ KHAI trạng thái an toàn dữ liệu của mình;
//   (b) chỉ có hai trạng thái (sống/chết) cho một thế giới có ba — máy chủ
//       chạy nhưng kho hỏng là trạng thái RIÊNG, phải nói riêng;
//   (c) 2,5 giây quá ngắn cho máy dev lạnh, nên CHẬM bị kết luận nhầm là CHẾT.
//
// Luật bất di bất dịch: hễ máy chủ đã trả lời thì KHÔNG BAO GIỜ được nói
// "chưa kết nối được" — nói sai trạng thái còn tệ hơn không nói gì.
// ---------------------------------------------------------------------------

export type ServerStatus = "ok" | "degraded" | "down";

/**
 * 4 giây. Máy dev lạnh biên dịch trang đầu rất chậm và `next dev` có thể giữ
 * request đầu tiên vài giây — 2,5 giây cắt nhầm một máy chủ hoàn toàn khoẻ.
 */
export const PROBE_TIMEOUT_MS = 4000;
/** Thử lại ĐÚNG một lần trước khi dám tuyên bố CHẾT. */
export const PROBE_ATTEMPTS = 2;
/** Nghỉ giữa hai lần thử — đủ cho một cú nấc mạng, không đủ để người dùng chờ. */
const PROBE_RETRY_DELAY_MS = 300;
/** Trả lời được nhưng lâu hơn ngưỡng này là CHẬM — vẫn sống, không phải chết. */
export const PROBE_SLOW_MS = 1500;

export interface ServerProbe {
  /** SỐNG / SUY GIẢM / CHẾT — ba trạng thái, không phải hai. */
  status: ServerStatus;
  /** Thân `/health` khi đọc được; null khi máy chủ không trả lời hoặc trả rác. */
  health: HealthInfo | null;
  /** Lý do suy giảm, ưu tiên NGUYÊN VĂN câu tiếng Việt của máy chủ. */
  warning: string | null;
  /** Vì sao kết luận CHẾT: hết giờ chờ hay không nối được. Null khi còn sống. */
  downKind: "timeout" | "error" | null;
  /** Mã HTTP nhận được (kể cả 5xx — máy chủ trả 500 vẫn là máy chủ đang sống). */
  httpStatus: number | null;
  /** Tổng thời gian chờ, tính cả lần thử lại. */
  elapsedMs: number;
  /** Số lần đã gọi `/health`. */
  attempts: number;
  /** Sống nhưng chậm hơn `PROBE_SLOW_MS` — để UI nói "chậm", không nói "chết". */
  slow: boolean;
}

/**
 * MỘT câu cho MỖI trạng thái. Ba câu phải khác nhau: người vận hành đọc câu
 * này để quyết định có lên sóng hay không.
 *
 * Câu "Chưa kết nối được máy chủ" CHỈ được phép nằm ở nhánh `down` — đó chính
 * là câu đã nói dối trong sự cố 13/09.
 */
export const SERVER_STATUS_MESSAGE: Record<ServerStatus, string> = {
  ok: "Máy chủ đang chạy bình thường — mọi chức năng sẵn sàng.",
  degraded:
    "Máy chủ vẫn chạy nhưng KHO DỮ LIỆU ĐANG SUY GIẢM — xem được số liệu hiện có, " +
    "nhưng dữ liệu mới có thể KHÔNG LƯU LẠI ĐƯỢC. Đừng lên sóng thật cho tới khi kho trở lại bình thường.",
  down: "Chưa kết nối được máy chủ — bạn vẫn xem thử được bằng dữ liệu mô phỏng.",
};

/**
 * Phân loại một câu trả lời `/health` thành SỐNG hay SUY GIẢM.
 *
 * Không bao giờ trả "down" ở đây: hàm này chỉ chạy khi máy chủ ĐÃ trả lời.
 *
 * Nguồn sự thật là chính máy chủ (`status`), không phải suy đoán của web. Hai
 * trường hợp web tự kết luận được, vì cả hai đều là sự thật kiểm chứng được
 * ngay trong payload:
 *   - máy chủ trả lời nhưng thân không đọc được → không xác nhận được gì;
 *   - kho là RAM trần KHÔNG ảnh chụp → khởi động lại là mất sạch (đúng cách
 *     13 phiên thật biến mất ngày 11/09/2026).
 * `memory+snapshot` KHÔNG bị tính là suy giảm: nó có `durable=false` nhưng vẫn
 * sống sót qua một lần khởi động lại, và đó là chế độ demo bình thường.
 */
export function serverStatusOf(health: HealthInfo | null, httpStatus: number): "ok" | "degraded" {
  if (health == null) return "degraded";
  const declared = typeof health.status === "string" ? health.status.trim().toLowerCase() : "";
  if (declared && declared !== "ok") return "degraded";
  if (httpStatus >= 400) return "degraded";
  if (health.durable === false && health.storage_mode === "memory" && health.snapshot == null) {
    return "degraded";
  }
  return "ok";
}

/** Lý do suy giảm — câu của máy chủ trước, câu của web chỉ là phương án cuối. */
function degradedWarning(health: HealthInfo | null, httpStatus: number): string {
  const w = health?.storage_warning;
  if (typeof w === "string" && w.trim()) return w.trim();
  if (health == null) {
    return (
      `Máy chủ trả lời (HTTP ${httpStatus}) nhưng /health không đọc được — ` +
      "không xác nhận được kho dữ liệu có an toàn hay không."
    );
  }
  const declared = typeof health.status === "string" ? health.status.trim() : "";
  if (declared && declared.toLowerCase() !== "ok") {
    return `Máy chủ tự khai trạng thái "${declared}" — kho dữ liệu không ở mức bình thường.`;
  }
  if (httpStatus >= 400) {
    return `Máy chủ trả HTTP ${httpStatus} cho /health — nó còn sống nhưng đang có sự cố.`;
  }
  return (
    "Kho dữ liệu chỉ nằm trong RAM và KHÔNG có ảnh chụp: khởi động lại tiến trình là " +
    "mất sạch mọi phiên."
  );
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Một lần gọi `/health`. Không bao giờ ném — kết quả LUÔN là một trạng thái. */
async function probeOnce(timeoutMs: number): Promise<ServerProbe> {
  const ctrl = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    ctrl.abort();
  }, timeoutMs);
  const t0 = Date.now();
  try {
    // Đọc thẳng bằng fetch thay vì `getHealth`: `request` ném khi mã HTTP khác
    // 2xx, mà một máy chủ trả 503 vì kho hỏng vẫn là máy chủ ĐANG SỐNG — gọi
    // nó là "chưa kết nối" chính là lời nói dối cần diệt.
    const res = await fetch(`${API_BASE}/health`, {
      signal: ctrl.signal,
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
    });
    let health: HealthInfo | null = null;
    try {
      const body: unknown = await res.json();
      if (body && typeof body === "object") health = body as HealthInfo;
    } catch {
      health = null; // thân không phải JSON — máy chủ sống nhưng không khai được
    }
    const status = serverStatusOf(health, res.status);
    const elapsedMs = Date.now() - t0;
    return {
      status,
      health,
      warning: status === "degraded" ? degradedWarning(health, res.status) : null,
      downKind: null,
      httpStatus: res.status,
      elapsedMs,
      attempts: 1,
      slow: elapsedMs >= PROBE_SLOW_MS,
    };
  } catch {
    return {
      status: "down",
      health: null,
      warning: null,
      downKind: timedOut ? "timeout" : "error",
      httpStatus: null,
      elapsedMs: Date.now() - t0,
      attempts: 1,
      slow: false,
    };
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Câu hỏi "máy chủ còn sống không" — hỏi `/health`, thử lại một lần, trả về
 * MỘT trong ba trạng thái. Không bao giờ ném.
 */
export async function probeServer(
  opts: { timeoutMs?: number; attempts?: number } = {},
): Promise<ServerProbe> {
  const timeoutMs = opts.timeoutMs ?? PROBE_TIMEOUT_MS;
  const maxAttempts = Math.max(1, opts.attempts ?? PROBE_ATTEMPTS);
  let result = await probeOnce(timeoutMs);
  let used = 1;
  let total = result.elapsedMs;
  while (result.status === "down" && used < maxAttempts) {
    await sleep(PROBE_RETRY_DELAY_MS);
    result = await probeOnce(timeoutMs);
    used += 1;
    total += result.elapsedMs + PROBE_RETRY_DELAY_MS;
  }
  return {
    ...result,
    attempts: used,
    elapsedMs: total,
    slow: result.status !== "down" && total >= PROBE_SLOW_MS,
  };
}

export function getState(sessionId: string): Promise<SessionState> {
  return request<SessionState>(`/sessions/${sessionId}/state?role=operator`);
}

/**
 * BLINDED host state (rule 3 / L6).
 *
 * Calls the host-role endpoint DIRECTLY and never falls back to the operator
 * payload: a fallback would put `assignment` and `seconds_remaining` into the
 * host machine's Network tab even though the UI does not draw them, which is
 * exactly the leak the blinding rule exists to prevent (incident 27/08).
 *
 * The strip below is defence in depth — if a future backend change ever leaks
 * a block field into the host payload, it dies here instead of reaching a
 * component.
 */
const HOST_FORBIDDEN_KEYS = [
  "block",
  "current_block",
  "assignment",
  "arm",
  "treatment",
  "seconds_remaining",
  "remaining",
  "phase",
  "propensity",
  "schedule",
  "seed",
  "design_hash",
  "cards",
] as const;

export async function getHostState(sessionId: string): Promise<HostState> {
  const raw = await request<Record<string, unknown>>(`/sessions/${sessionId}/state?role=host`);
  const leaked = HOST_FORBIDDEN_KEYS.filter((k) => k in raw);
  if (leaked.length > 0) {
    console.warn(`[livelift] payload host chứa trường bị cấm (${leaked.join(", ")}) — đã loại bỏ.`);
  }
  const product = raw.pinned_product as
    { name?: string; price?: number; stock?: number } | string | null | undefined;
  const productName = typeof product === "string" ? product : (product?.name ?? null);
  return {
    product_name: productName,
    price:
      (raw.price as number | null) ??
      (typeof product === "object" ? (product?.price ?? null) : null),
    stock:
      (raw.stock as number | null) ??
      (typeof product === "object" ? (product?.stock ?? null) : null),
    elapsed_s: (raw.elapsed_s as number) ?? 0,
  };
}

/**
 * Action cards.
 *
 * The API has no `/cards` route: cards are part of the operator state payload
 * (`GET /sessions/{id}/state?role=operator`). Calling a non-existent path used
 * to 404 and — via Promise.all — took the whole desk poll down with it
 * (incident 27/08). Client-side `exclude` supports the replay what-if panel.
 */
export async function getCards(
  sessionId: string,
  opts?: { excludeProductIds?: string[] },
): Promise<ActionCardData[]> {
  const state = await getState(sessionId);
  let cards = state.cards ?? [];
  if (opts?.excludeProductIds?.length) {
    const excluded = new Set(opts.excludeProductIds);
    cards = cards.filter((c) => !excluded.has(c.product_id));
  }
  return sanitizeCards(cards);
}

/**
 * Execute one action card. `productId` is REQUIRED: the server scopes the
 * inner-tier randomization to the clicked card's overlap set. Sending only
 * card_id left the server's product filter empty, so it randomized over the
 * whole candidate set — clicking card A could pin product B.
 */
export function executeCard(
  sessionId: string,
  cardId: string,
  productId: string,
): Promise<{ ok: boolean; action_id?: string }> {
  return request(`/sessions/${sessionId}/actions/execute`, {
    method: "POST",
    body: JSON.stringify({ card_id: cardId, product_id: productId }),
  });
}

/** Manual override — reason restricted to the three allowed values (rule 5). */
export function postOverride(
  sessionId: string,
  body: { product_id: string; reason: OverrideReason },
): Promise<{ ok: boolean }> {
  if (!(OVERRIDE_REASONS as readonly string[]).includes(body.reason)) {
    return Promise.reject(
      new Error(`Lý do không hợp lệ. Chỉ chấp nhận: ${OVERRIDE_REASONS.join(", ")}.`),
    );
  }
  return request(`/sessions/${sessionId}/actions/override`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** Comments (already PII-scrubbed server-side). The API takes no query
 * parameters — filtering/trimming happens client-side. */
export async function getComments(
  sessionId: string,
  startIso?: string | null,
): Promise<CommentItem[]> {
  const raw = await request<
    {
      comment_id: string;
      ts: string | null;
      text: string;
      intent: string | null;
      pii_kinds: string[];
    }[]
  >(`/sessions/${sessionId}/comments`);
  return toOffsets(raw, startIso).map((r) => ({
    comment_id: r.comment_id,
    offset_s: r.offset_s,
    ts: r.ts,
    // The API field is `text`; it is ALREADY PII-scrubbed server-side (raw text
    // never leaves the ingest process). The web name keeps that explicit.
    text_scrubbed: r.text,
    intent_label: (r.intent as CommentItem["intent_label"]) ?? null,
    pii_kinds: r.pii_kinds ?? [],
  }));
}

/**
 * Adapter layer: the API speaks absolute timestamps (`ts_bucket`, `ts`), the
 * charts want seconds-since-start. Normalising here keeps every component on
 * one shape and means a backend field rename breaks ONE function, not ten.
 *
 * The baseline series is derived CLIENT-SIDE (trailing mean) and is a forecast
 * -sourced number: per E2-04 it must never be rendered with an interval, and
 * it must be labeled "đường tham chiếu (trung bình trượt)" — the server does
 * not send a baseline and we must not invent one that looks authoritative.
 */
const BASELINE_WINDOW = 6; // 6 x 30s buckets = trailing 3 minutes

function toOffsets<T extends { ts: string | null }>(
  rows: T[],
  startIso?: string | null,
): (T & { offset_s: number })[] {
  const times = rows.map((r) => (r.ts ? Date.parse(r.ts) : NaN)).filter((t) => Number.isFinite(t));
  const base = startIso ? Date.parse(startIso) : Math.min(...times);
  const origin = Number.isFinite(base) ? base : 0;
  return rows.map((r) => {
    const t = r.ts ? Date.parse(r.ts) : NaN;
    return { ...r, offset_s: Number.isFinite(t) ? Math.max(0, (t - origin) / 1000) : 0 };
  });
}

function trailingMean(values: number[], i: number, window: number): number | null {
  const from = Math.max(0, i - window + 1);
  const slice = values.slice(from, i + 1).filter((v) => Number.isFinite(v));
  if (slice.length === 0) return null;
  return slice.reduce((a, b) => a + b, 0) / slice.length;
}

export async function getTicks(sessionId: string, startIso?: string | null): Promise<Tick[]> {
  const raw = await request<
    {
      ts_bucket: string | null;
      viewers: number;
      comment_rate: number;
      like_rate: number;
      click_count: number;
      pinned_product_id: string | null;
    }[]
  >(`/sessions/${sessionId}/ticks`);
  const withTs = raw.map((r) => ({ ...r, ts: r.ts_bucket }));
  const rows = toOffsets(withTs, startIso);
  const viewers = rows.map((r) => r.viewers);
  const clicksPerMin = rows.map((r) => r.click_count * 2); // 30s bucket -> per minute
  return rows.map((r, i) => ({
    offset_s: r.offset_s,
    ts_bucket: r.ts_bucket,
    viewers: r.viewers,
    comment_rate: r.comment_rate,
    like_rate: r.like_rate,
    click_count: r.click_count,
    pinned_product_id: r.pinned_product_id,
    baseline_viewers: trailingMean(viewers, i, BASELINE_WINDOW),
    baseline_clicks_per_min: trailingMean(clicksPerMin, i, BASELINE_WINDOW),
  }));
}

/** The pre-session randomization schedule (blocks). `GET` returns a plain
 * array, unlike `POST` which wraps it — the API is asymmetric here. */
export function getSchedule(sessionId: string): Promise<BlockInfo[]> {
  return request<BlockInfo[]>(`/sessions/${sessionId}/schedule`);
}

export function getReport(sessionId: string): Promise<unknown> {
  return request(`/sessions/${sessionId}/report`);
}

// ---------------------------------------------------------------------------
// Gói UI-KOL: session detail (video embed), signal matrix, reactions, báo cáo
// ---------------------------------------------------------------------------

/** Full session row incl. the design blob (`video_id` for replay analyses). */
export function getSessionDetail(sessionId: string): Promise<SessionDetail> {
  return request<SessionDetail>(`/sessions/${sessionId}`);
}

/**
 * Ma trận tín hiệu: what this session's data can honestly support. The desk
 * renders signal tiles FROM this matrix — a missing source becomes a labeled
 * "THIẾU nguồn" tile with the server's Vietnamese reason, never a fake 0.
 */
export function getSignalCoverage(sessionId: string): Promise<SignalCoverage> {
  return request<SignalCoverage>(`/sessions/${sessionId}/signals`);
}

/** Paid/visible audience events (Super Chat/gift/sticker/membership). */
export function getReactions(sessionId: string): Promise<ReactionItem[]> {
  return request<ReactionItem[]>(`/sessions/${sessionId}/reactions`);
}

/** Báo cáo sau phiên — mọi con số mang nguồn, mọi khoảng trống được tuyên bố. */
export function getBaoCao(sessionId: string): Promise<BaoCao> {
  return request<BaoCao>(`/sessions/${sessionId}/bao-cao`, { timeoutMs: 15000 });
}

/**
 * YouTube video id of a session, for the desk's embed frame.
 *
 * Source of truth is `design.video_id` (stored by the replay ingest since gói
 * UI-KOL); older sessions fall back to parsing `design.source_url` with the
 * same strict 11-char rule as the backend (`ingest.youtube_replay
 * .extract_video_id`). Returns null when neither knows — the caller must show
 * the gap, not a black frame.
 */
const YT_ID_RE = /^[A-Za-z0-9_-]{11}$/;
const YT_URL_RES = [
  /[?&]v=([A-Za-z0-9_-]{11})(?:[&#]|$)/,
  /youtu\.be\/([A-Za-z0-9_-]{11})(?:[?&#]|$)/,
  /\/(?:live|shorts|embed)\/([A-Za-z0-9_-]{11})(?:[?&#]|$)/,
];

export function youtubeVideoId(detail: SessionDetail | null): string | null {
  const design = detail?.design;
  if (!design) return null;
  const stored = design.video_id;
  if (typeof stored === "string" && YT_ID_RE.test(stored)) return stored;
  const url = design.source_url;
  if (typeof url === "string") {
    for (const re of YT_URL_RES) {
      const m = re.exec(url);
      if (m) return m[1];
    }
  }
  return null;
}

export function seedDemo(nSessions = 3): Promise<DemoSeedResult> {
  return request("/demo/seed", {
    method: "POST",
    body: JSON.stringify({ n_sessions: nSessions }),
    timeoutMs: 20000,
  });
}

// ---------------------------------------------------------------------------
// Replay-analysis (YouTube VOD ingestion) — SHARED API CONTRACT
// ---------------------------------------------------------------------------

/** Submit a finished YouTube live URL for observational analysis (202 → job). */
export function submitYoutubeReplay(url: string): Promise<{ job_id: string }> {
  return request("/replays/youtube", {
    method: "POST",
    body: JSON.stringify({ url }),
    timeoutMs: 10000,
  });
}

/** Poll one ingestion job. */
export function getReplayJob(jobId: string): Promise<ReplayJob> {
  return request(`/replays/jobs/${encodeURIComponent(jobId)}`);
}

/**
 * Pooled experiment result — the project's headline scientific output.
 * This IS `source: "experiment"`, so a confidence interval is required here
 * (E2-04 forbids intervals only on forecast-sourced numbers).
 *
 * `env` (gói DEMO-THẬT): mặc định "real" — kết quả THẬT, server đã loại mọi
 * phiên is_demo. "demo" trả bản gộp CHỈ dữ liệu mẫu với nhãn MÔ PHỎNG — dùng
 * cho chế độ DEMO của UI, luôn kèm watermark; hai bể không bao giờ trộn.
 */
export function getExperimentSummary(env: "real" | "demo" = "real"): Promise<ExperimentSummary> {
  return request<ExperimentSummary>(`/experiment/summary?env=${env}`, { timeoutMs: 15000 });
}

// ---------------------------------------------------------------------------
// Session lifecycle — everything the "Chạy phiên" screen needs.
//
// These endpoints existed from day one but had no UI, so running an experiment
// meant typing curl commands. That is fine for the team's own Live Lab (an
// engineer is sitting there) and unacceptable for a seller.
// ---------------------------------------------------------------------------

export function listProducts(): Promise<Product[]> {
  return request<Product[]>("/products");
}

export function createProduct(body: {
  product_id: string;
  name: string;
  category?: string | null;
  cost: number;
  price: number;
  stock: number;
}): Promise<Product> {
  return request<Product>("/products", { method: "POST", body: JSON.stringify(body) });
}

export function createSession(body: {
  platform: string;
  title?: string;
  mode?: SessionMode;
  planned_duration_min: number;
  host_id?: string | null;
}): Promise<SessionSummary> {
  return request<SessionSummary>("/sessions", { method: "POST", body: JSON.stringify(body) });
}

/**
 * Draw and persist the randomization schedule. HARD RULE: this must happen
 * BEFORE the session goes live — the API refuses (409) once a session has
 * started, which is what makes the randomization auditable.
 */
export function createSchedule(
  sessionId: string,
  body: { block_min?: number; washout_min?: number; jitter_s?: number; seed?: number },
): Promise<{
  session_id: string;
  status: string;
  seed: number;
  n_redraws: number;
  n_on: number;
  n_off: number;
  blocks: BlockInfo[];
  /** Cam kết thiết kế (SHA-256 của tham số + seed), công bố trước phát sóng. */
  design_hash: string;
  /** Cảnh báo tiếng Việt khi lịch không đạt đảm bảo cân bằng (phiên ngắn). */
  warning?: string | null;
}> {
  return request(`/sessions/${sessionId}/schedule`, {
    method: "POST",
    body: JSON.stringify(body),
    timeoutMs: 10000,
  });
}

export function startSession(sessionId: string): Promise<SessionSummary> {
  return request<SessionSummary>(`/sessions/${sessionId}/start`, { method: "POST" });
}

export function endSession(sessionId: string): Promise<SessionSummary> {
  return request<SessionSummary>(`/sessions/${sessionId}/end`, { method: "POST" });
}

/**
 * Huỷ một phiên CHƯA phát sóng (planned/scheduled) — gói WIZARD dùng cho nút
 * "tạo lại phiên" khi người dùng muốn sửa nền tảng/thời lượng/chế độ: backend
 * không có API sửa phiên (cố ý — thông số phiên là một phần của thiết kế thí
 * nghiệm), nên đường đúng là huỷ phiên nháp rồi tạo phiên mới. Phiên huỷ không
 * bao giờ vào kết quả (loại trừ cấu trúc, PREREGISTRATION §8.2).
 */
export function cancelSession(sessionId: string): Promise<SessionSummary> {
  return request<SessionSummary>(`/sessions/${sessionId}/cancel`, { method: "POST" });
}

export function createShortlink(body: {
  product_id: string;
  session_id?: string | null;
  target_url: string;
}): Promise<{ code: string; product_id: string; target_url: string }> {
  return request("/shortlinks", { method: "POST", body: JSON.stringify(body) });
}
