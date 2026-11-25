import { fetchJson, useLoad, type Load, type Poll } from "strata-react";
import type { Perf, PerfWindow } from "./types";

// The server reads the sampler's files and caches each window for 30 s (hour), 2 min (day) or 10 min
// (week), so asking more often than once a minute only repeats numbers. Same rule as use-status.ts:
// `useLoad` keeps the last numbers on screen under a StaleNotice when a refresh fails.
const API = "/_home/api/perf";

export function usePerf(window: PerfWindow, page: Poll): Load<Perf> {
  return useLoad({
    queryKey: ["perf", window],
    queryFn: () => fetchJson<Perf>(`${API}?window=${window}`, { cache: "no-store" }),
    poll: { ...page, every: 60_000 }, // the page's pause, at this read's own pace
    staleTime: 30_000,
    refetchOnWindowFocus: true,
    describeError: (e) => `Could not load the history: ${e instanceof Error ? e.message : "no answer"}`,
  });
}
