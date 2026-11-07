# homepage: notes for agents

- Standard library only, Python 3.9+. Keep it that way: it sits behind the login of every app and `webauth` guards everything, so fewer dependencies is better.
- `src/homepage/`: `snippets.py` (read the Caddy snippets), `collect.py` (all external calls go through the injectable `run`), `render.py` (HTML), `server.py` (HTTP). Tests in `tests/` fake `run`, no systemd needed: `PYTHONPATH=src python3 -m unittest discover -s tests`.
- Escape everything that reaches the HTML (`render.e`); a test checks it. Never pass request data to a command.
- The page is server-rendered with no JavaScript on purpose. Colours come from CSS variables with a dark-mode block; layout works at phone width.
- `bin/webauth` is the login and the one file that must never be left broken: test it by hand (`curl` the login page and `/auth/check`) after any change, and note that a bad commit here can lock you out of every app.
- Machine specifics (ports, which apps, passwords) do not belong here: they are in the dotfiles repo.
