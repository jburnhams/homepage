import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import type { Status } from "@/src/types";

export const status: Status = {
  generated: "2026-11-07T12:00:00+00:00",
  hostname: "omarchy",
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
export const server = setupServer(http.get(statusUrl, () => HttpResponse.json(status)));
