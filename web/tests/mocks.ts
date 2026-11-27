import { http, HttpResponse } from "msw";
import type { Perf, Status } from "@/src/types";

export const status: Status = {
  generated: "2026-11-07T12:00:00+00:00",
  hostname: "myhost",
  finding: null,
  apps: [
    { name: "Notes", path: "/notes/", desc: "Markdown notes", unit: "notes.service", state: "active", version: "behind", running_rev: "a1b2c3d", head_rev: "e4f5a6b" },
    { name: "Files", path: "/files/", desc: "File share", unit: "files.service", state: "failed", version: "" },
  ],
  jobs: [{ label: "Backup", unit: "backup.service", result: "success", active: "inactive", last: "Sat 2026-11-07 04:25:28 GMT", next: "Sun 2026-11-08 04:25:00 GMT" }],
  failed: [],
  disks: [{ label: "Root", path: "/", total: 1e11, used: 5e10, pct: 50 }],
  system: { uptime_s: 90_000, load: [0.5, 0.4, 0.3] },
  resources: {
    interval: 5, ncpu: 4, cpu: [10, 20, 30], mem: [40, 41, 42], mem_cache: [5, 5, 5],
    mem_total_kb: 16_000_000, mem_avail_kb: 8_000_000, mem_used_kb: 6_000_000, mem_free_kb: 4_000_000,
    mem_buffers_kb: 100_000, mem_cached_kb: 2_000_000, swap_total_kb: 0, swap_free_kb: 0,
    top_cpu: [{ pid: 1, name: "firefox", cpu: 55, rss: 1e9 }],
    top_mem: [{ pid: 2, name: "postgres", cpu: 1, rss: 2e9 }],
  },
};

export const statusUrl = "/_home/api/status";
export const perfUrl = "/_home/api/perf";

const line = (seconds: number, f: (i: number) => number) =>
  Array.from({ length: 24 }, (_, i) => ({ x: -Math.round(seconds * (1 - i / 23)), y: f(i) }));

export const perf = (window: "1h" | "24h" | "7d" = "1h"): Perf => {
  const seconds = { "1h": 3600, "24h": 86400, "7d": 604800 }[window];
  return {
    available: true, window, label: { "1h": "last hour", "24h": "last 24 hours", "7d": "last week" }[window],
    samples: 360, covered_s: Math.min(seconds, 3600), start: "2026-11-25T11:00:00", end: "2026-11-25T12:00:00", mem_total_gb: 32,
    verdict: "Programs waiting for memory was the tightest in the last hour: over its limit 12% of the time, mostly render-worker.",
    resources: [
      { key: "cpu", label: "CPU busy, all threads", unit: "%", mean: 20, p95: 60, max: 90, threshold: 80, stressed_pct: 0.4 },
      { key: "mem_wait", label: "Programs waiting for memory", unit: "%", mean: 5, p95: 30, max: 45, threshold: 10, stressed_pct: 12 },
      { key: "disk_sdb", label: "Disk sdb busy", unit: "%", mean: 1, p95: 8, max: 50, threshold: 80, stressed_pct: 4 },
      { key: "mem", label: "Memory in use", unit: "GB", mean: 18.2, p95: 25, max: 28.4, threshold: 28.8, stressed_pct: 0 },
      { key: "net_rx", label: "Network in (eth0)", unit: "MB/s", mean: 0.3, p95: 1.7, max: 2.4, threshold: 90, stressed_pct: 0 },
    ],
    services: [
      { name: "render-worker", label: "", cpu_hours: 3.2, ram_gb: 18.1, swap_gb: 4.3, written_gb: 0.4, read_gb: 0, gpu_mib: 9930 },
      { name: "nightly-import", label: "photos", cpu_hours: 0.5, ram_gb: 2.4, swap_gb: 0, written_gb: 1.2, read_gb: 1.5, gpu_mib: 0 },
    ],
    pressure: [
      { resource: "memory", minutes: 7, disks: [], who: [{ name: "render-worker", label: "", dir: "", share: 80 }, { name: "nightly-import", label: "photos", dir: "", share: 20 }] },
      { resource: "disk", minutes: 12, disks: [{ disk: "sdb", share: 85, spinning: true }], who: [{ name: "file-share", label: "", dir: "(whole service)", share: 60 }, { name: "media-sync", label: "", dir: "/data/archive/raw", share: 40 }] },
    ],
    disk_paths: [
      { disk: "sdb", name: "indexer", label: "", dir: "/data/archive/raw", read_gb: 120.4, write_gb: 0, active_min: 540, hours: 9, steady: true },
      { disk: "sdb", name: "copy-job", label: "", dir: "/data/archive/2015", read_gb: 80, write_gb: 2.1, active_min: 25, hours: 1, steady: false },
    ],
    series: { cpu: line(seconds, (i) => 10 + i), mem: line(seconds, (i) => 16 + i / 4), disk: line(seconds, () => 3), gpu: line(seconds, () => 0) },
  };
};

/** The healthy server: the handlers the unit tests and the visual shots both start from. */
export const handlers = [
  http.get(statusUrl, () => HttpResponse.json(status)),
  http.get(perfUrl, ({ request }) => HttpResponse.json(perf((new URL(request.url).searchParams.get("window") ?? "1h") as "1h" | "24h" | "7d"))),
];

// Server states for the visual shots (and reusable in tests).
export const statusLoading = http.get(statusUrl, () => new Promise<never>(() => {}));
export const statusError = http.get(statusUrl, () => new HttpResponse(null, { status: 500 }));
export const noApps = http.get(statusUrl, () => HttpResponse.json({ ...status, apps: [] }));
export const failedUnits = http.get(statusUrl, () =>
  HttpResponse.json({ ...status, finding: "Files is failed. Disk Root is 93 % full.", failed: ["files.service"], disks: [{ ...status.disks[0], used: 9.3e10, pct: 93 }] }),
);
