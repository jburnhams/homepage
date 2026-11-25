"""Render the status page: server-side HTML, no JavaScript (a <meta refresh> keeps it current)."""

import html
from collections.abc import Mapping, Sequence
from typing import Any

Data = Mapping[str, Any]

CSS = """
:root{--bg:#f6f5f3;--card:#fff;--ink:#1c1b19;--mute:#6b6862;--line:#dcd9d3;--accent:#2f6f5e;--ok:#2f8f5e;--warn:#b7791f;--bad:#c0392b;color-scheme:light dark}
@media (prefers-color-scheme:dark){:root{--bg:#161614;--card:#201f1d;--ink:#eceae5;--mute:#9c9890;--line:#34322f;--accent:#6bb8a2;--ok:#5fc08a;--warn:#e0a84a;--bad:#f0606a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}
main{max-width:56rem;margin:0 auto;padding:2.5rem 16px 3rem}
h1{font-size:1.5rem;font-weight:600;margin:0}h2{font-size:.875rem;font-weight:600;color:var(--mute);margin:2rem 0 .6rem}
td,.big,.axis,.sub{font-variant-numeric:tabular-nums}
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
.graphs{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(18rem,1fr))}
.gcard{padding:14px 16px;background:var(--card);border:1px solid var(--line);border-radius:10px}
.gcard h3{margin:0;font-size:.85rem;font-weight:500;color:var(--mute)}.gcard .big{font-size:1.6rem;font-weight:600;line-height:1.3}
.gcard .big small{font-size:.85rem;font-weight:400;color:var(--mute)}
svg.spark{display:block;width:100%;height:4.5rem;margin-top:.4rem;background:linear-gradient(var(--line) 1px,transparent 1px) 0 0/100% 25%;border-bottom:1px solid var(--line)}
svg.spark .area{fill:var(--accent);opacity:.18}svg.spark.plain .area{display:none}svg.spark .line{fill:none;stroke:var(--accent);stroke-width:2;vector-effect:non-scaling-stroke;stroke-linejoin:round}
svg.spark.hi .area{fill:var(--warn)}svg.spark.hi .line{stroke:var(--warn)}svg.spark.vhi .area{fill:var(--bad)}svg.spark.vhi .line{stroke:var(--bad)}
svg.spark .cache{fill:var(--accent);opacity:.08}
.stack{display:flex;height:.7rem;border-radius:4px;overflow:hidden;background:var(--line);margin:.6rem 0 .2rem}.stack i{display:block;height:100%}
.sw{display:inline-block;width:.6rem;height:.6rem;border-radius:2px;margin-right:.45rem}
.m-used{background:var(--accent)}.m-cached{background:color-mix(in srgb,var(--accent) 45%,transparent)}.m-buffers{background:var(--warn)}.m-free{background:transparent}.m-swap{background:var(--bad)}
.stack .m-free{background:transparent}table.mem{border:0;border-radius:0;background:none;font-size:.85rem}table.mem td{padding:3px 0}table.mem .d{color:var(--mute);font-size:.78rem}
.axis{display:flex;justify-content:space-between;font-size:.75rem;color:var(--mute)}
th.num,td.num{text-align:right;white-space:nowrap}td.name{max-width:10rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
@media (max-width:30rem){.jobs th:nth-child(3),.jobs td:nth-child(3){display:none}}
"""


def e(x: object) -> str:
    return html.escape(str(x), quote=True)


def human(n: float) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024
        i += 1
    return f"{n:.0f} {units[i]}" if i < 2 else f"{n:.1f} {units[i]}"


def fmt_uptime(s: float) -> str:
    d, r = divmod(int(s), 86400)
    h, r = divmod(r, 3600)
    return (f"{d}d " if d else "") + f"{h}h {r // 60}m"


def short_time(ts: str) -> str:
    """'Sat 2026-11-07 04:25:28 GMT' -> '11-07 04:25' (systemd's text, kept readable)."""
    parts = ts.split()
    if len(parts) >= 3 and "-" in parts[1]:
        return parts[1][5:] + " " + parts[2][:5]
    return ts or "-"


def app_card(a: Data) -> str:
    dot = {"active": "ok", "": "", "unknown": "warn"}.get(a.get("state", ""), "bad")
    meta = ""
    if a.get("unit"):
        meta += f'<span class="dot {dot}"></span><span>{e(a.get("state") or "unknown")}</span>'
    v = a.get("version")
    if v == "behind":
        meta += f'<span class="tag warn" title="restarted by app-refresh at night">code newer: {e(a["running_rev"])} → {e(a["head_rev"])}</span>'
    elif v == "current":
        meta += f'<span class="tag">{e(a["head_rev"])}</span>'
    return (
        f'<a class="card" href="{e(a["path"])}"><strong>{e(a["name"])}</strong>'
        f'<span class="d">{e(a.get("desc", ""))}</span><div class="meta">{meta}</div></a>'
    )


def job_row(j: Data) -> str:
    ok = j["result"] == "success"
    running = j["active"] in ("activating", "active")
    if running:
        dot, text = "warn", "running"
    elif ok:
        dot, text = "ok", "ok"
    else:
        dot, text = "bad", j["result"] or "never run"
    return (
        f'<tr><td>{e(j["label"])}</td><td><span class="dot {dot}"></span> {e(text)}</td>'
        f"<td>{e(short_time(j['last']))}</td><td>{e(short_time(j['next']))}</td></tr>"
    )


def disk_row(d: Data) -> str:
    cls = "vhi" if d["pct"] >= 90 else "hi" if d["pct"] >= 80 else ""
    return (
        f'<tr><td>{e(d["label"])}</td><td><div class="bar"><i class="{cls}" style="width:{d["pct"]}%"></i></div></td>'
        f"<td>{e(human(d['used']))} of {e(human(d['total']))}</td><td>{d['pct']}%</td></tr>"
    )


def sparkline(values: Sequence[float], label: str) -> str:
    """Inline SVG area chart of 0-100 values, newest on the right. Turns amber/red when the latest value is high."""
    if len(values) < 2:
        return f'<svg class="spark" role="img" aria-label="{e(label)}: collecting data"></svg>'
    w, h = 300, 100
    step = w / (len(values) - 1)
    pts = " ".join(f"{i * step:.1f},{h - max(0, min(100, v)):.1f}" for i, v in enumerate(values))
    last = values[-1]
    cls = "vhi" if last >= 90 else "hi" if last >= 75 else ""
    return (
        f'<svg class="spark plain {cls}" viewBox="0 0 {w} {h}" preserveAspectRatio="none" role="img" '
        f'aria-label="{e(label)}: {last:.0f}%, last {len(values)} samples">'
        f'<polygon class="area" points="0,{h} {pts} {w},{h}"/><polyline class="line" points="{pts}"/></svg>'
    )


def stacked(used: Sequence[float], cache: Sequence[float], label: str) -> str:
    """Memory history: apps (used) at the bottom, cache and buffers stacked on top."""
    if len(used) < 2 or len(cache) != len(used):
        return sparkline(used, label)
    w, h = 300, 100
    step = w / (len(used) - 1)
    low = [max(0, min(100, v)) for v in used]
    top = [max(0, min(100, u + c)) for u, c in zip(used, cache, strict=True)]

    def xy(vs: Sequence[float]) -> list[str]:
        return [f"{i * step:.1f},{h - v:.1f}" for i, v in enumerate(vs)]

    cls = "vhi" if used[-1] >= 90 else "hi" if used[-1] >= 75 else ""
    band = " ".join(xy(top) + xy(low)[::-1])
    return (
        f'<svg class="spark {cls}" viewBox="0 0 {w} {h}" preserveAspectRatio="none" role="img" '
        f'aria-label="{e(label)}: {used[-1]:.0f}% used by programs, {cache[-1]:.0f}% cache">'
        f'<polygon class="cache" points="{band}"/><polygon class="area" points="0,{h} {" ".join(xy(low))} {w},{h}"/>'
        f'<polyline class="line" points="{" ".join(xy(low))}"/></svg>'
    )


def mem_breakdown(r: Data) -> str:
    total = r.get("mem_total_kb", 0) or 1
    sw_total, sw_used = r.get("swap_total_kb", 0), r.get("swap_total_kb", 0) - r.get("swap_free_kb", 0)
    parts = [
        ("used", "Used", r.get("mem_used_kb", 0), "by programs"),
        ("cached", "Cached", r.get("mem_cached_kb", 0), "file cache, reclaimable"),
        ("buffers", "Buffers", r.get("mem_buffers_kb", 0), "kernel I/O buffers"),
        ("free", "Free", r.get("mem_free_kb", 0), "unused"),
    ]
    bar = "".join(
        f'<i class="m-{k}" style="width:{100 * kb / total:.2f}%" title="{n}: {e(human(kb * 1024))}"></i>'
        for k, n, kb, _ in parts
    )
    rows = "".join(
        f'<tr><td><span class="sw m-{k}"></span>{n} <span class="d">{d}</span></td>'
        f'<td class="num">{e(human(kb * 1024))}</td><td class="num">{100 * kb / total:.0f}%</td></tr>'
        for k, n, kb, d in parts
    )
    if sw_total:
        rows += (
            f'<tr><td><span class="sw m-swap"></span>Swap <span class="d">on disk</span></td>'
            f'<td class="num">{e(human(sw_used * 1024))}</td><td class="num">{100 * sw_used / sw_total:.0f}%</td></tr>'
        )
    return f'<div class="stack">{bar}</div><table class="mem">{rows}</table>'


def span_label(n: int, interval: float) -> str:
    s = max(0, n - 1) * interval
    return f"{s // 60} min ago" if s >= 90 else f"{s} s ago"


def proc_table(title: str, rows: Sequence[Data]) -> str:
    body = "".join(
        f'<tr><td class="name" title="pid {r["pid"]}">{e(r["name"])}</td>'
        f'<td class="num">{r["cpu"]:.0f}%</td><td class="num">{e(human(r["rss"]))}</td></tr>'
        for r in rows
    )
    return f'<div><table><tr><th>{e(title)}</th><th class="num">CPU</th><th class="num">Memory</th></tr>{body}</table></div>'


def resources_section(r: Data | None) -> str:
    if not r:
        return ""
    cpu, mem, n = r.get("cpu", []), r.get("mem", []), r.get("ncpu", 1)
    cpu_now = f"{cpu[-1]:.0f}%" if cpu else "…"
    total, avail = r.get("mem_total_kb", 0), r.get("mem_avail_kb", 0)
    used = r.get("mem_used_kb", total - avail) * 1024
    mem_now = f"{mem[-1]:.0f}%" if mem else "…"
    iv = r.get("interval", 5)

    def axis(v: Sequence[float]) -> str:
        return f'<div class="axis"><span>{span_label(len(v), iv)}</span><span>now</span></div>'

    cards = (
        f'<div class="gcard"><h3>CPU · {n} core{"s" if n != 1 else ""}</h3><div class="big">{cpu_now}</div>'
        f"{sparkline(cpu, 'CPU')}{axis(cpu)}</div>"
        f'<div class="gcard"><h3>Memory</h3><div class="big">{mem_now} <small>{e(human(used))} used of {e(human(total * 1024))}</small></div>'
        f"{stacked(mem, r.get('mem_cache', []), 'Memory')}{axis(mem)}{mem_breakdown(r)}</div>"
    )
    tables = ""
    if r.get("top_cpu"):
        tables = (
            f'<div class="graphs" style="margin-top:12px">{proc_table("Top by CPU", r["top_cpu"])}'
            f"{proc_table('Top by memory', r.get('top_mem', []))}</div>"
        )
    return f'<h2>Resources</h2><div class="graphs">{cards}</div>{tables}'


def finding(data: Data) -> str | None:
    """The one thing most worth knowing right now, or None when all is well."""
    if data.get("failed"):
        return f"{len(data['failed'])} failed unit(s): {', '.join(data['failed'][:3])}"
    for d in data.get("disks", []):
        if d["pct"] >= 90:
            return f"{d['label']} is {d['pct']}% full"
    r: Data = data.get("resources") or {}
    cpu: list[float] = r.get("cpu", [])[-6:]
    if len(cpu) >= 6 and min(cpu) >= 75:
        procs: list[Data] = r.get("top_cpu") or []
        name: str = procs[0].get("name", "") if procs else ""
        return "CPU above 75% for the last minute" + (f", mostly {name}" if name else "")
    if r.get("mem") and r["mem"][-1] >= 90:
        return f"Memory is {r['mem'][-1]:.0f}% used by programs"
    behind = [a["name"] for a in data.get("apps", []) if a.get("version") == "behind"]
    if behind:
        return f"{len(behind)} app(s) behind their code"
    return None


def perf_section(perf: Data | None) -> str:
    """The same numbers as the page's "Over time" section, for one window, as plain tables."""
    if not perf:
        return ""
    if not perf.get("available"):
        return (
            "<h2>Over time</h2><p class='sub'>No performance data yet. It is written by <code>perf-sample</code>.</p>"
        )
    rows = "".join(
        f"<tr><td>{e(r['label'])}</td><td>{e(perf_val(r, r['mean']))}</td><td>{e(perf_val(r, r['p95']))}</td>"
        f"<td>{e(perf_val(r, r['max']))}</td><td>{'' if r['stressed_pct'] is None else str(round(r['stressed_pct'])) + '%'}</td></tr>"
        for r in perf["resources"]
    )
    svc = "".join(
        f"<tr><td>{e(s['name'])}{(' <span class=d>' + e(s['label']) + '</span>') if s['label'] else ''}</td><td>{s['cpu_hours']:.2f}</td>"
        f"<td>{s['ram_gb']:.1f} GB</td><td>{s['written_gb']:.1f} GB</td><td>{s['gpu_mib']} MiB</td></tr>"
        for s in perf["services"]
    )
    return (
        f"<h2>Over time: {e(perf['label'])}</h2><p class='sub'>{e(perf['verdict'])}</p>"
        "<table class='jobs'><tr><th>Resource</th><th>Average</th><th>Busy (p95)</th><th>Peak</th><th>Over limit</th></tr>"
        + rows
        + "</table>"
        + (
            "<h2>Who used it</h2><table class='jobs'><tr><th>Service</th><th>CPU core-hours</th><th>Peak RAM</th><th>Written</th><th>GPU memory</th></tr>"
            + svc
            + "</table>"
            if svc
            else ""
        )
    )


def perf_val(r: Data, v: float) -> str:
    return f"{v:g} {r['unit']}" if r["unit"] != "%" else f"{v:.0f}%"


def page(data: Data, hostname: str = "homepage", refresh: float = 10, perf: Data | None = None) -> str:
    s: Data = data.get("system", {})
    sub: list[str] = []
    if "uptime_s" in s:
        sub.append("up " + fmt_uptime(s["uptime_s"]))
    if "mem_total_kb" in s:
        sub.append(
            f"{human((s['mem_total_kb'] - s['mem_avail_kb']) * 1024)} of {human(s['mem_total_kb'] * 1024)} RAM in use"
        )
    if s.get("load"):
        sub.append("load " + " ".join(f"{x:.1f}" for x in s["load"]))
    f = finding(data)
    sub.insert(0, f if f else "All good")
    alerts = ""
    if data.get("failed"):
        alerts += f'<div class="alert">Failed units: {e(", ".join(data["failed"]))}</div>'
    behind = [a["name"] for a in data.get("apps", []) if a.get("version") == "behind"]
    apps = (
        "".join(app_card(a) for a in data.get("apps", []))
        or '<p class="sub">No apps yet. Add a snippet in <code>~/.config/caddy/sites/</code>.</p>'
    )
    jobs = "".join(job_row(j) for j in data.get("jobs", []))
    disks = "".join(disk_row(d) for d in data.get("disks", []))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="{int(refresh)}"><title>{e(hostname)}</title><style>{CSS}</style></head>
<body><main>
<h1>{e(hostname)}</h1><p class="sub">{e(" · ".join(sub))}</p>
{alerts}
<h2>Apps</h2><div class="grid">{apps}</div>
{resources_section(data.get("resources"))}
{perf_section(perf)}
{"<h2>Jobs</h2><table class='jobs'><tr><th>Job</th><th>Last result</th><th>Last run</th><th>Next</th></tr>" + jobs + "</table>" if jobs else ""}
{"<h2>Storage</h2><table class='jobs'><tr><th>Disk</th><th></th><th>Used</th><th></th></tr>" + disks + "</table>" if disks else ""}
<footer>Updated {e(data.get("generated", "")[11:16])}
 · <a href="/_home/api/status">json</a> · <a href="/auth/logout">Sign out</a>{(" · " + str(len(behind)) + " app(s) behind their code") if behind else ""}</footer>
</main></body></html>"""
