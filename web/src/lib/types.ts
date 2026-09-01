/**
 * Shared types for the LiveLift control desk.
 *
 * Field names mirror the backend schema (src/livelift/migrations/0001_init.up.sql)
 * so the typed client maps API payloads 1:1.
 */

export type Assignment = "ON" | "OFF";
export type Phase = "early" | "mid" | "late";
export type SessionStatus = "planned" | "scheduled" | "live" | "ended";
export type SessionMode = "auto" | "suggest";

export interface Product {
  product_id: string;
  name: string;
  category: string | null;
  price: number;
  stock: number;
}

export interface SessionSummary {
  session_id: string;
  platform: string;
  title: string | null;
  mode: SessionMode;
  status: SessionStatus;
  planned_duration_min: number;
  start_ts: string | null; // ISO UTC
  end_ts: string | null;
}

/** One switchback block — OPERATOR view only, never shipped to the host screen. */
export interface BlockInfo {
  block_index: number;
  phase: Phase;
  assignment: Assignment | null; // null for washout
  is_washout: boolean;
  start_offset_s: number;
  end_offset_s: number;
  propensity: number | null;
}

/** Operator-facing session state (NOT blinded). */
/**
 * Operator state — mirrors `GET /sessions/{id}/state?role=operator` EXACTLY.
 * Verified against the running API on 27/08; keep it in lockstep with the
 * backend schema (tests/test_web_api_contract.py guards the paths).
 */
export interface SessionState {
  role: "operator";
  session_id: string;
  status: SessionStatus;
  mode: SessionMode;
  elapsed_s: number;
  current_block: CurrentBlock | null;
  pinned_product: Product | null;
  cards: ActionCardData[];
}

/** The block the session is in right now (operator view only — never host). */
export interface CurrentBlock {
  index: number;
  phase: "early" | "mid" | "late";
  assignment: "ON" | "OFF";
  is_washout: boolean;
  seconds_remaining: number;
}

/** Pooled experiment result from `GET /experiment/summary`. */
export interface ExperimentSummary {
  label: string;
  source: "experiment";
  n_sessions: number;
  n_blocks: number;
  n_on: number;
  n_off: number;
  estimate: number | null;
  estimate_ht: number | null;
  ci_low: number | null;
  ci_high: number | null;
  p_value: number | null;
  n_draws: number | null;
  measured_cv: number | null;
  measured_compliance: number | null;
  power_table: PowerRow[];
  message?: string | null;
  /** False when the design cannot be tested — render nothing inferential. */
  estimable?: boolean;
}

export interface PowerRow {
  scenario: string;
  n_sessions: number;
  blocks_per_session: number;
  n_blocks_total: number;
  cv: number;
  mde_relative: number;
}

/**
 * BLINDED host-facing state (rule L6).
 *
 * This type is the blinding boundary: it can only carry the pinned product,
 * its price/stock, and total elapsed time. No block boundaries, no assignment,
 * no time-remaining-in-block — do not add fields without an L6 review.
 */
export interface HostState {
  product_name: string | null;
  price: number | null;
  stock: number | null;
  elapsed_s: number;
}

/** One 30-second aggregate bucket (session_tick). */
export interface Tick {
  offset_s: number; // seconds since session start (bucket start)
  ts_bucket: string | null; // ISO UTC when known
  viewers: number;
  comment_rate: number; // comments per minute
  like_rate: number;
  click_count: number; // clicks inside this 30s bucket
  pinned_product_id: string | null;
  /** Forecast-model baseline (source="forecast" — never carries intervals). */
  baseline_viewers: number | null;
  baseline_clicks_per_min: number | null;
}

export const INTENT_LABELS = [
  "hoi_gia",
  "hoi_size",
  "che_dat",
  "chot_don",
  "van_chuyen",
  "khac",
] as const;
export type IntentLabel = (typeof INTENT_LABELS)[number];

/**
 * Intent display metadata. Colors are the validated dataviz categorical
 * palette (dark column), slots 1–6 in FIXED order — never reassigned when a
 * series is filtered out (color follows the entity).
 * Validated with scripts/validate_palette.js --mode dark: all checks pass.
 */
export const INTENT_META: Record<IntentLabel, { label: string; color: string }> = {
  hoi_gia: { label: "Hỏi giá", color: "#3987e5" },
  hoi_size: { label: "Hỏi size", color: "#d95926" },
  che_dat: { label: "Chê đắt", color: "#199e70" },
  chot_don: { label: "Chốt đơn", color: "#c98500" },
  van_chuyen: { label: "Vận chuyển", color: "#d55181" },
  khac: { label: "Khác", color: "#008300" },
};

/** A comment as it may be shown: text is ALREADY scrubbed server-side (PII rule). */
export interface CommentItem {
  comment_id: string;
  offset_s: number;
  ts: string | null; // ISO UTC
  text_scrubbed: string;
  intent_label: IntentLabel | null;
  pii_kinds: string[];
}

export type CardSource = "forecast" | "experiment";

/**
 * An action card. E2-04 display rule:
 * - source="forecast"  → NEVER carries ci_low/ci_high (sanitizeCard strips them);
 * - source="experiment" → may carry a 95% CI.
 */
export interface ActionCardData {
  card_id: string;
  rank: number;
  headline: string; // Vietnamese action headline
  product_id: string;
  product_name: string;
  rationale: string; // Vietnamese rationale
  source: CardSource;
  estimate: number | null; // relative lift, e.g. 0.18 = +18%
  ci_low: number | null; // experiment only
  ci_high: number | null; // experiment only
  auto_execute_in_s: number | null; // countdown when session mode = auto
}

/** Allowed manual-override reasons — the ONLY three (hard project rule 5). */
export const OVERRIDE_REASONS = ["hết hàng", "sai giá", "sự cố kỹ thuật"] as const;
export type OverrideReason = (typeof OVERRIDE_REASONS)[number];

export type ConnectionKind = "connecting" | "live" | "mock";

/** WebSocket push message shapes from /ws/{session_id}. */
export type WsMessage =
  | { type: "tick"; tick: Tick }
  | { type: "state"; state: SessionState }
  | { type: "comment"; comment: CommentItem }
  | { type: "cards"; cards: ActionCardData[] };

/** Full recorded dataset of one session, used by the replay engine. */
export interface SessionRecording {
  session: SessionSummary;
  blocks: BlockInfo[];
  ticks: Tick[];
  comments: CommentItem[];
  cards_timeline: { offset_s: number; cards: ActionCardData[] }[];
  products: Product[];
  duration_s: number;
}

// ---------------------------------------------------------------------------
// Replay-analysis (YouTube VOD ingestion) — SHARED API CONTRACT
// ---------------------------------------------------------------------------

/** Lifecycle of one POST /replays/youtube ingestion job. */
export type ReplayJobStatus = "queued" | "downloading" | "ingesting" | "done" | "error";

/** GET /replays/jobs/{job_id} response. */
export interface ReplayJob {
  job_id: string;
  status: ReplayJobStatus;
  detail: string | null;
  session_id: string | null;
  n_comments: number | null;
  video_title: string | null;
}

/** POST /demo/seed response. */
export interface DemoSeedResult {
  session_ids: string[];
  replay_session_id: string;
  product_ids: string[];
  shortlink_codes: string[];
}

/** Chart chrome tokens (dataviz reference palette, dark column). */
export const CHART = {
  surface: "#1a1a19",
  grid: "#2c2c2a",
  axis: "#383835",
  mut: "#898781",
  sec: "#c3c2b7",
  ink: "#ffffff",
  s1: "#3987e5",
  s2: "#d95926",
  on: "#9085e9", // block strip ON (slot 7 violet — not used by any chart series)
} as const;
