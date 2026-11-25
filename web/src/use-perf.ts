import { useQuery } from "@tanstack/react-query";
import { fetchJson, toLoad, type Load } from "strata-react";
import type { Perf, PerfWindow } from "./types";

// The server reads the sampler's files and caches each window for 30 s (hour), 2 min (day) or 10 min
// (week), so asking more often than once a minute only repeats numbers. Same stale-data rule as
// use-status.ts: after one good read a failed refresh keeps the last numbers on screen.
const API = "/_home/api/perf";

export function usePerf(window: PerfWindow, paused: boolean): { state: Load<Perf>; stale: string | null } {
  const query = useQuery({
    queryKey: ["perf", window],
    queryFn: () => fetchJson<Perf>(`${API}?window=${window}`, { cache: "no-store" }),
    refetchInterval: paused ? false : 60_000,
    staleTime: 30_000,
    refetchOnWindowFocus: true,
  });
  const describe = (e: unknown) => `Could not load the history: ${e instanceof Error ? e.message : "no answer"}`;
  const stale = query.isError ? describe(query.error) : null;
  const state: Load<Perf> = query.data ? { status: "ready", data: query.data } : toLoad(query, describe);
  return { state, stale };
}
