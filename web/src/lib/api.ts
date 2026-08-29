/**
 * Typed client for the LiveLift FastAPI backend.
 *
 * Base URL comes from NEXT_PUBLIC_API_URL (default http://localhost:8000).
 * Every call has a short timeout so an unreachable API fails fast and the UI
 * can fall back to mock mode.
 */

import type {
  ActionCardData,
  CommentItem,
  DemoSeedResult,
  HostState,
  OverrideReason,
  ReplayJob,
  SessionState,
  SessionSummary,
  Tick,
} from "./types";
import { OVERRIDE_REASONS } from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

/** http(s) base -> ws(s) URL for /ws/{sessionId}. */
export function wsUrl(sessionId: string): string {
  return `${API_BASE.replace(/^http/, "ws")}/ws/${sessionId}`;
}

async function request<T>(
  path: string,
  init?: RequestInit & { timeoutMs?: number },
): Promise<T> {
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

export function sanitizeCards(cards: ActionCardData[]): ActionCardData[] {
  return cards.map(sanitizeCard).slice(0, 3);
}

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------

export function listSessions(timeoutMs?: number): Promise<SessionSummary[]> {
  return request<SessionSummary[]>("/sessions", { timeoutMs });
}

export function getState(sessionId: string): Promise<SessionState> {
  return request<SessionState>(`/sessions/${sessionId}/state`);
}

/**
 * BLINDED host state (rule L6). Prefers the dedicated host-safe endpoint; if
 * the backend does not expose one, projects the operator state down to the
 * HostState boundary type so nothing block-related can reach the host screen.
 */
export async function getHostState(sessionId: string): Promise<HostState> {
  try {
    return await request<HostState>(`/sessions/${sessionId}/host`);
  } catch {
    const s = await getState(sessionId);
    return {
      product_name: s.pinned_product?.name ?? null,
      price: s.pinned_product?.price ?? null,
      stock: s.pinned_product?.stock ?? null,
      elapsed_s: s.elapsed_s,
    };
  }
}

export async function getCards(
  sessionId: string,
  opts?: { excludeProductIds?: string[]; atOffsetS?: number },
): Promise<ActionCardData[]> {
  const params = new URLSearchParams();
  if (opts?.excludeProductIds?.length) {
    params.set("exclude", opts.excludeProductIds.join(","));
  }
  if (opts?.atOffsetS != null) params.set("at_s", String(Math.floor(opts.atOffsetS)));
  const qs = params.toString();
  const cards = await request<ActionCardData[]>(
    `/sessions/${sessionId}/cards${qs ? `?${qs}` : ""}`,
  );
  return sanitizeCards(cards);
}

export function executeCard(
  sessionId: string,
  cardId: string,
): Promise<{ ok: boolean; action_id?: string }> {
  return request(`/sessions/${sessionId}/execute`, {
    method: "POST",
    body: JSON.stringify({ card_id: cardId }),
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
  return request(`/sessions/${sessionId}/override`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getComments(
  sessionId: string,
  opts?: { sinceOffsetS?: number; limit?: number },
): Promise<CommentItem[]> {
  const params = new URLSearchParams();
  if (opts?.sinceOffsetS != null) params.set("since_s", String(Math.floor(opts.sinceOffsetS)));
  if (opts?.limit != null) params.set("limit", String(opts.limit));
  const qs = params.toString();
  return request<CommentItem[]>(`/sessions/${sessionId}/comments${qs ? `?${qs}` : ""}`);
}

export function getTicks(sessionId: string): Promise<Tick[]> {
  return request<Tick[]>(`/sessions/${sessionId}/ticks`);
}

export function getReport(sessionId: string): Promise<unknown> {
  return request(`/sessions/${sessionId}/report`);
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
