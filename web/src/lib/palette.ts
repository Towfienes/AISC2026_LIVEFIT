/**
 * Block-strip colors (operator view only).
 *
 * ON uses categorical slot 7 (violet) — deliberately outside the chart series
 * slots 1–6 so the strip never collides with a chart series or an intent color.
 * OFF is the neutral axis fill: recessive, clearly "control", readable with the
 * BẬT/TẮT text labels (identity never by color alone).
 */

export const BLOCK_ON_COLOR = "#9085e9"; // slot 7 violet
export const BLOCK_OFF_COLOR = "#383835"; // neutral fill (axis token)
