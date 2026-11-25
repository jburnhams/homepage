from pathlib import Path

from homepage import snippets


def test_parse_full():
    t = "# app: Demo | /demo/ | A demo app\n# unit: demo\n# repo: demo-repo\nhandle_path /demo/* { }\n"
    assert snippets.parse_snippet(t) == {
        "name": "Demo",
        "path": "/demo/",
        "desc": "A demo app",
        "unit": "demo",
        "repo": "demo-repo",
    }


def test_parse_minimal_and_missing():
    info = snippets.parse_snippet("# app: X | /x/\n")
    assert info is not None
    assert info["desc"] == ""
    assert snippets.parse_snippet("# nothing here\n") is None
    assert snippets.parse_snippet("# app: | |\n") is None


def test_load_sorted_and_skips_bad(tmp_path: Path):
    for n, t in (
        ("b.caddy", "# app: beta | /b/ | b\n"),
        ("a.caddy", "# app: Alpha | /a/ | a\n"),
        ("c.caddy", "no app line\n"),
        ("d.txt", "# app: Z | /z/\n"),
    ):
        (tmp_path / n).write_text(t)
    assert [a["name"] for a in snippets.load_apps(str(tmp_path))] == ["Alpha", "beta"]
