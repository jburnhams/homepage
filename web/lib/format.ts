// Numbers and dates go through strata-react's `format` (Intl, non-breaking units, an en dash for a
// value that is not known). Only what is specific to this page stays here: systemd's time stamps,
// uptime and the chart's "seconds ago" ticks.
import { createFormat, NBSP } from "strata-react";

export const format = createFormat("en-GB");

/** The server's percentages run 0-100 (CPU can pass 100 on several cores); `format.percent` takes a ratio. */
export const percent = (v: number) => format.percent(v / 100);

/** /proc reports kibibytes; `format.bytes` takes bytes. */
export const kb = (v: number) => format.bytes(v * 1024);

export function uptime(s: number): string {
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `${d ? `${d}d ` : ""}${h}h ${m}m`;
}

/** systemd's "Sat 2026-11-07 04:25:28 GMT" -> "07 Nov 04:25"; empty -> a dash. */
export function systemdTime(ts: string): string {
  const [, date, time] = ts.split(" ");
  if (!date || !date.includes("-") || !time) return ts || format.missing;
  const [, mo, da] = date.split("-");
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${da} ${months[Number(mo) - 1] ?? mo} ${time.slice(0, 5)}`;
}

/** Seconds ago as a chart tick label: "now", "−30 s", "−2 min", "−6 h", "−3 d". */
export function ago(seconds: number): string {
  if (seconds <= 0) return "now";
  if (seconds < 90) return `−${Math.round(seconds)}${NBSP}s`;
  if (seconds < 90 * 60) return `−${Math.round(seconds / 60)}${NBSP}min`;
  if (seconds < 36 * 3600) return `−${Math.round(seconds / 3600)}${NBSP}h`;
  return `−${Math.round(seconds / 86400)}${NBSP}d`;
}

/** A reading with its unit: "42 %", "12.3 GB", "5.0 MB/s". */
export function measure(v: number, unit: string): string {
  return unit === "%" ? percent(v) : `${format.decimal(v)}${NBSP}${unit}`;
}

/** A length of time in words: "16 min", "3.5 h", "2.0 days". */
export function duration(s: number): string {
  if (s < 5400) return `${Math.round(s / 60)}${NBSP}min`;
  if (s < 172800) return `${format.decimal(s / 3600)}${NBSP}h`;
  return `${format.decimal(s / 86400)}${NBSP}days`;
}
