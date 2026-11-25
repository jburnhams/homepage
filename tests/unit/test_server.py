"""The server over real HTTP (uvicorn on a free loopback port), through the prefix Caddy forwards."""

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path

from fastapi import FastAPI

from homepage import collect, perfstats, server

LiveApp = Callable[[FastAPI], AbstractContextManager[str]]


def silent(cmd: list[str], timeout: float = 5) -> tuple[str, int]:
    return "", 1  # systemctl and git answer nothing, like a machine with no units


def get(base: str, path: str) -> tuple[int, str, str]:
    try:
        with urllib.request.urlopen(base + path, timeout=5) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read().decode()
    except urllib.error.HTTPError as ex:
        return ex.code, ex.headers.get("Content-Type", ""), ex.read().decode()


def make(tmp_path: Path, dist: str, runner: collect.Runner = silent, perf: perfstats.Perf | None = None) -> FastAPI:
    st = server.Status(str(tmp_path), str(tmp_path), str(tmp_path), runner=runner, hostname="testhost")
    return server.create_app(st, "testhost", dist=dist, perf=perf)


def test_without_a_build_the_page_is_server_rendered(tmp_path: Path, live_app: LiveApp):
    with live_app(make(tmp_path, str(tmp_path / "no-dist"))) as base:
        assert get(base, "/healthz")[::2] == (200, "ok\n")
        code, _, body = get(base, "/")
        assert (code, "testhost" in body) == (200, True)
        assert "testhost" in get(base, "/plain")[2]
        status, _, body = get(base, "/_home/api/status")  # the prefix Caddy forwards
        assert status == 200
        assert "apps" in json.loads(body)


def test_with_a_build_files_come_only_from_dist(tmp_path: Path, live_app: LiveApp):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><head></head>spa")
    (dist / "app.js").write_text("console.log(1)")
    secret = tmp_path / "secret.txt"
    secret.write_text("nope")
    with live_app(make(tmp_path, str(dist))) as base:
        assert "spa" in get(base, "/_home/")[2]
        code, ctype, body = get(base, "/_home/app.js")
        assert (code, body) == (200, "console.log(1)")
        assert "javascript" in ctype
        assert "testhost" in get(base, "/_home/plain")[2]  # the server-rendered page is still there
        assert "nope" not in get(base, "/_home/..%2fsecret.txt")[2]
        assert "nope" not in get(base, "/_home/%2e%2e/secret.txt")[2]
        data = json.loads(get(base, "/_home/api/status")[2])
        assert data["hostname"] == "testhost"
        assert "finding" in data


def test_responses_are_never_cached(tmp_path: Path, live_app: LiveApp):
    with live_app(make(tmp_path, str(tmp_path / "no-dist"))) as base, urllib.request.urlopen(base + "/healthz") as r:
        assert r.headers["Cache-Control"] == "no-store"


def test_unknown_api_path_is_a_404_not_the_page(tmp_path: Path, live_app: LiveApp):
    with live_app(make(tmp_path, str(tmp_path / "no-dist"))) as base:
        assert get(base, "/api/nope")[0] == 404
        assert get(base, "/_home/api/nope")[0] == 404


def test_health_system_and_settings_come_from_strata_python(tmp_path: Path, live_app: LiveApp):
    with live_app(make(tmp_path, str(tmp_path / "no-dist"))) as base:
        health = json.loads(get(base, "/_home/api/health")[2])
        assert health["ok"] is True
        system = json.loads(get(base, "/_home/api/system")[2])
        assert {f["name"] for f in system["folders"]} == {"sites", "state", "repos"}
        assert set(json.loads(get(base, "/_home/api/settings")[2])) == {
            "sites",
            "state",
            "repos",
            "jobs",
            "disks",
            "perf",
        }


def test_perf_window_param_and_missing_data(tmp_path: Path, live_app: LiveApp):
    empty = tmp_path / "perf"
    empty.mkdir()
    app = make(tmp_path, str(tmp_path / "no-dist"), perf=perfstats.Perf(str(empty)))
    with live_app(app) as base:
        assert json.loads(get(base, "/_home/api/perf?window=1h")[2])["window"] == "1h"
        assert not json.loads(get(base, "/_home/api/perf?window=7d")[2])["available"]  # empty folder: says so
        assert json.loads(get(base, "/_home/api/perf?window=../../etc")[2])["window"] == "24h"  # never reaches the disk
        assert "No performance data yet" in get(base, "/_home/plain")[2]


def test_perf_without_a_sampler_says_so(tmp_path: Path, live_app: LiveApp):
    with live_app(make(tmp_path, str(tmp_path / "no-dist"))) as base:
        assert not json.loads(get(base, "/_home/api/perf")[2])["available"]


def test_status_is_collected_at_most_every_ttl(tmp_path: Path):
    calls: list[list[str]] = []

    def counting(cmd: list[str], timeout: float = 5) -> tuple[str, int]:
        calls.append(cmd)
        return "", 1

    st = server.Status(str(tmp_path), str(tmp_path), str(tmp_path), runner=counting, ttl=3600)
    st.get()
    n = len(calls)
    assert n > 0
    st.get()
    assert len(calls) == n


def test_strip_prefix_only_takes_a_whole_path_segment():
    seen: list[str] = []

    async def inner(scope: dict[str, object], receive: object, send: object) -> None:
        seen.append(str(scope["path"]))

    import asyncio

    mw = server.StripPrefix(inner)  # pyright: ignore[reportArgumentType]

    async def go() -> None:
        for path in ("/_home", "/_home/x", "/_homework", "/other"):
            await mw({"type": "http", "path": path}, None, None)  # pyright: ignore[reportArgumentType]

    asyncio.run(go())
    assert seen == ["/", "/x", "/_homework", "/other"]
