"""Read the app list from the Caddy snippets (one `sites/*.caddy` per app).

Each snippet describes itself with comment lines at the top:
    # app: Name | /path/ | one-line description      (required)
    # unit: systemd-user-unit-name                   (optional: shows up/down)
    # repo: directory name under ~/code/github       (optional: shows running vs checked-out code)
"""

import glob
import os

AppInfo = dict[str, str]


def parse_snippet(text: str) -> AppInfo | None:
    """Return a dict (name, path, desc, unit, repo) or None if the text has no `# app:` line."""
    info: AppInfo = {"unit": "", "repo": ""}
    found = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("# app:") and not found:
            parts = [p.strip() for p in line[len("# app:") :].split("|")]
            if len(parts) >= 2 and parts[0] and parts[1]:
                info.update(name=parts[0], path=parts[1], desc=parts[2] if len(parts) > 2 else "")
                found = True
        elif line.startswith("# unit:"):
            info["unit"] = line[len("# unit:") :].strip()
        elif line.startswith("# repo:"):
            info["repo"] = line[len("# repo:") :].strip()
    return info if found else None


def load_apps(sites_dir: str) -> list[AppInfo]:
    apps: list[AppInfo] = []
    for f in sorted(glob.glob(os.path.join(sites_dir, "*.caddy"))):
        try:
            with open(f, encoding="utf-8") as fh:
                info = parse_snippet(fh.read())
        except OSError:
            continue
        if info:
            info["file"] = os.path.basename(f)
            apps.append(info)
    return sorted(apps, key=lambda a: a["name"].lower())
