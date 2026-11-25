"""The login service, run as a real process with a temporary config (never the real one): bin/webauth is the one file
that must not break, because it is the login in front of every app."""

import http.client
import importlib.machinery
import importlib.util
import json
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "bin" / "webauth"


def load_script() -> ModuleType:
    loader = importlib.machinery.SourceFileLoader("webauth_script", str(SCRIPT))
    spec = importlib.util.spec_from_loader("webauth_script", loader)
    assert spec
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def free_port() -> int:
    with closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def serve(conf: Path, port: int) -> Iterator[None]:
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), "serve", "--port", str(port)],
        env={"WEBAUTH_CONF": str(conf), "PATH": ""},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.05)
        yield
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def request(port: int, method: str, path: str, body: str = "", cookie: str = "") -> tuple[int, str, list[str]]:
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if cookie:
        headers["Cookie"] = cookie
    c.request(method, path, body=body or None, headers=headers)
    r = c.getresponse()
    text = r.read().decode()
    return r.status, text, [v for k, v in r.getheaders() if k == "Set-Cookie"]


def write_conf(tmp_path: Path, **extra: str) -> Path:
    conf = tmp_path / "auth.json"
    conf.write_text(json.dumps({"password_hash": load_script().hash_password("pw"), "secret": "ab" * 32, **extra}))
    return conf


@pytest.fixture
def port() -> int:
    return free_port()


def test_login_flow_with_the_generic_defaults(tmp_path: Path, port: int):
    for _ in serve(write_conf(tmp_path), port):
        status, page, _ = request(port, "GET", "/auth/login")
        assert status == 200
        assert "<h1>webauth</h1>" in page
        assert request(port, "GET", "/auth/check")[0] == 303
        status, _, cookies = request(port, "POST", "/auth/login", "password=pw&next=%2F")
        assert status == 303
        assert cookies[0].startswith("webauth_auth=")
        assert request(port, "GET", "/auth/check", cookie=cookies[0].split(";")[0])[0] == 200


def test_name_and_cookie_come_from_the_config(tmp_path: Path, port: int):
    for _ in serve(write_conf(tmp_path, name="my <host>", cookie="my_auth"), port):
        _, page, _ = request(port, "GET", "/auth/login")
        assert "<h1>my &lt;host&gt;</h1>" in page
        _, _, cookies = request(port, "POST", "/auth/login", "password=pw&next=%2F")
        assert cookies[0].startswith("my_auth=")
        assert request(port, "GET", "/auth/check", cookie=cookies[0].split(";")[0])[0] == 200


def test_a_bad_cookie_name_falls_back_instead_of_breaking_the_header(tmp_path: Path, port: int):
    for _ in serve(write_conf(tmp_path, cookie="bad name;x"), port):
        _, _, cookies = request(port, "POST", "/auth/login", "password=pw&next=%2F")
        assert cookies[0].startswith("webauth_auth=")


def test_a_wrong_password_is_refused(tmp_path: Path, port: int):
    for _ in serve(write_conf(tmp_path), port):
        assert request(port, "POST", "/auth/login", "password=nope&next=%2F")[0] == 401
