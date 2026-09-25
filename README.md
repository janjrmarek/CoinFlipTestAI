# CoinFlipTestAI

## Overview

A small Flask web app for betting on a biased coin against the clock, themed as a
TTTQ breakout bet. Before your first flip you choose the time limit and the odds of a
breakout win; every bet after that pays even money. The goal is to finish with as much
money as you can before time runs out.

## Application domain

- **Starting balance of $100,000.** Your balance, time left, total flips, breakout wins,
  breakout fails, and win % are shown at the top of the page.
- **Game settings, set once.** Before the first flip, choose the **time limit**
  (1–60 whole minutes, default 5) and the **TTTQ Breakout Win probability** (1–99 whole
  percent, default 60). Both are required to flip. Once the first flip is accepted they
  lock in for the rest of the game: the inputs are replaced with a line showing what's
  in play, and later flips ignore any different values sent to the server.
- **Betting a percentage of your balance.** Enter a bet as a percentage (0.01–100) of
  your *current* balance, not a fixed dollar amount, call **TTTQ Breakout Win** or
  **TTTQ Breakout Fail**, and press **Flip!** A win adds the staked amount to your
  balance; a loss subtracts it. As the balance changes, the same percentage is worth a
  different dollar amount, so the app shows a live "≈ $X" estimate under the field as
  you type. The result message spells out the percentage and dollar amount staked.
- **Time limit.** The clock starts on your first accepted flip (a rejected flip doesn't
  start it) and counts down on the page. When it reaches 0:00, betting is disabled and
  the page shows your final balance and number of flips. The server enforces the limit,
  so flips sent after time is up are ignored even if the page is out of date.
- **Refreshing starts a brand new game.** Reloading or reopening the page resets
  everything: balance, total flips, wins, fails, the clock, and the time limit and odds
  you chose (they go back to being editable, prefilled with the defaults).
- **Input checks.** The browser blocks bad input first (bet must be 0.01–100%, and a
  side must be picked; time limit and win probability must be whole numbers in range).
  The server checks again and rejects, with a message, anything that isn't a plain
  number (e.g. `abc`, `NaN`, `1e3`, `1,000`), a percentage of 0 or less, over 100%, or
  so small it would round to a $0.00 stake, and sides other than TTTQ Breakout Win or
  TTTQ Breakout Fail. When the balance hits $0, betting is disabled.
- **Reset.** **Reset to $100,000.00** clears everything and starts a new game, the same
  as a page refresh.

## Architecture and design

- Single-file app (`coin_toss.py`) with the page template inline; no database.
- The two outcomes are stored and compared internally as `"heads"`/`"tails"` — only the
  on-screen labels are "TTTQ Breakout Win"/"TTTQ Breakout Fail" (`OUTCOME_LABELS`).
- Routes: `GET /` shows the game, `POST /flip` places a bet (and, on the first flip,
  the game settings), `POST /reset` starts over.
- A bet is a percentage of the *current* balance at flip time, not a fixed dollar
  amount, so the stake is recalculated fresh on every flip and compounds as the
  balance changes; there's no separate "bet exceeds balance" check since any 0–100%
  bet is always affordable.
- Game state (balance, counts, last bet percentage and side, the chosen time limit and
  odds, and when the clock started) is stored in the browser session cookie, so each
  browser has its own game.
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

They cover invalid bet percentages and sides, winning and losing flips (including the
stake compounding as the balance changes), going broke, the game settings (required
before the first flip, validation, locking in, and how they affect the coin), the time
limit (when the clock starts, the countdown, flips at and after the limit, refresh,
reset), and the page's validation attributes.

## Configuration

Constants at the top of `coin_toss.py`:

| Constant | Default | Meaning |
| --- | --- | --- |
| `STARTING_BALANCE` | `"100000.00"` | Balance for a new or reset game |
| `DEFAULT_TIME_LIMIT_MINUTES` | `5` | Time limit prefilled in the settings form |
| `MIN_TIME_LIMIT_MINUTES` / `MAX_TIME_LIMIT_MINUTES` | `1` / `60` | Allowed range for the time limit |
| `DEFAULT_HEADS_PCT` | `60` | TTTQ Breakout Win probability prefilled in the settings form |
| `MIN_HEADS_PCT` / `MAX_HEADS_PCT` | `1` / `99` | Allowed range for the win probability |
| `DEFAULT_BET_PCT` | `"10"` | Bet percentage prefilled on a new game |
