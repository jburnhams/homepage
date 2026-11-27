"""Where the machine's time went over the last hour, day or week, from the files `perf-sample` writes.

`<dir>/YYYY-MM-DD.csv` has one row every 10 s of CPU, memory, pressure (PSI), disks, network and GPU.
`<dir>/units-YYYY-MM-DD.csv` has one row per service or job that was doing something in each sample.
`<dir>/diskpaths-YYYY-MM-DD.csv` has the data each service or job moved on each physical disk, with the folder (or `(whole service)`).
Both are plain CSV with a header, read here with the standard library only. Nothing is written.
"""

import csv
import datetime
import glob
import os
import re
import threading
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator
from typing import Any

Summary = dict[str, Any]

WINDOWS = {"1h": 3600, "24h": 86400, "7d": 7 * 86400}
LABELS = {"1h": "last hour", "24h": "last 24 hours", "7d": "last week"}
TTL = {"1h": 30, "24h": 120, "7d": 600}  # seconds a computed answer is reused, however many viewers
SAMPLE_S = 10  # the sampler's interval; totals multiply by it
POINTS = 90  # chart buckets

# (key, column, label, stressed above, unit, kind)
CORE = [
    ("cpu", "cpu_busy", "CPU busy, all threads", 80, "%"),
    ("core", "cpu_maxcore", "Busiest single core", 95, "%"),
    ("cpu_wait", "psi_cpu", "Programs waiting for a CPU", 10, "%"),
    ("mem_wait", "psi_mem_some", "Programs waiting for memory", 10, "%"),
    ("io_wait", "psi_io_some", "Programs waiting for a disk", 10, "%"),
]
PRESSURE = [  # (resource word, PSI column, threshold, units column that says who)
    ("memory", "psi_mem_some", 10, ("mem_gb",)),
    (
        "disk",
        "psi_io_some",
        10,
        (),
    ),  # who comes from diskpaths, on the disks that were busy: bytes summed over all disks blamed users of a fast disk
    ("cpu", "psi_cpu", 10, ("cpu_pct",)),
]


def _num(x: str | None) -> float | None:
    if x is None:
        return None
    try:
        return float(x)
    except ValueError:
        return None


def _files(directory: str, prefix: str, lo: datetime.datetime) -> list[str]:
    """Daily files that can hold anything at or after `lo`, oldest first."""
    pat = os.path.join(directory, prefix + "[0-9]*.csv")
    out: list[str] = []
    for f in sorted(glob.glob(pat)):
        day = os.path.basename(f)[len(prefix) : len(prefix) + 10]
        if day >= lo.strftime("%Y-%m-%d"):
            out.append(f)
    return out


def _read(
    directory: str, prefix: str, lo: datetime.datetime, hi: datetime.datetime
) -> Iterator[tuple[list[str], list[str]]]:
    """Yield (header, row) for rows with lo <= timestamp <= hi. Timestamps are local ISO text, so they compare as strings."""
    a, b = lo.isoformat(timespec="seconds"), hi.isoformat(timespec="seconds")
    for f in _files(directory, prefix, lo):
        try:
            with open(f, newline="") as fh:
                rd = csv.reader(fh)
                head = next(rd, None)
                if not head:
                    continue
                for row in rd:
                    if row and a <= row[0] <= b:
                        yield head, row
        except OSError:
            continue


def _pct(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    return sorted_vals[min(len(sorted_vals) - 1, int(len(sorted_vals) * p / 100))]


def _summ(key: str, label: str, vals: list[float | None], threshold: float | None, unit: str) -> Summary | None:
    vs = [v for v in vals if v is not None]
    if not vs:
        return None
    s = sorted(vs)
    return dict(
        key=key,
        label=label,
        unit=unit,
        mean=round(sum(vs) / len(vs), 1),
        p95=round(_pct(s, 95), 1),
        max=round(s[-1], 1),
        threshold=threshold,
        stressed_pct=round(100 * sum(v > threshold for v in vs) / len(vs), 1) if threshold is not None else None,
    )


_ONE_OFF = re.compile(r"^run-p\d+-i\d+\.scope$")  # systemd-run's random names: one row for all of them


def _name(unit: str, label: str) -> tuple[str, str]:
    if _ONE_OFF.match(unit):
        return "one-off run", label
    return (unit[:-8] if unit.endswith(".service") else unit), label


def summary(
    directory: str, window: str = "24h", now: datetime.datetime | None = None, mem_total_gb: float = 0.0
) -> Summary:
    """The whole answer for one window as a JSON-ready dict. `available` is False when there is no data yet."""
    if window not in WINDOWS:
        window = "24h"
    now = now or datetime.datetime.now()
    span = WINDOWS[window]
    lo = now - datetime.timedelta(seconds=span)
    cols: defaultdict[str, list[float | None]] = defaultdict(list)  # column -> values, one per sample
    stamps: list[str] = []
    for head, row in _read(directory, "", lo, now):
        stamps.append(row[0])
        for name, v in zip(head, row):
            if name not in ("ts", "top_cpu", "top_mem"):
                cols[name].append(_num(v))
    if len(stamps) < 2:
        return dict(available=False, window=window, label=LABELS[window])
    n = len(stamps)
    disks = sorted(c[:-5] for c in cols if c.endswith("_util") and not c.startswith("gpu"))
    nets = sorted(c[:-7] for c in cols if c.endswith("_rx_mbs"))

    cand: list[Summary | None] = []
    for key, col, label, thr, unit in CORE:
        cand.append(_summ(key, label, cols.get(col, []), thr, unit))
    for d in disks:
        cand.append(_summ("disk_" + d, "Disk %s busy" % d, cols[d + "_util"], 80, "%"))
    if "gpu_util" in cols:
        cand.append(_summ("gpu", "GPU busy", cols["gpu_util"], 80, "%"))
    if mem_total_gb:
        used = [None if v is None else max(0.0, mem_total_gb - v) for v in cols.get("mem_avail_gb", [])]
        cand.append(_summ("mem", "Memory in use", used, 0.9 * mem_total_gb, "GB"))
    swap: list[float | None] = [
        (a or 0) + (b or 0) for a, b in zip(cols.get("swapin_mbs", []), cols.get("swapout_mbs", []))
    ]
    cand.append(_summ("swap", "Swapping to disk", swap, 20, "MB/s"))
    for nic in nets:
        cand.append(_summ("net_rx", "Network in (%s)" % nic, cols[nic + "_rx_mbs"], 90, "MB/s"))
        cand.append(_summ("net_tx", "Network out (%s)" % nic, cols[nic + "_tx_mbs"], 90, "MB/s"))
    res: list[Summary] = [r for r in cand if r]

    # who was running while something waited
    hit_sets: dict[str, set[str]] = {}
    for word, col, thr, _ in PRESSURE:
        vals = cols.get(col, [])
        hit_sets[word] = {stamps[i] for i, v in enumerate(vals) if v is not None and v > thr}
    unit_rows: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for head, row in _read(directory, "units-", lo, now):
        unit_rows[row[0]].append(dict(zip(head, row)))
    by: defaultdict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {"cpu": 0.0, "ram": 0.0, "swap": 0.0, "w": 0.0, "r": 0.0, "gpu": 0.0}
    )
    pressure: list[Summary] = []
    ctr: dict[str, Any] = {word: Counter() for word, *_ in PRESSURE}
    for ts, rows in unit_rows.items():
        for r in rows:
            nm = _name(r.get("unit", ""), r.get("label", ""))
            a = by[nm]
            a["cpu"] += (_num(r.get("cpu_pct")) or 0) * SAMPLE_S / 100 / 3600
            a["ram"] = max(a["ram"], _num(r.get("mem_gb")) or 0)
            a["swap"] = max(a["swap"], _num(r.get("swap_gb")) or 0)
            a["w"] += (_num(r.get("io_w_mbs")) or 0) * SAMPLE_S / 1000
            a["r"] += (_num(r.get("io_r_mbs")) or 0) * SAMPLE_S / 1000
            a["gpu"] = max(a["gpu"], _num(r.get("gpu_mem_mib")) or 0)
            for word, _, _, keys in PRESSURE:
                if keys and ts in hit_sets[word]:
                    ctr[word][nm] += sum(_num(r.get(k)) or 0 for k in keys)

    # which disk and folder: data moved per service on each physical disk
    dp_rows = [dict(zip(head, row)) for head, row in _read(directory, "diskpaths-", lo, now)]
    spinning = {r["disk"]: r.get("rot") == "1" for r in dp_rows}
    idx = {s_: i for i, s_ in enumerate(stamps)}
    for word, _, _, _ in PRESSURE:
        if not hit_sets[word]:
            continue
        minutes = max(1, round(len(hit_sets[word]) * SAMPLE_S / 60))
        if word != "disk":
            tot = sum(ctr[word].values())
            who: list[Summary] = (
                [dict(name=k[0], label=k[1], dir="", share=round(100 * v / tot)) for k, v in ctr[word].most_common(4)]
                if tot
                else []
            )
            pressure.append(dict(resource=word, minutes=minutes, who=who, disks=[]))
            continue
        hit = hit_sets["disk"]
        busy: list[Summary] = []  # the disks that were over 50% busy while programs waited
        for d in disks:
            k = sum(1 for s_ in hit if (cols[d + "_util"][idx[s_]] or 0) > 50)
            if k:
                busy.append(dict(disk=d, share=round(100 * k / len(hit)), spinning=spinning.get(d)))
        busy.sort(key=lambda b: -b["share"])
        main = {b["disk"] for b in busy if b["share"] >= 20}
        c: defaultdict[tuple[tuple[str, str], str], float] = defaultdict(float)
        for r in dp_rows:
            if r["ts"] in hit and r["disk"] in main:
                c[(_name(r["unit"], r["label"]), r["dir"])] += (_num(r.get("read_mbs")) or 0) + (
                    _num(r.get("write_mbs")) or 0
                )
        total = sum(c.values())
        who = (
            [
                dict(name=k[0][0], label=k[0][1], dir=k[1], share=round(100 * v / total))
                for k, v in sorted(c.items(), key=lambda kv: -kv[1])[:4]
            ]
            if total
            else []
        )
        pressure.append(dict(resource="disk", minutes=minutes, who=who, disks=busy))

    # what uses the spinning disks, and whether steadily (a candidate for the NVMe) or in bursts (what they are for)
    agg: defaultdict[tuple[str, tuple[str, str], str], dict[str, Any]] = defaultdict(
        lambda: {"r": 0.0, "w": 0.0, "ts": set(), "hrs": set()}
    )
    for r in dp_rows:
        if r.get("rot") != "1":
            continue
        a = agg[(r["disk"], _name(r["unit"], r["label"]), r["dir"])]
        a["r"] += (_num(r.get("read_mbs")) or 0) * SAMPLE_S / 1000
        a["w"] += (_num(r.get("write_mbs")) or 0) * SAMPLE_S / 1000
        a["ts"].add(r["ts"])
        a["hrs"].add(r["ts"][:13])
    all_hours = len({s_[:13] for s_ in stamps})
    disk_paths: list[Summary] = [
        dict(
            disk=k[0],
            name=k[1][0],
            label=k[1][1],
            dir=k[2],
            read_gb=round(a["r"], 1),
            write_gb=round(a["w"], 1),
            active_min=round(len(a["ts"]) * SAMPLE_S / 60),
            hours=len(a["hrs"]),
            steady=len(a["hrs"]) >= max(3, 0.25 * all_hours),
        )
        for k, a in agg.items()
        if a["r"] + a["w"] >= 0.5
    ]
    disk_paths.sort(key=lambda d: (not d["steady"], -(d["read_gb"] + d["write_gb"])))
    disk_paths = disk_paths[:12]

    chosen: list[tuple[str, str]] = []
    for key, k in (("cpu", 8), ("ram", 6), ("w", 5), ("gpu", 3)):
        for nm, a in sorted(by.items(), key=lambda kv: -kv[1][key])[:k]:
            if a[key] > 0 and nm not in chosen:
                chosen.append(nm)
    services: list[Summary] = [
        dict(
            name=nm[0],
            label=nm[1],
            cpu_hours=round(by[nm]["cpu"], 2),
            ram_gb=round(by[nm]["ram"], 1),
            swap_gb=round(by[nm]["swap"], 1),
            written_gb=round(by[nm]["w"], 1),
            read_gb=round(by[nm]["r"], 1),
            gpu_mib=round(by[nm]["gpu"]),
        )
        for nm in chosen
    ]
    services.sort(key=lambda s: -s["cpu_hours"])

    # chart series: mean per bucket, x = seconds before now (negative), only buckets that have samples
    bucket = span / POINTS
    nowt = now.timestamp()
    busiest: list[float | None] = []
    for i in range(n):
        vs: list[float] = [v for d in disks if (v := cols[d + "_util"][i]) is not None]
        busiest.append(max(vs) if vs else None)
    memused = (
        [None if v is None else max(0.0, mem_total_gb - v) for v in cols.get("mem_avail_gb", [])]
        if mem_total_gb
        else []
    )
    series: dict[str, list[Summary]] = {}
    for key, vals in (
        ("cpu", cols.get("cpu_busy", [])),
        ("mem", memused),
        ("disk", busiest),
        ("gpu", cols.get("gpu_util", [])),
    ):
        if not vals:
            series[key] = []
            continue
        sums: defaultdict[int, float] = defaultdict(float)
        cnt: defaultdict[int, int] = defaultdict(int)
        for s, v in zip(stamps, vals):
            if v is None:
                continue
            b = int((datetime.datetime.fromisoformat(s).timestamp() - (nowt - span)) // bucket)
            sums[b] += v
            cnt[b] += 1
        series[key] = [dict(x=round((b + 0.5) * bucket - span), y=round(sums[b] / cnt[b], 1)) for b in sorted(sums)]
    covered = n * SAMPLE_S

    return dict(
        available=True,
        window=window,
        label=LABELS[window],
        samples=n,
        covered_s=min(covered, span),
        start=stamps[0],
        end=stamps[-1],
        mem_total_gb=round(mem_total_gb, 1),
        resources=res,
        services=services,
        pressure=pressure,
        disk_paths=disk_paths,
        series=series,
        verdict=verdict(window, res, pressure, covered, span),
    )


def verdict(window: str, res: list[Summary], pressure: list[Summary], covered: float, span: float) -> str:
    """One sentence: what, if anything, was short, and who was running then."""
    label = LABELS[window]
    short = sorted(
        (
            r
            for r in res
            if r["stressed_pct"] and r["stressed_pct"] >= 1 and r["key"] not in ("net_rx", "net_tx", "core")
        ),  # one busy core is normal; the table still shows it
        key=lambda r: -r["stressed_pct"],
    )
    note = "" if covered >= 0.9 * span else " Only %s of data so far." % _dur(covered)
    if not short:
        return "Nothing was short of CPU, memory or disk in the %s.%s" % (label, note)
    top = short[0]
    who = ""
    word = {"mem_wait": "memory", "io_wait": "disk", "cpu_wait": "cpu"}.get(top["key"])
    for p in pressure:
        if p["resource"] == word and p["who"]:
            w = p["who"][0]
            who = ", mostly %s" % (w["name"] + (" [%s]" % w["label"] if w["label"] else ""))
            if word == "disk" and p.get("disks"):
                who += " (%s was busy)" % p["disks"][0]["disk"]
    return "%s was the tightest in the %s: over its limit %s%% of the time%s.%s" % (
        top["label"],
        label,
        round(top["stressed_pct"]),
        who,
        note,
    )


def _dur(s: float) -> str:
    if s < 5400:
        return "%d min" % round(s / 60)
    if s < 172800:
        return "%.1f h" % (s / 3600)
    return "%.1f days" % (s / 86400)


class Perf:
    """Caches each window's answer for a while, so a busy page costs one pass over the files per TTL."""

    def __init__(
        self,
        directory: str,
        mem_total_gb: Callable[[], float] = lambda: 0.0,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime.datetime] = datetime.datetime.now,
    ) -> None:
        self.directory, self.mem_total_gb, self.clock, self.now = directory, mem_total_gb, clock, now
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[float, Summary]] = {}

    def get(self, window: str) -> Summary:
        if window not in WINDOWS:
            window = "24h"
        with self._lock:
            hit = self._cache.get(window)
            if hit and self.clock() - hit[0] < TTL[window]:
                return hit[1]
            data = (
                summary(self.directory, window, self.now(), self.mem_total_gb())
                if os.path.isdir(self.directory)
                else dict(available=False, window=window, label=LABELS[window])
            )
            self._cache[window] = (self.clock(), data)
            return data
