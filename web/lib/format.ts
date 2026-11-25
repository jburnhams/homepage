// Every number and time on screen goes through here, once. Units are joined with a non-breaking
// space so "4.2 GB" never wraps between figure and unit.
const NBSP = " ";
const locale = "en-GB";

const one = new Intl.NumberFormat(locale, { maximumFractionDigits: 1, minimumFractionDigits: 1 });
const zero = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
export const percent = (v: number) => `${zero.format(v)}${NBSP}%`;
export const clock = new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit", second: "2-digit" });

export function bytes(n: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }
  return `${i < 2 ? zero.format(n) : one.format(n)}${NBSP}${units[i]}`;
}

export const kb = (v: number) => bytes(v * 1024);

export function uptime(s: number): string {
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `${d ? `${d}d ` : ""}${h}h ${m}m`;
}

/** systemd's "Sat 2026-11-07 04:25:28 GMT" -> "07 Nov 04:25"; empty -> a dash. */
export function systemdTime(ts: string): string {
  const [, date, time] = ts.split(" ");
  if (!date || !date.includes("-") || !time) return ts || "–";
  const [, mo, da] = date.split("-");
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${da} ${months[Number(mo) - 1] ?? mo} ${time.slice(0, 5)}`;
}

/** Seconds ago as a tick label: "now", "−30 s", "−2 min", "−6 h", "−3 d". */
export function ago(seconds: number): string {
  if (seconds <= 0) return "now";
  if (seconds < 90) return `−${Math.round(seconds)}${NBSP}s`;
  if (seconds < 90 * 60) return `−${Math.round(seconds / 60)}${NBSP}min`;
  if (seconds < 36 * 3600) return `−${Math.round(seconds / 3600)}${NBSP}h`;
  return `−${Math.round(seconds / 86400)}${NBSP}d`;
}

/** A reading with its unit: "42 %", "12.3 GB", "5.0 MB/s". */
export function measure(v: number, unit: string): string {
  return unit === "%" ? percent(v) : `${one.format(v)}${NBSP}${unit}`;
}

/** A length of time in words: "16 min", "3.5 h", "2.0 days". */
export function duration(s: number): string {
  if (s < 5400) return `${Math.round(s / 60)}${NBSP}min`;
  if (s < 172800) return `${one.format(s / 3600)}${NBSP}h`;
  return `${one.format(s / 86400)}${NBSP}days`;
}
