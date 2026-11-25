"""A status with something to show in every section, for the page tests."""

DATA = {
    "generated": "2026-11-07T07:00:00+00:00",
    "apps": [
        {
            "name": "Demo <b>", "path": "/demo/", "desc": "d & e", "unit": "demo", "state": "active",
            "version": "behind", "running_rev": "aaaaaaaa", "head_rev": "bbbbbbbb",
        },
        {"name": "Plain", "path": "/p/", "desc": "", "unit": "", "state": "", "version": ""},
    ],
    "jobs": [
        {
            "label": "Backup", "unit": "b", "result": "success", "active": "inactive",
            "last": "Sat 2026-11-07 04:25:28 GMT", "next": "Sun 2026-11-08 02:30:00 GMT",
        },
        {"label": "Broken", "unit": "x", "result": "exit-code", "active": "failed", "last": "", "next": ""},
    ],
    "failed": ["x.service"],
    "disks": [{"label": "Root", "path": "/", "total": 1000**4, "used": 900 * 1000**3, "pct": 90}],
    "system": {"uptime_s": 90061, "load": (0.5, 0.4, 0.3), "mem_total_kb": 4000000, "mem_avail_kb": 1000000},
}  # fmt: skip
