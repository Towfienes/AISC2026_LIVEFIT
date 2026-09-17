"use client";

/**
 * Zone 1 "Nhịp phiên" — session rhythm.
 *
 * Vertically stacked panels sharing one x-axis (small multiples, never a
 * dual-axis chart): comment tempo, viewers, click rate per minute. Each chart
 * panel carries its dashed forecast baseline ("đường dự báo baseline") —
 * dashing is reserved for projections. Tooltips are synced via `syncId`.
 *
 * ---------------------------------------------------------------------------
 * KHÔNG VẼ ĐƯỜNG CHO NGUỒN KHÔNG TỒN TẠI (gói UI-KOL)
 * ---------------------------------------------------------------------------
 * Trước gói này biểu đồ luôn vẽ đủ hai đường "người xem" và "lượt bấm/phút".
 * Trên 13/13 phiên replay thật, cả hai nguồn đều KHÔNG tồn tại: `viewers` và
 * `click_count` trong tick chỉ là chỗ trống. Kết quả là khung lớn nhất của bàn
 * vẽ hai đường phẳng ở mức 0 — mâu thuẫn thẳng với ô "THIẾU nguồn" ngay phía
 * trên, và đúng là loại số bịa mà dự án cấm.
 *
 * Nay mỗi panel do MA TRẬN TÍN HIỆU của máy chủ quyết định:
 *   - đo được  → vẽ đường;
 *   - thiếu    → một dải "THIẾU nguồn" kèm nguyên văn lý do, KHÔNG vẽ gì.
 * Nhịp bình luận (tín hiệu luôn có thật khi có chat) lên panel đầu, nên phiên
 * replay vẫn có một đường đáng đọc thay vì hai đường phẳng vô nghĩa.
 *
 * ---------------------------------------------------------------------------
 * KHÔNG VẼ LẠI CÓ HIỆU ỨNG (gói UI-3)
 * ---------------------------------------------------------------------------
 * Bàn poll số liệu 5 giây một lần. Recharts mặc định chạy hiệu ứng vẽ đường
 * (và hiệu ứng trượt của tooltip) sau MỖI lần dữ liệu đổi — nghĩa là cả biểu
 * đồ sẽ tự vẽ lại 12 lần mỗi phút, suốt 90 phút. Ngoài việc tốn CPU ngay cạnh
 * một luồng phát trực tiếp, nó còn phá đúng thứ biểu đồ này tồn tại để làm:
 * đọc HÌNH DẠNG của đường. Vì vậy `isAnimationActive={false}` là bắt buộc trên
 * MỌI thành phần vẽ ở đây — kể cả `<Tooltip>`, thứ hay bị bỏ sót.
 *
 * Chuyển động duy nhất được phép trong khung này là con trỏ tooltip, và nó do
 * chính chuột của người dùng điều khiển.
 *
 * ---------------------------------------------------------------------------
 * NHÃN TRỤC KHÔNG LẶP, KHÔNG CHỒNG (gói D)
 * ---------------------------------------------------------------------------
 * Trên /replay biểu đồ bị ép còn ~100 px và lộ hai lỗi đọc số:
 *   - trục x in `0' 1' 1' 2' 2'`: Recharts tự rải vạch mỗi 30 giây, còn nhãn
 *     làm tròn về phút → hai vạch liền nhau cùng một nhãn. Nay vạch được đặt
 *     TƯỜNG MINH ở bội số nguyên của phút (bước 1/2/5/10… phút tuỳ độ dài),
 *     nên mỗi nhãn là một phút khác nhau;
 *   - nhãn trục y của panel dưới ("8") dính vào nhãn "0" của panel trên ("4"):
 *     nhãn đầu/cuối trục y tràn nửa dòng chữ ra ngoài vùng vẽ. Panel không in
 *     trục x nay chừa lề trên/dưới đủ nửa dòng chữ, và trục y bỏ bớt nhãn khi
 *     panel thấp thay vì in đè.
 */

import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  TooltipProps,
  XAxis,
  YAxis,
} from "recharts";

import { CHART, type BlockInfo, type Tick } from "@/lib/types";

import Term from "./Term";

/**
 * NHUỘM VÙNG KHỐI BẬT (gói DESK-HOST v2, kỹ thuật D4 của spec UI-VISUAL):
 * các quãng thời gian hệ thống được quyền ghim được tô tím rất nhạt trên mọi
 * panel — người liếc thấy ngay nhịp tăng có rơi vào vùng tím hay không, tức
 * là câu chuyện nhân quả bằng mắt. Chỉ là LỚP NỀN tĩnh vẽ từ lịch đã bốc thăm
 * (dữ liệu thật của bàn điều khiển), không phải hiệu ứng. OPERATOR-ONLY theo
 * vị trí đặt: chỉ /desk và /replay (hai màn thấy lịch) truyền `blocks` vào.
 */
const ON_TINT = "rgba(139, 123, 255, 0.08)";

interface OnSpan {
  x1: number;
  x2: number;
}

/** Các quãng BẬT giao với miền dữ liệu đã vẽ — quãng ngoài dữ liệu bị cắt. */
function onSpans(blocks: BlockInfo[] | undefined, lastOffsetS: number): OnSpan[] {
  if (!blocks || blocks.length === 0) return [];
  const out: OnSpan[] = [];
  for (const b of blocks) {
    if (b.is_washout || b.assignment !== "ON") continue;
    const x1 = Math.max(0, b.start_offset_s);
    const x2 = Math.min(b.end_offset_s, lastOffsetS);
    if (x2 > x1) out.push({ x1, x2 });
  }
  return out;
}

interface MinutePoint {
  offset_s: number;
  comments: number | null;
  viewers: number | null;
  baselineViewers: number | null;
  clicksPerMin: number | null;
  baselineClicks: number | null;
}

/** Aggregate 30-second ticks into per-minute points for a calm, readable line. */
function toMinutePoints(ticks: Tick[]): MinutePoint[] {
  const byMin = new Map<
    number,
    { v: number[]; bv: number[]; c: number; bc: number[]; cm: number[] }
  >();
  for (const t of ticks) {
    const m = Math.floor(t.offset_s / 60);
    let e = byMin.get(m);
    if (!e) {
      e = { v: [], bv: [], c: 0, bc: [], cm: [] };
      byMin.set(m, e);
    }
    e.v.push(t.viewers);
    e.cm.push(t.comment_rate);
    if (t.baseline_viewers != null) e.bv.push(t.baseline_viewers);
    if (t.baseline_clicks_per_min != null) e.bc.push(t.baseline_clicks_per_min);
    e.c += t.click_count;
  }
  const avg = (a: number[]) => (a.length === 0 ? null : a.reduce((x, y) => x + y, 0) / a.length);
  return Array.from(byMin.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([m, e]) => ({
      offset_s: m * 60,
      comments: avg(e.cm),
      viewers: avg(e.v),
      baselineViewers: avg(e.bv),
      clicksPerMin: e.c,
      baselineClicks: avg(e.bc),
    }));
}

/** Bước vạch trục x (phút) — chọn bước nhỏ nhất giữ số nhãn ≤ MAX_X_LABELS. */
const MINUTE_STEPS = [1, 2, 5, 10, 15, 20, 30, 60] as const;
const MAX_X_LABELS = 8;

/**
 * Vạch trục x ở BỘI SỐ NGUYÊN của phút, từ 0 tới `lastOffsetS`. Mỗi vạch là
 * một phút khác nhau nên nhãn không bao giờ lặp (lỗi `0' 1' 1' 2'` cũ).
 */
function minuteTicks(lastOffsetS: number): number[] {
  const spanMin = Math.max(1, Math.ceil(lastOffsetS / 60));
  const step =
    MINUTE_STEPS.find((m) => spanMin / m <= MAX_X_LABELS) ??
    Math.ceil(spanMin / MAX_X_LABELS / 60) * 60;
  const out: number[] = [];
  for (let m = 0; m * 60 <= lastOffsetS; m += step) out.push(m * 60);
  return out;
}

/** X-axis tick: seconds -> minute label ("25'"). Vạch luôn ở phút tròn. */
function fmtMinuteTick(s: number): string {
  return `${Math.floor(s / 60)}'`;
}

function RhythmTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded border border-hairline bg-raised px-3 py-2 text-meta shadow-lg">
      <div className="mb-1 font-semibold text-sec">Phút {Math.round(Number(label) / 60)}</div>
      {payload.map((p) => (
        <div key={String(p.dataKey)} className="flex items-center gap-2 text-sec">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ background: p.color ?? CHART.mut }}
          />
          <span>{p.name}:</span>
          <span className="tnum font-semibold text-ink">
            {p.value == null ? "—" : Math.round(p.value * 10) / 10}
          </span>
        </div>
      ))}
    </div>
  );
}

const AXIS_TICK = { fill: CHART.dim, fontSize: 13 } as const;
/**
 * Nhãn trục y (13 px) canh GIỮA vào vạch, nên nhãn trên cùng/dưới cùng tràn
 * ~7 px ra ngoài vùng vẽ. Lề 8 px giữ nửa dòng chữ đó trong panel của nó —
 * không đè lên nhãn của panel kế bên. Panel in trục x đã có dải trục làm đệm
 * phía dưới.
 */
const MARGIN = { top: 8, right: 12, left: 0, bottom: 8 } as const;
const MARGIN_WITH_X_AXIS = { top: 8, right: 12, left: 0, bottom: 0 } as const;

/**
 * Dải thay cho một panel không có nguồn. Cùng ngôn ngữ với thẻ tín hiệu
 * ("THIẾU nguồn" + lý do nguyên văn của máy chủ) để hai chỗ không mâu thuẫn
 * nhau trên cùng một màn hình.
 */
function MissingRow({ label, reason }: { label: string; reason: string }) {
  return (
    <div className="flex shrink-0 flex-wrap items-baseline gap-x-2 gap-y-0.5 rounded-md border border-hairline bg-raised px-2.5 py-1.5">
      <span className="shrink-0 text-label uppercase text-dim">{label}</span>
      <span className="shrink-0 text-meta font-bold tracking-wide text-dim">THIẾU nguồn</span>
      <span className="min-w-0 flex-1 truncate text-meta leading-snug text-dim" title={reason}>
        {reason}
      </span>
    </div>
  );
}

interface SeriesSpec {
  key: keyof MinutePoint;
  name: string;
  color: string;
  dashed?: boolean;
}

/** Một panel biểu đồ: trục y riêng, trục x chung (chỉ panel cuối in nhãn). */
function Panel({
  data,
  series,
  showAxis,
  className,
  spans = [],
  playheadX = null,
  xTicks,
}: {
  data: MinutePoint[];
  series: SeriesSpec[];
  showAxis: boolean;
  className: string;
  /** Vạch trục x ở phút tròn (xem `minuteTicks`). */
  xTicks: number[];
  /** Vùng khối BẬT nhuộm tím (D4) — lớp nền tĩnh, vẽ trước mọi đường. */
  spans?: OnSpan[];
  /** Vạch "đang ở đây" (giây) — null ẩn vạch (phiên đã kết thúc/replay đứng yên). */
  playheadX?: number | null;
}) {
  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          syncId="rhythm"
          margin={showAxis ? MARGIN_WITH_X_AXIS : MARGIN}
        >
          <CartesianGrid stroke={CHART.grid} strokeWidth={1} vertical={false} />
          {/* Trục x là TRỤC SỐ (giây): ReferenceArea/ReferenceLine cần toạ độ
              thật để vùng BẬT và vạch playhead rơi đúng chỗ giữa các phút. */}
          {showAxis ? (
            <XAxis
              dataKey="offset_s"
              type="number"
              domain={[0, "dataMax"]}
              ticks={xTicks}
              tickFormatter={fmtMinuteTick}
              tick={AXIS_TICK}
              axisLine={{ stroke: CHART.axis }}
              tickLine={false}
              interval="preserveStartEnd"
              minTickGap={40}
            />
          ) : (
            <XAxis dataKey="offset_s" type="number" domain={[0, "dataMax"]} hide />
          )}
          {/* preserveStartEnd + minTickGap: panel thấp thì Recharts BỎ nhãn
              giữa (giữ 0 và đỉnh) thay vì in các nhãn đè lên nhau. */}
          <YAxis
            width={44}
            tick={AXIS_TICK}
            axisLine={false}
            tickLine={false}
            domain={[0, "auto"]}
            allowDecimals={false}
            tickCount={4}
            interval="preserveStartEnd"
            minTickGap={6}
          />
          <Tooltip
            content={<RhythmTooltip />}
            cursor={{ stroke: CHART.axis, strokeWidth: 1 }}
            isAnimationActive={false}
          />
          {spans.map((a) => (
            <ReferenceArea
              key={`on-${a.x1}`}
              x1={a.x1}
              x2={a.x2}
              fill={ON_TINT}
              stroke="none"
              ifOverflow="hidden"
            />
          ))}
          {playheadX != null ? (
            <ReferenceLine x={playheadX} stroke={CHART.ink} strokeOpacity={0.8} />
          ) : null}
          {series.map((s) => (
            <Line
              key={String(s.key)}
              name={s.name}
              type="monotone"
              dataKey={s.key}
              stroke={s.color}
              strokeWidth={2}
              strokeDasharray={s.dashed ? "5 4" : undefined}
              dot={false}
              activeDot={s.dashed ? false : { r: 4, stroke: CHART.surface, strokeWidth: 2 }}
              isAnimationActive={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

interface Props {
  ticks: Tick[];
  /**
   * Lý do tiếng Việt từ MA TRẬN TÍN HIỆU của máy chủ khi nguồn không đo được
   * (`GET /sessions/{id}/signals`). `null`/bỏ trống = nguồn đo được, vẽ đường.
   * Không bao giờ suy đoán theo nền tảng — đó là việc của máy chủ.
   */
  viewersMissing?: string | null;
  clicksMissing?: string | null;
  /**
   * Lịch khối của phiên — CHỈ màn thấy lịch (desk/replay) truyền vào để nhuộm
   * vùng BẬT. Bỏ trống = không nhuộm gì (không đoán lịch).
   */
  blocks?: BlockInfo[];
  /** Vị trí hiện tại (giây) cho vạch "đang ở đây"; null/bỏ trống = ẩn vạch. */
  positionS?: number | null;
  /**
   * Ngữ cảnh PHÁT LẠI (/replay): số liệu không "tự về" — người xem phải bấm
   * Phát hoặc kéo thanh tua. Câu trạng thái rỗng của màn live ("Bạn không cần
   * bấm gì") sai ở đây nên được thay.
   */
  replay?: boolean;
}

export default function RhythmChart({
  ticks,
  viewersMissing,
  clicksMissing,
  blocks,
  positionS,
  replay = false,
}: Props) {
  const data = useMemo(() => toMinutePoints(ticks), [ticks]);
  const lastPointS = data.length > 0 ? data[data.length - 1].offset_s : 0;
  const xTicks = useMemo(() => minuteTicks(lastPointS), [lastPointS]);

  // Một điểm không vẽ thành đường: Recharts sẽ trả về khung trống có trục,
  // trông y hệt "biểu đồ hỏng". Nói thẳng còn đang chờ gì thì hơn.
  if (data.length < 2) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-1.5 px-4 text-center">
        <p className="text-body text-sec">
          {data.length === 0
            ? "Chưa có phút số liệu nào."
            : "Mới có một phút số liệu — cần hai phút mới vẽ được đường."}
        </p>
        <p className="text-meta text-dim">
          {replay
            ? "Bấm Phát hoặc kéo thanh tua qua phút đầu — biểu đồ vẽ theo bản ghi, mỗi phút một điểm."
            : "Biểu đồ tự vẽ khi số liệu về, khoảng 5 giây một lần. Bạn không cần bấm gì."}
        </p>
      </div>
    );
  }

  // Chỉ chú giải đường dự báo khi panel MANG nó thật sự được vẽ — chú giải cho
  // một đường không có trên hình là một lời nói dối nhỏ nhưng vẫn là nói dối.
  const hasBaseline =
    (!viewersMissing && data.some((d) => d.baselineViewers != null)) ||
    (!clicksMissing && data.some((d) => d.baselineClicks != null));
  // Panel cuối CÙNG CÓ VẼ mới in nhãn phút — nếu trục x rơi vào một dải THIẾU
  // thì cả biểu đồ mất thang thời gian.
  const drawn: ("comments" | "viewers" | "clicks")[] = ["comments"];
  if (!viewersMissing) drawn.push("viewers");
  if (!clicksMissing) drawn.push("clicks");
  const last = drawn[drawn.length - 1];

  // Vùng BẬT + vạch playhead cắt vào miền dữ liệu đã vẽ — không kéo dài trục
  // sang tương lai chưa có số liệu.
  const lastOffsetS = data[data.length - 1].offset_s;
  const spans = onSpans(blocks, lastOffsetS);
  const playheadX = positionS == null ? null : Math.min(positionS, lastOffsetS);

  return (
    <div className="flex h-full min-h-0 flex-col gap-1.5">
      {/* legend — identity never by color alone, và chỉ liệt kê đường CÓ VẼ */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-0.5 px-1 text-meta text-sec">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4 rounded" style={{ background: CHART.s3 }} />
          <Term tip="Số bình luận mỗi phút — tín hiệu nhịp duy nhất luôn đo được khi phòng chat có người.">
            Bình luận / phút
          </Term>
        </span>
        {!viewersMissing && (
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-0.5 w-4 rounded" style={{ background: CHART.s1 }} />
            <Term tip="Số người đang xem phiên live tại mỗi phút.">Người xem</Term>
          </span>
        )}
        {!clicksMissing && (
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-0.5 w-4 rounded" style={{ background: CHART.s2 }} />
            <Term tip="Số lần người xem bấm vào link sản phẩm trong mỗi phút — chỉ số chính để so khối BẬT với khối TẮT.">
              Lượt bấm link / phút
            </Term>
          </span>
        )}
        {hasBaseline && (
          <span className="flex items-center gap-1.5">
            <svg width="18" height="4" aria-hidden>
              <line
                x1="0"
                y1="2"
                x2="18"
                y2="2"
                stroke={CHART.mut}
                strokeWidth="2"
                strokeDasharray="4 3"
              />
            </svg>
            <Term tip="Con số từ mô hình dự báo — chưa qua thí nghiệm nên không có khoảng tin cậy. Nét đứt chỉ dành cho dự báo.">
              Dự báo nếu không can thiệp
            </Term>
          </span>
        )}
        {spans.length > 0 && (
          <span className="flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-3 rounded-sm"
              style={{ background: "rgba(139,123,255,0.45)" }}
            />
            <Term tip="Quãng thời gian hệ thống được quyền ghim theo lịch bốc thăm — so nhịp trong/ngoài vùng tím là câu chuyện nhân quả bằng mắt.">
              Vùng tím = khối BẬT
            </Term>
          </span>
        )}
        {playheadX != null && (
          <span className="flex items-center gap-1.5">
            <span aria-hidden className="inline-block h-3 w-0.5 rounded-full bg-ink" />
            đang ở đây
          </span>
        )}
      </div>

      {/* panel 1: nhịp bình luận — nguồn thật của MỌI phiên có chat */}
      <Panel
        data={data}
        series={[{ key: "comments", name: "Bình luận / phút", color: CHART.s3 }]}
        showAxis={last === "comments"}
        className="min-h-0 flex-[3]"
        spans={spans}
        playheadX={playheadX}
        xTicks={xTicks}
      />

      {/* panel 2: người xem + baseline dự báo — hoặc dải THIẾU nguồn */}
      {viewersMissing ? (
        <MissingRow label="Người xem" reason={viewersMissing} />
      ) : (
        <Panel
          data={data}
          series={[
            { key: "baselineViewers", name: "Dự báo baseline", color: CHART.mut, dashed: true },
            { key: "viewers", name: "Người xem", color: CHART.s1 },
          ]}
          showAxis={last === "viewers"}
          className="min-h-0 flex-[3]"
          spans={spans}
          playheadX={playheadX}
          xTicks={xTicks}
        />
      )}

      {/* panel 3: lượt bấm link / phút — hoặc dải THIẾU nguồn */}
      {clicksMissing ? (
        <MissingRow label="Lượt bấm / phút" reason={clicksMissing} />
      ) : (
        <Panel
          data={data}
          series={[
            { key: "baselineClicks", name: "Baseline bấm link", color: CHART.mut, dashed: true },
            { key: "clicksPerMin", name: "Lượt bấm link / phút", color: CHART.s2 },
          ]}
          showAxis={last === "clicks"}
          className="min-h-0 flex-[2]"
          spans={spans}
          playheadX={playheadX}
          xTicks={xTicks}
        />
      )}
    </div>
  );
}
