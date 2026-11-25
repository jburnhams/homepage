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

export type PerfWindow = "1h" | "24h" | "7d";
export type PerfResource = { key: string; label: string; unit: "%" | "GB" | "MB/s"; mean: number; p95: number; max: number; threshold: number | null; stressed_pct: number | null };
export type PerfService = { name: string; label: string; cpu_hours: number; ram_gb: number; swap_gb: number; written_gb: number; read_gb: number; gpu_mib: number };
export type PerfPressure = { resource: "memory" | "disk" | "cpu"; minutes: number; who: { name: string; label: string; share: number }[] };
export type PerfPoint = { x: number; y: number };
export type Perf =
  | { available: false; window: PerfWindow; label: string }
  | {
      available: true; window: PerfWindow; label: string; samples: number; covered_s: number; start: string; end: string;
      mem_total_gb: number; verdict: string; resources: PerfResource[]; services: PerfService[]; pressure: PerfPressure[];
      series: { cpu: PerfPoint[]; mem: PerfPoint[]; disk: PerfPoint[]; gpu: PerfPoint[] };
    };
