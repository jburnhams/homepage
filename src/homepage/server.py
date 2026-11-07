"""Tiny HTTP server (stdlib only) on 127.0.0.1: the page at /, JSON at /api/status. Caddy puts the login in front of it."""
import argparse
import json
import os
import mimetypes
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import collect, render, resources, snippets

HOME = os.path.expanduser("~")
DEFAULTS = dict(
    sites=os.path.join(HOME, ".config/caddy/sites"),
    state=os.path.join(HOME, ".local/state/app-refresh"),
    repos=os.path.join(HOME, "code/github"),
)
WEB_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "web", "dist")
PREFIX = "/_home"          # Caddy forwards /_home/* as well as /, the prefix is stripped here


class Status:
    """Collect at most every `ttl` seconds, whatever the number of viewers."""

    def __init__(self, sites, state, repos, runner=collect.run, ttl=10, sampler=None, hostname=""):
        self.sites, self.state, self.repos, self.runner, self.ttl = sites, state, repos, runner, ttl
        self.sampler, self.hostname = sampler, hostname
        self._lock, self._at, self._data = threading.Lock(), 0.0, None

    def get(self):
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
        data["finding"] = render.finding(data)          # one definition, shared by the page and the JSON
        return data


def make_handler(status, hostname, dist=WEB_DIST):
    assets = {}
    if os.path.isdir(dist):          # the built front end, committed in web/dist; absent -> server-rendered page
        assets = {n: os.path.join(dist, n) for n in os.listdir(dist) if os.path.isfile(os.path.join(dist, n))}

    class H(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):      # journal gets one line per request
            print("%s %s" % (self.address_string(), fmt % args), flush=True)

        def _send(self, code, body, ctype):
            b = body if isinstance(body, bytes) else body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path.startswith(PREFIX):
                path = path[len(PREFIX):] or "/"
            try:
                if path == "/healthz":
                    self._send(200, "ok\n", "text/plain; charset=utf-8")
                elif path == "/" and "index.html" in assets:
                    self._send(200, open(assets["index.html"], "rb").read(), "text/html; charset=utf-8")
                elif path in ("/", "/plain"):       # no JavaScript needed, refreshes itself
                    self._send(200, render.page(status.get(), hostname), "text/html; charset=utf-8")
                elif path.startswith("/") and path[1:] in assets and path[1:] != "index.html":
                    name = path[1:]                  # only names listed in dist/, never a path from the request
                    ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
                    self._send(200, open(assets[name], "rb").read(), ctype + "; charset=utf-8" if ctype.startswith("text/") or ctype.endswith("javascript") else ctype)
                elif path == "/api/status":
                    self._send(200, json.dumps(status.get(), indent=1, default=str), "application/json")
                else:
                    self._send(404, "not found\n", "text/plain; charset=utf-8")
            except Exception as ex:             # never kill the server over one request
                self._send(500, "error: %s\n" % ex, "text/plain; charset=utf-8")
    return H


def main(argv=None):
    p = argparse.ArgumentParser(prog="homepage")
    p.add_argument("command", choices=["serve", "print"], help="serve: HTTP server; print: the page to stdout")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8365)
    for k, v in DEFAULTS.items():
        p.add_argument("--" + k, default=v)
    a = p.parse_args(argv)
    sampler = resources.Sampler()
    if a.command == "serve":
        sampler.start()
    else:
        sampler.sample()
    host = socket.gethostname()
    st = Status(a.sites, a.state, a.repos, sampler=sampler, hostname=host)
    if a.command == "print":
        print(render.page(st.get(), host))
        return 0
    srv = ThreadingHTTPServer((a.host, a.port), make_handler(st, host))
    print("homepage on http://%s:%d" % (a.host, a.port), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0
