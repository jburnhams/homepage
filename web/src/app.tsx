import * as React from "react";
import { Pause, Play } from "lucide-react";
import { Button, ColorSchemeChoice, DataTable, DataView, EmptyState, LineChart, Meter, Metric, MetricStrip, PageHeader, Skeleton, StaleNotice, Status, TableSkeleton, type Column } from "strata-react";
import { Apps } from "@/components/apps";
import { Memory } from "@/components/memory";
import { ago, format, kb, percent, systemdTime, uptime } from "@/lib/format";
import type { Disk, Job, Proc, Resources, Status as Data } from "./types";
import { useStatus } from "./use-status";

const POLL_MS = 5000;

const procColumns: Column<Proc>[] = [
  { key: "name", header: "Process", cell: (p) => p.name, truncate: true, sort: (a, b) => a.name.localeCompare(b.name) },
  { key: "cpu", header: "CPU", numeric: true, cell: (p) => percent(p.cpu), sort: (a, b) => a.cpu - b.cpu },
  { key: "rss", header: "Memory", numeric: true, cell: (p) => format.bytes(p.rss), sort: (a, b) => a.rss - b.rss },
];

const jobColumns: Column<Job>[] = [
  { key: "label", header: "Job", cell: (j) => j.label },
  {
    key: "result",
    header: "Last result",
    cell: (j) =>
      j.active === "activating" || j.active === "active" ? (
        <Status tone="info">Running</Status>
      ) : j.result === "success" ? (
        <Status tone="success">OK</Status>
      ) : (
        <Status tone="danger">{j.result || "Never run"}</Status>
      ),
  },
  { key: "last", header: "Last run", cell: (j) => systemdTime(j.last), className: "max-sm:hidden" },
  { key: "next", header: "Next", cell: (j) => systemdTime(j.next) },
];

// Disks are levels, not rows of a table: a Meter per disk, with the same two limits for all of them
// (shares of the disk's size) so a full disk names its state in words as well as colour.
const DISK_LIMITS = [
  { at: 0.8, tone: "warning" as const, label: "Filling up" },
  { at: 0.9, tone: "danger" as const, label: "Nearly full" },
];

function Disks({ disks }: { disks: Disk[] }) {
  return (
    <ul aria-label="Disk use" className="grid gap-x-8 gap-y-5 md:grid-cols-2">
      {disks.map((d) => (
        <li key={d.path} className="grid">
          <Meter
            label={d.label}
            value={d.used}
            max={d.total}
            valueText={`${percent(d.pct)} used`}
            detail={`${format.bytes(d.used)} of ${format.bytes(d.total)}`}
            thresholds={DISK_LIMITS}
          />
        </li>
      ))}
    </ul>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-3">
      <h2 className="type-heading">{title}</h2>
      {children}
    </section>
  );
}

/** Newest on the right; x is seconds before the latest sample. */
function history(values: number[], interval: number) {
  const n = values.length;
  const series = values.map((y, i) => ({ x: -(n - 1 - i) * interval, y }));
  const first = series[0]?.x ?? 0;
  return { series, ticks: [first, Math.round(first / 2), 0] };
}

function Charts({ r }: { r: Resources }) {
  const cpu = history(r.cpu, r.interval);
  const mem = history(r.mem, r.interval);
  const collecting = <p className="type-body-sm text-muted-foreground">Collecting the first readings…</p>;
  return (
    <div className="grid gap-x-8 gap-y-6 md:grid-cols-2">
      <div className="grid content-start gap-2">
        <h3 className="type-label">CPU</h3>
        {cpu.series.length < 2 ? collecting : (
          <LineChart
            label={`CPU use over the last ${ago(-cpu.series[0].x)}`}
            series={cpu.series}
            seriesLabel="CPU, all cores"
            formatX={(x) => ago(-x)}
            formatY={percent}
            xTicks={cpu.ticks}
            height={200}
          />
        )}
      </div>
      <div className="grid content-start gap-4">
        <div className="grid gap-2">
          <h3 className="type-label">Memory used by programs</h3>
          {mem.series.length < 2 ? collecting : (
            <LineChart
              label={`Memory used by programs over the last ${ago(-mem.series[0].x)}`}
              series={mem.series}
              seriesLabel="Used, without cache"
              formatX={(x) => ago(-x)}
              formatY={percent}
              xTicks={mem.ticks}
              height={200}
              colour="var(--chart-2)"
            />
          )}
        </div>
        <Memory r={r} />
      </div>
    </div>
  );
}

function Page({ data, paused, onPause }: { data: Data; paused: boolean; onPause: () => void }) {
  const r = data.resources;
  const load = data.system.load;
  const cpu = r?.cpu.at(-1);
  const memPct = r?.mem.at(-1);
  return (
    <div className="grid gap-8">
      <PageHeader
        title={data.hostname}
        scope={[data.system.uptime_s !== undefined && `Up ${uptime(data.system.uptime_s)}`, `updated ${format.clock(new Date(data.generated))}`]
          .filter(Boolean)
          .join(" · ")}
        actions={
          <>
            <ColorSchemeChoice compact />
            <Button size="sm" onClick={onPause} aria-pressed={paused}>
              {paused ? <Play aria-hidden /> : <Pause aria-hidden />}
              {paused ? "Resume updates" : "Pause updates"}
            </Button>
          </>
        }
        finding={{ text: data.finding ?? "All good: every app is up, nothing has failed, disks have room." }}
      />

      {r && (
        <Section title="Resources">
          <MetricStrip label="Right now">
            <Metric label="CPU" value={cpu === undefined ? "–" : percent(cpu)} note={`${r.ncpu} core${r.ncpu === 1 ? "" : "s"}`} />
            <Metric
              label="Memory used"
              value={kb(r.mem_used_kb)}
              note={`${memPct === undefined ? "" : percent(memPct) + " of "}${kb(r.mem_total_kb)}; ${kb(r.mem_cached_kb + r.mem_buffers_kb)} cache`}
            />
            {load && <Metric label="Load, 1 min" value={load[0].toFixed(2)} note={`${load[1].toFixed(2)} over 5 min, ${load[2].toFixed(2)} over 15`} />}
          </MetricStrip>
          <Charts r={r} />
        </Section>
      )}

      {r && r.top_cpu.length > 0 && (
        <Section title="Top processes">
          <div className="grid gap-x-8 gap-y-6 md:grid-cols-2">
            <DataTable caption="Top processes by CPU" columns={procColumns} rows={r.top_cpu} rowKey={(p) => String(p.pid)} initialSort={{ key: "cpu", dir: "descending" }} />
            <DataTable caption="Top processes by memory" columns={procColumns} rows={r.top_mem} rowKey={(p) => String(p.pid)} initialSort={{ key: "rss", dir: "descending" }} />
          </div>
        </Section>
      )}

      <Section title="Apps">
        {data.apps.length ? (
          <Apps apps={data.apps} />
        ) : (
          <EmptyState title="No apps yet">Add a snippet to ~/.config/caddy/sites/ and it appears here.</EmptyState>
        )}
      </Section>

      {data.jobs.length > 0 && (
        <Section title="Jobs">
          <DataTable caption="Scheduled jobs" columns={jobColumns} rows={data.jobs} rowKey={(j) => j.unit} />
        </Section>
      )}
      {data.disks.length > 0 && (
        <Section title="Storage">
          <Disks disks={data.disks} />
        </Section>
      )}

      <footer className="flex flex-wrap gap-x-4 gap-y-1 border-t border-border pt-4 type-body-sm text-muted-foreground">
        <a href="/_home/api/status" className="underline">JSON</a>
        <a href="/_home/plain" className="underline">Plain page</a>
        <a href="/auth/logout" className="underline">Sign out</a>
      </footer>
    </div>
  );
}

function PageSkeleton() {
  return (
    <div className="grid gap-8" aria-label="Loading">
      <div className="grid gap-2"><Skeleton className="h-8 w-48" /><Skeleton className="h-5 w-64" /></div>
      <Skeleton className="h-48 w-full" />
      <TableSkeleton rows={4} columns={3} />
    </div>
  );
}

export function App() {
  const [paused, setPaused] = React.useState(false);
  const state = useStatus(POLL_MS, paused);
  React.useEffect(() => {
    if (state.status === "ready") document.title = state.data.hostname;
  }, [state]);
  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      <DataView
        state={state}
        isEmpty={() => false}
        skeleton={<PageSkeleton />}
        empty={null}
        staleNotice={(stale) => <StaleNotice stale={stale} shown={(when) => `Showing the last readings, from ${when}.`} />}
      >
        {(data) => <Page data={data} paused={paused} onPause={() => setPaused((p) => !p)} />}
      </DataView>
    </main>
  );
}
