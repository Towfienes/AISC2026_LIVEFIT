/**
 * Mock data engine — used when NEXT_PUBLIC_MOCK=1 or the API is unreachable,
 * so the desk demos standalone. All mock text is Vietnamese and pre-"scrubbed"
 * (mock comments never contain raw PII; a few carry redaction tokens to show
 * the PII filter at work).
 */

import type {
  ActionCardData,
  Assignment,
  BlockInfo,
  CommentItem,
  IntentLabel,
  Phase,
  Product,
  SessionRecording,
  SessionSummary,
  Tick,
} from "./types";
import { sanitizeCards } from "./api";

/** Deterministic PRNG (mulberry32) so mock sessions replay identically. */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const MOCK_PRODUCTS: Product[] = [
  { product_id: "P01", name: "Váy hoa nhí vintage", category: "váy", price: 259000, stock: 42 },
  { product_id: "P02", name: "Áo thun cotton oversize", category: "áo", price: 129000, stock: 120 },
  { product_id: "P03", name: "Quần jean ống rộng", category: "quần", price: 319000, stock: 65 },
  { product_id: "P04", name: "Áo khoác gió unisex", category: "áo khoác", price: 349000, stock: 30 },
  { product_id: "P05", name: "Chân váy tennis xếp ly", category: "váy", price: 179000, stock: 80 },
  { product_id: "P06", name: "Sơ mi lụa công sở", category: "áo", price: 289000, stock: 55 },
];

/** (scrubbed text, intent) pool — Vietnamese live-commerce chatter. */
const COMMENT_POOL: [string, IntentLabel][] = [
  ["cái váy này giá nhiêu v shop", "hoi_gia"],
  ["ib mình giá bộ đang lên với", "hoi_gia"],
  ["áo khoác bao nhiêu tiền ạ", "hoi_gia"],
  ["giá sale hôm nay còn không shop", "hoi_gia"],
  ["có size M không ạ", "hoi_size"],
  ["form này 60kg mặc vừa không shop", "hoi_size"],
  ["còn màu be size L không", "hoi_size"],
  ["cao 1m55 mặc váy này dài không", "hoi_size"],
  ["sao đắt vậy, bên kia có 99k à", "che_dat"],
  ["giá này hơi chát so với chất vải", "che_dat"],
  ["hôm trước thấy rẻ hơn mà ta", "che_dat"],
  ["chốt đơn áo đen size L nha shop", "chot_don"],
  ["mình lấy 2 cái váy hoa nhé", "chot_don"],
  ["chốt quần jean size 29 nha", "chot_don"],
  ["em chốt sơ mi trắng, gọi em nhé [SĐT đã ẩn]", "chot_don"],
  ["ship về Đà Nẵng mất mấy ngày v", "van_chuyen"],
  ["freeship không shop ơi", "van_chuyen"],
  ["gửi về [ĐỊA CHỈ đã ẩn] được không ạ", "van_chuyen"],
  ["đơn [MÃ ĐƠN đã ẩn] của em tới đâu rồi", "van_chuyen"],
  ["chị host dễ thương quá", "khac"],
  ["đợi hoài chưa thấy lên mẫu mới", "khac"],
  ["nhạc gì hay vậy mn", "khac"],
  ["hôm nay live tới mấy giờ", "khac"],
  ["cho xin cận vải với ạ", "khac"],
];

const PII_KINDS_BY_TOKEN: [string, string][] = [
  ["[SĐT đã ẩn]", "phone"],
  ["[ĐỊA CHỈ đã ẩn]", "address"],
  ["[MÃ ĐƠN đã ẩn]", "order_code"],
];

function phaseFor(index: number, nBlocks: number): Phase {
  const third = nBlocks / 3;
  if (index < third) return "early";
  if (index < 2 * third) return "mid";
  return "late";
}

/**
 * Balanced switchback schedule: per phase, half ON / half OFF, order shuffled
 * with the seeded RNG (mirrors core.assigner defaults: 5-min blocks, p=0.5).
 */
export function generateMockBlocks(durationMin: number, seed: number): BlockInfo[] {
  const rng = mulberry32(seed);
  const blockMin = 5;
  const n = Math.floor(durationMin / blockMin);
  const blocks: BlockInfo[] = [];
  for (let p = 0; p < 3; p++) {
    const lo = Math.floor((p * n) / 3);
    const hi = Math.floor(((p + 1) * n) / 3);
    const size = hi - lo;
    const arms: Assignment[] = [];
    for (let i = 0; i < size; i++) arms.push(i < Math.ceil(size / 2) ? "ON" : "OFF");
    for (let i = arms.length - 1; i > 0; i--) {
      const j = Math.floor(rng() * (i + 1));
      [arms[i], arms[j]] = [arms[j], arms[i]];
    }
    for (let i = lo; i < hi; i++) {
      blocks.push({
        block_index: i,
        phase: phaseFor(i, n),
        assignment: arms[i - lo],
        is_washout: false,
        start_offset_s: i * blockMin * 60,
        end_offset_s: (i + 1) * blockMin * 60,
        propensity: 0.5,
      });
    }
  }
  return blocks;
}

function assignmentAt(blocks: BlockInfo[], offsetS: number): Assignment | null {
  const b = blocks.find((x) => offsetS >= x.start_offset_s && offsetS < x.end_offset_s);
  return b?.assignment ?? null;
}

function buildCards(
  products: Product[],
  pinnedId: string,
  offsetS: number,
  rng: () => number,
): ActionCardData[] {
  const others = products.filter((p) => p.product_id !== pinnedId);
  const a = others[Math.floor(rng() * others.length)];
  let b = others[Math.floor(rng() * others.length)];
  if (b.product_id === a.product_id) b = others[(others.indexOf(a) + 1) % others.length];
  const lift = 0.1 + rng() * 0.15;
  const half = 0.08 + rng() * 0.08;
  const cards: ActionCardData[] = [
    {
      card_id: `c-${offsetS}-1`,
      rank: 1,
      headline: `Ghim lại: ${a.name}`,
      product_id: a.product_id,
      product_name: a.name,
      rationale: "Khối BẬT gần nhất tăng nhịp click so với khối TẮT liền kề cùng giai đoạn.",
      source: "experiment",
      estimate: lift,
      ci_low: lift - half,
      ci_high: lift + half,
      auto_execute_in_s: 20,
    },
    {
      card_id: `c-${offsetS}-2`,
      rank: 2,
      headline: `Chuẩn bị lên: ${b.name}`,
      product_id: b.product_id,
      product_name: b.name,
      rationale: "Mô hình dự báo nhu cầu tăng trong khung giờ tới theo lịch sử cùng khung.",
      source: "forecast",
      estimate: 0.05 + rng() * 0.1,
      ci_low: null,
      ci_high: null,
      auto_execute_in_s: 45,
    },
    {
      card_id: `c-${offsetS}-3`,
      rank: 3,
      headline: "Nhắc giá + mã freeship",
      product_id: pinnedId,
      product_name: products.find((p) => p.product_id === pinnedId)?.name ?? pinnedId,
      rationale: "Mô hình dự báo tỷ lệ chốt tăng khi nhắc ưu đãi vận chuyển lúc bình luận hỏi ship tăng.",
      source: "forecast",
      estimate: 0.04 + rng() * 0.06,
      ci_low: null,
      ci_high: null,
      auto_execute_in_s: 70,
    },
  ];
  return sanitizeCards(cards);
}

/** Generate the full recording of one mock session (deterministic per seed). */
export function generateRecording(session: SessionSummary, seed: number): SessionRecording {
  const rng = mulberry32(seed);
  const durationS = session.planned_duration_min * 60;
  const blocks = generateMockBlocks(session.planned_duration_min, seed + 7);
  const startMs = session.start_ts ? Date.parse(session.start_ts) : Date.now();

  const ticks: Tick[] = [];
  const comments: CommentItem[] = [];
  const cardsTimeline: { offset_s: number; cards: ActionCardData[] }[] = [];

  let viewers = 70 + rng() * 15;
  let pinnedIdx = 0;
  let commentSeq = 0;

  for (let t = 0; t < durationS; t += 30) {
    const arm = assignmentAt(blocks, t);
    // random walk 60–120, small lift while ON
    viewers += (rng() - 0.5) * 8 + (arm === "ON" ? 0.6 : -0.3);
    viewers = Math.min(120, Math.max(60, viewers));
    if (t > 0 && t % 240 === 0) pinnedIdx = (pinnedIdx + 1) % MOCK_PRODUCTS.length;
    const pinned = MOCK_PRODUCTS[pinnedIdx];

    const baseClickPerMin = 2.2 + 1.1 * Math.sin((t / durationS) * Math.PI);
    const clickPerMin = baseClickPerMin * (arm === "ON" ? 1.4 : 1.0) * (0.8 + rng() * 0.5);
    const clicks30 = Math.max(0, Math.round(clickPerMin / 2 + (rng() - 0.5)));
    const commentRate = viewers * (0.045 + rng() * 0.02);

    ticks.push({
      offset_s: t,
      ts_bucket: new Date(startMs + t * 1000).toISOString(),
      viewers: Math.round(viewers),
      comment_rate: Math.round(commentRate * 10) / 10,
      like_rate: Math.round(viewers * 0.3),
      click_count: clicks30,
      pinned_product_id: pinned.product_id,
      baseline_viewers: Math.round(72 + 18 * Math.sin((t / durationS) * Math.PI)),
      baseline_clicks_per_min: Math.round(baseClickPerMin * 10) / 10,
    });

    // comments inside this 30s bucket
    const nComments = Math.max(0, Math.round(commentRate / 2 + (rng() - 0.5) * 2));
    for (let i = 0; i < nComments; i++) {
      const [text, intent] = COMMENT_POOL[Math.floor(rng() * COMMENT_POOL.length)];
      const off = t + Math.floor(rng() * 30);
      comments.push({
        comment_id: `m-${seed}-${commentSeq++}`,
        offset_s: off,
        ts: new Date(startMs + off * 1000).toISOString(),
        text_scrubbed: text,
        intent_label: intent,
        pii_kinds: PII_KINDS_BY_TOKEN.filter(([tok]) => text.includes(tok)).map(([, k]) => k),
      });
    }

    if (t % 120 === 0) {
      cardsTimeline.push({
        offset_s: t,
        cards: buildCards(MOCK_PRODUCTS, MOCK_PRODUCTS[pinnedIdx].product_id, t, rng),
      });
    }
  }
  comments.sort((a, b) => a.offset_s - b.offset_s);

  return {
    session,
    blocks,
    ticks,
    comments,
    cards_timeline: cardsTimeline,
    products: MOCK_PRODUCTS,
    duration_s: durationS,
  };
}

/**
 * Demo clock for the mock "live" session: starts ~40% in, advances at 6x so a
 * 90-minute session plays out quickly, and is anchored to the wall clock so the
 * desk and the host screen (separate tabs) stay in sync. Loops when it reaches
 * the end.
 */
export function mockElapsedS(durationS: number): number {
  const base = Math.min(2100, Math.floor(durationS * 0.4));
  const span = Math.max(60, durationS - base);
  return base + (((Date.now() / 1000) * 6) % span);
}

export const MOCK_SESSIONS: SessionSummary[] = [
  {
    session_id: "mock-live-01",
    platform: "youtube",
    title: "Phiên tối — Thời trang nữ (25/08)",
    mode: "suggest",
    status: "live",
    planned_duration_min: 90,
    start_ts: "2026-08-25T13:00:00Z", // 20:00 Asia/Ho_Chi_Minh
    end_ts: null,
  },
  {
    session_id: "mock-ended-01",
    platform: "youtube",
    title: "Phiên tối — Thời trang nữ (22/08)",
    mode: "suggest",
    status: "ended",
    planned_duration_min: 90,
    start_ts: "2026-08-22T13:00:00Z",
    end_ts: "2026-08-22T14:30:00Z",
  },
  {
    session_id: "mock-ended-02",
    platform: "facebook",
    title: "Phiên trưa — Phụ kiện (20/08)",
    mode: "auto",
    status: "ended",
    planned_duration_min: 60,
    start_ts: "2026-08-20T05:00:00Z",
    end_ts: "2026-08-20T06:00:00Z",
  },
];

const RECORDING_SEEDS: Record<string, number> = {
  "mock-live-01": 20260825,
  "mock-ended-01": 20260822,
  "mock-ended-02": 20260820,
};

const recordingCache = new Map<string, SessionRecording>();

export function mockRecording(sessionId: string): SessionRecording {
  let rec = recordingCache.get(sessionId);
  if (!rec) {
    const session = MOCK_SESSIONS.find((s) => s.session_id === sessionId) ?? MOCK_SESSIONS[0];
    rec = generateRecording(session, RECORDING_SEEDS[session.session_id] ?? 1234);
    recordingCache.set(sessionId, rec);
  }
  return rec;
}

/**
 * Replay re-ranking when products are marked "hết hàng": drop their cards and
 * back-fill from remaining products as forecast-sourced suggestions (a forecast
 * card never carries a CI — E2-04).
 */
export function recomputeCards(
  rec: SessionRecording,
  offsetS: number,
  excludedIds: string[],
): ActionCardData[] {
  const entry =
    [...rec.cards_timeline].reverse().find((e) => e.offset_s <= offsetS) ?? rec.cards_timeline[0];
  if (!entry) return [];
  const kept = entry.cards.filter((c) => !excludedIds.includes(c.product_id));
  const usedIds = new Set(kept.map((c) => c.product_id));
  const rng = mulberry32(offsetS + excludedIds.length * 97 + 3);
  const fill = rec.products.filter(
    (p) => !excludedIds.includes(p.product_id) && !usedIds.has(p.product_id),
  );
  const out = [...kept];
  while (out.length < 3 && fill.length > 0) {
    const p = fill.shift()!;
    out.push({
      card_id: `refill-${offsetS}-${p.product_id}`,
      rank: out.length + 1,
      headline: `Thay thế: ${p.name}`,
      product_id: p.product_id,
      product_name: p.name,
      rationale: "Xếp hạng lại sau khi loại sản phẩm hết hàng — ứng viên kế tiếp theo dự báo.",
      source: "forecast",
      estimate: 0.03 + rng() * 0.08,
      ci_low: null,
      ci_high: null,
      auto_execute_in_s: null,
    });
  }
  return sanitizeCards(out.map((c, i) => ({ ...c, rank: i + 1 })));
}
