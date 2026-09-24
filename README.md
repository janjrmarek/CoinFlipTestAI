# CoinFlipTestAI

## Overview

A small Flask web app for betting on a biased coin against the clock. The coin lands
heads 60% of the time and tails 40%, every bet pays even money, and each game lasts
5 minutes. The goal is to finish with as much money as you can.

## Application domain

- **Starting balance of $25.** Your balance, time left, total flips, heads, tails, and
  heads % are shown at the top of the page.
- **Flipping.** Enter a bet (any amount up to your balance), call heads or tails, and
  press **Flip!** A win adds the bet to your balance; a loss subtracts it.
- **5-minute time limit.** The clock starts on your first flip (a rejected bet doesn't
  start it) and counts down on the page. When it reaches 0:00, betting is disabled and
  the page shows your final balance and number of flips. The server enforces the limit,
  so flips sent after time is up are ignored even if the page is out of date.
- **Input checks.** The browser blocks bad input first (bet must be $0.01 up to your
  balance, in whole cents, and a side must be picked). The server checks again and
  rejects, with a message, anything that isn't a plain number (e.g. `abc`, `NaN`,
  `1e3`, `1,000`), bets of $0 or less, bets with fractions of a cent, bets over your
  balance, and sides other than heads or tails. When the balance hits $0, betting is
  disabled.
- **Reset.** **Reset to $25** clears all stats and the clock, and starts a new game.

## Architecture and design

- Single-file app (`coin_toss.py`) with the page template inline; no database.
- Routes: `GET /` shows the game, `POST /flip` places a bet, `POST /reset` starts over.
- Game state (balance, counts, last bet and side, and when the clock started) is stored
  in the browser session cookie, so each browser has its own game.
- The countdown on the page is a small script that reloads the page when it hits zero;
  the real check happens on the server when a flip is posted.
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

They cover invalid bets and sides, winning and losing flips, going broke, the time
limit (when the clock starts, the countdown, flips at and after the limit, reset), and
the page's validation attributes.

## Configuration

Constants at the top of `coin_toss.py`:

| Constant | Default | Meaning |
| --- | --- | --- |
| `STARTING_BALANCE` | `"25.00"` | Balance for a new or reset game |
| `HEADS_PROBABILITY` | `0.60` | Chance each flip lands heads |
| `TIME_LIMIT_SECONDS` | `5 * 60` | Length of a game, from the first flip |
