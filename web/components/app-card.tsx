import { Status } from "strata-react";
import type { App } from "@/src/types";

// One app on the machine: a link, its one-line description, whether its service is up and whether it
// runs the code that is checked out. A card is warranted here because each one is a separate
// destination; every status carries a word.
export function AppCard({ app }: { app: App }) {
  const running = app.state === "active";
  return (
    <a
      href={app.path}
      className="grid content-start gap-1 rounded-surface border border-border bg-card p-4 text-card-foreground transition-state hover:border-primary"
    >
      <strong className="type-heading text-primary-11">{app.name}</strong>
      {app.desc && <span className="type-body-sm text-muted-foreground">{app.desc}</span>}
      <span className="mt-2 flex flex-wrap items-center gap-2">
        {app.unit && (
          <Status tone={running ? "success" : app.state === "unknown" || !app.state ? "warning" : "danger"}>
            {running ? "Running" : app.state || "Unknown"}
          </Status>
        )}
        {app.version === "behind" && (
          <Status tone="warning">{`Code newer: ${app.running_rev} → ${app.head_rev}`}</Status>
        )}
        {app.version === "current" && <Status tone="neutral">{app.head_rev ?? "current"}</Status>}
      </span>
    </a>
  );
}
