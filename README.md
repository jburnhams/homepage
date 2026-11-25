# homepage

The landing page and status board of a small home server: one page at `/` that lists the web apps behind the Caddy proxy and shows whether they are up, whether they run their latest code, how the nightly jobs went, and how full the disks are. Also holds `webauth`, the single login in front of every app.

The server is a FastAPI app on [strata-python](https://github.com/jburnhams/strata-python) (Python 3.11+, run with uv). The page is a React + Tailwind front end (`web/`) built on [strata-react](https://github.com/jburnhams/strata-react) that polls the JSON every 5 s and draws live charts; its built output `web/dist/` is committed, so the machine needs no Node. `/plain` is the old server-rendered page with no JavaScript (a 10 s `<meta refresh>`), also the fallback if `web/dist` is missing. Runs as a systemd user service on `127.0.0.1:8365`. Caddy puts the login in front of it.

```
browser -> Caddy :80 -> forward_auth -> webauth :8361   (login, signed cookie)
                      -> /            -> homepage :8365  (this app)
                      -> /<app>/      -> the apps
```

## Apps come from Caddy snippets
Each app has one `~/.config/caddy/sites/<app>.caddy`. Its first lines describe it:
```
# app: Name | /path/ | one-line description      required: a card on the page
# unit: systemd-user-unit                          optional: green/red dot (is-active)
# repo: directory under the `repos` setting          optional: running commit vs checked-out commit
```
The "running commit" is what `app-refresh` records in `~/.local/state/app-refresh/<unit>.rev` at every service start; a card shows `code newer: a -> b` when the checked-out code is ahead of what runs (the nightly refresh restarts it).

## What the page shows
- apps: state and version per snippet
- jobs: last result, last run and next run of the systemd user units named in the `jobs` setting (none by default; units that do not exist are skipped)
- resources: CPU, and memory split into used / cached / buffers / free / swap, each with a rolling 15 min graph (sampled every 5 s from `/proc` by a background thread in `resources.py`, history is in memory and starts empty after a restart), top 6 processes by CPU and by memory (CPU 100% = one core)
- failed user units (red box), uptime, memory, load, and the disks in the `disks` setting (the root disk by default; any other path only while it is a mount point)
- `/_home/api/status`: the same data as JSON; `/healthz`; and strata-python's shared `/_home/api/health`, `/_home/api/system` and `/_home/api/settings`

## Front end
```
cd web && npm install
npm run check     # typecheck + build into web/dist (commit it)
npm test          # Vitest + Testing Library + MSW
UX_RESEARCH=<checkout of jburnhams/ux-research> npm run lint   # slop-lint, operate mode
```
Design decisions and their reasons: `web/DESIGN.md`.

## Run and test
```
bin/homepage serve [--port 8365]       # the server (uv run --locked homepage; the first run builds .venv)
bin/homepage print                     # the plain page on stdout
bin/homepage doctor                    # imports and the programs it needs (systemctl, git)
bin/homepage set sites ~/x             # settings: sites, state, repos, jobs, disks, perf (also HOMEPAGE_SITES etc.)
scripts/check                          # the gate: ruff, pyright strict, ty, tests with coverage
```
Systemd data is read with `systemctl --user ...` (a fixed command list, nothing from the request reaches a shell), cached for 10 s however many people look.

## webauth
`bin/webauth` is the login (one password, scrypt hash, signed 365-day cookie, lockout after 5 wrong tries). Run it from a checkout (a small launcher script in your own config is enough). Existing sessions survive moves because the signing secret stays in `~/.config/webauth/auth.json`, outside this repo. That file may also set `name` (the heading on the login page; default `webauth`) and `cookie` (the cookie's name; default `webauth_auth`, and changing it signs everyone out once): see `examples/auth.json`. `webauth set-password`, `webauth sign-out-everywhere`.

## Deploying on a machine
The units, the Caddyfile and the snippets are machine config and belong in your own config repo, not here. `homepage.service` runs `bin/homepage serve` from a checkout of this repo; `app-refresh` restarts it when the checkout changes. The `caddy/Caddyfile` here is the reference for the proxy config (login check first, then the apps, then `/` and `/_home/*` to this app).
