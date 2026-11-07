"""Render the status page: server-side HTML, no JavaScript (a <meta refresh> keeps it current)."""
import html

CSS = """
:root{--bg:#f6f5f3;--card:#fff;--ink:#1c1b19;--mute:#6b6862;--line:#dcd9d3;--accent:#2f6f5e;--ok:#2f8f5e;--warn:#b7791f;--bad:#c0392b;color-scheme:light dark}
@media (prefers-color-scheme:dark){:root{--bg:#161614;--card:#201f1d;--ink:#eceae5;--mute:#9c9890;--line:#34322f;--accent:#6bb8a2;--ok:#5fc08a;--warn:#e0a84a;--bad:#e8685a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}
main{max-width:56rem;margin:0 auto;padding:2.5rem 16px 3rem}
h1{font-size:1.5rem;margin:0}h2{font-size:.8rem;text-transform:uppercase;letter-spacing:.06em;color:var(--mute);margin:2rem 0 .6rem}
.sub{color:var(--mute);margin:.15rem 0 0}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(15rem,1fr))}
.card{display:block;padding:14px 16px;background:var(--card);border:1px solid var(--line);border-radius:10px;color:inherit;text-decoration:none}
a.card:hover,a.card:focus-visible{border-color:var(--accent);outline:none}
.card strong{display:block;color:var(--accent)}.card span.d{display:block;color:var(--mute);font-size:.88rem}
.meta{display:flex;gap:.5rem;align-items:center;margin-top:.5rem;font-size:.82rem;color:var(--mute);flex-wrap:wrap}
.dot{width:.65rem;height:.65rem;border-radius:50%;display:inline-block;background:var(--mute)}
.dot.ok{background:var(--ok)}.dot.warn{background:var(--warn)}.dot.bad{background:var(--bad)}
.tag{border:1px solid var(--line);border-radius:999px;padding:0 .5rem}.tag.warn{border-color:var(--warn);color:var(--warn)}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:.92rem}
th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line)}tr:last-child td{border-bottom:0}th{color:var(--mute);font-weight:500}
.bar{height:.5rem;background:var(--line);border-radius:4px;overflow:hidden;min-width:6rem}.bar i{display:block;height:100%;background:var(--accent)}.bar i.hi{background:var(--warn)}.bar i.vhi{background:var(--bad)}
.alert{background:var(--card);border:1px solid var(--bad);color:var(--bad);border-radius:10px;padding:10px 14px;margin-top:1rem}
footer{margin-top:2.5rem;font-size:.85rem;color:var(--mute)}footer a{color:var(--mute)}
@media (max-width:30rem){th:nth-child(3),td:nth-child(3){display:none}}
"""


def e(x):
    return html.escape(str(x), quote=True)


def human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1024


def fmt_uptime(s):
    d, r = divmod(int(s), 86400)
    h, r = divmod(r, 3600)
    return (f"{d}d " if d else "") + f"{h}h {r // 60}m"


def short_time(ts):
    """'Sat 2026-11-07 04:25:28 GMT' -> '11-07 04:25' (systemd's text, kept readable)."""
    parts = ts.split()
    if len(parts) >= 3 and "-" in parts[1]:
        return parts[1][5:] + " " + parts[2][:5]
    return ts or "-"


def app_card(a):
    dot = {"active": "ok", "": "", "unknown": "warn"}.get(a.get("state", ""), "bad")
    meta = ""
    if a.get("unit"):
        meta += f'<span class="dot {dot}"></span><span>{e(a.get("state") or "unknown")}</span>'
    v = a.get("version")
    if v == "behind":
        meta += f'<span class="tag warn" title="restarted by app-refresh at night">code newer: {e(a["running_rev"])} → {e(a["head_rev"])}</span>'
    elif v == "current":
        meta += f'<span class="tag">{e(a["head_rev"])}</span>'
    return (f'<a class="card" href="{e(a["path"])}"><strong>{e(a["name"])}</strong>'
            f'<span class="d">{e(a.get("desc", ""))}</span><div class="meta">{meta}</div></a>')


def job_row(j):
    ok = j["result"] == "success"
    running = j["active"] in ("activating", "active")
    if running:
        dot, text = "warn", "running"
    elif ok:
        dot, text = "ok", "ok"
    else:
        dot, text = "bad", j["result"] or "never run"
    return (f'<tr><td>{e(j["label"])}</td><td><span class="dot {dot}"></span> {e(text)}</td>'
            f'<td>{e(short_time(j["last"]))}</td><td>{e(short_time(j["next"]))}</td></tr>')


def disk_row(d):
    cls = "vhi" if d["pct"] >= 90 else "hi" if d["pct"] >= 80 else ""
    return (f'<tr><td>{e(d["label"])}</td><td><div class="bar"><i class="{cls}" style="width:{d["pct"]}%"></i></div></td>'
            f'<td>{e(human(d["used"]))} of {e(human(d["total"]))}</td><td>{d["pct"]}%</td></tr>')


def page(data, hostname="omarchy", refresh=60):
    s = data.get("system", {})
    sub = []
    if "uptime_s" in s:
        sub.append("up " + fmt_uptime(s["uptime_s"]))
    if "mem_total_kb" in s:
        sub.append(f'{human((s["mem_total_kb"] - s["mem_avail_kb"]) * 1024)} of {human(s["mem_total_kb"] * 1024)} RAM in use')
    if s.get("load"):
        sub.append("load " + " ".join(f"{x:.1f}" for x in s["load"]))
    alerts = ""
    if data.get("failed"):
        alerts += f'<div class="alert">Failed units: {e(", ".join(data["failed"]))}</div>'
    behind = [a["name"] for a in data.get("apps", []) if a.get("version") == "behind"]
    apps = "".join(app_card(a) for a in data.get("apps", [])) or '<p class="sub">No apps yet. Add a snippet in <code>~/.config/caddy/sites/</code>.</p>'
    jobs = "".join(job_row(j) for j in data.get("jobs", []))
    disks = "".join(disk_row(d) for d in data.get("disks", []))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="{int(refresh)}"><title>{e(hostname)}</title><style>{CSS}</style></head>
<body><main>
<h1>{e(hostname)}</h1><p class="sub">{e(" · ".join(sub)) or "Apps on this machine"}</p>
{alerts}
<h2>Apps</h2><div class="grid">{apps}</div>
{"<h2>Jobs</h2><table><tr><th>Job</th><th>Last result</th><th>Last run</th><th>Next</th></tr>" + jobs + "</table>" if jobs else ""}
{"<h2>Storage</h2><table><tr><th>Disk</th><th></th><th>Used</th><th></th></tr>" + disks + "</table>" if disks else ""}
<footer>Updated {e(data.get("generated", "")[11:16])}
 · <a href="/_home/api/status">json</a> · <a href="/auth/logout">Sign out</a>{(" · " + str(len(behind)) + " app(s) behind their code") if behind else ""}</footer>
</main></body></html>"""
