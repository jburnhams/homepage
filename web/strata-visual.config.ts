// Visual regression for the status page: its one route in each server state, light and dark,
// wide and phone, served from the committed production build (dist/). The handlers are the same
// ones the unit tests use (tests/mocks.ts); the page is not told it is being tested.
import { defineVisualConfig } from "strata-react/visual";
import { failedUnits, handlers, noApps, statusError, statusLoading } from "./tests/mocks";

export default defineVisualConfig({
  // The page deliberately draws in the system UI font (DESIGN.md: it is served from a home server and
  // should not wait on a font download), which strata-visual's default refuses because it differs by
  // machine. The pin gives Chromium a fontconfig whose only font is the file below and answers every
  // system family with it, so the baselines are the same on every Linux machine and CI's.
  systemFonts: { pin: "DejaVu Sans", files: ["tests/visual/fonts/DejaVuSans.ttf"] },
  app: {
    dir: "dist",
    base: "/_home/",
    handlers,
    viewports: ["wide", "phone"],
    routes: [
      {
        name: "status",
        path: "/",
        states: {
          ready: [],
          loading: [statusLoading],
          // The query client retries once, so the message comes a second after the first 500.
          error: { handlers: [statusError], waitFor: "text=Could not load the status" },
          "no-apps": [noApps],
          "failed-units": [failedUnits],
        },
      },
    ],
  },
});
