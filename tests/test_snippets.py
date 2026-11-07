import os, tempfile, unittest
from homepage import snippets


class Snippets(unittest.TestCase):
    def test_parse_full(self):
        t = "# app: Demo | /demo/ | A demo app\n# unit: demo\n# repo: demo-repo\nhandle_path /demo/* { }\n"
        self.assertEqual(snippets.parse_snippet(t), dict(name="Demo", path="/demo/", desc="A demo app", unit="demo", repo="demo-repo"))

    def test_parse_minimal_and_missing(self):
        self.assertEqual(snippets.parse_snippet("# app: X | /x/\n")["desc"], "")
        self.assertIsNone(snippets.parse_snippet("# nothing here\n"))
        self.assertIsNone(snippets.parse_snippet("# app: | |\n"))

    def test_load_sorted_and_skips_bad(self):
        with tempfile.TemporaryDirectory() as d:
            for n, t in (("b.caddy", "# app: beta | /b/ | b\n"), ("a.caddy", "# app: Alpha | /a/ | a\n"), ("c.caddy", "no app line\n"), ("d.txt", "# app: Z | /z/\n")):
                open(os.path.join(d, n), "w").write(t)
            self.assertEqual([a["name"] for a in snippets.load_apps(d)], ["Alpha", "beta"])


if __name__ == "__main__":
    unittest.main()
