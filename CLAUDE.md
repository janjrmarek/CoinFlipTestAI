# CLAUDE.md

See README.md for:
- Project Goals and Overview (`Overview`)
- Application Domain description (`Application domain`: game rules, time limit, input checks)
- Architecture and Design (`Architecture and design`)
- CLI Workflows (`CLI workflows`: run the app, run the tests)

See docs/WORKITEMS.md for active backlog and work items (not created yet).

## Tooling
- **Environment**: Python 3.13+, Flask
- **Setup**: `pip install flask`. Planned: uv with a `pyproject.toml` so `uv sync` works (not set up yet).
- **Run**: `python coin_toss.py`, then open http://127.0.0.1:5000
- **Tests**: `python -m unittest discover -s tests` (pytest can also run them once installed)
- **Issue tracking**: Github
- **Windows note**: on this machine `python` may resolve to the Microsoft Store alias;
  use `C:\Users\John\AppData\Local\Programs\Python\Python313\python.exe` if it does.

## Conventions
- The time limit and all input checks are enforced on the server; browser checks are a convenience.
- A page refresh restarts the clock. `/flip` sets `session["after_flip"]` so its redirect to `/`
  keeps the clock; never make the page reload itself (e.g. at 0:00), as that would reset it.
- In tests, a `GET /` right after a flip is the redirect; a second `GET /` is a refresh.
- Every behaviour change comes with tests in `tests/test_coin_toss.py` and matching README updates.
- In tests, fake the clock by patching `coin_toss.time` (not `time.time`, which breaks Flask's
  session cookie signing) and force flip outcomes by patching `coin_toss.random.random`.
