"use client";

/**
 * Replay engine (E6-06): plays a finished session's recorded ticks, comments
 * and cards through the same three-zone layout, with speed control, a scrubber
 * and a "hết hàng" what-if toggle that re-ranks the action cards.
 *
 * Sources, in order: FastAPI endpoints (real recorded data) — falling back to
 * the deterministic mock recording when the API is unreachable.
 *
 * Honesty rule: client-side synthesized fallback cards are ALWAYS
 * source="forecast" (no interval). Only server-provided cards may claim
 * source="experiment" with a CI (E2-04).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getCards, getComments, getState, getTicks, listSessions } from "./api";
import { MOCK_SESSIONS, mockRecording, recomputeCards } from "./mock";
import type {
  ActionCardData,
  CommentItem,
  ConnectionKind,
  Product,
  SessionRecording,
  SessionSummary,
  Tick,
} from "./types";

const MOCK_FORCED = process.env.NEXT_PUBLIC_MOCK === "1";

export type ReplaySpeed = 1 | 4 | 16;

/** Build forecast-only fallback cards from recorded ticks (no fabricated CIs). */
function synthesizeTimeline(
  ticks: Tick[],
  products: Product[],
  durationS: number,
): { offset_s: number; cards: ActionCardData[] }[] {
  const out: { offset_s: number; cards: ActionCardData[] }[] = [];
  for (let t = 0; t < durationS; t += 120) {
    const windowTicks = ticks.filter((x) => x.offset_s > t - 600 && x.offset_s <= t);
    const clicksByProduct = new Map<string, number>();
    for (const tick of windowTicks) {
      if (tick.pinned_product_id) {
        clicksByProduct.set(
          tick.pinned_product_id,
          (clicksByProduct.get(tick.pinned_product_id) ?? 0) + tick.click_count,
        );
      }
    }
    const ranked = [...products].sort(
      (a, b) =>
        (clicksByProduct.get(b.product_id) ?? 0) - (clicksByProduct.get(a.product_id) ?? 0),
    );
    out.push({
      offset_s: t,
      cards: ranked.slice(0, 3).map((p, i) => ({
        card_id: `synth-${t}-${p.product_id}`,
        rank: i + 1,
        headline: `Ghim: ${p.name}`,
        product_id: p.product_id,
        product_name: p.name,
        rationale: "Xếp hạng theo nhịp click 10 phút gần nhất trong dữ liệu ghi lại.",
        source: "forecast",
        estimate: null,
        ci_low: null,
        ci_high: null,
        auto_execute_in_s: null,
      })),
    });
  }
  return out;
}

async function loadApiRecording(session: SessionSummary): Promise<SessionRecording> {
  const [state, ticks, comments] = await Promise.all([
    getState(session.session_id),
    getTicks(session.session_id),
    getComments(session.session_id, { limit: 2000 }),
  ]);
  const durationS = session.planned_duration_min * 60;
  const ids = [...new Set(ticks.map((t) => t.pinned_product_id).filter((x): x is string => !!x))];
  const products: Product[] =
    ids.length > 0
      ? ids.map((id) => ({ product_id: id, name: id, category: null, price: 0, stock: 0 }))
      : [];
  return {
    session,
    blocks: state.blocks,
    ticks,
    comments,
    cards_timeline: synthesizeTimeline(ticks, products, durationS),
    products,
    duration_s: durationS,
  };
}

export interface ReplayState {
  connection: ConnectionKind;
  sessions: SessionSummary[]; // finished sessions only
  sessionId: string | null;
  setSessionId: (id: string) => void;
  recording: SessionRecording | null;
  t: number;
  playing: boolean;
  speed: ReplaySpeed;
  togglePlay: () => void;
  setSpeed: (s: ReplaySpeed) => void;
  seek: (t: number) => void;
  visibleTicks: Tick[];
  visibleComments: CommentItem[];
  cards: ActionCardData[];
  excluded: ReadonlySet<string>;
  toggleExcluded: (productId: string) => void;
  cardsFromServer: boolean;
}

export function useReplay(): ReplayState {
  const [connection, setConnection] = useState<ConnectionKind>(
    MOCK_FORCED ? "mock" : "connecting",
  );
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [recording, setRecording] = useState<SessionRecording | null>(null);
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<ReplaySpeed>(4);
  const [excluded, setExcluded] = useState<Set<string>>(new Set());
  const [serverCards, setServerCards] = useState<ActionCardData[] | null>(null);
  const apiCardsBroken = useRef(false);

  // Session list: finished sessions only.
  useEffect(() => {
    const useMock = () => {
      const ended = MOCK_SESSIONS.filter((s) => s.status === "ended");
      setSessions(ended);
      setSessionId(ended[0]?.session_id ?? null);
      setConnection("mock");
    };
    if (MOCK_FORCED) {
      useMock();
      return;
    }
    let cancelled = false;
    listSessions(2500)
      .then((list) => {
        if (cancelled) return;
        const ended = list.filter((s) => s.status === "ended");
        if (ended.length === 0) {
          useMock();
          return;
        }
        setSessions(ended);
        setSessionId(ended[0].session_id);
        setConnection("live");
      })
      .catch(() => {
        if (!cancelled) useMock();
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Load the selected session's recording.
  useEffect(() => {
    if (!sessionId || connection === "connecting") return;
    setRecording(null);
    setT(0);
    setPlaying(false);
    setExcluded(new Set());
    setServerCards(null);
    apiCardsBroken.current = false;
    if (connection === "mock") {
      setRecording(mockRecording(sessionId));
      return;
    }
    let cancelled = false;
    const session = sessions.find((s) => s.session_id === sessionId);
    if (!session) return;
    loadApiRecording(session)
      .then((rec) => {
        if (!cancelled) setRecording(rec);
      })
      .catch(() => {
        if (!cancelled) {
          setRecording(mockRecording(MOCK_SESSIONS[1].session_id));
          setConnection("mock");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId, connection, sessions]);

  // Playback clock.
  useEffect(() => {
    if (!playing || !recording) return;
    const stepMs = 250;
    const timer = setInterval(() => {
      setT((prev) => {
        const next = prev + (stepMs / 1000) * speed;
        if (next >= recording.duration_s) {
          setPlaying(false);
          return recording.duration_s;
        }
        return next;
      });
    }, stepMs);
    return () => clearInterval(timer);
  }, [playing, speed, recording]);

  // Server-side cards for the current 2-minute bucket + exclusion set.
  const bucket = Math.floor(t / 120) * 120;
  useEffect(() => {
    if (connection !== "live" || !sessionId || apiCardsBroken.current) return;
    let cancelled = false;
    getCards(sessionId, { atOffsetS: bucket, excludeProductIds: [...excluded] })
      .then((cds) => {
        if (!cancelled) setServerCards(cds);
      })
      .catch(() => {
        apiCardsBroken.current = true;
        setServerCards(null);
      });
    return () => {
      cancelled = true;
    };
  }, [connection, sessionId, bucket, excluded]);

  const visibleTicks = useMemo(
    () => (recording ? recording.ticks.filter((x) => x.offset_s <= t) : []),
    [recording, t],
  );
  const visibleComments = useMemo(
    () => (recording ? recording.comments.filter((c) => c.offset_s <= t).slice(-60) : []),
    [recording, t],
  );
  const cards = useMemo(() => {
    if (!recording) return [];
    if (serverCards) return serverCards;
    return recomputeCards(recording, t, [...excluded]);
  }, [recording, serverCards, t, excluded]);

  const toggleExcluded = useCallback((productId: string) => {
    setExcluded((prev) => {
      const next = new Set(prev);
      if (next.has(productId)) next.delete(productId);
      else next.add(productId);
      return next;
    });
  }, []);

  return {
    connection,
    sessions,
    sessionId,
    setSessionId,
    recording,
    t,
    playing,
    speed,
    togglePlay: useCallback(() => setPlaying((p) => !p), []),
    setSpeed: useCallback((s: ReplaySpeed) => setSpeed(s), []),
    seek: useCallback((x: number) => setT(x), []),
    visibleTicks,
    visibleComments,
    cards,
    excluded,
    toggleExcluded,
    cardsFromServer: serverCards != null,
  };
}
