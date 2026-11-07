// Builds dist/ (index.html, app.js, app.css). dist/ is committed so the home server needs no Node.
import { build } from "esbuild";
import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const out = join(root, "dist");
mkdirSync(out, { recursive: true });

execFileSync("npx", ["tailwindcss", "-i", "app/globals.css", "-o", "dist/app.css", "--minify"], { cwd: root, stdio: "inherit" });
await build({
  entryPoints: [join(root, "src/main.tsx")],
  bundle: true,
  minify: true,
  outfile: join(out, "app.js"),
  format: "iife",
  jsx: "automatic",
  alias: { "@": root },
  define: { "process.env.NODE_ENV": '"production"' },
  logLevel: "warning",
});
// Absolute /_home/ URLs: Caddy forwards /_home/* to this app, and the server strips the prefix.
writeFileSync(
  join(out, "index.html"),
  `<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light dark"><title>Home server</title><link rel="stylesheet" href="/_home/app.css"></head><body><div id="root"></div><script src="/_home/app.js"></script></body></html>\n`,
);
