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

/**
 * `GET /sessions/{id}` — SessionSummary plus the design blob. For a replay
 * analysis the blob carries `analysis_only`, `source_url` and (gói UI-KOL)
 * `video_id` — the YouTube id the desk embeds next to the numbers.
 */
export interface SessionDetail extends SessionSummary {
  design: {
    analysis_only?: boolean;
    source_url?: string;
    video_id?: string | null;
    [key: string]: unknown;
  } | null;
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
  /**
   * SHA-256 commitment over (tham số thiết kế, seed) — công bố TRƯỚC phát sóng
   * (gói Q3). OPERATOR ONLY: it fingerprints the assignment mechanism, so it
   * must never reach the blinded host payload. `null` cho phiên chưa có lịch
   * hoặc lịch sinh trước gói Q3.
   */
  design_hash: string | null;
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
  // no estimate_ht: at constant p=0.5 the Hájek/IPW number is identical to
  // `estimate` — the API stopped serving a duplicate "second estimator".
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

// ---------------------------------------------------------------------------
// WebSocket contract — SERVER ENVELOPE {type, data}
//
// The API always publishes `{"type": <string>, "data": <payload>}` (see
// src/livelift/api/routes/{events,sessions,actions,redirect,ws}.py). The old
// client types read `msg.tick` / `msg.state` — fields the server never sends —
// so every push was silently dropped (the desk "worked" only because of the
// 5 s REST poll). Locked both ways by tests/test_web_api_contract.py.
// ---------------------------------------------------------------------------

/** "tick" payload: TickOut as JSON (wall-clock bucket, no offset_s). */
export interface WsTickData {
  session_id: string;
  ts_bucket: string; // ISO UTC
  viewers: number;
  comment_rate: number;
  like_rate: number;
  click_count: number;
  pinned_product_id: string | null;
}

/** "comment" payload: CommentOut as JSON — `text` is ALREADY scrubbed. */
export interface WsCommentData {
  comment_id: string;
  session_id: string;
  block_id: string | null;
  ts: string; // ISO UTC
  text: string; // scrubbed server-side
  pii_kinds: string[];
  intent: string | null;
}

/**
 * "state" payload is a PARTIAL patch — the server pushes only the field that
 * changed ({status} on start/end, {pinned_product_id} on execute/override).
 * It must be MERGED into local state, never treated as a full SessionState.
 */
export interface WsStateData {
  status?: SessionStatus;
  pinned_product_id?: string | null;
}

/** "click" payload: one shortlink click just landed (redirect.py). */
export interface WsClickData {
  product_id: string;
}

/** WebSocket push messages from /ws/{session_id} — always {type, data}. */
export type WsMessage =
  | { type: "hello"; data: { session_id: string } }
  | { type: "tick"; data: WsTickData }
  | { type: "comment"; data: WsCommentData }
  | { type: "state"; data: WsStateData }
  | { type: "click"; data: WsClickData };

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

// ---------------------------------------------------------------------------
// Signal coverage + báo cáo sau phiên (gói UI-KOL) — SHARED API CONTRACT
//
// The no-fabricated-numbers rule lives HERE for the UI: a signal the source
// cannot provide arrives as status="missing" WITH a Vietnamese reason, and the
// client renders the gap ("THIẾU nguồn") — never a fake 0.
// ---------------------------------------------------------------------------

export type SignalStatus = "ok" | "degraded" | "missing";

/** One row of `GET /sessions/{id}/signals` — what this session can measure. */
export interface SignalStateItem {
  name: string;
  status: SignalStatus;
  detail: string; // Vietnamese reason, shown verbatim
}

export interface CapabilityItem {
  name: string;
  status: SignalStatus;
  reason: string;
}

export interface SignalCoverage {
  session_id: string;
  signals: SignalStateItem[];
  capabilities: CapabilityItem[];
}

/** One paid/visible audience event (`GET /sessions/{id}/reactions`).
 * No author field exists anywhere on this path (hard rule 1). */
export interface ReactionItem {
  reaction_id: string;
  ts_utc: string;
  kind: "superchat" | "gift" | "sticker" | "membership" | "like";
  amount: number | null;
  currency: string | null;
}

/** `GET /sessions/{id}/bao-cao` — post-session report. Field names mirror
 * `BaoCaoOut` in src/livelift/api/schemas.py exactly. */
export interface BaoCaoDinhBinhLuan {
  gia_tri_per_phut: number;
  offset_s: number | null;
  ts: string;
}

export interface BaoCaoNguoiXem {
  dinh: number;
  trung_binh: number;
  n_diem_do: number;
}

export interface BaoCaoReactions {
  tong: number;
  theo_loai: Record<string, number>;
  tong_tien: Record<string, number>;
}

/** Mỗi ô hoặc có giá trị, hoặc null VÀ có lý do trong `thieu` — không 0 giả. */
export interface BaoCaoTongQuan {
  thoi_luong_s: number | null;
  tong_binh_luan: number;
  dinh_binh_luan: BaoCaoDinhBinhLuan | null;
  nguoi_xem: BaoCaoNguoiXem | null;
  luot_nhap_hop_le: number | null;
  reactions: BaoCaoReactions | null;
  thieu: Record<string, string>;
}

export interface BaoCaoKhoanhKhac {
  offset_s: number;
  ts: string | null;
  binh_luan_per_phut: number;
  nen_per_phut: number;
  ty_le: number | null;
  san_pham_dang_ghim: string | null;
  mo_ta: string; // câu quan sát đã dán nhãn — hiển thị nguyên văn
}

export interface BaoCaoYDinh {
  tong: number;
  dem_theo_nhan: Record<string, number>;
  /** BẮT BUỘC hiển thị kèm phân bố — precision phụ thuộc tỷ lệ nền từng lớp. */
  caveat: string;
}

export interface BaoCaoKetQuaThiNghiem {
  source: "experiment";
  khoa: boolean;
  ly_do_khoa: string | null;
  estimable: boolean;
  n_blocks: number;
  n_on: number;
  n_off: number;
  estimate: number | null;
  ci_low: number | null;
  ci_high: number | null;
  p_value: number | null;
  n_draws: number | null;
  message: string | null;
}

export interface BaoCao {
  session_id: string;
  tieu_de: string | null;
  platform: string;
  loai_phien: "thi_nghiem" | "quan_sat";
  nhan: string;
  tong_quan: BaoCaoTongQuan;
  tin_hieu: SignalStateItem[];
  nang_luc: CapabilityItem[];
  khoanh_khac: BaoCaoKhoanhKhac[];
  khoanh_khac_ghi_chu: string | null;
  phan_bo_y_dinh: BaoCaoYDinh;
  pii_da_che: Record<string, number>;
  /** null cho phiên quan sát — `nhan` nói rõ vì sao không có số nhân quả. */
  ket_qua_thi_nghiem: BaoCaoKetQuaThiNghiem | null;
  goi_y_chien_thuat: string[];
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
  mut: "#898781", // gridline/axis chrome only — 4.38:1 on the raised plane
  dim: "#a3a19a", // axis TEXT: 7.52:1 on page … 4.55:1 on axis, clears AA everywhere
  sec: "#c3c2b7",
  ink: "#ffffff",
  s1: "#3987e5",
  s2: "#d95926",
  s3: "#199e70", // nhịp bình luận — slot 3 (aqua) của bảng màu đã kiểm định
  on: "#9085e9", // block strip ON (slot 7 violet — not used by any chart series)
} as const;
