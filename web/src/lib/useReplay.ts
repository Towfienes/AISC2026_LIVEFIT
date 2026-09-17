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
 *
 * ---------------------------------------------------------------------------
 * GÓI D — bốn lỗi đã sửa ở hook này
 * ---------------------------------------------------------------------------
 * 1. MỞ ĐÚNG BUỔI (giới hạn #5): `/replay?session=<id>` từng bị bỏ qua — hook
 *    luôn chọn `ended[0]`, mà máy chủ trả danh sách theo `created_at` TĂNG
 *    DẦN, tức là buổi CŨ NHẤT. Nay `pickReplaySession` ưu tiên tuyệt đối mã
 *    trong link; mã không có (hoặc buổi chưa kết thúc) thì mở buổi kết thúc
 *    MỚI NHẤT và báo lý do qua `requestedStatus` — không lặng lẽ mở buổi khác.
 * 2. HAI KHUNG CHẾT: cột thẻ hỏi `getCards` của TRẠNG THÁI LIVE, mà máy chủ
 *    cố ý không phát thẻ cho phiên đã kết thúc (`api/cards.py`) → luôn `[]`,
 *    và `if (serverCards) return serverCards` (mảng rỗng vẫn truthy) chặn
 *    luôn đường xếp lại từ bản ghi. Thẻ "bây giờ" của máy chủ cũng không phải
 *    thẻ "tại phút T" của bản ghi, nên nay thẻ phát lại LUÔN xếp lại từ bản
 *    ghi. Danh sách sản phẩm lấy từ DANH MỤC (`listProducts`) thay vì chỉ từ
 *    `pinned_product_id` của tick (phiên gieo mẫu không có) với tên = mã.
 * 3. KHÔNG BỊA SỐ khi xếp lại: `recomputeCards` của mock bù thẻ bằng một
 *    ước lượng NGẪU NHIÊN; `replayCardsAt` bù thẻ với `estimate: null`, và lý
 *    do trên thẻ nói đúng dữ liệu nào đứng sau thứ tự (có hay không có lượt
 *    bấm theo sản phẩm).
 * 4. KHUNG ĐẦU KHÔNG TRỐNG: vừa tải xong bản ghi, vị trí phát được đặt ở
 *    `firstFrameOffset` — phút đầu tiên biểu đồ vẽ được đường (và bình luận
 *    đầu tiên nếu nó tới sớm) thay vì 00:00 với bốn khung rỗng.
 *
 * KIỂM TOÁN 17/09 — hai lỗi nữa:
 * 5. HAI ĐIỂM PHÚT THẬT: `firstFrameOffset` từng lấy tick đầu có
 *    `offset_s >= 60` — bộ thu bật muộn 10 phút (tick đầu ở 600) thì khung đầu
 *    chỉ có MỘT phút số liệu và biểu đồ vẫn trống. Nay lấy tick đầu tiên thuộc
 *    phút SAU phút của tick sớm nhất.
 * 6. "BẮT ĐẦU XEM THỬ" LÀ BẢN MÔ PHỎNG: trang chủ (kho suy giảm) hứa bản xem
 *    thử ngoại tuyến rồi mở `/replay?session=mock-ended-01`, nhưng hook chỉ
 *    rơi về mô phỏng khi máy chủ hỏng hoặc chưa có buổi kết thúc — máy chủ
 *    sống thì mã mock bị bỏ qua và trang mở một buổi THẬT của người bán kèm
 *    nhãn "DỮ LIỆU THẬT". Nay mã mang tiền tố `mock-` (mã máy chủ luôn là
 *    UUID) buộc chạy bản mô phỏng, lý do `"sample"`, không gọi máy chủ.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getComments,
  getSchedule,
  getSignalCoverage,
  getTicks,
  listProducts,
  listSessions,
  sanitizeCards,
} from "./api";
import { MOCK_SESSIONS, mockRecording } from "./mock";
import type {
  ActionCardData,
  BlockInfo,
  CommentItem,
  ConnectionKind,
  Product,
  SessionRecording,
  SessionSummary,
  SignalCoverage,
  Tick,
} from "./types";

const MOCK_FORCED = process.env.NEXT_PUBLIC_MOCK === "1";

/**
 * Tốc độ phát lại. 30x/60x (gói D): ở 16x một buổi 60 phút cần ~4 phút để
 * xem hết — "xem thử nhanh" không thể nhanh; ở 60x chỉ còn 1 phút.
 */
export type ReplaySpeed = 1 | 4 | 16 | 30 | 60;

/** Tốc độ mặc định: đủ nhanh để thấy nhịp phiên chuyển động ngay khi bấm Phát. */
const DEFAULT_SPEED: ReplaySpeed = 30;

/** Khung đầu chỉ tự tua tới bình luận đầu tiên nếu nó nằm trong 5 phút đầu. */
const FIRST_FRAME_MAX_COMMENT_S = 300;

/**
 * Vì sao trang đang chạy bản ghi mô phỏng thay cho dữ liệu máy chủ.
 * `"sample"`: link xin ĐÚNG bản xem thử ngoại tuyến (`?session=mock-…`).
 */
export type MockReason = "forced" | "server" | "no_ended" | "sample";

/** Tiền tố mã phiên của bản ghi mô phỏng phía web (mock.ts). */
const SAMPLE_ID_PREFIX = "mock-";

/**
 * Link xin bản ghi mô phỏng ngoại tuyến? Mã máy chủ là UUID nên không bao giờ
 * trùng tiền tố này — nhận ra nó là đủ để KHÔNG mở nhầm một buổi thật.
 */
export function isSampleSessionId(id: string | null | undefined): boolean {
  return typeof id === "string" && id.startsWith(SAMPLE_ID_PREFIX);
}

/**
 * Lý do mô phỏng khi link đổi sang `?session=mock-…`. Trang ĐÃ chạy mô phỏng
 * (mất máy chủ / chưa có buổi kết thúc) mà người xem chọn một bản khác trong ô
 * chọn phiên — `selectSession` ghi mã mock vào link — thì GIỮ lý do cũ (null =
 * không đổi): đổi sang "sample" sẽ xoá câu "chưa kết nối được máy chủ" khỏi
 * dải băng trong khi máy chủ vẫn chưa nối được.
 */
export function sampleLinkMockReason(connection: ConnectionKind): MockReason | null {
  return connection === "mock" ? null : "sample";
}

/** Trạng thái của mã phiên trong link `?session=`. */
export type RequestedStatus = "none" | "ok" | "not_ended" | "not_found";

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
    // Chỉ nói "xếp theo lượt bấm" khi bản ghi THẬT SỰ có lượt bấm gắn với sản
    // phẩm quanh thời điểm này; không có thì thứ tự chỉ là thứ tự danh mục.
    const measured = [...clicksByProduct.values()].some((n) => n > 0);
    const ranked = measured
      ? [...products].sort(
          (a, b) =>
            (clicksByProduct.get(b.product_id) ?? 0) - (clicksByProduct.get(a.product_id) ?? 0),
        )
      : [...products];
    out.push({
      offset_s: t,
      cards: ranked.slice(0, 3).map((p, i) => ({
        card_id: `synth-${t}-${p.product_id}`,
        rank: i + 1,
        headline: `Ghim: ${p.name}`,
        product_id: p.product_id,
        product_name: p.name,
        rationale: measured
          ? `${clicksByProduct.get(p.product_id) ?? 0} lượt bấm link khi đang ghim sản phẩm này trong 10 phút trước (theo bản ghi).`
          : "Bản ghi không có lượt bấm theo từng sản phẩm quanh lúc này — thẻ chỉ theo thứ tự danh mục, chưa phải dự báo.",
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

/** An analysis-only session (someone else's video) — observational, never an experiment. */
export function isAnalysisSession(session: SessionSummary | null | undefined): boolean {
  return session?.platform === "replay";
}

/** Mốc thời gian để xếp "mới nhất trước": kết thúc, không có thì lên sóng. */
function finishedAt(s: SessionSummary): number {
  const t = Date.parse(s.end_ts ?? s.start_ts ?? "");
  return Number.isFinite(t) ? t : 0;
}

/** Buổi đã kết thúc, MỚI NHẤT trước (máy chủ trả theo created_at tăng dần). */
export function endedNewestFirst(list: SessionSummary[]): SessionSummary[] {
  return list.filter((s) => s.status === "ended").sort((a, b) => finishedAt(b) - finishedAt(a));
}

/**
 * Buổi mở mặc định: mã trong link (ưu tiên tuyệt đối, nếu có trong danh sách
 * buổi đã kết thúc) → buổi kết thúc mới nhất → null.
 */
export function pickReplaySession(
  ended: SessionSummary[],
  requestedId: string | null | undefined,
): SessionSummary | null {
  if (requestedId) {
    const hit = ended.find((s) => s.session_id === requestedId);
    if (hit) return hit;
  }
  return ended[0] ?? null;
}

/**
 * Vị trí phát khi vừa mở bản ghi: phút đầu tiên biểu đồ nhịp có đủ HAI điểm
 * phút để vẽ đường, dời thêm tới bình luận đầu tiên nếu nó tới trong 5 phút
 * đầu. Bản ghi không có gì thì đứng ở 0.
 *
 * Biểu đồ gộp tick theo `Math.floor(offset_s / 60)` và cần ≥ 2 nhóm, nên
 * "điểm phút thứ hai" là tick sớm nhất thuộc phút LỚN HƠN phút của tick sớm
 * nhất — KHÔNG phải tick đầu có offset ≥ 60 (bộ thu bật muộn thì tick đầu đã
 * ở phút 10 và một mình nó chỉ là một điểm).
 */
export function firstFrameOffset(rec: SessionRecording): number {
  const candidates: number[] = [];
  let firstMinute = Number.POSITIVE_INFINITY;
  for (const x of rec.ticks) firstMinute = Math.min(firstMinute, Math.floor(x.offset_s / 60));
  let secondMinuteTick = Number.POSITIVE_INFINITY;
  for (const x of rec.ticks) {
    if (Math.floor(x.offset_s / 60) > firstMinute) {
      secondMinuteTick = Math.min(secondMinuteTick, x.offset_s);
    }
  }
  if (Number.isFinite(secondMinuteTick)) candidates.push(secondMinuteTick);
  let firstComment = Number.POSITIVE_INFINITY;
  for (const c of rec.comments) firstComment = Math.min(firstComment, c.offset_s);
  if (firstComment <= FIRST_FRAME_MAX_COMMENT_S) candidates.push(firstComment);
  if (candidates.length === 0) return 0;
  return Math.max(0, Math.min(rec.duration_s, Math.ceil(Math.max(...candidates))));
}

/** Mốc của mục dòng-thời-gian-thẻ đang có hiệu lực tại `t` (null = không có thẻ). */
function timelineOffsetAt(rec: SessionRecording, t: number): number | null {
  let hit: number | null = null;
  for (const e of rec.cards_timeline) {
    if (e.offset_s <= t) hit = e.offset_s;
  }
  return hit ?? rec.cards_timeline[0]?.offset_s ?? null;
}

/**
 * Thẻ tại mốc `offsetS` sau khi loại các sản phẩm "hết hàng". Thẻ bù vào là
 * ứng viên kế tiếp trong danh mục và KHÔNG mang con số nào (estimate null) —
 * không có mô hình nào đứng sau thứ tự bù nên không được in một phần trăm.
 */
export function replayCardsAt(
  rec: SessionRecording,
  offsetS: number | null,
  excluded: ReadonlySet<string>,
): ActionCardData[] {
  if (offsetS == null) return [];
  const entry = rec.cards_timeline.find((e) => e.offset_s === offsetS);
  if (!entry) return [];
  const out = entry.cards.filter((c) => !excluded.has(c.product_id));
  const used = new Set(out.map((c) => c.product_id));
  for (const p of rec.products) {
    if (out.length >= 3) break;
    if (excluded.has(p.product_id) || used.has(p.product_id)) continue;
    used.add(p.product_id);
    out.push({
      card_id: `refill-${entry.offset_s}-${p.product_id}`,
      rank: out.length + 1,
      headline: `Thay thế: ${p.name}`,
      product_id: p.product_id,
      product_name: p.name,
      rationale:
        "Ứng viên kế tiếp sau khi loại sản phẩm hết hàng — chưa có con số dự báo cho sản phẩm này.",
      source: "forecast",
      estimate: null,
      ci_low: null,
      ci_high: null,
      auto_execute_in_s: null,
    });
  }
  return sanitizeCards(out.map((c, i) => ({ ...c, rank: i + 1 })));
}

async function loadApiRecording(
  session: SessionSummary,
): Promise<{ rec: SessionRecording; catalogFailed: boolean }> {
  const analysis = isAnalysisSession(session);
  // Blocks live on the schedule endpoint, not on the state payload; an
  // analysis session has none by design, so its schedule call is skipped.
  // Danh mục sản phẩm hỏng thì bản ghi vẫn phát — chỉ khung "nếu hết hàng"
  // nói rõ là không tải được danh mục.
  const [ticks, comments, blocks, catalog] = await Promise.all([
    getTicks(session.session_id, session.start_ts),
    getComments(session.session_id, session.start_ts),
    analysis ? Promise.resolve([] as BlockInfo[]) : getSchedule(session.session_id),
    analysis ? Promise.resolve([] as Product[]) : listProducts().catch(() => null),
  ]);
  const lastTickEnd = ticks.length > 0 ? ticks[ticks.length - 1].offset_s + 30 : 0;
  const lastComment = comments.length > 0 ? comments[comments.length - 1].offset_s : 0;
  const durationS = Math.max(session.planned_duration_min * 60, lastTickEnd, lastComment);
  let products: Product[] = [];
  if (!analysis) {
    products = [...(catalog ?? [])];
    // Sản phẩm từng được ghim trong bản ghi nhưng không còn trong danh mục:
    // vẫn đưa vào (tên = mã, vì đó là tất cả những gì bản ghi biết).
    const known = new Set(products.map((p) => p.product_id));
    for (const t of ticks) {
      const id = t.pinned_product_id;
      if (id && !known.has(id)) {
        known.add(id);
        products.push({ product_id: id, name: id, category: null, price: 0, stock: 0 });
      }
    }
  }
  return {
    rec: {
      session,
      // Analysis sessions have no experiment schedule — force-empty defensively.
      blocks: analysis ? [] : blocks,
      ticks,
      comments,
      // Never synthesize action cards over an observational recording.
      cards_timeline: analysis ? [] : synthesizeTimeline(ticks, products, durationS),
      products,
      duration_s: durationS,
    },
    catalogFailed: !analysis && catalog == null,
  };
}

export interface ReplayState {
  connection: ConnectionKind;
  /** Vì sao đang chạy mô phỏng (null khi dữ liệu đến từ máy chủ). */
  mockReason: MockReason | null;
  sessions: SessionSummary[]; // finished sessions only, newest first
  sessionId: string | null;
  setSessionId: (id: string) => void;
  /** Mã trong `?session=` có mở được không — trang báo lý do khi không. */
  requestedStatus: RequestedStatus;
  recording: SessionRecording | null;
  /** Phiên đang phát là phân tích video của người khác (không có thẻ/sản phẩm). */
  analysis: boolean;
  /** Không tải được danh mục sản phẩm từ máy chủ. */
  catalogFailed: boolean;
  /** Vị trí mà bản ghi được tự tua tới lúc mở (xem `firstFrameOffset`). */
  firstFrameS: number;
  /** Lý do THIẾU nguồn người xem / lượt bấm từ ma trận tín hiệu của máy chủ. */
  viewersMissing: string | null;
  clicksMissing: string | null;
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
}

/**
 * @param requestedSessionId mã phiên đọc từ `?session=` của URL (trang đọc
 *   bằng `useSearchParams`); đổi mã là hook chọn lại buổi tương ứng.
 */
export function useReplay(requestedSessionId?: string | null): ReplayState {
  const requestedId = requestedSessionId?.trim() ? requestedSessionId.trim() : null;
  const [connection, setConnection] = useState<ConnectionKind>(
    MOCK_FORCED ? "mock" : "connecting",
  );
  const [mockReason, setMockReason] = useState<MockReason | null>(null);
  const [allSessions, setAllSessions] = useState<SessionSummary[]>([]);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [recording, setRecording] = useState<SessionRecording | null>(null);
  const [catalogFailed, setCatalogFailed] = useState(false);
  const [signals, setSignals] = useState<SignalCoverage | null>(null);
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<ReplaySpeed>(DEFAULT_SPEED);
  const [excluded, setExcluded] = useState<Set<string>>(new Set());
  const requestedRef = useRef(requestedId);
  // Cập nhật NGAY trong lần render: hiệu ứng tải danh sách bên dưới chạy trước
  // hiệu ứng đổi-mã, nên phải đọc được mã MỚI của link.
  requestedRef.current = requestedId;
  const wantSample = isSampleSessionId(requestedId);
  const connectionRef = useRef(connection);
  connectionRef.current = connection;

  const switchToMock = useCallback((reason: MockReason) => {
    const ended = endedNewestFirst(MOCK_SESSIONS);
    setAllSessions(MOCK_SESSIONS);
    setSessions(ended);
    setSessionId(pickReplaySession(ended, requestedRef.current)?.session_id ?? null);
    setMockReason(reason);
    setConnection("mock");
  }, []);

  // Session list: finished sessions only, newest first.
  useEffect(() => {
    if (MOCK_FORCED) {
      switchToMock("forced");
      return;
    }
    // Link xin bản xem thử ngoại tuyến: KHÔNG hỏi máy chủ — máy chủ sống thì
    // pickReplaySession sẽ bỏ qua mã mock và mở một buổi THẬT (lỗi 17/09).
    if (wantSample) {
      const reason = sampleLinkMockReason(connectionRef.current);
      if (reason) switchToMock(reason);
      return;
    }
    let cancelled = false;
    setConnection("connecting");
    listSessions(2500)
      .then((list) => {
        if (cancelled) return;
        const ended = endedNewestFirst(list);
        if (ended.length === 0) {
          switchToMock("no_ended");
          return;
        }
        setAllSessions(list);
        setSessions(ended);
        setSessionId(pickReplaySession(ended, requestedRef.current)?.session_id ?? null);
        setConnection("live");
      })
      .catch(() => {
        if (!cancelled) switchToMock("server");
      });
    return () => {
      cancelled = true;
    };
  }, [switchToMock, wantSample]);

  // `?session=` đổi sau khi trang đã mở (điều hướng phía client): chọn lại.
  useEffect(() => {
    if (!requestedId || sessions.length === 0) return;
    const hit = sessions.find((s) => s.session_id === requestedId);
    if (hit) setSessionId(hit.session_id);
  }, [requestedId, sessions]);

  // Load the selected session's recording.
  useEffect(() => {
    if (!sessionId || connection === "connecting") return;
    setRecording(null);
    setT(0);
    setPlaying(false);
    setExcluded(new Set());
    setCatalogFailed(false);
    setSignals(null);
    if (connection === "mock") {
      const rec = mockRecording(sessionId);
      setRecording(rec);
      setT(firstFrameOffset(rec));
      return;
    }
    let cancelled = false;
    const session = sessions.find((s) => s.session_id === sessionId);
    if (!session) return;
    loadApiRecording(session)
      .then(({ rec, catalogFailed: failed }) => {
        if (cancelled) return;
        setRecording(rec);
        setCatalogFailed(failed);
        setT(firstFrameOffset(rec));
      })
      .catch(() => {
        // Máy chủ rơi giữa chừng: chuyển HẲN sang bộ mô phỏng (danh sách +
        // phiên đang chọn), để nhãn "MÔ PHỎNG" và nội dung luôn khớp nhau.
        if (!cancelled) switchToMock("server");
      });
    // Ma trận tín hiệu: panel nào máy chủ nói THIẾU nguồn thì biểu đồ không
    // vẽ đường phẳng từ tick trống. Không tải được thì giữ nguyên (không đoán).
    getSignalCoverage(session.session_id)
      .then((cov) => {
        if (!cancelled) setSignals(cov);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [sessionId, connection, sessions, switchToMock]);

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

  const analysis = isAnalysisSession(recording?.session);
  const firstFrameS = useMemo(() => (recording ? firstFrameOffset(recording) : 0), [recording]);

  const visibleTicks = useMemo(
    () => (recording ? recording.ticks.filter((x) => x.offset_s <= t) : []),
    [recording, t],
  );
  const visibleComments = useMemo(
    () => (recording ? recording.comments.filter((c) => c.offset_s <= t).slice(-60) : []),
    [recording, t],
  );
  // Thẻ chỉ đổi khi sang mục mới của dòng thời gian (2 phút một mục), không
  // phải mỗi 250 ms của đồng hồ phát.
  const cardsOffset = recording ? timelineOffsetAt(recording, t) : null;
  const cards = useMemo(
    () => (recording && !analysis ? replayCardsAt(recording, cardsOffset, excluded) : []),
    [recording, analysis, cardsOffset, excluded],
  );

  const requestedStatus = useMemo<RequestedStatus>(() => {
    if (!requestedId || connection === "connecting") return "none";
    if (sessions.some((s) => s.session_id === requestedId)) return "ok";
    return allSessions.some((s) => s.session_id === requestedId) ? "not_ended" : "not_found";
  }, [requestedId, connection, sessions, allSessions]);

  const missingReason = (name: string): string | null => {
    const s = signals?.signals.find((x) => x.name === name);
    return s && s.status === "missing" ? s.detail : null;
  };

  /** Bấm Phát khi đã hết bản ghi thì phát lại từ đầu, không đứng im ở cuối. */
  const togglePlay = useCallback(() => {
    if (!playing && recording && t >= recording.duration_s) setT(0);
    setPlaying((p) => !p);
  }, [playing, recording, t]);

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
    mockReason: connection === "mock" ? mockReason : null,
    sessions,
    sessionId,
    setSessionId,
    requestedStatus,
    recording,
    analysis,
    catalogFailed,
    firstFrameS,
    viewersMissing: connection === "live" ? missingReason("ticks") : null,
    clicksMissing: connection === "live" ? missingReason("clicks") : null,
    t,
    playing,
    speed,
    togglePlay,
    setSpeed: useCallback((s: ReplaySpeed) => setSpeed(s), []),
    seek: useCallback((x: number) => setT(x), []),
    visibleTicks,
    visibleComments,
    cards,
    excluded,
    toggleExcluded,
  };
}
