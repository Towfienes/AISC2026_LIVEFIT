/**
 * Shared types for the LiveLift control desk.
 *
 * Field names mirror the backend schema (src/livelift/migrations/0001_init.up.sql)
 * so the typed client maps API payloads 1:1.
 */

export type Assignment = "ON" | "OFF";
export type Phase = "early" | "mid" | "late";
/**
 * `cancelled` = đóng mà KHÔNG phát sóng (migration 0008). Khác hẳn `ended`:
 * phiên huỷ chưa từng lên sóng nên không mang `start_ts`, không có khối đo
 * nào, và không bao giờ vào kết quả gộp (tiền đăng ký §8.2).
 */
export type SessionStatus = "planned" | "scheduled" | "live" | "ended" | "cancelled";
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
  /**
   * DỮ LIỆU MẪU (gói DEMO-THẬT, migration 0009): phiên máy sinh để xem
   * thử/tập demo — không có buổi phát nào từng diễn ra. Khác `dry_run`
   * (phiên THẬT chạy thử). Bị loại khỏi mọi kết quả thật phía server;
   * UI phải vẽ nhãn DEMO ở mọi nơi phiên này xuất hiện.
   */
  is_demo: boolean;
  /** Phiên THẬT chạy thử — bị loại khỏi kết quả gộp (PREREGISTRATION §8.2).
   *  Máy chủ luôn gửi; optional để payload cũ và dữ liệu giả vẫn hợp lệ. */
  dry_run?: boolean;
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
  /**
   * Cờ DỮ LIỆU MẪU của phiên (xem SessionSummary.is_demo) — bàn điều khiển
   * vẽ nhãn DEMO từ đây. Optional vì state cũ/mock có thể chưa mang trường
   * này; thiếu nghĩa là "không rõ", KHÔNG nghĩa là thật.
   */
  is_demo?: boolean;
  /**
   * Trạng thái máy tự lái + cảnh báo im lặng (gói DESK-HOST v2) — chỉ có ở
   * phiên mode="auto"; null/thiếu cho phiên gợi ý. Bàn hiển thị nguyên văn,
   * không suy diễn thêm.
   */
  autopilot?: AutopilotState | null;
  /**
   * Lý do tiếng Việt vì sao danh sách thẻ rỗng THEO THIẾT KẾ (phiên đã kết
   * thúc, phiên phân tích video…) — phân biệt với "chưa đủ số liệu".
   */
  cards_note?: string | null;
}

/**
 * Trạng thái máy tự lái phía máy chủ (OPERATOR ONLY — nêu đích danh chỉ số
 * khối nên không bao giờ được đưa sang màn host bị làm mù, luật L6). Gương
 * của `AutopilotState` trong api/schemas.py; `alarm` là câu cảnh báo tiếng
 * Việt khi phiên auto đang KHÔNG tạo ra can thiệp nào.
 */
export interface AutopilotState {
  enabled: boolean;
  last_run_ts: string | null; // ISO UTC — nhịp tim lần chạy gần nhất
  actions_taken: number;
  on_blocks_total: number;
  on_blocks_done: number;
  missed_on_blocks: number[];
  last_error: string | null;
  alarm: string | null;
}

/** The block the session is in right now (operator view only — never host). */
export interface CurrentBlock {
  index: number;
  phase: "early" | "mid" | "late";
  assignment: "ON" | "OFF";
  is_washout: boolean;
  seconds_remaining: number;
}

/**
 * Một câu của "tóm tắt 3 câu" (AI-LAYER lớp 0 — analysis/narrate.py, gói
 * KẾT-QUẢ). Văn xuôi TEMPLATE tất định phía server, không LLM: mọi con số
 * trong `text` chép từ chính payload chứa nó; `refs` là đường dẫn JSON của
 * từng số — UI hiển thị làm nguồn (title/hover), không bao giờ tự viết lại
 * câu hay tự chế số ở client.
 */
export type CauBadge = "thi_nghiem" | "quan_sat" | "thieu_du_lieu";

export interface CauTomTat {
  text: string;
  badge: CauBadge;
  refs: string[];
}

/** Pooled experiment result from `GET /experiment/summary`. */
export interface ExperimentSummary {
  label: string;
  source: "experiment";
  /**
   * Nguồn dữ liệu của bản gộp (gói DEMO-THẬT): "real" — kết quả THẬT, mọi
   * phiên is_demo đã bị loại phía server; "demo" — bản gộp CHỈ dữ liệu mẫu,
   * `label` nói rõ MÔ PHỎNG. UI ở env=demo phải vẽ nhãn/watermark DEMO và
   * không bao giờ trình bày nó như kết quả thật.
   */
  env: "real" | "demo";
  /** Lý do tiếng Việt → số phiên bị giữ NGOÀI bản gộp (tiền đăng ký §8.2). */
  sessions_excluded?: Record<string, number>;
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
  /**
   * Tóm tắt 3 câu (kết luận / bằng chứng / việc nên làm) — server soạn bằng
   * template tất định, tôn trọng khóa §7. Optional vì payload cũ chưa mang.
   */
  tom_tat_3_cau?: CauTomTat[];
  /** Tổng lượt nhấp thô / hợp lệ của mọi phiên trong bản gộp (chỉ số chính). */
  raw_clicks?: number | null;
  valid_clicks?: number | null;
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
  /** Thẻ `forecast`: trung bình hậu nghiệm LƯỢT BẤM trên 1000 người-xem-giây
   *  (Gamma-Poisson, src/livelift/api/cards.py) — KHÔNG phải % tăng; chỉ dùng
   *  để xếp hạng. Thẻ `experiment`: mức chênh ước lượng của thí nghiệm. */
  estimate: number | null;
  ci_low: number | null; // experiment only
  ci_high: number | null; // experiment only
  auto_execute_in_s: number | null; // countdown when session mode = auto
}

/** `POST /sessions/{id}/actions/execute` — khớp `ExecuteOut` (schemas.py).
 *  `randomized`/`overlap_set`: máy chủ bốc thăm công bằng giữa các sản phẩm có
 *  dự báo ngang nhau, nên `product_id` được ghim có thể KHÁC sản phẩm trên thẻ. */
export interface ExecuteOut {
  action_id: string;
  block_index: number;
  action_type: "pin";
  source: "model";
  product_id: string;
  inner_propensity: number;
  randomized: boolean;
  overlap_set: string[];
  considered: { product_id: string; estimate: number; ci_low: number; ci_high: number }[];
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
  /** Dòng phụ máy chủ có thể gửi kèm (vd số link đo đã tạo). */
  secondary?: string | null;
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
  /** Cờ DỮ LIỆU MẪU (xem SessionSummary.is_demo) — báo cáo phiên demo phải
   * mang nhãn/watermark DEMO trên mọi con số. */
  is_demo: boolean;
  /**
   * Số bình luận TỔNG HỢP (nguồn Mô phỏng) trong phiên. Nguồn Mô phỏng bật trên
   * phiên CHẠY THỬ — mà phiên chạy thử có `is_demo=false` — nên riêng `is_demo`
   * không đủ nói báo cáo đang đếm câu do máy soạn. > 0 ⇒ trang phải dán nhãn
   * "dữ liệu tổng hợp". Optional: máy chủ cũ không gửi (khi đó không suy ra 0).
   */
  binh_luan_tong_hop?: number;
  tong_quan: BaoCaoTongQuan;
  tin_hieu: SignalStateItem[];
  nang_luc: CapabilityItem[];
  khoanh_khac: BaoCaoKhoanhKhac[];
  khoanh_khac_ghi_chu: string | null;
  phan_bo_y_dinh: BaoCaoYDinh;
  pii_da_che: Record<string, number>;
  /** null cho phiên quan sát — `nhan` nói rõ vì sao không có số nhân quả. */
  ket_qua_thi_nghiem: BaoCaoKetQuaThiNghiem | null;
  /** Tóm tắt 3 câu của phiên — cùng luật với ExperimentSummary.tom_tat_3_cau. */
  tom_tat_3_cau?: CauTomTat[];
  goi_y_chien_thuat: string[];
}

/** POST /demo/seed response. */
export interface DemoSeedResult {
  session_ids: string[];
  replay_session_id: string;
  product_ids: string[];
  shortlink_codes: string[];
}

/**
 * `GET /health` — trích phần chip DEMO/THẬT cần (gói DEMO-THẬT). `mode` là
 * chế độ dữ liệu TỔNG HỢP của kho phía server:
 * - "demo"  — kho CHỈ chứa dữ liệu mẫu;
 * - "real"  — không có phiên demo nào (kho rỗng cũng là "real");
 * - "mixed" — kho chứa CẢ HAI → UI phải cảnh báo rõ, dán nhãn từng phiên.
 * Đây là mô tả dữ liệu đang có, không thay công tắc chế độ phía client
 * (localStorage `ll.mode`).
 */
export interface HealthInfo {
  status: string;
  store_backend: string;
  mode: "demo" | "real" | "mixed";
  mode_counts: { demo: number; real: number };
  /** Câu giải thích tiếng Việt, hiển thị được nguyên văn trong tooltip chip. */
  mode_note: string;
  /** Các trường an toàn dữ liệu khác của /health (durable, storage_mode, ...). */
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Bộ thu bình luận chạy nền + nền tảng + đơn hàng (kiểm toán 17/09/2026)
// — SHARED API CONTRACT. Tên trường khớp nguyên văn src/livelift/api/routes/
// ingest.py (PlatformReadiness, IngestStatus) và routes/orders.py.
// ---------------------------------------------------------------------------

/** `GET /platforms` — nền tảng nào thu được NGAY, thiếu biến nào. Không bao
 *  giờ chứa giá trị khoá, chỉ TÊN biến còn thiếu. */
export interface PlatformReadiness {
  platform: "youtube" | "facebook" | "shopee" | "tiktok" | string;
  ten: string;
  ready: boolean;
  mode: "chinh_thuc" | "du_phong" | "khong_ho_tro";
  missing: string[];
  source_hint: string;
  note: string;
}

/** Vòng đời bộ thu (xem src/livelift/api/ingest_jobs.py). */
export type IngestState =
  | "chua_bat"
  | "dang_khoi_dong"
  | "dang_thu"
  | "dang_thu_lai"
  | "cho_len_song"
  | "da_dung"
  | "phien_ket_thuc"
  | "nguon_ket_thuc"
  | "loi";

/** `mo_phong` = phát một KỊCH BẢN BÌNH LUẬN TỔNG HỢP (do tác tử AI soạn, không
 *  phải bình luận người thật) như một buổi live, để kiểm thử đường ống đầu-cuối
 *  không cần khoá nền tảng — máy chủ chỉ cho dùng trên phiên demo/chạy thử. */
export type IngestPlatform = "youtube" | "facebook" | "shopee" | "mo_phong";

/** `GET|POST /sessions/{id}/ingest` và `POST .../ingest/stop`. */
export interface IngestStatus {
  session_id: string;
  state: IngestState;
  running: boolean;
  platform: string | null;
  source_id: string | null;
  resolved_source: string | null;
  started_at: string | null;
  ended_at: string | null;
  restarts: number;
  comments_seen: number;
  comments_posted: number;
  ticks_posted: number;
  last_viewers: number | null;
  write_failures: number;
  last_event_at: string | null;
  seconds_since_last_event: number | null;
  last_error: string | null;
  tick_error: string | null;
  api_usage_pct: number | null;
  /** Bản ghi đọc được lúc kho chập chờn, đang chờ ghi lại (giữ trong RAM). */
  pending_writes?: number;
  /** Bản ghi đã MẤT vì hàng đợi chờ ghi lại bị đầy. */
  dropped_writes?: number;
}

/** Một đơn hàng (`OrderOut`). Không có trường người mua nào (quy tắc cứng 1). */
export interface OrderItem {
  order_id: string;
  session_id: string;
  block_id: string | null;
  ts: string;
  product_id: string | null;
  qty: number;
  gross: number;
  fees: number;
  net_margin: number | null;
}

/** `GET /sessions/{id}/orders`. */
export interface OrderSummary {
  session_id: string;
  tong_don: number;
  tong_san_pham: number;
  tong_doanh_thu: number;
  don: OrderItem[];
}

/** `POST /sessions/{id}/orders/import`. */
export interface OrderImportResult {
  nhap_moi: number;
  trung_bo_qua: number;
  /** Tối đa 50 dòng lỗi đầu tiên; tổng thật ở `tong_loi`. */
  loi: { dong: number; ly_do: string }[];
  tong_loi?: number;
  tong_don: number;
  tong_doanh_thu: number;
}

/** Chart chrome tokens — v2 khớp thang mặt phẳng xanh đêm của gói SKIN
 *  (tailwind.config.ts giữ cùng bộ giá trị; số contrast trong globals.css). */
export const CHART = {
  surface: "#0d0f16",
  grid: "#1b1e28",
  axis: "#191d29",
  mut: "#7d8494", // gridline/axis chrome only — dưới AA trên plane axis, chỉ trang trí
  dim: "#8a91a3", // axis TEXT: 6.35:1 on page … 5.33:1 on axis, clears AA everywhere
  sec: "#b6bcc8",
  ink: "#f4f5f8",
  s1: "#3987e5",
  s2: "#d95926",
  s3: "#199e70", // nhịp bình luận — slot 3 (aqua) của bảng màu đã kiểm định
  on: "#8b7bff", // block strip ON (slot 7 violet — not used by any chart series)
} as const;
