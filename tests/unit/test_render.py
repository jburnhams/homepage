from sample_status import DATA

from homepage import render, resources


def test_page_escapes_and_shows_state():
    h = render.page(DATA, "host<x>")
    assert "<b>" not in h  # app names are escaped
    assert "Demo &lt;b&gt;" in h
    assert "host&lt;x&gt;" in h
    assert "code newer: aaaaaaaa" in h
    assert "Failed units: x.service" in h
    assert "exit-code" in h
    assert 'class="vhi"' in h  # 90% disk is flagged
    assert "up 1d 1h 1m" in h


def test_empty_page():
    h = render.page({"generated": "", "apps": [], "jobs": [], "failed": [], "disks": [], "system": {}}, "h")
    assert "No apps yet" in h
    assert "<h2>Jobs</h2>" not in h
    assert "All good" in h


def test_helpers():
    assert render.short_time("Sat 2026-11-07 04:25:28 GMT") == "11-07 04:25"
    assert render.short_time("") == "-"
    assert render.human(1536) == "2 KB"
    assert render.human(5 * 1024**4) == "5.0 TB"
    assert render.fmt_uptime(90061) == "1d 1h 1m"


def test_resources_section():
    r = {
        "interval": 5, "ncpu": 4, "cpu": [10, 95, 50], "mem": [40, 41, 42], "mem_cache": [10, 10, 20],
        "mem_used_kb": 1600000, "mem_free_kb": 1000000, "mem_buffers_kb": 100000, "mem_cached_kb": 1300000,
        "mem_total_kb": 4000000, "mem_avail_kb": 2000000, "swap_total_kb": 1000, "swap_free_kb": 400,
        "top_cpu": [{"pid": 1, "name": "<script>", "cpu": 12.0, "rss": 2048}], "top_mem": [],
    }  # fmt: skip
    h = render.resources_section(r)
    assert "<script>" not in h
    assert "&lt;script&gt;" in h
    assert "<polyline" in h
    assert "CPU · 4 cores" in h
    assert "10 s ago" in h
    for w in ("Used", "Cached", "Buffers", "Free", "Swap"):
        assert w in h
    assert 'class="cache"' in h


def test_a_real_sample_renders():
    s = resources.Sampler()
    s.sample()
    s.sample()
    assert "Memory" in render.resources_section(s.snapshot())


def test_sparkline_flags_and_empty():
    assert "plain vhi" in render.sparkline([1, 95], "x")
    assert "collecting" in render.sparkline([1], "x")
    assert render.resources_section(None) == ""


def test_finding_priority():
    assert render.finding({"failed": [], "disks": [], "apps": []}) is None
    f = render.finding({"failed": ["x.service"], "disks": [{"label": "R", "pct": 95}]})
    assert "failed unit" in (f or "")
    f = render.finding({"failed": [], "disks": [{"label": "R", "pct": 95}]})
    assert "95% full" in (f or "")
    hot = {"cpu": [80] * 6, "top_cpu": [{"name": "ffmpeg"}]}
    f = render.finding({"failed": [], "disks": [], "resources": hot})
    assert "mostly ffmpeg" in (f or "")
    f = render.finding({"failed": [], "disks": [], "resources": {"mem": [93]}})
    assert "93% used by programs" in (f or "")
    behind = [{"name": "A", "version": "behind"}]
    f = render.finding({"failed": [], "disks": [], "apps": behind})
    assert "1 app(s) behind" in (f or "")
