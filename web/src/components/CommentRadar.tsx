"use client";

/**
 * Zone 3 "Radar bình luận" — stacked per-minute intent distribution over the
 * last 5 minutes.
 *
 * Color rules (dataviz): intents keep their FIXED categorical slots from
 * INTENT_META regardless of which intents appear in the window (color follows
 * the entity). Identity is never color-alone: the legend names every intent and
 * the tooltip lists labels. 2px surface gaps separate stacked segments.
 */

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  TooltipProps,
  XAxis,
  YAxis,
} from "recharts";

import { CHART, INTENT_LABELS, INTENT_META, type CommentItem } from "@/lib/types";

interface Props {
  comments: CommentItem[];
  /** Current position (s since session start) — window is [nowS-300, nowS). */
  nowS: number;
}

type MinuteRow = { minute: number; label: string } & Record<string, number | string>;

function buildRows(comments: CommentItem[], nowS: number): MinuteRow[] {
  const endMin = Math.max(0, Math.floor(nowS / 60));
  const rows: MinuteRow[] = [];
  for (let m = Math.max(0, endMin - 4); m <= endMin; m++) {
    const row: MinuteRow = { minute: m, label: `${m}'` };
    for (const k of INTENT_LABELS) row[k] = 0;
    rows.push(row);
  }
  const lo = rows[0]?.minute ?? 0;
  for (const c of comments) {
    const m = Math.floor(c.offset_s / 60);
    if (m < lo || m > endMin || c.offset_s > nowS) continue;
    const key = c.intent_label ?? "khac";
    const row = rows[m - lo];
    row[key] = (row[key] as number) + 1;
  }
  return rows;
}

function RadarTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null;
  const total = payload.reduce((s, p) => s + (typeof p.value === "number" ? p.value : 0), 0);
  return (
    <div className="rounded border border-hairline bg-raised px-3 py-2 text-xs shadow-lg">
      <div className="mb-1 font-semibold text-sec">
        Phút {String(label)} · <span className="tnum text-ink">{total}</span> bình luận
      </div>
      {[...payload].reverse().map((p) => (
        <div key={String(p.dataKey)} className="flex items-center gap-2 text-sec">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ background: p.color ?? CHART.mut }}
          />
          <span>{p.name}:</span>
          <span className="tnum font-semibold text-ink">{p.value ?? 0}</span>
        </div>
      ))}
    </div>
  );
}

export default function CommentRadar({ comments, nowS }: Props) {
  const rows = useMemo(() => buildRows(comments, nowS), [comments, nowS]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* legend — fixed intent order, names beside colors */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 px-1 pb-1 text-[10px] text-sec">
        {INTENT_LABELS.map((k) => (
          <span key={k} className="flex items-center gap-1">
            <span
              className="inline-block h-2 w-2 rounded-sm"
              style={{ background: INTENT_META[k].color }}
            />
            {INTENT_META[k].label}
          </span>
        ))}
      </div>
      <div className="min-h-0 flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 4, right: 8, left: 0, bottom: 0 }} barCategoryGap="25%">
            <CartesianGrid stroke={CHART.grid} strokeWidth={1} vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fill: CHART.mut, fontSize: 10 }}
              axisLine={{ stroke: CHART.axis }}
              tickLine={false}
            />
            <YAxis
              width={28}
              tick={{ fill: CHART.mut, fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip content={<RadarTooltip />} cursor={{ fill: "rgba(255,255,255,0.05)" }} />
            {INTENT_LABELS.map((k) => (
              <Bar
                key={k}
                name={INTENT_META[k].label}
                dataKey={k}
                stackId="intent"
                fill={INTENT_META[k].color}
                stroke={CHART.surface}
                strokeWidth={1}
                isAnimationActive={false}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
