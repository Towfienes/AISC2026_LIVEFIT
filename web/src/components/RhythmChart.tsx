"use client";

/**
 * Zone 1 "Nhịp phiên" — session rhythm.
 *
 * Two vertically stacked panels sharing one x-axis (small multiples, never a
 * dual-axis chart): viewers on top, click rate per minute below. Each panel
 * carries its dashed forecast baseline ("đường dự báo baseline") — dashing is
 * reserved for projections. Tooltips are synced via Recharts `syncId`.
 */

import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  TooltipProps,
  XAxis,
  YAxis,
} from "recharts";

import { CHART, type Tick } from "@/lib/types";

interface MinutePoint {
  offset_s: number;
  viewers: number | null;
  baselineViewers: number | null;
  clicksPerMin: number | null;
  baselineClicks: number | null;
}

/** Aggregate 30-second ticks into per-minute points for a calm, readable line. */
function toMinutePoints(ticks: Tick[]): MinutePoint[] {
  const byMin = new Map<number, { v: number[]; bv: number[]; c: number; bc: number[] }>();
  for (const t of ticks) {
    const m = Math.floor(t.offset_s / 60);
    let e = byMin.get(m);
    if (!e) {
      e = { v: [], bv: [], c: 0, bc: [] };
      byMin.set(m, e);
    }
    e.v.push(t.viewers);
    if (t.baseline_viewers != null) e.bv.push(t.baseline_viewers);
    if (t.baseline_clicks_per_min != null) e.bc.push(t.baseline_clicks_per_min);
    e.c += t.click_count;
  }
  const avg = (a: number[]) => (a.length === 0 ? null : a.reduce((x, y) => x + y, 0) / a.length);
  return Array.from(byMin.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([m, e]) => ({
      offset_s: m * 60,
      viewers: avg(e.v),
      baselineViewers: avg(e.bv),
      clicksPerMin: e.c,
      baselineClicks: avg(e.bc),
    }));
}

/** X-axis tick: seconds -> minute label ("25'"). */
function fmtMinuteTick(s: number): string {
  return `${Math.round(s / 60)}'`;
}

function RhythmTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded border border-hairline bg-raised px-3 py-2 text-xs shadow-lg">
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

const AXIS_TICK = { fill: CHART.mut, fontSize: 10 } as const;
const MARGIN = { top: 4, right: 12, left: 0, bottom: 0 } as const;

export default function RhythmChart({ ticks }: { ticks: Tick[] }) {
  const data = useMemo(() => toMinutePoints(ticks), [ticks]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* legend — identity never by color alone */}
      <div className="flex items-center gap-4 px-1 pb-1 text-[11px] text-sec">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4 rounded" style={{ background: CHART.s1 }} />
          Người xem
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4 rounded" style={{ background: CHART.s2 }} />
          Lượt bấm link / phút
        </span>
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
          Đường dự báo baseline
        </span>
      </div>

      {/* panel 1: viewers + forecast baseline */}
      <div className="min-h-0 flex-[3]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} syncId="rhythm" margin={MARGIN}>
            <CartesianGrid stroke={CHART.grid} strokeWidth={1} vertical={false} />
            <XAxis dataKey="offset_s" hide />
            <YAxis width={36} tick={AXIS_TICK} axisLine={false} tickLine={false} domain={[0, "auto"]} />
            <Tooltip content={<RhythmTooltip />} cursor={{ stroke: CHART.axis, strokeWidth: 1 }} />
            <Line
              name="Dự báo baseline"
              type="monotone"
              dataKey="baselineViewers"
              stroke={CHART.mut}
              strokeWidth={2}
              strokeDasharray="5 4"
              dot={false}
              activeDot={false}
              isAnimationActive={false}
              connectNulls
            />
            <Line
              name="Người xem"
              type="monotone"
              dataKey="viewers"
              stroke={CHART.s1}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, stroke: CHART.surface, strokeWidth: 2 }}
              isAnimationActive={false}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* panel 2: click rate per minute (own y-axis, same x) */}
      <div className="min-h-0 flex-[2]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} syncId="rhythm" margin={MARGIN}>
            <CartesianGrid stroke={CHART.grid} strokeWidth={1} vertical={false} />
            <XAxis
              dataKey="offset_s"
              tickFormatter={fmtMinuteTick}
              tick={AXIS_TICK}
              axisLine={{ stroke: CHART.axis }}
              tickLine={false}
              interval="preserveStartEnd"
              minTickGap={40}
            />
            <YAxis
              width={36}
              tick={AXIS_TICK}
              axisLine={false}
              tickLine={false}
              domain={[0, "auto"]}
              allowDecimals={false}
            />
            <Tooltip content={<RhythmTooltip />} cursor={{ stroke: CHART.axis, strokeWidth: 1 }} />
            <Line
              name="Baseline bấm link"
              type="monotone"
              dataKey="baselineClicks"
              stroke={CHART.mut}
              strokeWidth={2}
              strokeDasharray="5 4"
              dot={false}
              activeDot={false}
              isAnimationActive={false}
              connectNulls
            />
            <Line
              name="Lượt bấm link / phút"
              type="monotone"
              dataKey="clicksPerMin"
              stroke={CHART.s2}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, stroke: CHART.surface, strokeWidth: 2 }}
              isAnimationActive={false}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
