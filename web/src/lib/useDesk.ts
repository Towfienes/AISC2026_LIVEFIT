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
  executeCard as apiExecute,
  getCards,
  getComments,
  getState,
  getTicks,
  listSessions,
  postOverride,
  sanitizeCards,
} from "./api";
import { MOCK_SESSIONS, mockElapsedS, mockRecording } from "./mock";
import type {
  ActionCardData,
  BlockInfo,
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
}

export function useDesk(): DeskState {
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

  const session = useMemo(
    () => sessions.find((s) => s.session_id === sessionId) ?? null,
    [sessions, sessionId],
  );
  const durationS = (session?.planned_duration_min ?? 90) * 60;

  // -------------------------------------------------------------------------
  // Probe the API once; fall back to mock if unreachable.
  // -------------------------------------------------------------------------
  useEffect(() => {
    if (MOCK_FORCED) return;
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
  }, []);

  // Reset per-session UI state on switch.
  useEffect(() => {
    setSkippedIds(new Set());
    setExecutedIds(new Set());
    setManualPin(null);
    setTicks([]);
    setComments([]);
    setCards([]);
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
      try {
        const [st, tks, cds, cms] = await Promise.all([
          getState(sessionId),
          getTicks(sessionId),
          getCards(sessionId),
          getComments(sessionId, { sinceOffsetS: lastCommentOffset.current, limit: 100 }),
        ]);
        if (cancelled) return;
        setElapsedS(st.elapsed_s);
        setViewers(st.viewers);
        setPinned(st.pinned_product);
        setBlocks(st.blocks);
        setModeState(st.session.mode);
        setTicks(tks);
        setCards(cds);
        if (cms.length) {
          lastCommentOffset.current = cms[cms.length - 1].offset_s;
          setComments((prev) => [...prev, ...cms].slice(-200));
        }
      } catch {
        // keep the previous render; the WS status dot reports connectivity
      }
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

  // WebSocket push (live mode only).
  const onWs = useCallback((msg: WsMessage) => {
    if (msg.type === "tick") {
      setTicks((prev) => [...prev.filter((t) => t.offset_s !== msg.tick.offset_s), msg.tick]);
      setViewers(msg.tick.viewers);
    } else if (msg.type === "comment") {
      setComments((prev) => [...prev, msg.comment].slice(-200));
    } else if (msg.type === "cards") {
      setCards(sanitizeCards(msg.cards));
    } else if (msg.type === "state") {
      setElapsedS(msg.state.elapsed_s);
      setViewers(msg.state.viewers);
      setPinned(msg.state.pinned_product);
      setBlocks(msg.state.blocks);
      setModeState(msg.state.session.mode);
    }
  }, []);
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
          await apiExecute(sessionId, card.card_id);
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
  };
}
