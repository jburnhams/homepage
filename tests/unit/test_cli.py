import json
from pathlib import Path

import pytest
from strata_python.testing import run_cli, run_module

from homepage import cli


def test_doctor_reports_what_the_page_needs():
    out = run_cli(cli.main, "doctor", check=False)
    assert "fastapi" in out.stdout
    assert "systemctl" in out.stdout


def test_set_writes_the_settings_file_and_the_page_reads_it(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("HOMEPAGE_HOME", str(tmp_path))
    sites = tmp_path / "sites"
    run_cli(cli.main, "set", "sites", str(sites))
    saved = json.loads((tmp_path / "settings.json").read_text())
    assert saved["sites"] == str(sites)


def test_print_shows_the_plain_page(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    (tmp_path / "x.caddy").write_text("# app: Shown App | /shown/ | here\n")
    monkeypatch.setenv("HOMEPAGE_SITES", str(tmp_path))
    out = run_cli(cli.main, "print")
    assert "Shown App" in out.stdout
    assert out.stdout.startswith("<!doctype html>")


def test_the_module_runs_as_a_process():
    out = run_module("homepage", "doctor", check=False)
    assert "homepage" in out.stdout
