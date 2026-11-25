import json, threading, unittest, urllib.error, urllib.request
from http.server import ThreadingHTTPServer
from homepage import render, server

DATA = dict(
    generated="2026-11-07T07:00:00+00:00",
    apps=[dict(name="Demo <b>", path="/demo/", desc="d & e", unit="demo", state="active", version="behind", running_rev="aaaaaaaa", head_rev="bbbbbbbb"),
          dict(name="Plain", path="/p/", desc="", unit="", state="", version="")],
    jobs=[dict(label="Backup", unit="b", result="success", active="inactive", last="Sat 2026-11-07 04:25:28 GMT", next="Sun 2026-11-08 02:30:00 GMT"),
          dict(label="Broken", unit="x", result="exit-code", active="failed", last="", next="")],
    failed=["x.service"], disks=[dict(label="Root", path="/", total=1000 ** 4, used=900 * 1000 ** 3, pct=90)],
    system=dict(uptime_s=90061, load=(0.5, 0.4, 0.3), mem_total_kb=4000000, mem_avail_kb=1000000),
)


class Render(unittest.TestCase):
    def test_page_escapes_and_shows_state(self):
        h = render.page(DATA, "host<x>")
        self.assertNotIn("<b>", h)                       # app names are escaped
        self.assertIn("Demo &lt;b&gt;", h)
        self.assertIn("host&lt;x&gt;", h)
        self.assertIn("code newer: aaaaaaaa", h)
        self.assertIn("Failed units: x.service", h)
        self.assertIn("exit-code", h)
        self.assertIn('class="vhi"', h)                  # 90% disk is flagged
        self.assertIn("up 1d 1h 1m", h)

    def test_empty_page(self):
        h = render.page(dict(generated="", apps=[], jobs=[], failed=[], disks=[], system={}), "h")
        self.assertIn("No apps yet", h)
        self.assertNotIn("<h2>Jobs</h2>", h)

    def test_helpers(self):
        self.assertEqual(render.short_time("Sat 2026-11-07 04:25:28 GMT"), "11-07 04:25")
        self.assertEqual(render.short_time(""), "-")
        self.assertEqual(render.human(1536), "2 KB")


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        st = server.Status("/nonexistent", "/nonexistent", "/nonexistent", runner=lambda c, timeout=5: ("", 1))
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(st, "testhost", dist="/nonexistent"))
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def get(self, path):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d%s" % (self.port, path), timeout=5) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as ex:
            return ex.code, ex.read().decode()

    def test_routes(self):
        self.assertEqual(self.get("/healthz"), (200, "ok\n"))
        code, body = self.get("/")
        self.assertEqual(code, 200)
        self.assertIn("testhost", body)
        code, body = self.get("/_home/api/status")              # the prefix Caddy forwards
        self.assertEqual(code, 200)
        self.assertIn("apps", json.loads(body))
        self.assertEqual(self.get("/nope")[0], 404)


class PerfEndpoint(unittest.TestCase):
    def test_window_param_and_missing_data(self):
        import tempfile
        from homepage import perfstats
        with tempfile.TemporaryDirectory() as d:
            st = server.Status("/nonexistent", "/nonexistent", "/nonexistent", runner=lambda c, timeout=5: ("", 1), hostname="h")
            srv = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(st, "h", dist="/nonexistent", perf=perfstats.Perf(d)))
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            try:
                def get(path):
                    with urllib.request.urlopen("http://127.0.0.1:%d%s" % (srv.server_address[1], path), timeout=5) as r:
                        return json.loads(r.read().decode())
                self.assertEqual(get("/_home/api/perf?window=1h")["window"], "1h")
                self.assertFalse(get("/_home/api/perf?window=7d")["available"])           # empty folder: says so, no error
                self.assertEqual(get("/_home/api/perf?window=../../etc")["window"], "24h")  # unknown values fall back, never reach the disk
                self.assertIn("No performance data yet", urllib.request.urlopen("http://127.0.0.1:%d/_home/plain" % srv.server_address[1]).read().decode())
            finally:
                srv.shutdown()


class Static(unittest.TestCase):
    """The built front end: files come only from the dist/ listing, never from a path in the request."""

    def test_serves_dist_and_plain_fallback(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "index.html"), "w").write("<!doctype html>spa")
            open(os.path.join(d, "app.js"), "w").write("console.log(1)")
            st = server.Status("/nonexistent", "/nonexistent", "/nonexistent", runner=lambda c, timeout=5: ("", 1), hostname="h")
            srv = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(st, "h", dist=d))
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            try:
                def get(path):
                    try:
                        with urllib.request.urlopen("http://127.0.0.1:%d%s" % (srv.server_address[1], path), timeout=5) as r:
                            return r.status, r.headers.get("Content-Type"), r.read().decode()
                    except urllib.error.HTTPError as ex:
                        return ex.code, None, ""
                self.assertEqual(get("/_home/")[2], "<!doctype html>spa")
                code, ctype, body = get("/_home/app.js")
                self.assertEqual((code, body), (200, "console.log(1)"))
                self.assertIn("javascript", ctype)
                self.assertIn("h", get("/_home/plain")[2])                      # server-rendered page still there
                self.assertEqual(get("/_home/../server.py")[0], 404)
                self.assertEqual(get("/_home/index.html")[0], 404)              # only "/" serves it
                data = json.loads(get("/_home/api/status")[2])
                self.assertEqual(data["hostname"], "h")
                self.assertIn("finding", data)
            finally:
                srv.shutdown()


if __name__ == "__main__":
    unittest.main()
