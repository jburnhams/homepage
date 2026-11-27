import { fetchJson, useLoad, type Load, type Poll, type SystemInfoLike } from "strata-react";

// strata-python's `GET /api/system`, read at the page's own prefix. Not `useSystemInfo`: that puts the
// page's <base> in front of the path, and this page is served at `/` and at `/_home/` (Caddy forwards both),
// so the base `add_web` injects is not always the prefix the API is mounted at; the status read does the same.
export function useSystem(poll: Poll): Load<SystemInfoLike> {
  return useLoad({
    queryKey: ["system"],
    queryFn: () => fetchJson<SystemInfoLike>("/_home/api/system", { cache: "no-store" }),
    poll,
    describeError: (e) => `Could not load the server report: ${e instanceof Error ? e.message : "no answer"}`,
  });
}
