"use client";

/**
 * "Dải thẻ tín hiệu" — four glance-from-distance signal tiles (gói UI-KOL).
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
 */

import { CHART, type ConnectionKind, type SignalCoverage, type Tick } from "@/lib/types";

import SectionTitle from "./ui/SectionTitle";
import { cx } from "./ui/cx";

export type TileState = "value" | "degraded" | "missing";

export interface SignalTile {
  key: string;
  label: string;
  state: TileState;
  /** Formatted display figure — only present in the value/degraded states. */
  value?: string | null;
  /** One-line context under a measured value ("ngay lúc này", …). */
  hint?: string;
  /** Vietnamese reason for a missing/degraded source (from the matrix). */
  reason?: string;
  /** Raw series for the sparkline (last ~20 points), value state only. */
  spark?: number[];
  sparkColor?: string;
}

const LOADING_HINT = "đang tải ma trận tín hiệu…";

function fmtRate(v: number): string {
  const rounded = v >= 10 ? Math.round(v) : Math.round(v * 10) / 10;
  return rounded.toLocaleString("vi-VN");
}

/**
 * Derive the four tiles from desk state + the server's signal matrix.
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
}): SignalTile[] {
  const { signals, connection, viewers, ticks, clicksPerMin, reactionsTotal } = input;
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
      reason: ticksSig.detail,
      spark: tail.map((t) => t.viewers),
      sparkColor: CHART.s1,
    };
  } else {
    viewersTile = {
      key: "viewers",
      label: "Người xem",
      state: "value",
      value: lastTick == null ? null : Math.round(viewers).toLocaleString("vi-VN"),
      hint: lastTick == null ? "chưa có điểm đo nào" : "ngay lúc này",
      spark: tail.map((t) => t.viewers),
      sparkColor: CHART.s1,
    };
  }

  // 2. bình luận / phút — comment_rate của điểm đo 30 giây gần nhất
  let commentTile: SignalTile;
  if (waiting) {
    commentTile = { key: "comments", label: "Bình luận / phút", state: "value", value: null, hint: LOADING_HINT };
  } else if (lastTick == null) {
    commentTile = {
      key: "comments",
      label: "Bình luận / phút",
      state: "missing",
      reason: "chưa có điểm đo nhịp bình luận nào — nguồn chat chưa nối hoặc phiên chưa bắt đầu",
    };
  } else {
    commentTile = {
      key: "comments",
      label: "Bình luận / phút",
      state: "value",
      value: fmtRate(lastTick.comment_rate),
      hint: "điểm đo 30 giây gần nhất",
      spark: tail.map((t) => t.comment_rate),
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
      hint: clicksPerMin == null ? "chưa có điểm đo trong 60 giây" : "60 giây gần nhất",
      spark: tail.map((t) => t.click_count * 2),
      sparkColor: CHART.s2,
    };
  }

  // 4. tim & quà — tồn tại để trung thực về khoảng trống nguồn
  const reactSig = find("reactions");
  let reactTile: SignalTile;
  if (waiting) {
    reactTile = { key: "reactions", label: "Tim & quà", state: "value", value: null, hint: LOADING_HINT };
  } else if (reactSig && reactSig.status === "ok") {
    reactTile = {
      key: "reactions",
      label: "Tim & quà",
      state: "value",
      value: reactionsTotal == null ? null : reactionsTotal.toLocaleString("vi-VN"),
      hint: "Super Chat · quà · hội viên (cả phiên)",
    };
  } else {
    reactTile = {
      key: "reactions",
      label: "Tim & quà",
      state: "missing",
      reason:
        reactSig?.detail ??
        "chưa có nguồn sự kiện tim/quà cho phiên này — ô hiển thị THIẾU thay vì một số 0 giả",
    };
  }

  return [viewersTile, commentTile, clicksTile, reactTile];
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
    <svg viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden className="h-6 w-full">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

function Tile({ tile }: { tile: SignalTile }) {
  const degraded = tile.state === "degraded";
  return (
    <div
      className={cx(
        "flex min-w-0 flex-col rounded-md border p-2.5",
        degraded ? "border-warn/60 bg-warn/10" : "border-hairline bg-raised",
      )}
    >
      <div className="text-label uppercase text-dim">{tile.label}</div>
      {tile.state === "missing" ? (
        <>
          <div className="mt-1 text-strong text-dim">THIẾU nguồn</div>
          <p className="mt-1 line-clamp-3 text-meta leading-snug text-dim" title={tile.reason}>
            {tile.reason}
          </p>
        </>
      ) : (
        <>
          <div
            className={cx(
              "mt-1 text-num-s leading-none tracking-tight",
              degraded ? "text-warn-ink" : "text-ink",
            )}
          >
            {tile.value ?? "—"}
          </div>
          {tile.spark && tile.spark.length > 0 ? (
            <Sparkline values={tile.spark} color={tile.sparkColor ?? CHART.s1} />
          ) : null}
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
    <section
      aria-label="Dải thẻ tín hiệu"
      className={cx("flex flex-col rounded-lg border border-hairline bg-surface p-3", className)}
    >
      <SectionTitle className="mb-1.5" meta={meta}>
        Tín hiệu phiên
      </SectionTitle>
      <div className="grid flex-1 grid-cols-2 content-start gap-2">
        {tiles.map((t) => (
          <Tile key={t.key} tile={t} />
        ))}
      </div>
    </section>
  );
}
