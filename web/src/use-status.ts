import { fetchJson, useLoad, type Load, type Poll } from "strata-react";
import type { Status } from "./types";

// Polls the JSON the server already serves, through strata-react's `useLoad` (TanStack Query behind
// it). The server samples /proc on its own clock, so polling faster than its interval only repeats
// numbers; 5 s matches it. Polling stops while the tab is hidden and refetches when it shows again;
// `poll` (from `usePoll`, shared with the pause button) turns the interval off while paused and notes when each read arrived. When a refresh fails after a good read, `useLoad` keeps the data
// and sets `stale`, which DataView draws as a StaleNotice (why, how old, Try again); only the
// first load is a hard error.
const API = "/_home/api/status";

export function useStatus(poll: Poll): Load<Status> {
  return useLoad({
    queryKey: ["status"],
    queryFn: () => fetchJson<Status>(API, { cache: "no-store" }),
    poll,
    staleTime: poll.every,
    refetchOnWindowFocus: true,
    describeError: (e) => `Could not load the status: ${e instanceof Error ? e.message : "no answer"} Check that the homepage service is running.`,
  });
}
