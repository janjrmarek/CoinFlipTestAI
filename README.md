# CoinFlipTestAI

A small Flask web app for betting on a biased coin. The coin lands heads 60% of the
time and tails 40%, and every bet pays even money. You can flip one at a time or
simulate a few minutes of play at once to see how a strategy works out over many flips.

## Features

- **Starting balance of $25.** Your balance, total flips, heads, tails, and heads % are
  shown at the top of the page.
- **Single flips.** Enter a bet (any amount up to your balance), call heads or tails, and
  press **Flip!** A win adds the bet to your balance; a loss subtracts it.
- **5-minute simulation.** **Simulate 5 minutes (300 flips)** (by default) plays 300 flips in one go
  (one flip per second) using the bet and side currently selected. If your balance
  drops below the bet, it bets whatever is left, and it stops early if you go broke.
  A summary shows how many flips ran and how much you're up or down.
- **Input checks.** The browser blocks bad input first (bet must be $0.01 up to your
  balance, in whole cents, and a side must be picked). The server checks again and
  rejects, with a message, anything that isn't a plain number (e.g. `abc`, `NaN`,
  `1e3`, `1,000`), bets of $0 or less, bets with fractions of a cent, bets over your
  balance, and sides other than heads or tails. When the balance hits $0, betting is
  disabled.
- **Reset.** **Reset to $25** clears all stats and starts over.

## Scope

- Single-file app (`coin_toss.py`) with the page template inline; no database.
- Game state is stored in the browser session cookie, so each browser has its own game.
- The session secret key is generated at startup, so restarting the server resets
  everyone's progress.
- Intended for local experimentation, not production use (it runs Flask's development
  server in debug mode).

## Running it

Requires Python 3 and Flask.

```bash
pip install flask
python coin_toss.py
```

Then open http://127.0.0.1:5000 in your browser.

## Testing

Tests use Python's built-in `unittest`, so nothing extra is needed. From the repo root:

```bash
python -m unittest discover -s tests
```

They cover invalid bets and sides on both flip and simulate, winning and losing flips,
going broke, the simulation, reset, and the page's validation attributes.

## Configuration

Constants at the top of `coin_toss.py`:

| Constant | Default | Meaning |
| --- | --- | --- |
| `STARTING_BALANCE` | `"25.00"` | Balance for a new or reset game |
| `HEADS_PROBABILITY` | `0.60` | Chance each flip lands heads |
| `FLIPS_PER_SECOND` | `1` | Flip rate used by the simulation |
| `SIMULATED_MINUTES` | `5` | Length of the simulation (the button label follows it) |
