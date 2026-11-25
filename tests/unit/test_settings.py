from pathlib import Path

import pytest
from strata_python.testing import run_cli

from homepage import cli, settings


def test_defaults_are_generic():
    assert settings.SETTINGS.get_list("jobs") == []
    assert settings.SETTINGS.get_list("disks") == ["Root | /"]


def test_pair_normalises_and_refuses():
    assert settings.pair("  Backup|nightly-backup ") == "Backup | nightly-backup"
    assert settings.split_pair("Backup | nightly-backup") == ("Backup", "nightly-backup")
    for bad in ("no separator", "| unit", "Label |"):
        with pytest.raises(ValueError, match="Label"):
            settings.pair(bad)


def test_disk_path_must_be_absolute(tmp_path: Path):
    assert settings.disk_entry(f"Data | {tmp_path}") == f"Data | {tmp_path}"
    with pytest.raises(ValueError, match="absolute"):
        settings.disk_entry("Data | relative/dir")


def test_jobs_and_disks_come_from_the_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("HOMEPAGE_JOBS", "Backup | nightly-backup; Sync | work-sync")
    monkeypatch.setenv("HOMEPAGE_DISKS", f"Root | /; Data | {tmp_path}")
    assert settings.SETTINGS.get_list("jobs") == ["Backup | nightly-backup", "Sync | work-sync"]
    assert [settings.split_pair(e)[0] for e in settings.SETTINGS.get_list("disks")] == ["Root", "Data"]


def test_the_plain_page_shows_a_configured_job_and_disk(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("HOMEPAGE_SITES", str(tmp_path))
    monkeypatch.setenv("HOMEPAGE_DISKS", "Everything | /")
    out = run_cli(cli.main, "print")
    assert "Everything" in out.stdout
