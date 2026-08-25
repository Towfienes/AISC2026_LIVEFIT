/** Number / time formatting: vi-VN locale, display timezone Asia/Ho_Chi_Minh. */

const TZ = "Asia/Ho_Chi_Minh";

const numberFmt = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 });
const vndFmt = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0,
});
const timeFmt = new Intl.DateTimeFormat("vi-VN", {
  timeZone: TZ,
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});
const dateFmt = new Intl.DateTimeFormat("vi-VN", {
  timeZone: TZ,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

export function fmtNumber(n: number): string {
  return numberFmt.format(n);
}

export function fmtVnd(n: number): string {
  return vndFmt.format(n);
}

/** Elapsed seconds -> "HH:MM:SS". */
export function fmtClock(totalS: number): string {
  const s = Math.max(0, Math.floor(totalS));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  const pad = (x: number) => String(x).padStart(2, "0");
  return `${pad(h)}:${pad(m)}:${pad(ss)}`;
}

/** Elapsed seconds -> "MM:SS" (short, for countdowns and axes). */
export function fmtMinSec(totalS: number): string {
  const s = Math.max(0, Math.floor(totalS));
  const m = Math.floor(s / 60);
  const ss = s % 60;
  return `${String(m).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
}

/** ISO UTC timestamp -> local wall clock in Asia/Ho_Chi_Minh. */
export function fmtTimeHCM(iso: string): string {
  return timeFmt.format(new Date(iso));
}

/** ISO UTC timestamp -> date in Asia/Ho_Chi_Minh (dd/mm/yyyy). */
export function fmtDateHCM(iso: string): string {
  return dateFmt.format(new Date(iso));
}

/**
 * Elapsed seconds -> compact label: "MM:SS" under one hour, "HH:MM:SS" above
 * (used for block boundaries and scrubber positions).
 */
export function fmtElapsed(totalS: number): string {
  return totalS >= 3600 ? fmtClock(totalS) : fmtMinSec(totalS);
}

/** Signed percent, e.g. 0.183 -> "+18%". */
export function fmtPct(x: number): string {
  const v = Math.round(x * 100);
  return `${v >= 0 ? "+" : ""}${v}%`;
}
