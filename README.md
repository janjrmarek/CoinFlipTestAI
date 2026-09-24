# CoinFlipTestAI

## Overview

A small Flask web app for betting on a biased coin against the clock. Before your
first flip you choose the time limit and the coin's odds; every bet after that pays
even money. The goal is to finish with as much money as you can before time runs out.

## Application domain

- **Starting balance of $25.** Your balance, time left, total flips, heads, tails, and
  heads % are shown at the top of the page.
- **Game settings, set once.** Before the first flip, choose the **time limit**
  (1–60 whole minutes, default 5) and the **heads probability** (1–99 whole percent,
  default 60). Both are required to flip. Once the first flip is accepted they lock in
  for the rest of the game: the inputs are replaced with a line showing what's in play,
  and later flips ignore any different values sent to the server.
- **Flipping.** Enter a bet (any amount up to your balance), call heads or tails, and
  press **Flip!** A win adds the bet to your balance; a loss subtracts it.
- **Time limit.** The clock starts on your first accepted flip (a rejected flip doesn't
  start it) and counts down on the page. When it reaches 0:00, betting is disabled and
  the page shows your final balance and number of flips. The server enforces the limit,
  so flips sent after time is up are ignored even if the page is out of date.
- **Refreshing starts a brand new game.** Reloading or reopening the page resets
  everything: balance, total flips, heads, tails, the clock, and the time limit and
  odds you chose (they go back to being editable, prefilled with the defaults).
- **Input checks.** The browser blocks bad input first (bet must be $0.01 up to your
  balance, in whole cents, and a side must be picked; time limit and heads probability
  must be whole numbers in range). The server checks again and rejects, with a message,
  anything that isn't a plain number (e.g. `abc`, `NaN`, `1e3`, `1,000`), bets of $0 or
  less, bets with fractions of a cent, bets over your balance, sides other than heads
  or tails, and time limits or odds outside their allowed range. When the balance hits
  $0, betting is disabled.
- **Reset.** **Reset to $25** clears everything and starts a new game, the same as a
  page refresh.

## Architecture and design

- Single-file app (`coin_toss.py`) with the page template inline; no database.
- Routes: `GET /` shows the game, `POST /flip` places a bet (and, on the first flip,
  the game settings), `POST /reset` starts over.
- Game state (balance, counts, last bet and side, the chosen time limit and odds, and
  when the clock started) is stored in the browser session cookie, so each browser has
  its own game.
- Every flip redirects back to `GET /` after marking the session (`after_flip`). Any
  `GET /` without that mark is a fresh load or refresh, and clears the whole session,
  starting a brand new game.
- The countdown on the page is a small script that locks the page itself at zero
  (reloading would start a new game); the real check happens on the server when a flip
  is posted.
- The session secret key is generated at startup, so restarting the server resets
  everyone's progress.
- Intended for local experimentation, not production use (it runs Flask's development
  server in debug mode).

## CLI workflows

Requires Python 3 and Flask.

**Run the app:**

```bash
pip install flask
python coin_toss.py
```

Then open http://127.0.0.1:5000 in your browser.

**Run the tests** (built-in `unittest`, nothing extra needed), from the repo root:

```bash
python -m unittest discover -s tests
```

They cover invalid bets and sides, winning and losing flips, going broke, the game
settings (required before the first flip, validation, locking in, and how they affect
the coin), the time limit (when the clock starts, the countdown, flips at and after the
limit, refresh, reset), and the page's validation attributes.

## Configuration

Constants at the top of `coin_toss.py`:

| Constant | Default | Meaning |
| --- | --- | --- |
| `STARTING_BALANCE` | `"25.00"` | Balance for a new or reset game |
| `DEFAULT_TIME_LIMIT_MINUTES` | `5` | Time limit prefilled in the settings form |
| `MIN_TIME_LIMIT_MINUTES` / `MAX_TIME_LIMIT_MINUTES` | `1` / `60` | Allowed range for the time limit |
| `DEFAULT_HEADS_PCT` | `60` | Heads probability prefilled in the settings form |
| `MIN_HEADS_PCT` / `MAX_HEADS_PCT` | `1` / `99` | Allowed range for the heads probability |
