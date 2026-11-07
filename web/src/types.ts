export type App = {
  name: string; path: string; desc: string; unit: string; state: string;
  version: "" | "current" | "behind" | "unknown"; running_rev?: string; head_rev?: string;
};
export type Job = { label: string; unit: string; result: string; active: string; last: string; next: string };
export type Disk = { label: string; path: string; total: number; used: number; pct: number };
export type Proc = { pid: number; name: string; cpu: number; rss: number };
export type Resources = {
  interval: number; ncpu: number; cpu: number[]; mem: number[]; mem_cache: number[];
  mem_total_kb: number; mem_avail_kb: number; mem_used_kb: number; mem_free_kb: number;
  mem_buffers_kb: number; mem_cached_kb: number; swap_total_kb: number; swap_free_kb: number;
  top_cpu: Proc[]; top_mem: Proc[];
};
export type Status = {
  generated: string; hostname: string; finding: string | null;
  apps: App[]; jobs: Job[]; failed: string[]; disks: Disk[];
  system: { uptime_s?: number; load?: [number, number, number] };
  resources?: Resources;
};
