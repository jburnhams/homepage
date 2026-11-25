"""Collect the status shown on the page. Everything external goes through `run` so tests can fake it."""

import datetime
import os
import shutil
import subprocess
from collections.abc import Callable
from typing import Any

from strata_python import oslib

from .snippets import AppInfo

Runner = Callable[..., tuple[str, int]]
Data = dict[str, Any]


def run(cmd: list[str], timeout: float = 5) -> tuple[str, int]:
    """(stdout, returncode); never raises. The commands are a fixed list in this module, nothing from a request."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603
        return r.stdout.strip(), r.returncode
    except (OSError, subprocess.SubprocessError):
        return "", 127


def _show(unit: str, props: list[str], runner: Runner) -> dict[str, str]:
    out, _ = runner(["systemctl", "--user", "show", unit, "-p", ",".join(props)])
    d: dict[str, str] = {}
    for line in out.splitlines():
        k, _, v = line.partition("=")
        d[k] = v
    return d


def app_status(app: AppInfo, runner: Runner = run, state_dir: str | None = None, repos_dir: str | None = None) -> Data:
    """Add state/started/version to an app dict (from snippets.load_apps)."""
    a: Data = dict(app)
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


def job_status(jobs_to_show: list[tuple[str, str]], runner: Runner = run) -> list[Data]:
    """`(label, systemd user unit)` pairs from the `jobs` setting; only units that exist are shown."""
    jobs: list[Data] = []
    for label, unit in jobs_to_show:
        d = _show(
            unit + ".service",
            ["LoadState", "Result", "ActiveState", "ExecMainExitTimestamp", "ExecMainStatus"],
            runner,
        )
        if d.get("LoadState") != "loaded":
            continue
        t = _show(unit + ".timer", ["NextElapseUSecRealtime"], runner)
        jobs.append(
            {
                "label": label,
                "unit": unit,
                "result": d.get("Result", ""),
                "active": d.get("ActiveState", ""),
                "last": d.get("ExecMainExitTimestamp", ""),
                "next": t.get("NextElapseUSecRealtime", ""),
            }
        )
    return jobs


def failed_units(runner: Runner = run) -> list[str]:
    out, _ = runner(["systemctl", "--user", "--failed", "--no-legend", "--plain"])
    return [line.split()[0] for line in out.splitlines() if line.strip()]


def disks(paths: list[tuple[str, str]]) -> list[Data]:
    """`(label, path)` pairs from the `disks` setting; a path other than `/` is skipped while it is not a mount point."""
    res: list[Data] = []
    for label, p in paths:
        if p != "/" and not os.path.ismount(p):
            continue
        try:
            u = shutil.disk_usage(p)
        except OSError:
            continue
        pct = round(100 * u.used / u.total) if u.total else 0
        res.append({"label": label, "path": p, "total": u.total, "used": u.used, "pct": pct})
    return res


def system() -> Data:
    d: Data = {}
    try:
        with open("/proc/uptime") as fh:
            d["uptime_s"] = int(float(fh.read().split()[0]))
        with open("/proc/meminfo") as fh:
            mem = {line.split(":")[0]: int(line.split()[1]) for line in fh if ":" in line}
        d["mem_total_kb"], d["mem_avail_kb"] = mem["MemTotal"], mem["MemAvailable"]
    except (OSError, KeyError, ValueError, IndexError):
        pass
    load = oslib.load_average()
    if load:
        d["load"] = load
    return d


def collect(
    apps: list[AppInfo],
    state_dir: str,
    repos_dir: str,
    runner: Runner = run,
    jobs: list[tuple[str, str]] | None = None,
    disk_paths: list[tuple[str, str]] | None = None,
) -> Data:
    return {
        "generated": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "apps": [app_status(a, runner, state_dir, repos_dir) for a in apps],
        "jobs": job_status(jobs or [], runner),
        "failed": failed_units(runner),
        "disks": disks(disk_paths if disk_paths is not None else [("Root", "/")]),
        "system": system(),
    }
