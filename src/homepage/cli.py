"""`homepage doctor | set | serve | print`, on strata-python's `cli`."""

import argparse
import socket
import sys
from collections.abc import Sequence

from strata_python import cli, web

from . import __version__, render, resources
from .server import Status, create_app
from .settings import SETTINGS

PORT = 8365


def _status(*, live: bool) -> tuple[Status, str]:
    sampler = resources.Sampler()
    if live:
        sampler.start()
    else:
        sampler.sample()
    host = socket.gethostname()
    status = Status(SETTINGS.get("sites"), SETTINGS.get("state"), SETTINGS.get("repos"), sampler=sampler, hostname=host)
    return status, host


def _serve(host: str, port: int) -> None:
    status, hostname = _status(live=True)
    web.serve(create_app(status, hostname), ["--host", host, "--port", str(port)], default_port=PORT)


def _print(_args: argparse.Namespace) -> int:
    status, hostname = _status(live=False)
    sys.stdout.write(render.page(status.get(), hostname) + "\n")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="homepage")
    sub = parser.add_subparsers(dest="cmd", required=True)
    cli.add_doctor(
        sub,
        "homepage",
        __version__,
        ("fastapi", "uvicorn"),
        checks=[
            cli.Check("systemctl", cli.program("systemctl", "the page reads systemd user units")),
            cli.Check("git", cli.program("git", "needed to compare running and checked-out code")),
        ],
    )
    cli.add_set(sub, SETTINGS)
    cli.add_serve(sub, _serve, default_port=PORT)
    sub.add_parser("print", help="the plain page on stdout").set_defaults(fn=_print)
    args = parser.parse_args(argv)
    return int(args.fn(args))
