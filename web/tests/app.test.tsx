import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { renderWithStrata } from "strata-react/testing";
import { App } from "@/src/app";
import { server, status, statusUrl } from "./server";

describe("the home server page", () => {
  it("shows the host, its default finding and every section", async () => {
    renderWithStrata(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: "omarchy" })).toBeInTheDocument();
    expect(screen.getByText(/All good: every app is up/)).toBeInTheDocument();
    for (const name of ["Resources", "Top processes", "Apps", "Jobs", "Storage"]) {
      expect(screen.getByRole("heading", { name })).toBeInTheDocument();
    }
    expect(screen.getByRole("table", { name: "Top processes by CPU" })).toHaveTextContent("firefox");
    expect(screen.getByRole("table", { name: "Top processes by memory" })).toHaveTextContent("postgres");
    expect(screen.getByRole("table", { name: "Scheduled jobs" })).toHaveTextContent("OK");
  });

  it("shows the server's finding when there is one", async () => {
    server.use(http.get(statusUrl, () => HttpResponse.json({ ...status, finding: "Disk Root is 93 % full." })));
    renderWithStrata(<App />);
    expect(await screen.findByText("Disk Root is 93 % full.")).toBeInTheDocument();
  });

  it("gives each app a link with a word for its state and version", async () => {
    renderWithStrata(<App />);
    const notes = await screen.findByRole("link", { name: /Notes/ });
    expect(notes).toHaveAttribute("href", "/notes/");
    expect(notes).toHaveTextContent("Running");
    expect(notes).toHaveTextContent("Code newer: a1b2c3d → e4f5a6b");
    expect(screen.getByRole("link", { name: /Files/ })).toHaveTextContent("failed");
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
    expect(await screen.findByRole("heading", { level: 1, name: "omarchy" })).toBeInTheDocument();
  });

  it("keeps the last readings and says they are old when a refresh fails", async () => {
    let fail = false;
    server.use(http.get(statusUrl, () => (fail ? new HttpResponse(null, { status: 500 }) : HttpResponse.json(status))));
    const { client } = renderWithStrata(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: "omarchy" })).toBeInTheDocument();
    fail = true;
    await client.refetchQueries({ queryKey: ["status"] });
    expect(await screen.findByText(/Showing the last readings/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "omarchy" })).toBeInTheDocument();
  });

  it("pauses and resumes updates", async () => {
    renderWithStrata(<App />);
    const pause = await screen.findByRole("button", { name: "Pause updates" });
    await userEvent.click(pause);
    expect(screen.getByRole("button", { name: "Resume updates" })).toHaveAttribute("aria-pressed", "true");
    await waitFor(() => expect(screen.getByRole("button", { name: "Resume updates" })).toBeEnabled());
  });
});
