import * as React from "react";
import type { Status } from "./types";
import type { Load } from "@/components/ui/data-view";

// Polls the JSON the server already serves. The server samples /proc on its own clock, so polling
// faster than its interval only repeats numbers; 5 s matches it. Polling stops while the tab is
// hidden or the person has paused it, and resumes with an immediate fetch.
const API = "/_home/api/status";

export function useStatus(intervalMs: number, paused: boolean) {
  const [state, setState] = React.useState<Load<Status>>({ status: "loading" });
  const [stale, setStale] = React.useState<string | null>(null);
  const [tick, setTick] = React.useState(0);
  const retry = React.useCallback(() => setTick((t) => t + 1), []);

  React.useEffect(() => {
    let stop = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const load = async () => {
      try {
        const r = await fetch(API, { cache: "no-store" });
        if (!r.ok) throw new Error(`The server answered ${r.status}.`);
        const data = (await r.json()) as Status;
        if (!stop) {
          setState({ status: "ready", data });
          setStale(null);
        }
      } catch (ex) {
        const message = `Could not load the status: ${ex instanceof Error ? ex.message : "no answer"} Check that the homepage service is running.`;
        if (!stop) {
          // Keep showing the last good data and say it is old; only the first load is a hard error.
          setState((s) => (s.status === "ready" ? s : { status: "error", message, retry }));
          setStale(message);
        }
      }
      if (!stop && !paused && !document.hidden) timer = setTimeout(load, intervalMs);
    };
    const onVisible = () => {
      if (!document.hidden && !paused) {
        clearTimeout(timer);
        void load();
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    void load();
    return () => {
      stop = true;
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [intervalMs, paused, tick, retry]);

  return { state, stale };
}
