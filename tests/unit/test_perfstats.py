import datetime
from pathlib import Path

from homepage import perfstats, render

NOW = datetime.datetime(2026, 11, 25, 12, 0, 0)
MAIN = (
    "ts,cpu_busy,cpu_maxcore,psi_cpu,psi_mem_some,psi_io_some,mem_avail_gb,swapin_mbs,swapout_mbs,"
    "nvme0n1_util,sdb_util,eth0_rx_mbs,eth0_tx_mbs,gpu_util,top_cpu,top_mem"
)
UNITS = "ts,unit,label,cpu_pct,mem_gb,swap_gb,io_r_mbs,io_w_mbs,gpu_mem_mib,gpu_sm_pct,nproc"


def stamp(minutes_ago: int) -> str:
    return (NOW - datetime.timedelta(minutes=minutes_ago)).isoformat(timespec="seconds")


DISKP = "ts,unit,label,disk,rot,dir,read_mbs,write_mbs,src"


def make(d: Path, rows: list[str], units: list[str], diskpaths: list[str] | None = None) -> None:
    """The daily files `perf-sample` writes, for today."""
    day = NOW.strftime("%Y-%m-%d")
    if diskpaths is not None:
        (d / ("diskpaths-" + day + ".csv")).write_text(DISKP + "\n" + "\n".join(diskpaths) + "\n")
    (d / (day + ".csv")).write_text(MAIN + "\n" + "\n".join(rows) + "\n")
    (d / ("units-" + day + ".csv")).write_text(UNITS + "\n" + "\n".join(units) + "\n")


def calm(minutes: tuple[int, ...]) -> list[str]:
    return [f"{stamp(m)},5,40,0,0,0,30,0,0,1,1,0,0,0,a,b" for m in minutes]


def test_none_when_empty(tmp_path: Path):
    assert not perfstats.summary(str(tmp_path), "1h", NOW)["available"]
    assert not perfstats.Perf(str(tmp_path / "missing")).get("1h")["available"]


def test_window_stress_and_who(tmp_path: Path):
    # 3 samples inside the hour (one under memory pressure), 1 from 3 h ago that the hour must ignore
    rows = [f"{stamp(m)},50,99,1,{p},0,10,0,0,5,1,2,1,0,python,python" for m, p in ((50, 0), (30, 40), (10, 0))] + [
        f"{stamp(180)},99,99,99,99,99,10,0,0,5,1,2,1,0,x,y"
    ]
    units = [
        f"{stamp(30)},big.service,,36000,20,0,0,0,0,0,3",
        f"{stamp(30)},small.service,,10,1,0,0,0,0,0,1",
        f"{stamp(10)},big.service,,18000,19,0,0,0,0,0,3",
        f"{stamp(180)},old.service,,100,5,0,0,0,0,0,1",
        f"{stamp(30)},nightly-import.service,photos,200,2,0,1,2,0,0,1",
        f"{stamp(30)},run-p123-i456.scope,job,90,1,0,0,0,0,0,1",
    ]
    make(tmp_path, rows, units)
    s = perfstats.summary(str(tmp_path), "1h", NOW, mem_total_gb=32)
    assert s["available"]
    assert s["samples"] == 3  # the 3 h old row is outside the hour
    by = {r["key"]: r for r in s["resources"]}
    assert by["mem_wait"]["max"] == 40
    assert by["mem_wait"]["stressed_pct"] == 33.3
    assert by["mem"]["max"] == 22  # 32 total - 10 available
    assert by["core"]["stressed_pct"] == 100
    names = [(x["name"], x["label"]) for x in s["services"]]
    assert ("old", "") not in names
    assert ("one-off run", "job") in names  # random run-p123-i456.scope names are folded
    assert ("nightly-import", "photos") in names  # untagged work keeps its label
    big = next(x for x in s["services"] if x["name"] == "big")
    assert big["ram_gb"] == 20
    assert big["cpu_hours"] == 1.5  # (36000 + 18000) % of a core x 10 s
    mem = next(p for p in s["pressure"] if p["resource"] == "memory")
    assert mem["who"][0]["name"] == "big"  # at the one pressured sample, big held most memory
    assert "memory" in s["verdict"]
    assert "big" in s["verdict"]
    assert "Only" in s["verdict"]  # 30 s of data in a 1 h window
    assert all(-3600 <= p["x"] <= 0 for p in s["series"]["cpu"])


def test_calm_machine(tmp_path: Path):
    make(tmp_path, calm((50, 30, 10)), [])
    s = perfstats.summary(str(tmp_path), "1h", NOW, mem_total_gb=32)
    assert s["verdict"].startswith("Nothing was short")
    assert s["pressure"] == []


def test_unknown_window_is_a_day_and_results_are_cached(tmp_path: Path):
    make(tmp_path, calm((50, 10)), [])
    t = [0.0]
    p = perfstats.Perf(str(tmp_path), clock=lambda: t[0], now=lambda: NOW)
    assert p.get("bogus")["window"] == "24h"
    first = p.get("24h")
    t[0] = 10
    assert p.get("24h") is first  # inside the ttl
    t[0] = 1000
    assert p.get("24h") is not first


def test_plain_page_shows_it_escaped(tmp_path: Path):
    make(tmp_path, calm((50, 10)), [f"{stamp(10)},evil.service,<b>x</b>,50,2,0,0,0,0,0,1"])
    html = render.perf_section(perfstats.summary(str(tmp_path), "24h", NOW, 32))
    assert "evil" in html
    assert "<b>x</b>" not in html
    assert "&lt;b&gt;" in html
    assert "No performance data yet" in render.perf_section({"available": False, "label": "x"})


def test_disk_waits_are_blamed_on_the_busy_disk_not_on_who_moved_most_bytes(tmp_path: Path):
    # the database moves far more bytes, but on the SSD; the waits were on the spinning disk sdb
    hit = [stamp(30), stamp(10)]
    rows = [f"{stamp(50)},5,40,0,0,0,30,0,0,5,1,0,0,0,a,b"] + [f"{t},5,40,0,0,40,30,0,0,5,90,0,0,0,a,b" for t in hit]
    dp = (
        [f"{t},database.service,,nvme0n1,0,(whole service),0,200,cgroup" for t in hit]
        + [f"{t},media-sync.service,,sdb,1,/data/archive/raw,80,0,files" for t in hit]
        + [f"{t},file-share.service,,sdb,1,(whole service),0,50,cgroup" for t in hit]
    )
    make(tmp_path, rows, [], dp)
    s = perfstats.summary(str(tmp_path), "1h", NOW, 32)
    p = next(x for x in s["pressure"] if x["resource"] == "disk")
    assert [x["disk"] for x in p["disks"]] == ["sdb"]  # only sdb was over 50 % busy
    assert p["disks"][0]["share"] == 100
    assert p["disks"][0]["spinning"] is True
    assert [x["name"] for x in p["who"]] == ["media-sync", "file-share"]  # no postgresql
    assert p["who"][0]["dir"] == "/data/archive/raw"
    assert p["who"][0]["share"] == 62
    assert "sdb was busy" in s["verdict"]
    assert "database" not in s["verdict"]


def test_spinning_disk_use_is_steady_or_bursts(tmp_path: Path):
    hours = [10, 70, 130, 190]  # four different hours: steady
    rows = calm((*hours, 250))
    dp = (
        [f"{stamp(m)},indexer.service,,sdb,1,/data/imports,100,0,files" for m in hours]
        + [f"{stamp(250)},copy-job,,sdb,1,/data/archive/2015,500,0,files"]  # one big burst: GB but one hour
        + [f"{stamp(10)},database.service,,nvme0n1,0,(whole service),0,300,cgroup"]
    )
    make(tmp_path, rows, [], dp)
    paths = perfstats.summary(str(tmp_path), "24h", NOW, 32)["disk_paths"]
    by = {(x["name"], x["dir"]): x for x in paths}
    assert by[("indexer", "/data/imports")]["steady"]
    assert by[("indexer", "/data/imports")]["hours"] == 4
    assert not by[("copy-job", "/data/archive/2015")]["steady"]
    assert "database" not in [x["name"] for x in paths]  # only spinning disks are listed
    assert paths[0]["name"] == "indexer"  # steady users first: they are the ones to move
