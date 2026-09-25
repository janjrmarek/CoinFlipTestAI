"""
Biased Coin Toss Simulator
--------------------------
A small Flask web app themed as a TTTQ breakout bet. Before your first flip, choose a
time limit and the odds of a breakout win; those lock in once you flip. Start with
$100,000, bet a percentage of your balance, pick a side, and track total flips, wins,
fails, and your running balance. Refreshing the page starts a brand new game.

The two outcomes are stored and compared internally as "heads" (breakout win) and
"tails" (breakout fail) — only the on-screen labels changed, via OUTCOME_LABELS below.

Run:
    pip install flask
    python coin_toss.py
Then open http://127.0.0.1:5000 in your browser.
"""

import random
import re
import secrets
import time
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from flask import Flask, redirect, render_template_string, request, session, url_for

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

STARTING_BALANCE = "100000.00"
CENT = Decimal("0.01")
BET_PATTERN = re.compile(r"-?(\d+\.?\d*|\.\d+)", re.ASCII)
WHOLE_NUMBER_PATTERN = re.compile(r"\d+", re.ASCII)

DEFAULT_TIME_LIMIT_MINUTES = 5
MIN_TIME_LIMIT_MINUTES = 1
MAX_TIME_LIMIT_MINUTES = 60

DEFAULT_HEADS_PCT = 60
MIN_HEADS_PCT = 1
MAX_HEADS_PCT = 99

DEFAULT_BET_PCT = "10"

OUTCOME_LABELS = {"heads": "TTTQ Breakout Win", "tails": "TTTQ Breakout Fail"}

PAGE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Coin Toss</title>
<style>
  body { font-family: system-ui, sans-serif; background:#f4f1ea; color:#222;
         display:flex; justify-content:center; padding:40px 16px; margin:0; }
  .card { background:#fff; border-radius:12px; padding:28px; max-width:440px; width:100%;
          box-shadow:0 4px 18px rgba(0,0,0,.08); }
  h1 { margin:0 0 4px; font-size:1.6rem; }
  .odds { color:#666; margin:0 0 20px; font-size:.9rem; }
  .stats { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:20px; }
  .stat { background:#f7f7f7; border-radius:8px; padding:12px; text-align:center; }
  .stat .label { font-size:.8rem; color:#666; text-transform:uppercase; letter-spacing:.05em; }
  .stat .value { font-size:1.5rem; font-weight:700; margin-top:4px; }
  .balance, .timer { background:#1f3a2e; color:#fff; }
  .balance .label, .timer .label, .timer .hint { color:#b8d4c4; }
  .timer .hint { font-size:.75rem; margin-top:2px; }
  .result { padding:12px; border-radius:8px; margin-bottom:16px; text-align:center; font-weight:600; }
  .win { background:#e3f4e8; color:#1d6b35; }
  .lose { background:#fbe6e4; color:#9b2c20; }
  .error { background:#fff4d6; color:#7a5a00; }
  label { display:block; font-weight:600; margin:10px 0 6px; }
  input[type=number] { width:100%; padding:10px; font-size:1rem; border:1px solid #ccc;
                       border-radius:6px; box-sizing:border-box; }
  .sides { display:flex; gap:16px; }
  button { width:100%; padding:12px; font-size:1rem; font-weight:600; border:none;
           border-radius:6px; cursor:pointer; margin-top:16px; }
  .flip { background:#c9a227; color:#222; }
  .flip:disabled { background:#ddd; color:#888; cursor:not-allowed; }
  .reset { background:transparent; color:#666; text-decoration:underline; margin-top:8px; }
  .settings-locked { color:#666; font-size:.85rem; margin:10px 0 0; }
  .bet-preview { color:#666; font-size:.8rem; margin:4px 0 0; min-height:1.1em; }
</style>
</head>
<body>
<div class="card">
  <h1>🪙 Coin Toss</h1>
  <p class="odds">TTTQ Breakout Win {{ heads_pct }}% &middot; TTTQ Breakout Fail {{ tails_pct }}% &middot; Even-money payout</p>

  <div class="stats">
    <div class="stat balance"><div class="label">Balance</div><div class="value">${{ balance }}</div></div>
    <div class="stat timer"><div class="label">Time left</div>
      <div class="value" id="timer" data-left="{{ seconds_left }}" data-running="{{ 'yes' if running else 'no' }}">{{ time_left }}</div>
      {% if not running and not time_up %}<div class="hint">Starts on first flip</div>{% endif %}
    </div>
    <div class="stat"><div class="label">Total flips</div><div class="value">{{ flips }}</div></div>
    <div class="stat"><div class="label">Breakout wins</div><div class="value">{{ heads }}</div></div>
    <div class="stat"><div class="label">Breakout fails</div><div class="value">{{ tails }}</div></div>
    <div class="stat"><div class="label">Win %</div><div class="value">{{ heads_pct_stat }}</div></div>
  </div>

  <div class="result error" id="time-up" {% if not time_up %}hidden{% endif %}>
    Time's up! You finished with ${{ balance }} after {{ flips }} flips.</div>
  {% if message and not time_up %}
    <div class="result {{ message_class }}" id="message">{{ message }}</div>
  {% endif %}

  <form method="post" action="{{ url_for('flip') }}">
    {% if not started %}
      <label for="time_limit">Time limit (minutes)</label>
      <input id="time_limit" name="time_limit" type="number" min="{{ min_minutes }}" max="{{ max_minutes }}"
             step="1" value="{{ time_limit_input }}" required>

      <label for="heads_pct_input">TTTQ Breakout Win probability (%)</label>
      <input id="heads_pct_input" name="heads_pct" type="number" min="{{ min_pct }}" max="{{ max_pct }}"
             step="1" value="{{ heads_pct_input }}" required>
    {% else %}
      <p class="settings-locked">Time limit: {{ time_limit_minutes }} min &middot;
        TTTQ Breakout Win odds: {{ heads_pct }}% / TTTQ Breakout Fail {{ tails_pct }}%</p>
    {% endif %}

    <label for="bet_pct">Bet (% of balance)</label>
    <input id="bet_pct" name="bet_pct" type="number" step="0.01" min="0.01" max="100"
           value="{{ last_bet_pct }}" data-balance="{{ balance_raw }}"
           required {% if locked %}disabled{% endif %}>
    <p class="bet-preview" id="bet-preview"></p>

    <label>Your call</label>
    <div class="sides">
      <label><input type="radio" name="side" value="heads" required {% if last_side == 'heads' %}checked{% endif %}> TTTQ Breakout Win</label>
      <label><input type="radio" name="side" value="tails" {% if last_side == 'tails' %}checked{% endif %}> TTTQ Breakout Fail</label>
    </div>

    <button class="flip" type="submit" {% if locked %}disabled{% endif %}>
      {% if time_up %}Time's up{% elif broke %}Out of money{% else %}Flip!{% endif %}
    </button>
  </form>

  <form method="post" action="{{ url_for('reset') }}">
    <button class="reset" type="submit">Reset to {{ starting_balance }}</button>
  </form>
</div>
<script>
  // Count down in the browser; the server enforces the limit either way.
  // At zero, lock the page here rather than reloading, since a reload restarts the clock.
  const timer = document.getElementById("timer");
  if (timer.dataset.running === "yes") {
    const end = Date.now() + Number(timer.dataset.left) * 1000;
    const tick = () => {
      const left = Math.max(0, Math.ceil((end - Date.now()) / 1000));
      timer.textContent = Math.floor(left / 60) + ":" + String(left % 60).padStart(2, "0");
      if (left > 0) return setTimeout(tick, 250);
      document.getElementById("time-up").hidden = false;
      document.getElementById("message")?.remove();
      document.getElementById("bet_pct").disabled = true;
      const flip = document.querySelector(".flip");
      flip.disabled = true;
      flip.textContent = "Time's up";
    };
    tick();
  }

  // Show the dollar amount a bet percentage works out to, at the current balance.
  const betInput = document.getElementById("bet_pct");
  const betPreview = document.getElementById("bet-preview");
  const updateBetPreview = () => {
    const balance = Number(betInput.dataset.balance);
    const pct = Number(betInput.value);
    betPreview.textContent = pct > 0 && pct <= 100 && !isNaN(balance)
      ? "≈ $" + (balance * pct / 100).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})
      : "";
  };
  betInput.addEventListener("input", updateBetPreview);
  updateBetPreview();
</script>
</body>
</html>
"""


def init_state():
    session.setdefault("balance", STARTING_BALANCE)
    session.setdefault("flips", 0)
    session.setdefault("heads", 0)
    session.setdefault("tails", 0)
    session.setdefault("last_bet_pct", DEFAULT_BET_PCT)
    session.setdefault("last_side", "heads")
    session.setdefault("time_limit_input", str(DEFAULT_TIME_LIMIT_MINUTES))
    session.setdefault("heads_pct_input", str(DEFAULT_HEADS_PCT))


def seconds_left():
    """Seconds remaining in this game. The clock starts on the first flip."""
    limit = session.get("time_limit_minutes", DEFAULT_TIME_LIMIT_MINUTES) * 60
    started = session.get("started_at")
    if started is None:
        return limit
    return max(0, limit - int(time.time() - started))


@app.route("/")
def index():
    # Every flip marks the session before its redirect here. Any other load of the
    # page (opening it, refreshing it) starts a brand new game: balance, stats, the
    # clock and the settings all reset.
    if not session.pop("after_flip", False):
        session.clear()
    init_state()

    balance = Decimal(session["balance"])
    flips = session["flips"]
    heads_pct_stat = f"{session['heads'] / flips * 100:.1f}%" if flips else "—"
    started = "started_at" in session
    heads_pct = session.get("heads_pct", DEFAULT_HEADS_PCT)
    left = seconds_left()
    time_up = left == 0
    return render_template_string(
        PAGE,
        balance=f"{balance:,.2f}",
        balance_raw=f"{balance:.2f}",
        starting_balance=f"${Decimal(STARTING_BALANCE):,.2f}",
        flips=flips,
        heads=session["heads"],
        tails=session["tails"],
        heads_pct_stat=heads_pct_stat,
        last_bet_pct=session["last_bet_pct"],
        last_side=session["last_side"],
        broke=balance <= 0,
        time_up=time_up,
        locked=balance <= 0 or time_up,
        seconds_left=left,
        time_left=f"{left // 60}:{left % 60:02d}",
        running=started and not time_up,
        started=started,
        heads_pct=heads_pct,
        tails_pct=100 - heads_pct,
        time_limit_minutes=session.get("time_limit_minutes", DEFAULT_TIME_LIMIT_MINUTES),
        time_limit_input=session["time_limit_input"],
        heads_pct_input=session["heads_pct_input"],
        min_minutes=MIN_TIME_LIMIT_MINUTES,
        max_minutes=MAX_TIME_LIMIT_MINUTES,
        min_pct=MIN_HEADS_PCT,
        max_pct=MAX_HEADS_PCT,
        message=session.pop("message", None),
        message_class=session.pop("message_class", ""),
    )


def read_bet(balance):
    """Parse side and bet percentage from the form. Returns (side, pct, stake, error_message),
    where stake is pct% of balance, rounded to the nearest cent."""
    side = request.form.get("side", "")
    if side not in ("heads", "tails"):
        return side, None, None, "Pick TTTQ Breakout Win or TTTQ Breakout Fail."

    # Plain decimal numbers only: rejects NaN, Infinity, exponents, commas,
    # underscores and non-ASCII digits, all of which Decimal() would accept or choke on.
    raw = request.form.get("bet_pct", "").strip()
    if not raw:
        return side, None, None, "Enter a bet percentage."
    if not BET_PATTERN.fullmatch(raw):
        return side, None, None, "Enter the bet as a percentage, like 10 or 2.5."
    try:
        pct = Decimal(raw)
    except InvalidOperation:
        return side, None, None, "Enter the bet as a percentage, like 10 or 2.5."

    if pct <= 0:
        return side, None, None, "Enter a percentage greater than 0%."
    if pct > 100:
        return side, None, None, "You can bet at most 100% of your balance."

    stake = (balance * pct / 100).quantize(CENT, rounding=ROUND_HALF_UP)
    if stake <= 0:
        return side, None, None, "That percentage is too small to bet anything."
    return side, pct, stake, None


def read_settings():
    """Parse and validate the one-time game settings, sent with the first flip.
    Returns (minutes, heads_pct, error_message). Attempted values are kept in the
    session either way, so a rejected first flip doesn't clear what was typed."""
    raw_minutes = request.form.get("time_limit", "").strip()
    raw_pct = request.form.get("heads_pct", "").strip()
    session["time_limit_input"] = raw_minutes or session["time_limit_input"]
    session["heads_pct_input"] = raw_pct or session["heads_pct_input"]

    if not raw_minutes:
        return None, None, "Enter a time limit."
    if not WHOLE_NUMBER_PATTERN.fullmatch(raw_minutes):
        return None, None, "Enter the time limit as a whole number of minutes."
    minutes = int(raw_minutes)
    if not (MIN_TIME_LIMIT_MINUTES <= minutes <= MAX_TIME_LIMIT_MINUTES):
        return None, None, f"Time limit must be between {MIN_TIME_LIMIT_MINUTES} and {MAX_TIME_LIMIT_MINUTES} minutes."

    if not raw_pct:
        return None, None, "Enter the TTTQ Breakout Win probability."
    if not WHOLE_NUMBER_PATTERN.fullmatch(raw_pct):
        return None, None, "Enter the TTTQ Breakout Win probability as a whole number percentage."
    pct = int(raw_pct)
    if not (MIN_HEADS_PCT <= pct <= MAX_HEADS_PCT):
        return None, None, f"TTTQ Breakout Win probability must be between {MIN_HEADS_PCT} and {MAX_HEADS_PCT}."

    return minutes, pct, None


@app.route("/flip", methods=["POST"])
def flip():
    init_state()
    session["after_flip"] = True  # so the redirect back to the page keeps the game
    if seconds_left() == 0:
        return redirect(url_for("index"))  # the page shows the time's-up summary

    is_first_flip = "started_at" not in session
    if is_first_flip:
        minutes, pct, settings_error = read_settings()
        if settings_error:
            session["message"], session["message_class"] = settings_error, "error"
            return redirect(url_for("index"))

    balance = Decimal(session["balance"])
    side, bet_pct, stake, error = read_bet(balance)
    if error:
        session["message"], session["message_class"] = error, "error"
        return redirect(url_for("index"))

    if is_first_flip:
        session["time_limit_minutes"] = minutes
        session["heads_pct"] = pct
        session["started_at"] = time.time()

    result = "heads" if random.random() * 100 < session["heads_pct"] else "tails"
    session["flips"] += 1
    session[result] += 1
    label = OUTCOME_LABELS[result]

    if result == side:
        balance += stake
        session["message"] = f"{label}! Bet {bet_pct}% (${stake:,.2f}) — won ${stake:,.2f}."
        session["message_class"] = "win"
    else:
        balance -= stake
        session["message"] = f"{label}. Bet {bet_pct}% (${stake:,.2f}) — lost ${stake:,.2f}."
        session["message_class"] = "lose"

    session["balance"] = str(balance)
    session["last_bet_pct"] = str(bet_pct)
    session["last_side"] = side
    return redirect(url_for("index"))


@app.route("/reset", methods=["POST"])
def reset():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
