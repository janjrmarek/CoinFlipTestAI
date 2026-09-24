"""
Biased Coin Toss Simulator
--------------------------
A small Flask web app: 60% heads / 40% tails.
Start with $25, bet any amount up to your balance, pick a side,
and track total flips, heads, tails, and your running balance.

Run:
    pip install flask
    python coin_toss.py
Then open http://127.0.0.1:5000 in your browser.
"""

import random
import secrets
from decimal import Decimal, InvalidOperation

from flask import Flask, redirect, render_template_string, request, session, url_for

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

STARTING_BALANCE = "25.00"
HEADS_PROBABILITY = 0.60
FLIPS_PER_SECOND = 1
SIMULATED_MINUTES = 5

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
  .balance { grid-column:1 / -1; background:#1f3a2e; color:#fff; }
  .balance .label { color:#b8d4c4; }
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
  .simulate { background:#1f3a2e; color:#fff; }
  .simulate:disabled { background:#ddd; color:#888; cursor:not-allowed; }
  .reset { background:transparent; color:#666; text-decoration:underline; margin-top:8px; }
</style>
</head>
<body>
<div class="card">
  <h1>🪙 Coin Toss</h1>
  <p class="odds">Heads 60% &middot; Tails 40% &middot; Even-money payout</p>

  <div class="stats">
    <div class="stat balance"><div class="label">Balance</div><div class="value">${{ balance }}</div></div>
    <div class="stat"><div class="label">Total flips</div><div class="value">{{ flips }}</div></div>
    <div class="stat"><div class="label">Heads</div><div class="value">{{ heads }}</div></div>
    <div class="stat"><div class="label">Tails</div><div class="value">{{ tails }}</div></div>
    <div class="stat"><div class="label">Heads %</div><div class="value">{{ heads_pct }}</div></div>
  </div>

  {% if message %}
    <div class="result {{ message_class }}">{{ message }}</div>
  {% endif %}

  <form id="play" method="post" action="{{ url_for('flip') }}">
    <label for="bet">Bet amount ($)</label>
    <input id="bet" name="bet" type="number" step="0.01" min="0.01" max="{{ balance }}"
           value="{{ last_bet }}" required {% if broke %}disabled{% endif %}>

    <label>Your call</label>
    <div class="sides">
      <label><input type="radio" name="side" value="heads" {% if last_side == 'heads' %}checked{% endif %}> Heads</label>
      <label><input type="radio" name="side" value="tails" {% if last_side == 'tails' %}checked{% endif %}> Tails</label>
    </div>

    <button class="flip" type="submit" {% if broke %}disabled{% endif %}>
      {% if broke %}Out of money{% else %}Flip!{% endif %}
    </button>
  </form>

  <form method="post" action="{{ url_for('reset') }}">
    <button class="reset" type="submit">Reset to $25</button>
  </form>

  <button class="simulate" type="submit" form="play" formaction="{{ url_for('simulate') }}"
          {% if broke %}disabled{% endif %}>
    Simulate {{ sim_minutes }} minute{{ "" if sim_minutes == 1 else "s" }} ({{ sim_flips }} flips)
  </button>
</div>
</body>
</html>
"""


def init_state():
    session.setdefault("balance", STARTING_BALANCE)
    session.setdefault("flips", 0)
    session.setdefault("heads", 0)
    session.setdefault("tails", 0)
    session.setdefault("last_bet", "1.00")
    session.setdefault("last_side", "heads")


@app.route("/")
def index():
    init_state()
    balance = Decimal(session["balance"])
    flips = session["flips"]
    heads_pct = f"{session['heads'] / flips * 100:.1f}%" if flips else "—"
    return render_template_string(
        PAGE,
        balance=f"{balance:.2f}",
        flips=flips,
        heads=session["heads"],
        tails=session["tails"],
        heads_pct=heads_pct,
        last_bet=session["last_bet"],
        last_side=session["last_side"],
        broke=balance <= 0,
        sim_minutes=SIMULATED_MINUTES,
        sim_flips=SIMULATED_MINUTES * 60 * FLIPS_PER_SECOND,
        message=session.pop("message", None),
        message_class=session.pop("message_class", ""),
    )


def read_bet(balance):
    """Parse side and bet from the form. Returns (side, bet, error_message)."""
    side = request.form.get("side", "heads")
    if side not in ("heads", "tails"):
        side = "heads"

    try:
        bet = Decimal(request.form.get("bet", "0")).quantize(Decimal("0.01"))
    except InvalidOperation:
        bet = Decimal("0")

    if bet <= 0:
        return side, bet, "Enter a bet greater than $0."
    if bet > balance:
        return side, bet, f"You only have ${balance:.2f} to bet."
    return side, bet, None


def toss():
    result = "heads" if random.random() < HEADS_PROBABILITY else "tails"
    session["flips"] += 1
    session[result] += 1
    return result


@app.route("/flip", methods=["POST"])
def flip():
    init_state()
    balance = Decimal(session["balance"])
    side, bet, error = read_bet(balance)
    if error:
        session["message"], session["message_class"] = error, "error"
        return redirect(url_for("index"))

    result = toss()

    if result == side:
        balance += bet
        session["message"] = f"{result.title()}! You won ${bet:.2f}."
        session["message_class"] = "win"
    else:
        balance -= bet
        session["message"] = f"{result.title()}. You lost ${bet:.2f}."
        session["message_class"] = "lose"

    session["balance"] = str(balance)
    session["last_bet"] = str(min(bet, balance)) if balance > 0 else "0"
    session["last_side"] = side
    return redirect(url_for("index"))


@app.route("/simulate", methods=["POST"])
def simulate():
    """Flip repeatedly for SIMULATED_MINUTES at FLIPS_PER_SECOND with the same bet and side.
    If the balance drops below the bet, bet whatever is left; stop when broke."""
    init_state()
    start = balance = Decimal(session["balance"])
    side, bet, error = read_bet(balance)
    if error:
        session["message"], session["message_class"] = error, "error"
        return redirect(url_for("index"))

    total = SIMULATED_MINUTES * 60 * FLIPS_PER_SECOND
    done = 0
    while done < total and balance > 0:
        stake = min(bet, balance)
        balance += stake if toss() == side else -stake
        done += 1

    change = balance - start
    summary = f"Simulated {done} flips betting ${bet:.2f} on {side}: "
    summary += f"{'up' if change >= 0 else 'down'} ${abs(change):.2f}."
    if done < total:
        summary += " Went broke early."
    session["message"] = summary
    session["message_class"] = "win" if change >= 0 else "lose"
    session["balance"] = str(balance)
    session["last_bet"] = str(min(bet, balance)) if balance > 0 else "0"
    session["last_side"] = side
    return redirect(url_for("index"))


@app.route("/reset", methods=["POST"])
def reset():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
