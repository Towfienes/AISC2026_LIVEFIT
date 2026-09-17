"use client";

/**
 * Data orchestration for the control desk.
 *
 * Live mode: REST polling every 5 s + WebSocket push (/ws/{sessionId}).
 * Mock mode: NEXT_PUBLIC_MOCK=1 or unreachable API — deterministic client-side
 * generator (mock.ts) driven by an accelerated demo clock.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  endSession as apiEndSession,
  executeCard as apiExecute,
  getCards,
  getComments,
  getSchedule,
  getState,
  getTicks,
  listProducts,
  listSessions,
  postOverride,
  sanitizeCards,
} from "./api";
import { MOCK_SESSIONS, mockElapsedS, mockRecording } from "./mock";
import { pickCurrentSession } from "./pickSession";
import type {
  ActionCardData,
  AutopilotState,
  BlockInfo,
  CurrentBlock,
  CommentItem,
  ConnectionKind,
  OverrideReason,
  Product,
  SessionMode,
  SessionSummary,
  Tick,
  WsMessage,
} from "./types";
import { useLiveSocket, type SocketStatus } from "./useLiveSocket";

const MOCK_FORCED = process.env.NEXT_PUBLIC_MOCK === "1";
const POLL_MS = 5000;

// ---------------------------------------------------------------------------
// Lỗi lệnh vận hành (gói C1 — giới hạn #6)
// ---------------------------------------------------------------------------

/**
 * Lỗi của một lệnh trên bàn (Thực hiện thẻ, Kết thúc phiên), mang cờ `network`.
 *
 * VÌ SAO (giới hạn #6, ảnh d02): bấm Thực hiện trong khối TẮT, máy chủ trả 409
 * kèm câu tiếng Việt rất rõ ("Khối TẮT: đội vận hành làm theo cách thường
 * lệ…"), nhưng `catch {}` cũ nuốt câu đó và ném câu cố định "kiểm tra kết nối
 * API" — người vận hành đi kiểm tra dây mạng trong khi mạng không hỏng gì.
 * `request()` trong api.ts đã đưa `detail` của máy chủ vào `Error.message`,
 * nên ở đây chỉ việc GIỮ nó; chỉ lỗi mạng thật mới được nói "kiểm tra kết nối".
 */
export class DeskCommandError extends Error {
  readonly network: boolean;
  constructor(message: string, network: boolean) {
    super(message);
    this.name = "DeskCommandError";
    this.network = network;
  }
}

/**
 * Lỗi MẠNG thật: fetch không tới được máy chủ (TypeError "Failed to fetch"),
 * bị huỷ vì quá thời gian chờ (AbortError), hoặc thông điệp mạng của trình
 * duyệt khác. Một câu trả lời HTTP có mã lỗi KHÔNG phải lỗi mạng.
 */
export function isNetworkError(e: unknown): boolean {
  if (e instanceof TypeError) return true;
  const name =
    e != null && typeof e === "object" && "name" in e ? String((e as { name: unknown }).name) : "";
  if (name === "AbortError" || name === "TimeoutError") return true;
  const msg = e instanceof Error ? e.message : typeof e === "string" ? e : "";
  return /failed to fetch|networkerror|network request failed|load failed|fetch failed/i.test(msg);
}

/** Chuyển một lỗi bất kỳ thành DeskCommandError, giữ NGUYÊN câu của máy chủ. */
export function toCommandError(e: unknown, fallback: string): DeskCommandError {
  if (e instanceof DeskCommandError) return e;
  if (isNetworkError(e)) {
    return new DeskCommandError(
      "Không gửi được lệnh tới máy chủ — mất kết nối hoặc máy chủ không trả lời.",
      true,
    );
  }
  const raw = e instanceof Error ? e.message.trim() : "";
  if (!raw) return new DeskCommandError(fallback, false);
  // Máy chủ không kèm câu tiếng Việt: request() rơi về "API 500 …" — vẫn là
  // máy chủ TỪ CHỐI, không phải mất mạng, nên nói đúng như vậy.
  if (/^API \d{3}\b/.test(raw)) return new DeskCommandError(`${fallback} (${raw})`, false);
  return new DeskCommandError(raw, false);
}

// ---------------------------------------------------------------------------
// Kết quả lệnh Thực hiện (gói C3 — bốc thăm giữa các thẻ ngang nhau)
// ---------------------------------------------------------------------------

/**
 * Phần hẹp của `ExecuteOut` (src/livelift/api/schemas.py) mà bàn cần đọc.
 *
 * `executeCard` trong api.ts (tệp đóng băng) khai báo kiểu trả về là
 * `{ ok, action_id? }` — thiếu `product_id`, `randomized`, `overlap_set` mà
 * máy chủ THẬT SỰ gửi. Đọc qua interface cục bộ này, mọi trường tuỳ chọn để
 * một máy chủ cũ không làm vỡ bàn.
 */
interface ExecuteOutWire {
  action_id?: string;
  product_id?: string | null;
  randomized?: boolean;
  overlap_set?: string[] | null;
}

/** Điều máy chủ đã làm sau một cú bấm Thực hiện. */
export interface ExecuteOutcome {
  cardProductId: string;
  cardProductName: string;
  /** Sản phẩm máy chủ THẬT SỰ ghim (có thể khác thẻ vừa bấm). */
  pinnedProductId: string;
  pinnedProductName: string;
  /** Máy chủ bốc thăm trong tập sản phẩm có dự báo ngang nhau. */
  randomized: boolean;
  /** Số sản phẩm trong tập bốc thăm; null khi máy chủ không gửi tập. */
  poolSize: number | null;
}

/**
 * Đọc phản hồi của `POST /actions/execute` thành điều máy chủ đã làm.
 *
 * Hàm thuần (không đụng state React) để test chạy được bằng dữ liệu THẬT của
 * máy chủ. `raw` là `unknown` có chủ ý: tệp api.ts khai báo thiếu trường, nên
 * mọi trường đều được kiểm kiểu trước khi dùng — máy chủ cũ không gửi
 * `product_id` thì coi như ghim đúng thẻ vừa bấm, không đoán gì thêm.
 */
export function readExecuteOutcome(
  card: { product_id: string; product_name: string },
  raw: unknown,
  nameOf: (productId: string) => string,
): ExecuteOutcome {
  const wire: ExecuteOutWire = raw != null && typeof raw === "object" ? (raw as ExecuteOutWire) : {};
  const pinnedId =
    typeof wire.product_id === "string" && wire.product_id ? wire.product_id : card.product_id;
  const pool = wire.overlap_set;
  return {
    cardProductId: card.product_id,
    cardProductName: card.product_name,
    pinnedProductId: pinnedId,
    pinnedProductName: pinnedId === card.product_id ? card.product_name : nameOf(pinnedId),
    randomized: wire.randomized === true,
    poolSize: Array.isArray(pool) ? pool.length : null,
  };
}

/**
 * Câu xác nhận cho người vận hành — null khi máy chủ ghim đúng sản phẩm trên
 * thẻ mà không bốc thăm (không có gì bất ngờ để giải thích).
 *
 * VÌ SAO (P0, ảnh f08): bấm thẻ "Ghim Bình giữ nhiệt", máy chủ bốc thăm công
 * bằng và ghim "Sáp thơm", bàn im lặng. Người vận hành tưởng hệ thống lỗi và
 * ghim tay lại — đúng hành động làm bẩn dữ liệu thí nghiệm.
 */
export function executeNotice(o: ExecuteOutcome | null): string | null {
  if (!o) return null;
  const differs = o.pinnedProductId !== o.cardProductId;
  if (!o.randomized && !differs) return null;
  const tail = differs ? ` (thẻ bạn bấm là ${o.cardProductName})` : "";
  if (o.randomized) {
    const pool =
      o.poolSize != null && o.poolSize > 1
        ? `giữa ${o.poolSize} sản phẩm ngang nhau`
        : "giữa các sản phẩm ngang nhau";
    return (
      `Hệ thống bốc thăm công bằng ${pool}, đã ghim: ${o.pinnedProductName}${tail}. ` +
      "Đây là chủ ý để đo cho công bằng — không cần ghim tay lại."
    );
  }
  return `Máy chủ đã ghim: ${o.pinnedProductName}${tail}. Không cần ghim tay lại.`;
}

export interface DeskState {
  connection: ConnectionKind;
  wsStatus: SocketStatus;
  sessions: SessionSummary[];
  sessionId: string | null;
  setSessionId: (id: string) => void;
  session: SessionSummary | null;
  elapsedS: number;
  durationS: number;
  viewers: number;
  pinned: Product | null;
  blocks: BlockInfo[];
  /** Operator-only: the block the session is in right now (null on the host view). */
  currentBlock: CurrentBlock | null;
  /**
   * Cam kết thiết kế (SHA-256 tham số + seed) của phiên đang xem — hiển thị
   * rút gọn trên thanh trạng thái. Operator-only; null khi chưa có lịch.
   */
  designHash: string | null;
  /**
   * Máy tự lái phía máy chủ (phiên mode="auto") + cảnh báo im lặng — hiển thị
   * nguyên văn ở cột hành động. Null cho phiên gợi ý/mock. Operator-only (L6).
   */
  autopilot: AutopilotState | null;
  /** Lý do thẻ rỗng THEO THIẾT KẾ từ máy chủ (phiên đã kết thúc, phân tích…). */
  cardsNote: string | null;
  /** Vietnamese warning when a data source is failing; null when all is well. */
  degraded: string | null;
  ticks: Tick[];
  comments: CommentItem[]; // ascending by offset
  cards: ActionCardData[];
  executedCardIds: ReadonlySet<string>;
  mode: SessionMode;
  setMode: (m: SessionMode) => void;
  canToggleMode: boolean;
  products: Product[];
  /**
   * Gửi lệnh Thực hiện. Trả về điều máy chủ đã làm (sản phẩm thật sự được
   * ghim, có bốc thăm không) — null khi không gửi gì. Ném DeskCommandError khi
   * máy chủ từ chối hoặc mất mạng (thẻ đã được trả lại danh sách).
   */
  execute: (card: ActionCardData) => Promise<ExecuteOutcome | null>;
  skip: (cardId: string) => void;
  override: (productId: string, reason: OverrideReason) => Promise<void>;
  /** True when the selected session is live on a real API (not mock). */
  canEndSession: boolean;
  /** Gọi endpoint kết thúc phiên (POST /sessions/{id}/end) — live mode only. */
  endSession: () => Promise<void>;
}

export interface UseDeskOptions {
  /** Switch to the deterministic mock demo (e.g. the desk empty-state button). */
  forceMock?: boolean;
  /**
   * Deep link `/desk?session=ID` (spec UX-FLOW luồng 3, gói WIZARD): wizard
   * Chuẩn bị phiên bấm "Bắt đầu phát sóng" rồi chuyển thẳng sang bàn — bàn
   * phải mở ĐÚNG phiên vừa tạo, không phải phiên live đầu tiên trong danh
   * sách (hai phiên live song song là tình huống thật ở Live Lab).
   */
  preferredSessionId?: string | null;
}

export function useDesk(opts?: UseDeskOptions): DeskState {
  const forceMock = opts?.forceMock === true;
  const preferredSessionId = opts?.preferredSessionId ?? null;
  const [connection, setConnection] = useState<ConnectionKind>(
    MOCK_FORCED ? "mock" : "connecting",
  );
  const [sessions, setSessions] = useState<SessionSummary[]>(MOCK_FORCED ? MOCK_SESSIONS : []);
  const [sessionId, setSessionId] = useState<string | null>(
    MOCK_FORCED ? MOCK_SESSIONS[0].session_id : null,
  );
  const [elapsedS, setElapsedS] = useState(0);
  const [viewers, setViewers] = useState(0);
  const [pinned, setPinned] = useState<Product | null>(null);
  const [blocks, setBlocks] = useState<BlockInfo[]>([]);
  const [ticks, setTicks] = useState<Tick[]>([]);
  const [comments, setComments] = useState<CommentItem[]>([]);
  const [cards, setCards] = useState<ActionCardData[]>([]);
  const [mode, setModeState] = useState<SessionMode>("suggest");
  const [products, setProducts] = useState<Product[]>([]);
  const [skippedIds, setSkippedIds] = useState<Set<string>>(new Set());
  const [executedIds, setExecutedIds] = useState<Set<string>>(new Set());
  const [manualPin, setManualPin] = useState<{ product: Product; atS: number } | null>(null);
  /** Current block, operator view only — never handed to the host screen. */
  const [currentBlock, setCurrentBlock] = useState<CurrentBlock | null>(null);
  /** Design commitment hash of the selected session (operator view only). */
  const [designHash, setDesignHash] = useState<string | null>(null);
  /** Máy tự lái + cảnh báo im lặng của phiên auto (operator view only). */
  const [autopilot, setAutopilot] = useState<AutopilotState | null>(null);
  /** Lý do thẻ rỗng theo thiết kế, nguyên văn từ máy chủ. */
  const [cardsNote, setCardsNote] = useState<string | null>(null);
  /** Vietnamese warning when one data source is failing (see the poll loop). */
  const [degraded, setDegraded] = useState<string | null>(null);
  /** Session start, used to turn API timestamps into seconds-since-start. */
  const sessionStartIso = useRef<string | null>(null);
  /**
   * Mốc nước cao nhất của bình luận đã nhận — poll chỉ lấy phần MỚI hơn mốc
   * này. Là ref theo PHIÊN: phải trả về 0 mỗi lần đổi phiên (xem effect reset
   * ngay dưới), nếu không phiên ngắn hơn phiên trước sẽ không có bình luận nào
   * vượt mốc và feed đứng im ở "Chưa có bình luận nào" — một câu SAI trên một
   * buổi có hàng nghìn bình luận (bắt gặp trên bàn buổi Achan 11/09: chọn buổi
   * Trang sức 138 phút rồi đổi sang Achan 117 phút ⇒ 6.586 bình luận biến mất).
   */
  const lastCommentOffset = useRef(0);

  const session = useMemo(
    () => sessions.find((s) => s.session_id === sessionId) ?? null,
    [sessions, sessionId],
  );
  const durationS = (session?.planned_duration_min ?? 90) * 60;
  sessionStartIso.current = session?.start_ts ?? null;

  // -------------------------------------------------------------------------
  // Probe the API once; fall back to mock if unreachable.
  // -------------------------------------------------------------------------
  useEffect(() => {
    if (MOCK_FORCED) return;
    if (forceMock) {
      setSessions(MOCK_SESSIONS);
      setSessionId(MOCK_SESSIONS[0].session_id);
      setConnection("mock");
      return;
    }
    let cancelled = false;
    listSessions(2500)
      .then((list) => {
        if (cancelled) return;
        setSessions(list);
        // Deep link thắng heuristic; sau đó là phiên live MỚI NHẤT rồi phiên
        // mới nhất nói chung (pickSession.ts — sửa gốc bug đồng hồ 328:36:29:
        // "live đầu tiên trong danh sách" từng vớ phải phiên mô phỏng cũ chưa
        // được kết thúc).
        const picked = pickCurrentSession(list, preferredSessionId);
        setSessionId(picked ? picked.session_id : null);
        setConnection("live");
      })
      .catch(() => {
        if (cancelled) return;
        setSessions(MOCK_SESSIONS);
        setSessionId(MOCK_SESSIONS[0].session_id);
        setConnection("mock");
      });
    return () => {
      cancelled = true;
    };
  }, [forceMock, preferredSessionId]);

  // Reset per-session UI state on switch.
  useEffect(() => {
    setSkippedIds(new Set());
    setExecutedIds(new Set());
    setManualPin(null);
    setTicks([]);
    setComments([]);
    lastCommentOffset.current = 0;
    setCards([]);
    // Lịch khối là dữ liệu theo phiên: không được hiển thị lịch của phiên cũ
    // trên trục thời gian của phiên mới trong lúc chờ poll đầu tiên.
    setBlocks([]);
    setCurrentBlock(null);
    // Cam kết thiết kế thuộc về đúng một phiên: giữ lại hash phiên cũ trong
    // lúc chờ poll đầu tiên sẽ là một cam kết SAI trên màn hình.
    setDesignHash(null);
    // Trạng thái tự lái + lý do thẻ rỗng cũng thuộc về đúng một phiên.
    setAutopilot(null);
    setCardsNote(null);
    // Sản phẩm đang ghim cũng thuộc về đúng một phiên: sản phẩm của phiên cũ
    // không được đứng trên hero phiên mới trong lúc chờ poll đầu tiên.
    setPinned(null);
  }, [sessionId]);

  // -------------------------------------------------------------------------
  // MOCK mode: reveal the pre-generated recording along the demo clock.
  // -------------------------------------------------------------------------
  useEffect(() => {
    if (connection !== "mock" || !sessionId) return;
    const rec = mockRecording(sessionId);
    setBlocks(rec.blocks);
    setProducts(rec.products);
    setModeState(rec.session.mode);
    const step = () => {
      const el = rec.session.status === "ended" ? rec.duration_s : mockElapsedS(rec.duration_s);
      setElapsedS(el);
      const visTicks = rec.ticks.filter((t) => t.offset_s <= el);
      setTicks(visTicks);
      setComments(rec.comments.filter((c) => c.offset_s <= el).slice(-60));
      const last = visTicks[visTicks.length - 1];
      setViewers(last?.viewers ?? 0);
      const entry =
        [...rec.cards_timeline].reverse().find((e) => e.offset_s <= el) ?? rec.cards_timeline[0];
      setCards(entry ? sanitizeCards(entry.cards) : []);
    };
    step();
    const timer = setInterval(step, 1000);
    return () => clearInterval(timer);
  }, [connection, sessionId]);

  // Mock pinned product: manual pin (recent) wins over the tick's pinned id.
  useEffect(() => {
    if (connection !== "mock") return;
    const last = ticks[ticks.length - 1];
    if (manualPin && elapsedS - manualPin.atS < 240) {
      setPinned(manualPin.product);
      return;
    }
    const p = products.find((x) => x.product_id === last?.pinned_product_id) ?? null;
    setPinned(p);
  }, [connection, ticks, manualPin, elapsedS, products]);

  // -------------------------------------------------------------------------
  // LIVE mode: initial load + 5 s polling.
  // -------------------------------------------------------------------------
  useEffect(() => {
    if (connection !== "live" || !sessionId) return;
    let cancelled = false;
    const pull = async () => {
      // allSettled, not all: one failing source must degrade ONE panel, never
      // freeze the whole desk. Promise.all rejected the entire poll when a
      // single call failed and the catch silently kept the empty first render,
      // so the desk looked "connected" but never updated (incident 27/08).
      const [stR, tksR, cdsR, cmsR, schR] = await Promise.allSettled([
        getState(sessionId),
        getTicks(sessionId, sessionStartIso.current),
        getCards(sessionId),
        getComments(sessionId, sessionStartIso.current),
        // The switchback schedule is static once drawn, but fetching it in the
        // same allSettled poll keeps one failure model (degrade one panel).
        // Without it, live mode never set `blocks` and the desk showed an
        // empty BlockStrip while the mock demo looked perfect.
        getSchedule(sessionId),
      ]);
      if (cancelled) return;

      if (stR.status === "fulfilled") {
        const st = stR.value;
        setElapsedS(st.elapsed_s);
        setPinned(st.pinned_product ?? null);
        setModeState(st.mode);
        setCurrentBlock(st.current_block ?? null);
        setDesignHash(st.design_hash ?? null);
        setAutopilot(st.autopilot ?? null);
        setCardsNote(st.cards_note ?? null);
        // Gói C4: trạng thái phiên cũng đi theo poll, không chỉ theo WebSocket.
        // Phiên bị kết thúc từ máy khác (hoặc tự hết giờ) trong lúc socket đang
        // nối lại thì danh sách phiên nạp một lần lúc mở bàn sẽ mãi "đang live"
        // — hero tiếp tục in "BẬT — Chuyển khối sau…" trên một phiên đã đóng.
        const status = st.status;
        if (status) {
          setSessions((prev) =>
            prev.some((s) => s.session_id === sessionId && s.status !== status)
              ? prev.map((s) => (s.session_id === sessionId ? { ...s, status } : s))
              : prev,
          );
        }
      }
      if (tksR.status === "fulfilled") {
        setTicks(tksR.value);
        const last = tksR.value[tksR.value.length - 1];
        if (last) setViewers(last.viewers);
      }
      if (cdsR.status === "fulfilled") setCards(cdsR.value);
      if (schR.status === "fulfilled") setBlocks(schR.value);
      if (cmsR.status === "fulfilled" && cmsR.value.length) {
        const fresh = cmsR.value.filter((c) => c.offset_s > lastCommentOffset.current);
        if (fresh.length) {
          lastCommentOffset.current = fresh[fresh.length - 1].offset_s;
          // Dedupe theo comment_id: bình luận có thể đã tới trước qua WebSocket.
          setComments((prev) => {
            const seen = new Set(prev.map((c) => c.comment_id));
            const add = fresh.filter((c) => !seen.has(c.comment_id));
            return add.length ? [...prev, ...add].slice(-200) : prev;
          });
        }
      }

      const failed = [
        stR.status === "rejected" ? "trạng thái phiên" : null,
        tksR.status === "rejected" ? "người xem" : null,
        cdsR.status === "rejected" ? "thẻ hành động" : null,
        cmsR.status === "rejected" ? "bình luận" : null,
        schR.status === "rejected" ? "lịch khối" : null,
      ].filter(Boolean) as string[];
      setDegraded(failed.length ? `Không tải được: ${failed.join(", ")}` : null);
    };
    pull();
    const timer = setInterval(pull, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [connection, sessionId]);

  // Live mode: 1 s local clock between polls — CHỈ khi phiên đang phát thật.
  // Phiên đã kết thúc có elapsed đóng băng ở end_ts; để đồng hồ cục bộ tự
  // cộng thêm là hiển thị 01:30:02/01:30:00 giữa hai lần poll (gói DESK-HOST).
  const sessionStatus = session?.status ?? null;
  useEffect(() => {
    if (connection !== "live" || sessionStatus !== "live") return;
    const timer = setInterval(() => setElapsedS((e) => e + 1), 1000);
    return () => clearInterval(timer);
  }, [connection, sessionStatus]);

  // Live mode: load the product catalog once so a WebSocket "state" patch
  // ({pinned_product_id}) can be resolved to a displayable product.
  useEffect(() => {
    if (connection !== "live") return;
    let cancelled = false;
    listProducts()
      .then((ps) => {
        if (!cancelled) setProducts(ps);
      })
      .catch(() => {
        // non-fatal: the 5 s state poll carries the full pinned product
      });
    return () => {
      cancelled = true;
    };
  }, [connection]);

  // WebSocket push (live mode only). The server envelope is ALWAYS
  // {type, data} — see routes/{events,sessions,actions,redirect}.py, locked by
  // tests/test_web_api_contract.py. "state" is a PARTIAL patch to merge, and
  // "click" bumps the current 30 s bucket so clicks show without waiting for
  // the next poll.
  const onWs = useCallback(
    (msg: WsMessage) => {
      switch (msg.type) {
        case "tick": {
          const start = sessionStartIso.current ? Date.parse(sessionStartIso.current) : NaN;
          const at = Date.parse(msg.data.ts_bucket);
          // Without a session start there is no offset axis — let the poll
          // (which shares toOffsets' fallback origin) pick it up instead.
          if (!Number.isFinite(start) || !Number.isFinite(at)) return;
          const tick: Tick = {
            offset_s: Math.max(0, (at - start) / 1000),
            ts_bucket: msg.data.ts_bucket,
            viewers: msg.data.viewers,
            comment_rate: msg.data.comment_rate,
            like_rate: msg.data.like_rate,
            click_count: msg.data.click_count ?? 0,
            pinned_product_id: msg.data.pinned_product_id ?? null,
            // Đường tham chiếu (trung bình trượt) được tính lại ở lần poll kế.
            baseline_viewers: null,
            baseline_clicks_per_min: null,
          };
          setTicks((prev) => [...prev.filter((t) => t.offset_s !== tick.offset_s), tick]);
          setViewers(tick.viewers);
          break;
        }
        case "comment": {
          const start = sessionStartIso.current ? Date.parse(sessionStartIso.current) : NaN;
          const at = Date.parse(msg.data.ts);
          const offsetS =
            Number.isFinite(start) && Number.isFinite(at) ? Math.max(0, (at - start) / 1000) : 0;
          const item: CommentItem = {
            comment_id: msg.data.comment_id,
            offset_s: offsetS,
            ts: msg.data.ts,
            // API field `text` — already PII-scrubbed server-side (rule 1).
            text_scrubbed: msg.data.text,
            intent_label: (msg.data.intent as CommentItem["intent_label"]) ?? null,
            pii_kinds: msg.data.pii_kinds ?? [],
          };
          setComments((prev) =>
            prev.some((c) => c.comment_id === item.comment_id)
              ? prev
              : [...prev, item].slice(-200),
          );
          break;
        }
        case "state": {
          // Partial merge: only touch what the patch carries.
          const patch = msg.data;
          if (patch.status !== undefined) {
            const status = patch.status;
            setSessions((prev) =>
              prev.map((s) => (s.session_id === sessionId ? { ...s, status } : s)),
            );
          }
          if ("pinned_product_id" in patch) {
            if (patch.pinned_product_id == null) {
              setPinned(null);
            } else {
              const p = products.find((x) => x.product_id === patch.pinned_product_id);
              // Unknown id (catalog not loaded yet): keep the last pinned —
              // the 5 s state poll carries the full product and corrects it.
              if (p) setPinned(p);
            }
          }
          break;
        }
        case "click": {
          setTicks((prev) => {
            if (prev.length === 0) return prev;
            const last = prev[prev.length - 1];
            return [...prev.slice(0, -1), { ...last, click_count: last.click_count + 1 }];
          });
          break;
        }
        default:
          // "hello" và các loại tương lai: bỏ qua, không phải lỗi.
          break;
      }
    },
    [sessionId, products],
  );
  const wsStatus = useLiveSocket(connection === "live" ? sessionId : null, onWs, connection === "live");

  // -------------------------------------------------------------------------
  // Actions
  // -------------------------------------------------------------------------
  // Ref cho các giá trị đổi MỖI GIÂY/mỗi poll: `execute` đọc chúng lúc bấm chứ
  // không mang chúng trong deps — nếu không, hàm được tạo lại mỗi giây và bộ
  // hẹn giờ tự thực thi của bản demo bị huỷ-đặt-lại trước khi kịp chạy.
  const elapsedRef = useRef(elapsedS);
  elapsedRef.current = elapsedS;
  const productsRef = useRef(products);
  productsRef.current = products;
  const cardsRef = useRef(cards);
  cardsRef.current = cards;
  /**
   * Phiên ĐANG XEM lúc này — khác `sessionId` mà closure của một lệnh đã giữ
   * lúc bấm. Lệnh Thực hiện chờ máy chủ tới 3,5 giây; người vận hành đổi ô chọn
   * phiên trong lúc đó thì phản hồi về muộn KHÔNG được sửa state của phiên mới
   * (sửa lỗi P2 17/09: sản phẩm vừa ghim ở phiên A hiện trên hero phiên B).
   */
  const sessionIdRef = useRef(sessionId);
  sessionIdRef.current = sessionId;

  const execute = useCallback(
    async (card: ActionCardData): Promise<ExecuteOutcome | null> => {
      if (!sessionId) return null;
      const sentFor = sessionId;
      const stillViewing = () => sessionIdRef.current === sentFor;
      setExecutedIds((prev) => new Set(prev).add(card.card_id));
      // Tên sản phẩm máy chủ đã ghim: danh mục trước, rồi các thẻ đang hiện;
      // không tìm thấy thì in mã — không bịa tên.
      const nameOf = (pid: string): string =>
        productsRef.current.find((x) => x.product_id === pid)?.name ??
        cardsRef.current.find((c) => c.product_id === pid)?.product_name ??
        pid;

      if (connection !== "live") {
        const p = productsRef.current.find((x) => x.product_id === card.product_id);
        if (p) setManualPin({ product: p, atS: elapsedRef.current });
        return {
          cardProductId: card.product_id,
          cardProductName: card.product_name,
          pinnedProductId: card.product_id,
          pinnedProductName: card.product_name,
          randomized: false,
          poolSize: null,
        };
      }

      let raw: unknown;
      try {
        // Gửi kèm product_id: server phải scope đúng thẻ được bấm — chỉ gửi
        // card_id từng khiến server ngẫu nhiên hoá trên TOÀN BỘ tập ứng viên
        // (bấm thẻ A, ghim sản phẩm B).
        raw = await apiExecute(sessionId, card.card_id, card.product_id);
      } catch (e) {
        // Đã đổi phiên: tập "đã thực hiện" đã được làm mới cho phiên kia (mã
        // thẻ "card-1-P2" trùng nhau giữa các phiên) — không xoá nhầm dấu ✓.
        if (stillViewing()) {
          setExecutedIds((prev) => {
            const next = new Set(prev);
            next.delete(card.card_id);
            return next;
          });
        }
        // Giữ NGUYÊN câu tiếng Việt của máy chủ (409 khối TẮT, hết hàng…);
        // chỉ lỗi mạng thật mới thành "mất kết nối".
        throw toCommandError(e, "Máy chủ không nhận lệnh ghim.");
      }

      // ĐỌC phản hồi thay vì vứt đi: máy chủ có thể bốc thăm giữa các thẻ có
      // dự báo ngang nhau và ghim một sản phẩm KHÁC thẻ vừa bấm.
      const outcome = readExecuteOutcome(card, raw, nameOf);
      const pinnedProduct = productsRef.current.find(
        (x) => x.product_id === outcome.pinnedProductId,
      );
      // Hiện ngay sản phẩm máy chủ đã ghim, không chờ poll 5 giây kế tiếp —
      // CHỈ khi người vận hành vẫn đang xem đúng phiên đã gửi lệnh.
      if (pinnedProduct && stillViewing()) setPinned(pinnedProduct);
      return outcome;
    },
    [sessionId, connection],
  );

  const skip = useCallback((cardId: string) => {
    setSkippedIds((prev) => new Set(prev).add(cardId));
  }, []);

  const canEndSession = connection === "live" && session?.status === "live";

  const endSession = useCallback(async () => {
    if (!sessionId || connection !== "live") return;
    try {
      const updated = await apiEndSession(sessionId);
      setSessions((prev) =>
        prev.map((s) => (s.session_id === updated.session_id ? updated : s)),
      );
    } catch (e) {
      // Cùng luật với Thực hiện: câu của máy chủ giữ nguyên, chỉ lỗi mạng thật
      // mới được gọi là lỗi kết nối.
      throw toCommandError(e, "Máy chủ không kết thúc được phiên.");
    }
  }, [sessionId, connection]);

  const override = useCallback(
    async (productId: string, reason: OverrideReason) => {
      if (!sessionId) return;
      if (connection === "live") {
        await postOverride(sessionId, { product_id: productId, reason });
      } else {
        const p = products.find((x) => x.product_id === productId);
        if (p) setManualPin({ product: p, atS: elapsedS });
      }
    },
    [sessionId, connection, products, elapsedS],
  );

  // Auto mode: countdown reaches zero -> auto-execute rank-1 card (mock only;
  // in live mode the backend executes and pushes the result).
  const visibleCards = useMemo(
    () => cards.filter((c) => !skippedIds.has(c.card_id)).slice(0, 3),
    [cards, skippedIds],
  );
  // Bản demo cũng tôn trọng lịch khối như máy chủ thật: chỉ tự ghim trong khối
  // BẬT. Giá trị này chỉ đổi ở ranh giới khối, nên không làm bộ hẹn giờ chạy lại
  // mỗi giây.
  const inOnBlock = useMemo(() => {
    const b = blocks.find((x) => elapsedS >= x.start_offset_s && elapsedS < x.end_offset_s);
    return b != null && !b.is_washout && b.assignment === "ON";
  }, [blocks, elapsedS]);
  const autoTop = visibleCards.find(
    (c) => !executedIds.has(c.card_id) && c.auto_execute_in_s != null,
  );
  const autoTopId = autoTop?.card_id ?? null;
  const autoTopDelayS = autoTop?.auto_execute_in_s ?? null;
  useEffect(() => {
    if (connection !== "mock" || mode !== "auto" || !inOnBlock || autoTopId == null) return;
    const timer = setTimeout(() => {
      const top = cardsRef.current.find((c) => c.card_id === autoTopId);
      if (top) void execute(top).catch(() => undefined);
    }, (autoTopDelayS ?? 20) * 1000);
    return () => clearTimeout(timer);
  }, [connection, mode, inOnBlock, autoTopId, autoTopDelayS, execute]);

  const setMode = useCallback(
    (m: SessionMode) => {
      if (connection === "mock") setModeState(m);
    },
    [connection],
  );

  return {
    connection,
    wsStatus,
    sessions,
    sessionId,
    setSessionId,
    session,
    elapsedS,
    durationS,
    viewers,
    pinned,
    blocks,
    currentBlock,
    designHash,
    autopilot,
    cardsNote,
    degraded,
    ticks,
    comments,
    cards: visibleCards,
    executedCardIds: executedIds,
    mode,
    setMode,
    canToggleMode: connection === "mock",
    products,
    execute,
    skip,
    override,
    canEndSession,
    endSession,
  };
}
