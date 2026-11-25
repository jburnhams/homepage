"""The HTTP side, on strata-python's `web`: FastAPI on 127.0.0.1 (the page at /, JSON at /api/status). Caddy puts the
login in front of it.

Caddy forwards `/_home/*` as well as `/`, without stripping the prefix, so `StripPrefix` takes it off before routing
(the JSON stays at `/_home/api/status`, which the front end and the plain page link to). `add_web` serves the built
front end in `web/dist` (committed, so the machine needs no Node), with `index.html` at every path no route here
answers. Without a build `/` is the server-rendered page, as is `/plain` always (no JavaScript, refreshes itself)."""

import os
import threading
import time
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from strata_python import web

from . import __version__, collect, perfstats, render, resources, snippets
from .settings import SETTINGS

WEB_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "web", "dist")
PREFIX = "/_home"  # Caddy forwards /_home/* as well as /, the prefix is stripped here

Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]


class StripPrefix:
    """ASGI middleware: a request for `/_home/x` is routed as `/x`, and `/_home` as `/`."""

    def __init__(self, app: Callable[[Scope, Receive, Send], Awaitable[None]], prefix: str = PREFIX) -> None:
        self.app, self.prefix = app, prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            path: str = scope["path"]
            if path == self.prefix or path.startswith(self.prefix + "/"):
                stripped = path[len(self.prefix) :] or "/"
                scope = dict(scope, path=stripped, raw_path=stripped.encode())
        await self.app(scope, receive, send)


class Status:
    """Collect at most every `ttl` seconds, whatever the number of viewers."""

    def __init__(
        self,
        sites: str,
        state: str,
        repos: str,
        runner: collect.Runner = collect.run,
        ttl: float = 10,
        sampler: resources.Sampler | None = None,
        hostname: str = "",
    ) -> None:
        self.sites, self.state, self.repos, self.runner, self.ttl = sites, state, repos, runner, ttl
        self.sampler, self.hostname = sampler, hostname
        self._lock = threading.Lock()
        self._at = 0.0
        self._data: collect.Data | None = None

    def get(self) -> collect.Data:
        with self._lock:
            if self._data is None or time.monotonic() - self._at > self.ttl:
                apps = snippets.load_apps(self.sites)
                self._data = collect.collect(apps, self.state, self.repos, self.runner)
                self._at = time.monotonic()
            data = self._data
        # live numbers are never cached: the sampler already rate-limits itself
        data = dict(data, hostname=self.hostname)
        if self.sampler:
            data["resources"] = self.sampler.snapshot()
        data["finding"] = render.finding(data)  # one definition, shared by the page and the JSON
        return data


def create_app(status: Status, hostname: str, dist: str = WEB_DIST, perf: perfstats.Perf | None = None) -> FastAPI:
    commit = web.source_commit(__file__)
    app = web.base_app("homepage", __version__, SETTINGS, commit=commit)
    web.add_error_handlers(app)
    web.add_system(
        app,
        __version__,
        commit=commit,
        folders={"sites": lambda: status.sites, "state": lambda: status.state, "repos": lambda: status.repos},
    )

    @app.middleware("http")
    async def no_store(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:  # pyright: ignore[reportUnusedFunction]
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"  # a status board is never worth a stale copy
        return response

    @app.get("/healthz", response_class=PlainTextResponse, include_in_schema=False)
    def healthz() -> str:  # pyright: ignore[reportUnusedFunction]
        return "ok\n"

    @app.get("/api/status")
    def get_status() -> collect.Data:  # pyright: ignore[reportUnusedFunction]
        return status.get()

    @app.get("/api/perf")
    def get_perf(window: str = "24h") -> perfstats.Summary:  # pyright: ignore[reportUnusedFunction]
        """1h, 24h or 7d, from the files perf-sample writes; anything else is 24h, and no files says so."""
        if perf is None:
            return {"available": False, "window": "24h", "label": ""}
        return perf.get(window)

    @app.get("/plain", response_class=HTMLResponse, include_in_schema=False)
    def plain() -> str:  # pyright: ignore[reportUnusedFunction]
        return render.page(status.get(), hostname, perf=perf.get("24h") if perf else None)

    if not os.path.isfile(os.path.join(dist, "index.html")):  # no build: the server-rendered page is the page
        app.add_api_route("/", plain, response_class=HTMLResponse, include_in_schema=False)
    web.add_web(app, dist)
    app.add_middleware(StripPrefix)
    return app
