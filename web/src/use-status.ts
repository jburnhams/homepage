import { useQuery } from "@tanstack/react-query";
import { fetchJson, toLoad, type Load } from "strata-react";
import type { Status } from "./types";

// Polls the JSON the server already serves, through Strata's query bridge. The server samples /proc
// on its own clock, so polling faster than its interval only repeats numbers; 5 s matches it.
// TanStack Query stops polling while the tab is hidden (refetchIntervalInBackground is off) and
// refetches when it shows again; pausing turns the interval off. If a refresh fails after a good
// read, the last data stays on screen and `stale` says it is old; only the first load is a hard error.
const API = "/_home/api/status";

export function useStatus(intervalMs: number, paused: boolean): { state: Load<Status>; stale: string | null } {
  const query = useQuery({
    queryKey: ["status"],
    queryFn: () => fetchJson<Status>(API, { cache: "no-store" }),
    refetchInterval: paused ? false : intervalMs,
    staleTime: intervalMs,
    refetchOnWindowFocus: true,
  });
  const describe = (e: unknown) => `Could not load the status: ${e instanceof Error ? e.message : "no answer"} Check that the homepage service is running.`;
  const stale = query.isError ? describe(query.error) : null;
  // toLoad maps any query error to an error state, even when a good read is still cached, which would
  // replace the whole page. Keep showing the last data and let `stale` say it is old.
  const state: Load<Status> = query.data ? { status: "ready", data: query.data } : toLoad(query, describe);
  return { state, stale };
}
