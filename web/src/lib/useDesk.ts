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
import type {
  ActionCardData,
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
  execute: (card: ActionCardData) => Promise<void>;
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
}

export function useDesk(opts?: UseDeskOptions): DeskState {
  const forceMock = opts?.forceMock === true;
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
  /** Vietnamese warning when one data source is failing (see the poll loop). */
  const [degraded, setDegraded] = useState<string | null>(null);
  /** Session start, used to turn API timestamps into seconds-since-start. */
  const sessionStartIso = useRef<string | null>(null);

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
        const live = list.find((s) => s.status === "live") ?? list[0] ?? null;
        setSessionId(live ? live.session_id : null);
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
  }, [forceMock]);

  // Reset per-session UI state on switch.
  useEffect(() => {
    setSkippedIds(new Set());
    setExecutedIds(new Set());
    setManualPin(null);
    setTicks([]);
    setComments([]);
    setCards([]);
    // Lịch khối là dữ liệu theo phiên: không được hiển thị lịch của phiên cũ
    // trên trục thời gian của phiên mới trong lúc chờ poll đầu tiên.
    setBlocks([]);
    setCurrentBlock(null);
    // Cam kết thiết kế thuộc về đúng một phiên: giữ lại hash phiên cũ trong
    // lúc chờ poll đầu tiên sẽ là một cam kết SAI trên màn hình.
    setDesignHash(null);
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
  const lastCommentOffset = useRef(0);
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

  // Live mode: 1 s local clock between polls.
  useEffect(() => {
    if (connection !== "live") return;
    const timer = setInterval(() => setElapsedS((e) => e + 1), 1000);
    return () => clearInterval(timer);
  }, [connection]);

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
  const execute = useCallback(
    async (card: ActionCardData) => {
      if (!sessionId) return;
      setExecutedIds((prev) => new Set(prev).add(card.card_id));
      if (connection === "live") {
        try {
          // Gửi kèm product_id: server phải scope đúng thẻ được bấm — chỉ gửi
          // card_id từng khiến server ngẫu nhiên hoá trên TOÀN BỘ tập ứng viên
          // (bấm thẻ A, ghim sản phẩm B).
          await apiExecute(sessionId, card.card_id, card.product_id);
        } catch {
          setExecutedIds((prev) => {
            const next = new Set(prev);
            next.delete(card.card_id);
            return next;
          });
          throw new Error("Không gửi được lệnh — kiểm tra kết nối API.");
        }
      } else {
        const p = products.find((x) => x.product_id === card.product_id);
        if (p) setManualPin({ product: p, atS: elapsedS });
      }
    },
    [sessionId, connection, products, elapsedS],
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
    } catch {
      throw new Error("Không kết thúc được phiên — kiểm tra kết nối API rồi thử lại.");
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
  useEffect(() => {
    if (connection !== "mock" || mode !== "auto") return;
    const top = visibleCards.find((c) => !executedIds.has(c.card_id) && c.auto_execute_in_s != null);
    if (!top) return;
    const timer = setTimeout(() => {
      void execute(top);
    }, (top.auto_execute_in_s ?? 20) * 1000);
    return () => clearTimeout(timer);
  }, [connection, mode, visibleCards, executedIds, execute]);

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
