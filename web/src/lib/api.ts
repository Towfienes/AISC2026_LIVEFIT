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
      throw new Error(`API ${res.status} ${res.statusText} — ${path}`);
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

export function listSessions(timeoutMs?: number): Promise<SessionSummary[]> {
  return request<SessionSummary[]>("/sessions", { timeoutMs });
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
 */
export function getExperimentSummary(): Promise<ExperimentSummary> {
  return request<ExperimentSummary>("/experiment/summary", { timeoutMs: 15000 });
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

export function createShortlink(body: {
  product_id: string;
  session_id?: string | null;
  target_url: string;
}): Promise<{ code: string; product_id: string; target_url: string }> {
  return request("/shortlinks", { method: "POST", body: JSON.stringify(body) });
}
