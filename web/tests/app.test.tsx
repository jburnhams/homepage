import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { renderWithStrata } from "strata-react/testing";
import { App } from "@/src/app";
import { perf, perfUrl, server, status, statusUrl } from "./server";

describe("the home server page", () => {
  it("shows the host, its default finding and every section", async () => {
    renderWithStrata(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: "myhost" })).toBeInTheDocument();
    expect(screen.getByText(/All good: every app is up/)).toBeInTheDocument();
    for (const name of ["Resources", "Over time", "Top processes", "Apps", "Jobs", "Storage"]) {
      expect(screen.getByRole("heading", { name })).toBeInTheDocument();
    }
    expect(screen.getByRole("grid", { name: "Top processes by CPU" })).toHaveTextContent("firefox");
    expect(screen.getByRole("grid", { name: "Top processes by memory" })).toHaveTextContent("postgres");
    expect(screen.getByRole("grid", { name: "Scheduled jobs" })).toHaveTextContent("OK");
  });

  it("shows the server's finding when there is one", async () => {
    server.use(http.get(statusUrl, () => HttpResponse.json({ ...status, finding: "Disk Root is 93 % full." })));
    renderWithStrata(<App />);
    expect(await screen.findByText("Disk Root is 93 % full.")).toBeInTheDocument();
  });

  it("gives each app a link with a word for its state and version", async () => {
    renderWithStrata(<App />);
    const notes = await screen.findByRole("link", { name: "Notes" });
    expect(notes).toHaveAttribute("href", "/notes/");
    expect(notes).toHaveAccessibleDescription(/Running/);
    expect(notes).toHaveAccessibleDescription(/Code newer: a1b2c3d → e4f5a6b/);
    expect(screen.getByRole("link", { name: "Files" })).toHaveAccessibleDescription(/failed/);
  });

  it("teaches the next step when there are no apps", async () => {
    server.use(http.get(statusUrl, () => HttpResponse.json({ ...status, apps: [] })));
    renderWithStrata(<App />);
    expect(await screen.findByText("No apps yet")).toBeInTheDocument();
  });

  it("says what failed, with Try again, when the first load fails", async () => {
    server.use(http.get(statusUrl, () => new HttpResponse(null, { status: 500 })));
    renderWithStrata(<App />);
    expect(await screen.findByText(/Could not load the status/, undefined, { timeout: 5000 })).toBeInTheDocument();
    server.use(http.get(statusUrl, () => HttpResponse.json(status)));
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(await screen.findByRole("heading", { level: 1, name: "myhost" })).toBeInTheDocument();
  });

  it("keeps the last readings and says they are old when a refresh fails", async () => {
    let fail = false;
    server.use(http.get(statusUrl, () => (fail ? new HttpResponse(null, { status: 500 }) : HttpResponse.json(status))));
    const { client } = renderWithStrata(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: "myhost" })).toBeInTheDocument();
    fail = true;
    await client.refetchQueries({ queryKey: ["status"] });
    const notice = await screen.findByRole("status");
    expect(notice).toHaveTextContent(/Could not load the status/);
    expect(notice).toHaveTextContent(/Showing the last readings, from/);
    expect(screen.getByRole("heading", { level: 1, name: "myhost" })).toBeInTheDocument();
    fail = false;
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
  });

  it("draws each disk as a meter in words, and names a disk that is filling up", async () => {
    server.use(
      http.get(statusUrl, () =>
        HttpResponse.json({ ...status, disks: [{ label: "Root", path: "/", total: 100e9, used: 93e9, pct: 93 }] }),
      ),
    );
    renderWithStrata(<App />);
    const root = await screen.findByRole("meter", { name: "Root" });
    expect(root).toHaveAttribute("aria-valuetext", expect.stringMatching(/93\s?% used/));
    expect(screen.getByText("Nearly full")).toBeInTheDocument();
  });

  it("breaks the memory down by use, with swap as its own meter", async () => {
    renderWithStrata(<App />);
    const memory = await screen.findByRole("table", { name: "Memory by use" });
    for (const part of ["Used by programs", "Cached", "Buffers", "Free"]) expect(memory).toHaveTextContent(part);
  });

  it("pauses and resumes updates", async () => {
    renderWithStrata(<App />);
    const pause = await screen.findByRole("button", { name: "Pause updates" });
    await userEvent.click(pause);
    expect(screen.getByRole("button", { name: "Resume updates" })).toHaveAttribute("aria-pressed", "true");
    await waitFor(() => expect(screen.getByRole("button", { name: "Resume updates" })).toBeEnabled());
  });
});

describe("the over-time section", () => {
  it("opens on the last hour with the server's verdict, a word for each limit and who was busy", async () => {
    renderWithStrata(<App />);
    expect(await screen.findByText(/Programs waiting for memory was the tightest in the last hour/)).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Last hour", selected: true })).toBeInTheDocument();
    const table = screen.getByRole("grid", { name: "Resources over the period" });
    expect(table).toHaveTextContent("Often 12%");      // 12% of the time over its limit is named, not just coloured
    expect(table).toHaveTextContent("Fine");
    expect(screen.getByText(/Programs waited for memory for 7 min/)).toHaveTextContent("render-worker 80%");
    expect(screen.getByText(/Programs waited for memory for 7 min/)).toHaveTextContent("Busiest then");
    // a disk wait names the busy disk and who moved data on it, with the folder, never someone who only used a fast disk
    const disk = screen.getByText(/Programs waited for disk for 12 min/);
    expect(disk).toHaveTextContent("sdb (spinning) 85%");
    expect(disk).toHaveTextContent("media-sync in /data/archive/raw 40%");
    expect(disk).toHaveTextContent("file-share 60%");
    expect(disk).toHaveTextContent("Most data moved on those disks");
    const spin = screen.getByRole("grid", { name: "Spinning-disk use by service and folder" });
    expect(spin).toHaveTextContent("Steady, move?"); // 9 hours of use on a spinning disk: a candidate for the SSD
    expect(spin).toHaveTextContent("Bursts"); // one hour of big reads: what the disk is for
    expect(screen.getByRole("grid", { name: "Services and jobs by use" })).toHaveTextContent("nightly-import [photos]");
  });

  it("asks the server for the day when that tab is chosen", async () => {
    const asked: string[] = [];
    server.use(http.get(perfUrl, ({ request }) => {
      const w = new URL(request.url).searchParams.get("window") as "1h" | "24h" | "7d";
      asked.push(w);
      return HttpResponse.json(perf(w));
    }));
    renderWithStrata(<App />);
    await screen.findByText(/tightest in the last hour/);
    await userEvent.click(screen.getByRole("tab", { name: "24 hours" }));
    await waitFor(() => expect(asked).toContain("24h"));
    expect(screen.getByRole("tab", { name: "24 hours", selected: true })).toBeInTheDocument();
  });

  it("says so when there is no history yet, and keeps the rest of the page", async () => {
    server.use(http.get(perfUrl, () => HttpResponse.json({ available: false, window: "1h", label: "last hour" })));
    renderWithStrata(<App />);
    expect(await screen.findByText("No history yet")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Apps" })).toBeInTheDocument();
  });
});
