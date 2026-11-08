// Visual regression for the status page: its one route in each server state, light and dark,
// wide and phone, served from the committed production build (dist/). The handlers are the same
// ones the unit tests use (tests/mocks.ts); the page is not told it is being tested.
import { defineVisualConfig } from "strata-react/visual";
import { failedUnits, handlers, noApps, statusError, statusLoading } from "./tests/mocks";

export default defineVisualConfig({
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
