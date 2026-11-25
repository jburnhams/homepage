"""Where the page reads its data from. strata-python's `Settings`: `~/.homepage/settings.json`, each key also an
environment variable (`HOMEPAGE_SITES`, `HOMEPAGE_STATE`, `HOMEPAGE_REPOS`), `homepage set KEY VALUE` and the
`/api/settings` routes. These were the `--sites`, `--state` and `--repos` flags of `serve` and `print`."""

import os

from strata_python.settings import Setting, Settings, absolute_path

HOME = os.path.expanduser("~")

SETTINGS = Settings(
    "homepage",
    [
        Setting("sites", default=lambda: os.path.join(HOME, ".config/caddy/sites"), normalise=absolute_path),
        Setting("state", default=lambda: os.path.join(HOME, ".local/state/app-refresh"), normalise=absolute_path),
        Setting("repos", default=lambda: os.path.join(HOME, "code/github"), normalise=absolute_path),
    ],
)
