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
- The two outcomes are `"heads"`/`"tails"` internally (session keys, `side` form values); only
  the display text is "TTTQ Breakout Win"/"TTTQ Breakout Fail", via `OUTCOME_LABELS`. Don't rename
  the internal keys without a good reason — it'd touch session data, routes, and every test.
- A bet is a percentage (`bet_pct`) of the *current* balance, computed fresh on every flip, not a
  stored dollar amount — so the stake compounds as the balance changes and there's no "exceeds
  balance" check to maintain (any 0–100% is always affordable). Round with `ROUND_HALF_UP`.
- The time limit, the game settings, and all input checks are enforced on the server; browser
  checks (`required`, `min`/`max`) are a convenience only.
- The time limit and heads odds are read from the form on the first flip only (`is_first_flip =
  "started_at" not in session`) and then locked into the session; later flips ignore those fields.
- A page refresh starts a brand new game: `/flip` sets `session["after_flip"]` so its own redirect
  to `/` keeps state, and any other `GET /` clears the whole session. Never make the page reload
  itself (e.g. at 0:00), as that would wipe the game instead of just showing it's over.
- In tests, a `GET /` right after a flip is that redirect; a second `GET /` in a row is a refresh
  and resets everything, including any state set directly via `session_transaction()` — build test
  state through real POSTs (with mocked `random.random`), not by poking the session then loading `/`.
- Every behaviour change comes with tests in `tests/test_coin_toss.py` and matching README updates.
- In tests, fake the clock by patching `coin_toss.time` (not `time.time`, which breaks Flask's
  session cookie signing) and force flip outcomes by patching `coin_toss.random.random`.
