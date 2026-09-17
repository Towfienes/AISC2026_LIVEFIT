"use client";

/**
 * "Cột KPI" — the desk's glance-from-distance signal tiles (gói DESK-HOST v2,
 * theo mockup mock_desk.png: nhãn label trên, số hiển thị to dưới, delta ▲▼ và
 * sparkline; trước đây là lưới 2×2 nhỏ của gói UI-KOL).
 *
 * OPERATOR VIEW ONLY by placement (renders inside /desk). The tiles carry no
 * assignment/block information, only audience telemetry.
 *
 * HONESTY CONTRACT (the whole point of this component): every tile is in one
 * of exactly three states —
 *
 *   GIÁ TRỊ    the source measured something → display figure + sparkline;
 *   SUY GIẢM   the source is partial → amber border, value + reason;
 *   THIẾU      the source cannot provide this signal → the words
 *              "THIẾU nguồn" and the SERVER's Vietnamese reason from the
 *              signal matrix (GET /sessions/{id}/signals). NEVER the digit 0.
 *
 * A replay analysis therefore shows THIẾU for viewers (a finished VOD does not
 * expose concurrent viewers), THIẾU for hearts/gifts when the chat replay had
 * none, and real numbers for comment tempo — the same matrix the report
 * prints. This is LiveLift's honest difference from tools that render 0.
 *
 * CHUYỂN ĐỘNG (luật UI-3 giữ nguyên): con số đi qua count-up 350ms có ngưỡng
 * (useCountUp) + nháy nền xác nhận (Flash) — phản hồi cho MỘT sự kiện "số vừa
 * đổi", không có gì lặp vô hạn; sparkline là SVG tĩnh.
 */

import { useCountUp } from "@/lib/motion";
import { CHART, type CommentItem, type ConnectionKind, type SignalCoverage, type Tick } from "@/lib/types";

import SectionTitle from "./ui/SectionTitle";
import Flash from "./ui/Flash";
import { cx } from "./ui/cx";

export type TileState = "value" | "degraded" | "missing";

export interface SignalTile {
  key: string;
  label: string;
  state: TileState;
  /** Formatted display figure — only present in the value/degraded states. */
  value?: string | null;
  /**
   * Giá trị số thô cho count-up (motion UI-3). Null khi chưa có số liệu —
   * ô hiện "—", KHÔNG đếm từ 0 lên.
   */
  raw?: number | null;
  /** Hậu tố nhỏ sau con số (ví dụ "/5 phút") — không phải đơn vị bịa. */
  suffix?: string;
  /** One-line context under a measured value ("ngay lúc này", …). */
  hint?: string;
  /** Vietnamese reason for a missing/degraded source (from the matrix). */
  reason?: string;
  /** Raw series for the sparkline (last ~20 points), value state only. */
  spark?: number[];
  sparkColor?: string;
  /**
   * Chênh so với điểm đo liền trước (spark[n-1] − spark[n-2]) — suy trực tiếp
   * từ chuỗi ĐÃ ĐO, không phải dự báo. Null/undefined = không hiện delta.
   */
  delta?: number | null;
  /**
   * Ô GỌN một dòng — dành cho tín hiệu tồn tại vì nghĩa vụ trung thực (Tim &
   * quà thường là THIẾU) mà không chiếm chỗ của 4 KPI vận hành chính.
   */
  compact?: boolean;
  /**
   * Việc người vận hành làm được NGAY để lấp nguồn thiếu (gói C7) — chỉ in ở
   * trạng thái THIẾU. Ví dụ ô Bình luận: chỉ cách bật Bộ thu bình luận thay vì
   * một câu "nguồn chat chưa nối" không kèm lối ra.
   */
  fix?: string;
}

const LOADING_HINT = "đang tải ma trận tín hiệu…";

/** Cách bật bộ thu — đúng tên khung và tên nút trên bàn (IngestPanel). */
export const COMMENTS_FIX =
  "Bật ở khung “Bộ thu bình luận”: chọn nền tảng, dán link buổi live rồi bấm “Bật bộ thu”.";

/** Các nhãn ý định "đang muốn mua" của radar — dùng cho ô KPI thứ tư. */
const BUY_INTENTS = new Set(["hoi_gia", "hoi_size", "chot_don", "van_chuyen"]);

function fmtRate(v: number): string {
  const rounded = v >= 10 ? Math.round(v) : Math.round(v * 10) / 10;
  return rounded.toLocaleString("vi-VN");
}

/** Delta = điểm cuối − điểm kề cuối của một chuỗi ĐÃ ĐO; null khi chưa đủ 2 điểm. */
function tailDelta(series: number[]): number | null {
  if (series.length < 2) return null;
  return series[series.length - 1] - series[series.length - 2];
}

/**
 * Derive the tiles from desk state + the server's signal matrix.
 *
 * `signals == null` in live mode means the matrix has not arrived yet — the
 * tiles show "—" rather than guessing. In mock mode there is no matrix; the
 * demo values are shown and the reactions tile stays THIẾU (the mock has no
 * such source either, and the tile must behave like the real desk).
 */
export function buildSignalTiles(input: {
  signals: SignalCoverage | null;
  connection: ConnectionKind;
  viewers: number;
  ticks: Tick[];
  clicksPerMin: number | null;
  reactionsTotal: number | null;
  /** Bình luận đã nhận (đã lọc PII) — nguồn của ô "Ý định mua (radar)". */
  comments?: CommentItem[];
  /** Vị trí hiện tại (giây) — cửa sổ radar là [nowS-300, nowS]. */
  nowS?: number;
  /**
   * Phiên đã kết thúc: "ngay lúc này" là một câu SAI trên buổi đã đóng —
   * hint đổi thành "điểm đo cuối phiên" (con số vẫn là phép đo thật cuối cùng).
   */
  ended?: boolean;
}): SignalTile[] {
  const { signals, connection, viewers, ticks, clicksPerMin, reactionsTotal } = input;
  const ended = input.ended === true;
  const comments = input.comments ?? [];
  // Không viết `?? 0` (gate không-bịa-số cấm mẫu đó): thiếu nowS thì cửa sổ
  // radar bắt đầu từ đầu phiên — đây là tham số vị trí, không phải phép đo.
  const nowS = input.nowS === undefined ? 0 : input.nowS;
  const find = (name: string) => signals?.signals.find((s) => s.name === name) ?? null;
  const waiting = connection === "live" && signals == null;
  const lastTick = ticks.length > 0 ? ticks[ticks.length - 1] : null;
  const tail = ticks.slice(-20);

  // 1. người xem hiện tại — chỉ khi tick mang số người xem THẬT
  const ticksSig = find("ticks");
  let viewersTile: SignalTile;
  if (waiting) {
    viewersTile = { key: "viewers", label: "Người xem", state: "value", value: null, hint: LOADING_HINT };
  } else if (ticksSig && ticksSig.status === "missing") {
    viewersTile = { key: "viewers", label: "Người xem", state: "missing", reason: ticksSig.detail };
  } else if (ticksSig && ticksSig.status === "degraded") {
    viewersTile = {
      key: "viewers",
      label: "Người xem",
      state: "degraded",
      value: Math.round(viewers).toLocaleString("vi-VN"),
      raw: Math.round(viewers),
      reason: ticksSig.detail,
      spark: tail.map((t) => t.viewers),
      delta: tailDelta(tail.map((t) => t.viewers)),
      sparkColor: CHART.s1,
    };
  } else {
    viewersTile = {
      key: "viewers",
      label: "Người xem",
      state: "value",
      value: lastTick == null ? null : Math.round(viewers).toLocaleString("vi-VN"),
      raw: lastTick == null ? null : Math.round(viewers),
      hint: lastTick == null ? "chưa có điểm đo nào" : ended ? "điểm đo cuối phiên" : "ngay lúc này",
      spark: tail.map((t) => t.viewers),
      delta: lastTick == null ? null : tailDelta(tail.map((t) => t.viewers)),
      sparkColor: CHART.s1,
    };
  }

  // 2. bình luận / phút — comment_rate của điểm đo 30 giây gần nhất
  const commentsSig = find("comments");
  // "Chưa có bình luận nào" chỉ được nói khi CẢ bàn lẫn máy chủ đều không có:
  // bàn chưa nhận bình luận nào VÀ ma trận nói nguồn bình luận thiếu (hoặc
  // chưa có ma trận — bản xem thử). Nếu không, một phiên có bình luận đang về
  // mà nguồn không gửi điểm đo nhịp (kênh YouTube ẩn số người xem) sẽ bị báo
  // "bộ thu chưa bật" ngay cạnh feed đầy bình luận.
  const noCommentsSeen =
    comments.length === 0 && (commentsSig == null || commentsSig.status === "missing");
  // Ma trận nói KHÔNG có bình luận nào và mọi điểm đo đều ghi nhịp 0: số 0 đó
  // là chỗ trống của một nguồn chưa bật, không phải phép đo — in THIẾU.
  const commentsAbsent =
    noCommentsSeen && commentsSig != null && tail.every((t) => !(t.comment_rate > 0));
  let commentTile: SignalTile;
  if (waiting) {
    commentTile = { key: "comments", label: "Bình luận / phút", state: "value", value: null, hint: LOADING_HINT };
  } else if (commentsAbsent || (lastTick == null && noCommentsSeen)) {
    commentTile = {
      key: "comments",
      label: "Bình luận / phút",
      state: "missing",
      reason: ended
        ? "phiên không ghi được bình luận nào"
        : "chưa nhận được bình luận nào — bộ thu bình luận chưa bật hoặc buổi live chưa bắt đầu",
      // Phiên đã đóng thì không còn gì để bật; bản demo không có bộ thu.
      fix: ended || connection !== "live" ? undefined : COMMENTS_FIX,
    };
  } else if (lastTick == null) {
    // Bình luận CÓ về nhưng nguồn không gửi điểm đo nhịp 30 giây nào: không
    // tính được bình luận/phút. Suy giảm (không phải THIẾU nguồn) và KHÔNG mời
    // bật bộ thu — bộ thu đang chạy.
    commentTile = {
      key: "comments",
      label: "Bình luận / phút",
      state: "degraded",
      value: null,
      raw: null,
      reason: ended
        ? "phiên có bình luận nhưng không có điểm đo nhịp nào — không tính được bình luận/phút"
        : "bình luận đang về nhưng nguồn chưa gửi điểm đo nhịp — chưa tính được bình luận/phút",
    };
  } else {
    commentTile = {
      key: "comments",
      label: "Bình luận / phút",
      state: "value",
      value: fmtRate(lastTick.comment_rate),
      raw: lastTick.comment_rate,
      hint: "điểm đo 30 giây gần nhất",
      spark: tail.map((t) => t.comment_rate),
      delta: tailDelta(tail.map((t) => t.comment_rate)),
      sparkColor: CHART.s3,
    };
  }

  // 3. lượt bấm / phút — chỉ đo được khi phiên có link đo tự phục vụ
  const clicksSig = find("clicks");
  let clicksTile: SignalTile;
  if (waiting) {
    clicksTile = { key: "clicks", label: "Lượt bấm / phút", state: "value", value: null, hint: LOADING_HINT };
  } else if (clicksSig && clicksSig.status === "missing") {
    clicksTile = { key: "clicks", label: "Lượt bấm / phút", state: "missing", reason: clicksSig.detail };
  } else {
    clicksTile = {
      key: "clicks",
      label: "Lượt bấm / phút",
      state: "value",
      value: clicksPerMin == null ? null : clicksPerMin.toLocaleString("vi-VN"),
      raw: clicksPerMin,
      hint:
        clicksPerMin == null
          ? ended
            ? "không có lượt bấm trong 60 giây cuối phiên"
            : "chưa có điểm đo trong 60 giây"
          : ended
            ? "60 giây cuối phiên"
            : "60 giây gần nhất",
      spark: tail.map((t) => t.click_count * 2),
      // Không hiện delta khi chính con số đang là "—": mũi tên cạnh một ô
      // trống đọc như một phép đo không tồn tại.
      delta: clicksPerMin == null ? null : tailDelta(tail.map((t) => t.click_count * 2)),
      sparkColor: CHART.s2,
    };
  }

  // 4. Ý ĐỊNH MUA (RADAR) — số bình luận 5 phút gần nhất được radar gắn nhãn
  // hỏi giá / hỏi size / chốt đơn / vận chuyển. Đây là SỐ ĐẾM NHÃN MÁY, không
  // phải số người mua: hint nói thẳng độ tin cậy tuỳ phiên (nghĩa vụ trung
  // thực từ live-fire — precision radar dao động theo tỷ lệ nền từng buổi).
  let intentTile: SignalTile;
  if (waiting) {
    intentTile = { key: "intent", label: "Ý định mua (radar)", state: "value", value: null, hint: LOADING_HINT };
  } else if (comments.length === 0) {
    intentTile = {
      key: "intent",
      label: "Ý định mua (radar)",
      state: "value",
      value: null,
      hint: "chưa có bình luận nào để radar đọc",
    };
  } else {
    const winLo = Math.max(0, nowS - 300);
    const buyCount = comments.filter(
      (c) =>
        c.offset_s >= winLo &&
        c.offset_s <= nowS &&
        c.intent_label != null &&
        BUY_INTENTS.has(c.intent_label),
    ).length;
    // sparkline: số nhãn mua theo từng phút của 10 phút gần nhất — cùng nguồn
    const perMin: number[] = [];
    const endMin = Math.floor(nowS / 60);
    for (let m = Math.max(0, endMin - 9); m <= endMin; m++) {
      perMin.push(
        comments.filter(
          (c) =>
            Math.floor(c.offset_s / 60) === m &&
            c.intent_label != null &&
            BUY_INTENTS.has(c.intent_label),
        ).length,
      );
    }
    intentTile = {
      key: "intent",
      label: "Ý định mua (radar)",
      state: "value",
      value: buyCount.toLocaleString("vi-VN"),
      raw: buyCount,
      suffix: "/5 phút",
      // Ngắn nhưng vẫn trung thực — độ chính xác của radar dao động theo tỷ
      // lệ nền từng buổi (đã đo, live-fire): người vận hành không được coi
      // đây là số người mua.
      hint: "nhãn máy — độ chính xác tuỳ phiên",
      spark: perMin,
      delta: tailDelta(perMin),
      sparkColor: "#a99cff",
    };
  }

  // 5. tim & quà — tồn tại để trung thực về khoảng trống nguồn. Ô GỌN một
  // dòng: nó không thuộc 4 KPI vận hành của mockup nhưng khoảng trống nguồn
  // vẫn phải nhìn thấy được (không im lặng giấu tín hiệu thiếu).
  const reactSig = find("reactions");
  let reactTile: SignalTile;
  if (waiting) {
    reactTile = { key: "reactions", label: "Tim & quà", state: "value", value: null, hint: LOADING_HINT, compact: true };
  } else if (reactSig && reactSig.status === "ok") {
    reactTile = {
      key: "reactions",
      label: "Tim & quà",
      state: "value",
      value: reactionsTotal == null ? null : reactionsTotal.toLocaleString("vi-VN"),
      raw: reactionsTotal,
      hint: "Super Chat · quà · hội viên (cả phiên)",
      compact: true,
    };
  } else {
    reactTile = {
      key: "reactions",
      label: "Tim & quà",
      state: "missing",
      reason:
        reactSig?.detail ??
        "chưa có nguồn sự kiện tim/quà cho phiên này — ô hiển thị THIẾU thay vì một số 0 giả",
      compact: true,
    };
  }

  return [viewersTile, commentTile, clicksTile, intentTile, reactTile];
}

/** Tiny inline sparkline — static SVG, no animation, decorative only. */
function Sparkline({ values, color }: { values: number[]; color: string }) {
  const finite = values.filter((v) => Number.isFinite(v));
  if (finite.length < 2 || !finite.some((v) => v > 0)) return null;
  const max = Math.max(...finite);
  const min = Math.min(...finite);
  const span = max - min || 1;
  const points = finite
    .map((v, i) => {
      const x = (i / (finite.length - 1)) * 100;
      const y = 22 - ((v - min) / span) * 20;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden className="h-7 w-full">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

/** Delta ▲▼ so với điểm đo liền trước — mực good/crit, số tabular. */
function Delta({ value }: { value: number | null | undefined }) {
  if (value == null || value === 0) return null;
  const up = value > 0;
  const shown = Math.abs(value) >= 10 ? Math.round(value) : Math.round(value * 10) / 10;
  return (
    <span
      className={cx("tnum font-num text-meta font-semibold", up ? "text-good-ink" : "text-crit-ink")}
      title="so với điểm đo liền trước"
    >
      {up ? "▲" : "▼"} {up ? "+" : "−"}
      {Math.abs(shown).toLocaleString("vi-VN")}
    </span>
  );
}

/**
 * Con số hiển thị của một ô: count-up 350ms có ngưỡng khi có giá trị thô,
 * Flash xác nhận "vừa đổi". Null → "—", không đếm từ 0.
 */
function TileFigure({ tile, degraded }: { tile: SignalTile; degraded: boolean }) {
  const shown = useCountUp(tile.raw ?? null);
  const text =
    tile.raw != null && shown != null
      ? (tile.raw >= 10 ? Math.round(shown) : Math.round(shown * 10) / 10).toLocaleString("vi-VN")
      : (tile.value ?? "—");
  return (
    <span className="relative inline-flex items-baseline gap-1">
      <Flash value={tile.value ?? null} className="-inset-x-1.5 -inset-y-0.5" />
      {/* num-s (28px): bậc hiển thị của KPI — đủ liếc từ xa mà cột 4 ô + video
          vẫn nằm gọn trong 1080px không cuộn (đo bằng ảnh chụp). */}
      <span
        className={cx(
          "relative text-num-s leading-none tracking-tight",
          degraded ? "text-warn-ink" : "text-ink",
        )}
      >
        {text}
      </span>
      {tile.suffix ? <span className="relative text-meta text-dim">{tile.suffix}</span> : null}
    </span>
  );
}

function Tile({ tile }: { tile: SignalTile }) {
  const degraded = tile.state === "degraded";
  if (tile.compact) {
    // Một dòng: nhãn + (số | chip THIẾU); lý do đầy đủ nằm trong title.
    return (
      <div
        className="flex min-w-0 items-center gap-2 rounded-lg border border-hairline bg-surface px-3 py-1.5"
        title={tile.state === "missing" ? tile.reason : tile.hint}
      >
        <span className="shrink-0 text-label uppercase text-dim">{tile.label}</span>
        {tile.state === "missing" ? (
          <>
            <span className="shrink-0 rounded-full border border-warn/60 bg-warn/10 px-2 py-0.5 text-meta font-bold tracking-wide text-warn-ink">
              THIẾU nguồn
            </span>
            <span className="min-w-0 flex-1 truncate text-meta leading-snug text-dim">
              {tile.reason}
            </span>
          </>
        ) : (
          <span className="tnum font-num text-strong text-ink">{tile.value ?? "—"}</span>
        )}
      </div>
    );
  }
  return (
    <div
      className={cx(
        "flex min-w-0 flex-col rounded-lg border p-2.5",
        degraded ? "border-warn/60 bg-warn/10" : "border-hairline bg-surface",
      )}
    >
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-label uppercase text-dim">{tile.label}</span>
        {tile.state !== "missing" ? <Delta value={tile.delta} /> : null}
      </div>
      {tile.state === "missing" ? (
        <>
          {/* Chip THIẾU gọn + lý do NGUYÊN VĂN của máy chủ — không bao giờ 0 giả */}
          <div className="mt-1.5">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-warn/60 bg-warn/10 px-2.5 py-0.5 text-meta font-bold tracking-wide text-warn-ink">
              THIẾU nguồn
            </span>
          </div>
          <p className="mt-1.5 line-clamp-3 text-meta leading-snug text-dim" title={tile.reason}>
            {tile.reason}
          </p>
          {tile.fix ? (
            <p className="mt-1 text-meta font-semibold leading-snug text-info-ink">
              <span aria-hidden>→ </span>
              {tile.fix}
            </p>
          ) : null}
        </>
      ) : (
        <>
          <div className="mt-1.5 flex items-end justify-between gap-2">
            <TileFigure tile={tile} degraded={degraded} />
            {tile.spark && tile.spark.length > 0 ? (
              <div className="w-[6.5rem] shrink-0">
                <Sparkline values={tile.spark} color={tile.sparkColor ?? CHART.s1} />
              </div>
            ) : null}
          </div>
          <p
            className="mt-1 line-clamp-2 text-meta leading-snug text-dim"
            title={degraded ? tile.reason : undefined}
          >
            {degraded ? tile.reason : tile.hint}
          </p>
        </>
      )}
    </div>
  );
}

interface Props {
  tiles: SignalTile[];
  /** Right-aligned slot in the header (e.g. the "Báo cáo phiên" link). */
  meta?: React.ReactNode;
  className?: string;
}

export default function SignalTiles({ tiles, meta, className }: Props) {
  return (
    <section aria-label="Cột chỉ số phiên" className={cx("flex flex-col", className)}>
      <SectionTitle className="mb-1.5" meta={meta}>
        Tín hiệu phiên
      </SectionTitle>
      <div className="flex flex-col gap-2">
        {tiles.map((t) => (
          <Tile key={t.key} tile={t} />
        ))}
      </div>
    </section>
  );
}
