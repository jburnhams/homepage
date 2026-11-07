import os, tempfile, unittest
from homepage import collect


def fake(table):
    def runner(cmd, timeout=5):
        for k, v in table.items():
            if k in " ".join(cmd):
                return v
        return "", 1
    return runner


class Collect(unittest.TestCase):
    def test_app_status_current_and_behind(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "svc.rev"), "w").write("a" * 40)
            app = dict(name="S", path="/s/", desc="", unit="svc", repo="r")
            r = fake({"is-active": ("active", 0), "ActiveEnterTimestamp": ("ActiveEnterTimestamp=Sat 2026-11-07 01:00:00 GMT", 0), "rev-parse": ("a" * 40, 0)})
            self.assertEqual(collect.app_status(app, r, d, "/repos")["version"], "current")
            r = fake({"is-active": ("active", 0), "rev-parse": ("b" * 40, 0)})
            a = collect.app_status(app, r, d, "/repos")
            self.assertEqual((a["version"], a["running_rev"], a["head_rev"]), ("behind", "aaaaaaaa", "bbbbbbbb"))

    def test_app_without_unit_or_rev(self):
        a = collect.app_status(dict(name="S", path="/s/", desc="", unit="", repo=""), fake({}), "/nope", "/repos")
        self.assertEqual((a["state"], a["version"]), ("", ""))
        with tempfile.TemporaryDirectory() as d:
            a = collect.app_status(dict(name="S", path="/s/", desc="", unit="svc", repo="r"), fake({"is-active": ("inactive", 3), "rev-parse": ("c" * 40, 0)}), d, "/repos")
            self.assertEqual((a["state"], a["version"]), ("inactive", "unknown"))

    def test_jobs_only_existing_units(self):
        def runner(cmd, timeout=5):
            if "work-sync.service" in cmd:
                return "LoadState=loaded\nResult=success\nActiveState=inactive\nExecMainExitTimestamp=Sat 2026-11-07 04:25:28 GMT\nExecMainStatus=0", 0
            if "work-sync.timer" in cmd:
                return "NextElapseUSecRealtime=Sun 2026-11-08 04:05:00 GMT", 0
            return "LoadState=not-found", 0
        jobs = collect.job_status(runner)
        self.assertEqual([j["unit"] for j in jobs], ["work-sync"])
        self.assertEqual((jobs[0]["result"], jobs[0]["next"]), ("success", "Sun 2026-11-08 04:05:00 GMT"))

    def test_failed_units(self):
        self.assertEqual(collect.failed_units(fake({"--failed": ("a.service loaded failed failed A\nb.service loaded failed failed B", 0)})), ["a.service", "b.service"])
        self.assertEqual(collect.failed_units(fake({})), [])

    def test_run_never_raises(self):
        self.assertEqual(collect.run(["/nonexistent/binary"]), ("", 127))

    def test_disks_skips_unmounted(self):
        res = collect.disks([("Root", "/"), ("Gone", "/definitely/not/mounted")])
        self.assertEqual([d["label"] for d in res], ["Root"])
        self.assertTrue(0 <= res[0]["pct"] <= 100)


if __name__ == "__main__":
    unittest.main()
