from pathlib import Path

from homepage import resources


def make_proc(
    root: Path, cpu: tuple[int, int], procs: dict[int, tuple[str, int, int]], avail_kb: int = 2000000
) -> None:
    """A /proc on disk. cpu: (busy, idle) ticks; procs: {pid: (name, ticks, rss_pages)}."""
    (root / "stat").write_text(
        f"cpu  {cpu[0]} 0 0 {cpu[1]} 0 0 0 0 0 0\ncpu0 1 0 0 1 0 0 0 0 0 0\ncpu1 1 0 0 1 0 0 0 0 0 0\n"
    )
    (root / "meminfo").write_text(
        "MemTotal: 4000000 kB\nMemFree: 1000000 kB\nBuffers: 200000 kB\nCached: 700000 kB\n"
        f"SReclaimable: 100000 kB\nMemAvailable: {avail_kb} kB\nSwapTotal: 100 kB\nSwapFree: 100 kB\n"
    )
    for pid, (name, ticks, rss) in procs.items():
        (root / str(pid)).mkdir(exist_ok=True)
        # fields after ")": state + 10 more up to utime(14) stime(15) ... rss is field 24
        f = ["S"] + ["0"] * 10 + [str(ticks), "0"] + ["0"] * 8 + [str(rss)] + ["0"] * 5
        (root / str(pid) / "stat").write_text(f"{pid} ({name}) " + " ".join(f))


def test_cpu_mem_and_top(tmp_path: Path):
    t = [0.0]
    s = resources.Sampler(proc=str(tmp_path), interval=5, keep=3, top=2, clock=lambda: t[0])
    make_proc(tmp_path, (100, 900), {1: ("a b)(c", 0, 10), 2: ("idle", 0, 500), 3: ("big", 0, 9000)})
    s.sample()
    assert s.snapshot()["cpu"] == []  # needs two samples
    t[0] = 5
    make_proc(
        tmp_path,
        (200, 1800),
        {1: ("a b)(c", 250, 10), 2: ("idle", 0, 500), 3: ("big", 0, 9000)},
        avail_kb=1000000,
    )
    s.sample()
    snap = s.snapshot()
    assert snap["cpu"] == [10.0]  # 100 busy of 1000 ticks
    assert snap["mem"][-1] == 50.0  # (4000-1000-200-800)/4000
    assert snap["mem_cache"][-1] == 25.0
    assert (snap["mem_used_kb"], snap["mem_cached_kb"]) == (2000000, 800000)
    assert snap["ncpu"] == 2
    assert snap["top_cpu"][0]["name"] == "a b)(c"  # odd names parse
    assert snap["top_cpu"][0]["cpu"] == round(100 * 250 / resources.CLK_TCK / 5, 1)
    assert snap["top_mem"][0]["name"] == "big"
    assert len(snap["top_cpu"]) == 2
    for i in range(5):
        t[0] += 5
        make_proc(tmp_path, (200 + i, 1800 + 10 * i), {})
        s.sample()
    assert len(s.snapshot()["cpu"]) == 3  # rolling window


def test_missing_proc_does_not_raise():
    s = resources.Sampler(proc="/nonexistent")
    s.sample()
    assert s.snapshot()["cpu"] == []


def test_start_samples_straight_away_and_stop_ends_it():
    s = resources.Sampler(interval=3600)  # the real /proc; the next tick is an hour away
    s.start()
    try:
        assert s.snapshot()["mem_total_kb"] > 0
    finally:
        s.stop()
    s.stop()  # twice is fine
