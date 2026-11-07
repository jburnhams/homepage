"""Collect the status shown on the page. Everything external goes through `run` so tests can fake it."""
import datetime
import os
import shutil
import subprocess

# (label, systemd user unit). Only units that exist are shown.
JOBS = [
    ("Backup (restic)", "omarchy-restic-backup"),
    ("Work sync", "work-sync"),
    ("Mirror sync", "mirror-sync"),
    ("App refresh", "app-refresh"),
    ("GitHub sync", "github-sync"),
    ("Health check", "omarchy-health-check"),
    ("Garmin sync", "garmin-sync"),
]


def run(cmd, timeout=5):
    """(stdout, returncode); never raises."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except (OSError, subprocess.SubprocessError):
        return "", 127


def _show(unit, props, runner):
    out, rc = runner(["systemctl", "--user", "show", unit, "-p", ",".join(props)])
    d = {}
    for line in out.splitlines():
        k, _, v = line.partition("=")
        d[k] = v
    return d


def app_status(app, runner=run, state_dir=None, repos_dir=None):
    """Add state/started/version to an app dict (from snippets.load_apps)."""
    a = dict(app)
    a["state"] = ""
    a["version"] = ""
    if a.get("unit"):
        out, _ = runner(["systemctl", "--user", "is-active", a["unit"]])
        a["state"] = out or "unknown"
        a["started"] = _show(a["unit"], ["ActiveEnterTimestamp"], runner).get("ActiveEnterTimestamp", "")
    if a.get("unit") and a.get("repo") and state_dir and repos_dir:
        try:
            with open(os.path.join(state_dir, a["unit"] + ".rev")) as fh:
                running = fh.read().strip()
        except OSError:
            running = ""
        head, rc = runner(["git", "-C", os.path.join(repos_dir, a["repo"]), "rev-parse", "HEAD"])
        if running and rc == 0 and head:
            a["version"] = "current" if running == head else "behind"
            a["running_rev"], a["head_rev"] = running[:8], head[:8]
        else:
            a["version"] = "unknown"
    return a


def job_status(runner=run):
    jobs = []
    for label, unit in JOBS:
        d = _show(unit + ".service", ["LoadState", "Result", "ActiveState", "ExecMainExitTimestamp", "ExecMainStatus"], runner)
        if d.get("LoadState") != "loaded":
            continue
        t = _show(unit + ".timer", ["NextElapseUSecRealtime"], runner)
        jobs.append(dict(label=label, unit=unit, result=d.get("Result", ""), active=d.get("ActiveState", ""),
                         last=d.get("ExecMainExitTimestamp", ""), next=t.get("NextElapseUSecRealtime", "")))
    return jobs


def failed_units(runner=run):
    out, _ = runner(["systemctl", "--user", "--failed", "--no-legend", "--plain"])
    return [l.split()[0] for l in out.splitlines() if l.strip()]


def disks(paths=None):
    paths = paths or [("Root (NVMe)", "/"), ("Mirror disk", "/srv/mirror"), ("Server share (~/data)", os.path.expanduser("~/data"))]
    res = []
    for label, p in paths:
        if p != "/" and not os.path.ismount(p):
            continue
        try:
            u = shutil.disk_usage(p)
        except OSError:
            continue
        res.append(dict(label=label, path=p, total=u.total, used=u.used, pct=round(100 * u.used / u.total) if u.total else 0))
    return res


def system():
    d = {}
    try:
        with open("/proc/uptime") as fh:
            d["uptime_s"] = int(float(fh.read().split()[0]))
        d["load"] = os.getloadavg()
        mem = {l.split(":")[0]: int(l.split()[1]) for l in open("/proc/meminfo") if ":" in l}
        d["mem_total_kb"], d["mem_avail_kb"] = mem["MemTotal"], mem["MemAvailable"]
    except (OSError, KeyError, ValueError, IndexError):
        pass
    return d


def collect(apps, state_dir, repos_dir, runner=run):
    return dict(
        generated=datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        apps=[app_status(a, runner, state_dir, repos_dir) for a in apps],
        jobs=job_status(runner),
        failed=failed_units(runner),
        disks=disks(),
        system=system(),
    )
