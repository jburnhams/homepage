import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { cleanup } from "@testing-library/react";
import { installLayoutShims } from "strata-react/testing";
import { server } from "./server";

// jsdom does no layout; the library's measuring components need these shims. Real layout is not
// checked here.
installLayoutShims();

beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => {
  cleanup();
  server.resetHandlers();
});
afterAll(() => server.close());
