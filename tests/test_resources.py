import os, tempfile, unittest
from homepage import render, resources


def make_proc(root, cpu, procs, avail_kb=2000000):
    """cpu: (busy, idle) ticks; procs: {pid: (name, ticks, rss_pages)}."""
    open(os.path.join(root, "stat"), "w").write(f"cpu  {cpu[0]} 0 0 {cpu[1]} 0 0 0 0 0 0\ncpu0 1 0 0 1 0 0 0 0 0 0\ncpu1 1 0 0 1 0 0 0 0 0 0\n")
    open(os.path.join(root, "meminfo"), "w").write(f"MemTotal: 4000000 kB\nMemAvailable: {avail_kb} kB\nSwapTotal: 100 kB\nSwapFree: 100 kB\n")
    for pid, (name, ticks, rss) in procs.items():
        os.makedirs(os.path.join(root, str(pid)), exist_ok=True)
        # fields after ")" : state + 10 more up to utime(14) stime(15) ... rss is field 24
        f = ["S"] + ["0"] * 10 + [str(ticks), "0"] + ["0"] * 8 + [str(rss)] + ["0"] * 5
        open(os.path.join(root, str(pid), "stat"), "w").write(f"{pid} ({name}) " + " ".join(f))


class Sampling(unittest.TestCase):
    def test_cpu_mem_and_top(self):
        with tempfile.TemporaryDirectory() as d:
            t = [0.0]
            s = resources.Sampler(proc=d, interval=5, keep=3, top=2, clock=lambda: t[0])
            make_proc(d, (100, 900), {1: ("a b)(c", 0, 10), 2: ("idle", 0, 500), 3: ("big", 0, 9000)})
            s.sample()
            self.assertEqual(s.snapshot()["cpu"], [])                      # needs two samples
            t[0] = 5
            make_proc(d, (200, 1800), {1: ("a b)(c", 250, 10), 2: ("idle", 0, 500), 3: ("big", 0, 9000)}, avail_kb=1000000)
            s.sample()
            snap = s.snapshot()
            self.assertEqual(snap["cpu"], [10.0])                           # 100 busy of 1000 ticks
            self.assertEqual(snap["mem"][-1], 75.0)
            self.assertEqual(snap["ncpu"], 2)
            self.assertEqual(snap["top_cpu"][0]["name"], "a b)(c")          # odd names parse
            self.assertEqual(snap["top_cpu"][0]["cpu"], round(100 * 250 / resources.CLK_TCK / 5, 1))
            self.assertEqual(snap["top_mem"][0]["name"], "big")
            self.assertEqual(len(snap["top_cpu"]), 2)
            for i in range(5):
                t[0] += 5; make_proc(d, (200 + i, 1800 + 10 * i), {}); s.sample()
            self.assertEqual(len(s.snapshot()["cpu"]), 3)                   # rolling window

    def test_missing_proc_does_not_raise(self):
        s = resources.Sampler(proc="/nonexistent")
        s.sample()
        self.assertEqual(s.snapshot()["cpu"], [])


class Render(unittest.TestCase):
    def test_section(self):
        r = dict(interval=5, ncpu=4, cpu=[10, 95, 50], mem=[40, 41, 42], mem_total_kb=4000000, mem_avail_kb=2000000,
                 swap_total_kb=0, swap_free_kb=0,
                 top_cpu=[dict(pid=1, name="<script>", cpu=12.0, rss=2048)], top_mem=[])
        h = render.resources_section(r)
        self.assertNotIn("<script>", h)
        self.assertIn("&lt;script&gt;", h)
        self.assertIn("<polyline", h)
        self.assertIn("CPU · 4 cores", h)
        self.assertIn("10 s ago", h)

    def test_flags_and_empty(self):
        self.assertIn("spark vhi", render.sparkline([1, 95], "x"))
        self.assertIn("collecting", render.sparkline([1], "x"))
        self.assertEqual(render.resources_section(None), "")


if __name__ == "__main__":
    unittest.main()
