import * as React from "react";
import { DataTable, DataView, EmptyState, LineChart, Skeleton, Status, Tabs, type Column } from "strata-react";
import { ago, duration, format, measure, percent } from "@/lib/format";
import type { Perf, PerfDiskPath, PerfPoint, PerfPressure, PerfResource, PerfService, PerfWindow } from "@/src/types";
import { usePerf } from "@/src/use-perf";

const WINDOWS: { value: PerfWindow; label: string; seconds: number }[] = [
  { value: "1h", label: "Last hour", seconds: 3600 },
  { value: "24h", label: "24 hours", seconds: 86400 },
  { value: "7d", label: "Week", seconds: 604800 },
];

/** A word for how often a resource was over its limit; never colour alone. */
function Over({ r }: { r: PerfResource }) {
  const p = r.stressed_pct;
  if (p === null) return <span className="text-muted-foreground">–</span>;
  if (p < 1) return <Status tone="success">Fine</Status>;
  if (p < 10) return <Status tone="warning">{`Sometimes ${percent(p)}`}</Status>;
  return <Status tone="danger">{`Often ${percent(p)}`}</Status>;
}

type Col<T> = Column<T> & { phone?: boolean };

/** Columns marked `phone: false` are left out below 640 px. The library's `className` only reaches cells, which would leave their headers behind. */
const fit = <T,>(cols: Col<T>[], narrow: boolean): Column<T>[] =>
  cols.filter((c) => !narrow || c.phone !== false).map(({ phone: _p, ...c }) => c);

function useNarrow(): boolean {
  const query = "(max-width: 639px)";
  const [narrow, setNarrow] = React.useState(() => typeof matchMedia === "function" && matchMedia(query).matches);
  React.useEffect(() => {
    if (typeof matchMedia !== "function") return;
    const m = matchMedia(query);
    const on = () => setNarrow(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
  return narrow;
}

const resourceColumns: Col<PerfResource>[] = [
  { key: "label", header: "Resource", cell: (r) => r.label, truncate: true },
  { key: "mean", header: "Average", numeric: true, cell: (r) => measure(r.mean, r.unit), phone: false },
  { key: "p95", header: "Busy (95%)", numeric: true, cell: (r) => measure(r.p95, r.unit), phone: false },
  { key: "max", header: "Peak", numeric: true, cell: (r) => measure(r.max, r.unit), phone: false },
  { key: "over", header: "Over its limit", cell: (r) => <Over r={r} />, sort: (a, b) => (a.stressed_pct ?? -1) - (b.stressed_pct ?? -1) },
];

const who = (s: { name: string; label: string }) => (s.label ? `${s.name} [${s.label}]` : s.name);

const serviceColumns: Col<PerfService>[] = [
  { key: "name", header: "Service or job", cell: who, truncate: true, sort: (a, b) => who(a).localeCompare(who(b)) },
  { key: "cpu", header: "CPU hours", numeric: true, cell: (s) => s.cpu_hours.toFixed(2), sort: (a, b) => a.cpu_hours - b.cpu_hours },
  { key: "ram", header: "Memory", numeric: true, cell: (s) => measure(s.ram_gb, "GB"), sort: (a, b) => a.ram_gb - b.ram_gb },
  { key: "written", header: "Disk written", numeric: true, cell: (s) => measure(s.written_gb, "GB"), phone: false },
  { key: "gpu", header: "GPU memory", numeric: true, cell: (s) => (s.gpu_mib ? format.bytes(s.gpu_mib * 1024 * 1024) : "–"), phone: false },
];

const resourceWord = { memory: "memory", disk: "disk", cpu: "a CPU" } as const;

/** "media-sync in /data/archive/raw 62%"; a whole-service row has no folder. */
const who2 = (w: { name: string; label: string; dir: string; share: number }) =>
  `${who(w)}${w.dir && w.dir !== "(whole service)" ? ` in ${w.dir}` : ""} ${w.share}%`;

function Pressure({ p }: { p: PerfPressure }) {
  const names = p.who.filter((w) => w.share > 0).map(who2);
  const disks = p.disks.map((d) => `${d.disk}${d.spinning ? " (spinning)" : ""} ${percent(d.share)}`);
  return (
    <li>
      Programs waited for {resourceWord[p.resource]} for {duration(p.minutes * 60)}.
      {disks.length > 0 && ` Busy then: ${disks.join(", ")}.`}
      {names.length > 0 && ` ${p.resource === "disk" ? "Most data moved on those disks" : "Busiest then"}: ${names.join(", ")}.`}
    </li>
  );
}

const pathColumns: Col<PerfDiskPath>[] = [
  { key: "disk", header: "Disk", cell: (d) => d.disk },
  { key: "name", header: "Service or job", cell: (d) => who(d), truncate: true, sort: (a, b) => who(a).localeCompare(who(b)) },
  { key: "dir", header: "Folder", cell: (d) => (d.dir === "(whole service)" ? "whole service" : d.dir), truncate: true, phone: false },
  { key: "data", header: "Data", numeric: true, cell: (d) => measure(d.read_gb + d.write_gb, "GB"), sort: (a, b) => a.read_gb + a.write_gb - (b.read_gb + b.write_gb) },
  { key: "active", header: "Active", numeric: true, cell: (d) => duration(d.active_min * 60), sort: (a, b) => a.active_min - b.active_min, phone: false },
  { key: "pattern", header: "Pattern", cell: (d) => (d.steady ? <Status tone="warning">Steady, move?</Status> : <Status tone="neutral">Bursts</Status>) },
];

function Chart({ title, points, seconds, unit, yMax, colour }: { title: string; points: PerfPoint[]; seconds: number; unit: "%" | "GB"; yMax?: number; colour?: string }) {
  const ticks = [-seconds, -Math.round(seconds / 2), 0];
  return (
    <div className="grid content-start gap-2">
      <h4 className="type-label">{title}</h4>
      {points.length < 2 ? (
        <p className="type-body-sm text-muted-foreground">Not enough readings yet.</p>
      ) : (
        <LineChart
          label={`${title} over the ${seconds === 3600 ? "last hour" : seconds === 86400 ? "last 24 hours" : "last week"}`}
          series={points}
          seriesLabel={title}
          formatX={(x) => ago(-x)}
          formatY={(y) => measure(y, unit)}
          xTicks={ticks}
          yMax={yMax}
          height={160}
          colour={colour}
        />
      )}
    </div>
  );
}

function Panel({ perf, seconds }: { perf: Perf; seconds: number }) {
  const narrow = useNarrow();
  if (!perf.available) {
    return <EmptyState title="No history yet">The sampler writes it every 10 seconds (perf-sample). It appears here after a minute.</EmptyState>;
  }
  const memMax = Math.ceil(perf.mem_total_gb / 4) * 4 || undefined;
  return (
    <div className="grid gap-6">
      <p className="type-body">{perf.verdict}</p>
      <div className="grid gap-x-8 gap-y-6 md:grid-cols-2">
        <Chart title="CPU busy" points={perf.series.cpu} seconds={seconds} unit="%" yMax={100} />
        <Chart title="Memory in use" points={perf.series.mem} seconds={seconds} unit="GB" yMax={memMax} colour="var(--chart-2)" />
        <Chart title="Busiest disk" points={perf.series.disk} seconds={seconds} unit="%" yMax={100} colour="var(--chart-3)" />
        <Chart title="GPU busy" points={perf.series.gpu} seconds={seconds} unit="%" yMax={100} colour="var(--chart-4)" />
      </div>
      <DataTable caption="Resources over the period" columns={fit(resourceColumns, narrow)} rows={perf.resources} rowKey={(r) => r.key} />
      {perf.pressure.length > 0 && (
        <div className="grid gap-2">
          <h3 className="type-label">What was running when it waited</h3>
          <ul className="grid gap-1 type-body-sm">{perf.pressure.map((p) => <Pressure key={p.resource} p={p} />)}</ul>
        </div>
      )}
      {perf.disk_paths.length > 0 && (
        <div className="grid gap-2">
          <h3 className="type-label">Spinning disks: what uses them</h3>
          <p className="type-body-sm text-muted-foreground">
            Steady use of a spinning disk is what to move to the SSD; bursts of big files are what these disks are for.
          </p>
          <DataTable caption="Spinning-disk use by service and folder" columns={fit(pathColumns, narrow)} rows={perf.disk_paths} rowKey={(d) => `${d.disk}|${who(d)}|${d.dir}`} />
        </div>
      )}
      {perf.services.length > 0 && (
        <DataTable caption="Services and jobs by use" columns={fit(serviceColumns, narrow)} rows={perf.services} rowKey={(s) => who(s)} initialSort={{ key: "cpu", dir: "descending" }} />
      )}
      <p className="type-body-sm text-muted-foreground">
        {`${duration(perf.covered_s)} of readings, every 10 seconds. Over its limit means CPU above 80 %, a disk above 80 % busy, programs waiting more than 10 % of the time, or swapping above 20 MB/s.`}
      </p>
    </div>
  );
}

function WindowPanel({ window, paused }: { window: PerfWindow; paused: boolean }) {
  const state = usePerf(window, paused);
  const seconds = WINDOWS.find((w) => w.value === window)!.seconds;
  return (
    <DataView state={state} isEmpty={() => false} skeleton={<Skeleton className="h-64 w-full" />} empty={null}>
      {(perf) => <Panel perf={perf} seconds={seconds} />}
    </DataView>
  );
}

/** Where the machine's time went: hour, day or week, picked by the `range` search parameter. */
export function OverTime({ paused }: { paused: boolean }) {
  return (
    <Tabs param="range" label="Time range" items={WINDOWS.map(({ value, label }) => ({ value, label }))}>
      {(v) => <WindowPanel window={v as PerfWindow} paused={paused} />}
    </Tabs>
  );
}
