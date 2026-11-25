from pathlib import Path

from homepage import collect


def fake(table: dict[str, tuple[str, int]]) -> collect.Runner:
    """A stand-in for `systemctl` and `git`, the one true external here: the first key found in the command answers."""

    def runner(cmd: list[str], timeout: float = 5) -> tuple[str, int]:
        for k, v in table.items():
            if k in " ".join(cmd):
                return v
        return "", 1

    return runner


def test_app_status_current_and_behind(tmp_path: Path):
    (tmp_path / "svc.rev").write_text("a" * 40)
    app = {"name": "S", "path": "/s/", "desc": "", "unit": "svc", "repo": "r"}
    r = fake(
        {
            "is-active": ("active", 0),
            "ActiveEnterTimestamp": ("ActiveEnterTimestamp=Sat 2026-11-07 01:00:00 GMT", 0),
            "rev-parse": ("a" * 40, 0),
        }
    )
    assert collect.app_status(app, r, str(tmp_path), "/repos")["version"] == "current"
    r = fake({"is-active": ("active", 0), "rev-parse": ("b" * 40, 0)})
    a = collect.app_status(app, r, str(tmp_path), "/repos")
    assert (a["version"], a["running_rev"], a["head_rev"]) == ("behind", "aaaaaaaa", "bbbbbbbb")


def test_app_without_unit_or_rev(tmp_path: Path):
    plain = {"name": "S", "path": "/s/", "desc": "", "unit": "", "repo": ""}
    a = collect.app_status(plain, fake({}), "/nope", "/repos")
    assert (a["state"], a["version"]) == ("", "")
    app = {"name": "S", "path": "/s/", "desc": "", "unit": "svc", "repo": "r"}
    a = collect.app_status(
        app, fake({"is-active": ("inactive", 3), "rev-parse": ("c" * 40, 0)}), str(tmp_path), "/repos"
    )
    assert (a["state"], a["version"]) == ("inactive", "unknown")


def test_jobs_only_existing_units():
    def runner(cmd: list[str], timeout: float = 5) -> tuple[str, int]:
        if "work-sync.service" in cmd:
            return (
                "LoadState=loaded\nResult=success\nActiveState=inactive\n"
                "ExecMainExitTimestamp=Sat 2026-11-07 04:25:28 GMT\nExecMainStatus=0",
                0,
            )
        if "work-sync.timer" in cmd:
            return "NextElapseUSecRealtime=Sun 2026-11-08 04:05:00 GMT", 0
        return "LoadState=not-found", 0

    jobs = collect.job_status([("Backup", "nightly-backup"), ("Sync", "work-sync")], runner)
    assert [j["unit"] for j in jobs] == ["work-sync"]
    assert (jobs[0]["result"], jobs[0]["next"]) == ("success", "Sun 2026-11-08 04:05:00 GMT")


def test_no_jobs_configured_shows_none():
    assert collect.job_status([], fake({})) == []


def test_failed_units():
    out = "a.service loaded failed failed A\nb.service loaded failed failed B"
    assert collect.failed_units(fake({"--failed": (out, 0)})) == ["a.service", "b.service"]
    assert collect.failed_units(fake({})) == []


def test_run_never_raises():
    assert collect.run(["/nonexistent/binary"]) == ("", 127)


def test_run_returns_output():
    out, rc = collect.run(["python3", "-c", "print('hi')"])
    assert (out, rc) == ("hi", 0)


def test_disks_skips_unmounted():
    res = collect.disks([("Root", "/"), ("Gone", "/definitely/not/mounted")])
    assert [d["label"] for d in res] == ["Root"]
    assert 0 <= res[0]["pct"] <= 100


def test_system_reads_the_real_proc():
    s = collect.system()
    assert s["uptime_s"] > 0
    assert s["mem_total_kb"] >= s["mem_avail_kb"] > 0
    assert len(s["load"]) == 3


def test_collect_assembles_everything(tmp_path: Path):
    data = collect.collect([], str(tmp_path), str(tmp_path), fake({}))
    assert [d["path"] for d in data["disks"]] == ["/"]  # the default is the root disk alone
    assert data["jobs"] == []
    assert set(data) == {"generated", "apps", "jobs", "failed", "disks", "system"}
