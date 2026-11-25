import { LinkCard, LinkCardList, Status } from "strata-react";
import type { App } from "@/src/types";

// The apps on the machine, as strata-react's LinkCard: each is a separate destination, so a card is
// warranted. The card is one link named by the app; its description and status words are read as
// the link's description, so a screen reader is not read every word as the name. Every status
// carries a word, so colour is never the only cue.
export function Apps({ apps }: { apps: App[] }) {
  return (
    <LinkCardList label="Apps">
      {apps.map((app) => {
        const running = app.state === "active";
        return (
          <LinkCard
            key={app.path}
            href={app.path}
            title={app.name}
            description={app.desc || undefined}
            marks={
              <>
                {app.unit && (
                  <Status tone={running ? "success" : app.state === "unknown" || !app.state ? "warning" : "danger"}>
                    {running ? "Running" : app.state || "Unknown"}
                  </Status>
                )}
                {app.version === "behind" && <Status tone="warning">{`Code newer: ${app.running_rev} → ${app.head_rev}`}</Status>}
                {app.version === "current" && <Status tone="neutral">{app.head_rev ?? "current"}</Status>}
              </>
            }
          />
        );
      })}
    </LinkCardList>
  );
}
