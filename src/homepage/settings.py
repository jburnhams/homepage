"""Where the page reads its data from. strata-python's `Settings`: `~/.homepage/settings.json`, each key also an
environment variable (`HOMEPAGE_SITES`, `HOMEPAGE_STATE`, `HOMEPAGE_REPOS`, `HOMEPAGE_PERF`), `homepage set KEY VALUE` and the
`/api/settings` routes. These were the `--sites`, `--state`, `--repos` and `--perf` flags of `serve` and `print`.

Everything that is about one machine is a setting, never code: where the data is, which systemd units count as nightly jobs
and which disks to show. `jobs` and `disks` are lists of `Label | value` entries (the same shape as the Caddy snippets'
`# app:` line), `;`-separated in the environment. The defaults are generic: no jobs, and the root disk."""

import os

from strata_python.settings import ListSetting, Setting, Settings, absolute_path

HOME = os.path.expanduser("~")


def pair(value: str) -> str:
    """Normaliser for a `Label | value` entry; the spelling stored is `Label | value`."""
    label, sep, rest = value.partition("|")
    if not sep or not label.strip() or not rest.strip():
        raise ValueError("must look like `Label | value`")
    return f"{label.strip()} | {rest.strip()}"


def split_pair(entry: str) -> tuple[str, str]:
    """`Label | value` -> (label, value), for an entry `pair` accepted."""
    label, _, rest = entry.partition("|")
    return label.strip(), rest.strip()


def disk_entry(value: str) -> str:
    """`Label | /absolute/path`, the path with `~` expanded."""
    label, path = split_pair(pair(value))
    return f"{label} | {absolute_path(path)}"


SETTINGS = Settings(
    "homepage",
    [
        Setting("sites", default=lambda: os.path.join(HOME, ".config/caddy/sites"), normalise=absolute_path),
        Setting("state", default=lambda: os.path.join(HOME, ".local/state/app-refresh"), normalise=absolute_path),
        Setting("repos", default=lambda: os.path.join(HOME, "code/github"), normalise=absolute_path),
        # written by perf-sample; absent -> the page says there is no history yet
        # `Label | systemd-user-unit`, one per job whose `<unit>.service` and `.timer` are shown (units that do not exist are skipped)
        ListSetting("jobs", default=[], item=pair, sep=";"),
        # `Label | /path`; a path other than `/` is shown only while it is a mount point
        ListSetting("disks", default=["Root | /"], item=disk_entry, sep=";"),
        Setting("perf", default=lambda: os.path.join(HOME, ".local/share/perf-stats"), normalise=absolute_path),
    ],
)
