import datetime, os, tempfile, unittest
from homepage import perfstats, render

NOW = datetime.datetime(2026, 11, 25, 12, 0, 0)
MAIN = ("ts,cpu_busy,cpu_maxcore,psi_cpu,psi_mem_some,psi_io_some,mem_avail_gb,swapin_mbs,swapout_mbs,"
        "nvme0n1_util,sda_util,eno1_rx_mbs,eno1_tx_mbs,gpu_util,top_cpu,top_mem")
UNITS = "ts,unit,label,cpu_pct,mem_gb,swap_gb,io_r_mbs,io_w_mbs,gpu_mem_mib,gpu_sm_pct,nproc"


def stamp(minutes_ago):
    return (NOW - datetime.timedelta(minutes=minutes_ago)).isoformat(timespec="seconds")


def make(d, rows, units):
    day = NOW.strftime("%Y-%m-%d")
    open(os.path.join(d, day + ".csv"), "w").write(MAIN + "\n" + "\n".join(rows) + "\n")
    open(os.path.join(d, "units-" + day + ".csv"), "w").write(UNITS + "\n" + "\n".join(units) + "\n")


class Summary(unittest.TestCase):
    def test_none_when_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(perfstats.summary(d, "1h", NOW)["available"])
            self.assertFalse(perfstats.Perf(d + "/missing").get("1h")["available"])

    def test_window_stress_and_who(self):
        with tempfile.TemporaryDirectory() as d:
            # 3 samples inside the hour (one under memory pressure), 1 from 3 h ago that the hour must ignore
            make(d, [f"{stamp(m)},50,99,1,{p},0,10,0,0,5,1,2,1,0,python,python" for m, p in ((50, 0), (30, 40), (10, 0))]
                    + [f"{stamp(180)},99,99,99,99,99,10,0,0,5,1,2,1,0,x,y"],
                 [f"{stamp(30)},big.service,,36000,20,0,0,0,0,0,3", f"{stamp(30)},small.service,,10,1,0,0,0,0,0,1",
                  f"{stamp(10)},big.service,,18000,19,0,0,0,0,0,3", f"{stamp(180)},old.service,,100,5,0,0,0,0,0,1",
                  f"{stamp(30)},claude-remote-control.service,docs:python,200,2,0,1,2,0,0,1",
                  f"{stamp(30)},run-p123-i456.scope,job,90,1,0,0,0,0,0,1"])
            s = perfstats.summary(d, "1h", NOW, mem_total_gb=32)
            self.assertTrue(s["available"])
            self.assertEqual(s["samples"], 3)                                          # the 3 h old row is outside the hour
            by = {r["key"]: r for r in s["resources"]}
            self.assertEqual(by["mem_wait"]["max"], 40)
            self.assertAlmostEqual(by["mem_wait"]["stressed_pct"], 33.3, 1)
            self.assertEqual(by["mem"]["max"], 22)                                     # 32 total - 10 available
            self.assertEqual(by["core"]["stressed_pct"], 100)
            names = [(x["name"], x["label"]) for x in s["services"]]
            self.assertNotIn(("old", ""), names)
            self.assertIn(("one-off run", "job"), names)                               # random run-p123-i456.scope names are folded
            self.assertIn(("claude-remote-control", "docs:python"), names)             # untagged work keeps its label
            big = [x for x in s["services"] if x["name"] == "big"][0]
            self.assertEqual(big["ram_gb"], 20)
            self.assertEqual(big["cpu_hours"], 1.5)                                   # (36000 + 18000) % of a core x 10 s
            mem = [p for p in s["pressure"] if p["resource"] == "memory"][0]
            self.assertEqual(mem["who"][0]["name"], "big")                              # at the one pressured sample, big held most memory
            self.assertIn("memory", s["verdict"])
            self.assertIn("big", s["verdict"])
            self.assertIn("Only", s["verdict"])                                         # 30 s of data in a 1 h window
            self.assertTrue(all(-3600 <= p["x"] <= 0 for p in s["series"]["cpu"]))

    def test_calm_machine(self):
        with tempfile.TemporaryDirectory() as d:
            make(d, [f"{stamp(m)},5,40,0,0,0,30,0,0,1,1,0,0,0,a,b" for m in (50, 30, 10)], [])
            s = perfstats.summary(d, "1h", NOW, mem_total_gb=32)
            self.assertTrue(s["verdict"].startswith("Nothing was short"))
            self.assertEqual(s["pressure"], [])

    def test_unknown_window_is_a_day_and_results_are_cached(self):
        with tempfile.TemporaryDirectory() as d:
            make(d, [f"{stamp(m)},5,40,0,0,0,30,0,0,1,1,0,0,0,a,b" for m in (50, 10)], [])
            t = [0.0]
            p = perfstats.Perf(d, clock=lambda: t[0], now=lambda: NOW)
            self.assertEqual(p.get("bogus")["window"], "24h")
            first = p.get("24h")
            t[0] = 10
            self.assertIs(p.get("24h"), first)                                          # inside the ttl
            t[0] = 1000
            self.assertIsNot(p.get("24h"), first)

    def test_plain_page_shows_it_escaped(self):
        with tempfile.TemporaryDirectory() as d:
            make(d, [f"{stamp(m)},5,40,0,0,0,30,0,0,1,1,0,0,0,a,b" for m in (50, 10)],
                 [f"{stamp(10)},evil.service,<b>x</b>,50,2,0,0,0,0,0,1"])
            html = render.perf_section(perfstats.summary(d, "24h", NOW, 32))
            self.assertIn("evil", html)
            self.assertNotIn("<b>x</b>", html)
            self.assertIn("&lt;b&gt;", html)
            self.assertIn("No performance data yet", render.perf_section(dict(available=False, label="x")))


if __name__ == "__main__":
    unittest.main()
