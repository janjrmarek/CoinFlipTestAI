"""Tests for coin_toss.py. Run from the repo root with:  python -m unittest discover -s tests"""

import os
import sys
import unittest
from decimal import ROUND_HALF_UP, Decimal
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import coin_toss  # noqa: E402

HEADS = 0.0  # random.random() values that force each outcome at the default 60% odds
TAILS = 0.99

STARTING_BALANCE = Decimal("100000.00")
CENT = Decimal("0.01")


def stake_for(balance, pct):
    """The dollar amount coin_toss.read_bet() computes for a given balance and pct."""
    return (balance * Decimal(pct) / 100).quantize(CENT, rounding=ROUND_HALF_UP)


INVALID_BET_PCTS = [
    ("", "Enter a bet percentage."),
    ("   ", "Enter a bet percentage."),
    ("abc", "Enter the bet as a percentage, like 10 or 2.5."),
    ("NaN", "Enter the bet as a percentage, like 10 or 2.5."),
    ("sNaN", "Enter the bet as a percentage, like 10 or 2.5."),
    ("Infinity", "Enter the bet as a percentage, like 10 or 2.5."),
    ("-Infinity", "Enter the bet as a percentage, like 10 or 2.5."),
    ("1e3", "Enter the bet as a percentage, like 10 or 2.5."),
    ("1e30", "Enter the bet as a percentage, like 10 or 2.5."),
    ("1,000", "Enter the bet as a percentage, like 10 or 2.5."),
    ("1_0", "Enter the bet as a percentage, like 10 or 2.5."),
    ("$5", "Enter the bet as a percentage, like 10 or 2.5."),
    ("5 5", "Enter the bet as a percentage, like 10 or 2.5."),
    ("١٢", "Enter the bet as a percentage, like 10 or 2.5."),  # Arabic-Indic digits
    (".", "Enter the bet as a percentage, like 10 or 2.5."),
    ("-", "Enter the bet as a percentage, like 10 or 2.5."),
    ("0", "Enter a percentage greater than 0%."),
    ("0.00", "Enter a percentage greater than 0%."),
    ("-0", "Enter a percentage greater than 0%."),
    ("-5", "Enter a percentage greater than 0%."),
    ("100.01", "You can bet at most 100% of your balance."),
    ("101", "You can bet at most 100% of your balance."),
    ("9" * 100, "You can bet at most 100% of your balance."),
    ("0.000001", "That percentage is too small to bet anything."),
]

INVALID_SIDES = [None, "", "edge", "HEADS", "Tails", "heads "]

INVALID_TIME_LIMITS = [
    ("", "Enter a time limit."),
    ("   ", "Enter a time limit."),
    ("abc", "Enter the time limit as a whole number of minutes."),
    ("5.5", "Enter the time limit as a whole number of minutes."),
    ("-5", "Enter the time limit as a whole number of minutes."),
    ("1e1", "Enter the time limit as a whole number of minutes."),
    ("0", "Time limit must be between 1 and 60 minutes."),
    ("61", "Time limit must be between 1 and 60 minutes."),
    ("100", "Time limit must be between 1 and 60 minutes."),
]

INVALID_HEADS_PCTS = [
    ("", "Enter the TTTQ Breakout Win probability."),
    ("abc", "Enter the TTTQ Breakout Win probability as a whole number percentage."),
    ("50.5", "Enter the TTTQ Breakout Win probability as a whole number percentage."),
    ("-1", "Enter the TTTQ Breakout Win probability as a whole number percentage."),
    ("0", "TTTQ Breakout Win probability must be between 1 and 99."),
    ("100", "TTTQ Breakout Win probability must be between 1 and 99."),
    ("101", "TTTQ Breakout Win probability must be between 1 and 99."),
]


class CoinTossTestCase(unittest.TestCase):
    def setUp(self):
        coin_toss.app.config["TESTING"] = True
        self.client = coin_toss.app.test_client()
        self.client.get("/")  # initialise the session

    def post(self, route, bet_pct=None, side=None, time_limit=None, heads_pct=None):
        # time_limit/heads_pct default to valid values so tests that aren't about
        # settings don't need to supply them (they're only read on the first flip).
        data = {
            "time_limit": str(coin_toss.DEFAULT_TIME_LIMIT_MINUTES) if time_limit is None else time_limit,
            "heads_pct": str(coin_toss.DEFAULT_HEADS_PCT) if heads_pct is None else heads_pct,
        }
        if bet_pct is not None:
            data["bet_pct"] = bet_pct
        if side is not None:
            data["side"] = side
        return self.client.post(route, data=data)

    def state(self):
        with self.client.session_transaction() as sess:
            return dict(sess)

    def set_balance(self, amount):
        with self.client.session_transaction() as sess:
            sess["balance"] = amount

    def assert_rejected(self, response, message):
        self.assertEqual(response.status_code, 302)
        state = self.state()
        self.assertEqual(state["message"], message)
        self.assertEqual(state["message_class"], "error")
        self.assertEqual(state["balance"], str(STARTING_BALANCE))
        self.assertEqual(state["flips"], 0)
        self.assertNotIn("started_at", state)  # a rejected first flip doesn't start the game
        self.assertNotIn("time_limit_minutes", state)
        self.assertNotIn("heads_pct", state)


class InvalidInputTests(CoinTossTestCase):
    def test_invalid_bet_pcts_are_rejected(self):
        for pct, message in INVALID_BET_PCTS:
            with self.subTest(pct=pct):
                self.setUp()
                self.assert_rejected(self.post("/flip", pct, "heads"), message)

    def test_missing_bet_pct_field(self):
        self.assert_rejected(self.post("/flip", side="heads"), "Enter a bet percentage.")

    def test_invalid_sides_are_rejected(self):
        for side in INVALID_SIDES:
            with self.subTest(side=side):
                self.setUp()
                self.assert_rejected(
                    self.post("/flip", "1", side), "Pick TTTQ Breakout Win or TTTQ Breakout Fail."
                )

    def test_rejected_input_never_causes_server_error(self):
        weird = ["\x00", "1" * 10000, "0x10", "1..2", "--1", "+1", "1.2.3", "🪙"]
        for pct in weird:
            with self.subTest(pct=pct[:20]):
                self.setUp()
                response = self.post("/flip", pct, "heads")
                self.assertEqual(response.status_code, 302)
                self.assertEqual(self.state()["flips"], 0)

    def test_broke_player_cannot_bet(self):
        self.set_balance("0")
        self.post("/flip", "50", "heads")  # any valid pct of $0 rounds to nothing
        state = self.state()
        self.assertEqual(state["message"], "That percentage is too small to bet anything.")
        self.assertEqual(state["flips"], 0)

    def test_removed_simulate_route_is_gone(self):
        self.assertEqual(self.post("/simulate", "1", "heads").status_code, 404)

    def test_get_on_post_only_routes_is_not_allowed(self):
        for route in ("/flip", "/reset"):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 405)

    def test_unknown_route_is_404(self):
        self.assertEqual(self.client.get("/nope").status_code, 404)


class ValidInputTests(CoinTossTestCase):
    def flip(self, pct, side, outcome):
        with mock.patch("coin_toss.random.random", return_value=outcome):
            return self.post("/flip", pct, side)

    def test_winning_flip_adds_the_staked_percentage(self):
        self.flip("5", "heads", HEADS)
        state = self.state()
        self.assertEqual(Decimal(state["balance"]), STARTING_BALANCE + stake_for(STARTING_BALANCE, "5"))
        self.assertEqual((state["flips"], state["heads"], state["tails"]), (1, 1, 0))
        self.assertEqual(state["message_class"], "win")

    def test_losing_flip_subtracts_the_staked_percentage(self):
        self.flip("5", "heads", TAILS)
        state = self.state()
        self.assertEqual(Decimal(state["balance"]), STARTING_BALANCE - stake_for(STARTING_BALANCE, "5"))
        self.assertEqual((state["flips"], state["heads"], state["tails"]), (1, 0, 1))
        self.assertEqual(state["message_class"], "lose")

    def test_accepted_bet_pct_formats(self):
        for pct in ["1", "2.5", ".5", "1.50", " 3 ", "007", "1.500", "100", "0.01"]:
            with self.subTest(pct=pct):
                self.setUp()
                self.flip(pct, "heads", HEADS)
                expected = STARTING_BALANCE + stake_for(STARTING_BALANCE, pct.strip())
                self.assertEqual(Decimal(self.state()["balance"]), expected)

    def test_message_shows_pct_and_dollar_stake(self):
        self.flip("5", "heads", HEADS)
        message = self.state()["message"]
        self.assertIn("TTTQ Breakout Win", message)
        self.assertIn("5%", message)
        self.assertIn("$5,000.00", message)

    def test_betting_whole_balance_and_losing_goes_broke(self):
        self.flip("100", "tails", HEADS)
        state = self.state()
        self.assertEqual(Decimal(state["balance"]), 0)
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn("Out of money", page)

    def test_stake_is_a_pct_of_the_current_balance_each_time(self):
        # Winning first grows the balance, so the second 10% bet is a bigger dollar amount.
        with mock.patch("coin_toss.random.random", side_effect=[HEADS, HEADS]):
            self.post("/flip", "10", "heads")
            balance_after_first = Decimal(self.state()["balance"])
            self.post("/flip", "10", "heads")
        expected_second_stake = stake_for(balance_after_first, "10")
        self.assertEqual(Decimal(self.state()["balance"]), balance_after_first + expected_second_stake)
        self.assertGreater(expected_second_stake, stake_for(STARTING_BALANCE, "10"))

    def test_bet_pct_is_remembered(self):
        self.flip("15", "heads", TAILS)
        self.assertEqual(self.state()["last_bet_pct"], "15")

    def test_side_is_remembered(self):
        self.flip("1", "tails", TAILS)
        self.assertEqual(self.state()["last_side"], "tails")

    def test_reset_clears_everything(self):
        self.flip("5", "heads", HEADS)
        self.client.post("/reset")
        self.client.get("/")
        state = self.state()
        self.assertEqual((state["balance"], state["flips"]), (str(STARTING_BALANCE), 0))


class GameSettingsTests(CoinTossTestCase):
    """Time limit and TTTQ Breakout Win odds must be set on the first flip and then lock in."""

    def test_invalid_time_limits_are_rejected(self):
        for value, message in INVALID_TIME_LIMITS:
            with self.subTest(value=value):
                self.setUp()
                self.assert_rejected(self.post("/flip", "1", "heads", time_limit=value), message)

    def test_invalid_heads_pcts_are_rejected(self):
        for value, message in INVALID_HEADS_PCTS:
            with self.subTest(value=value):
                self.setUp()
                self.assert_rejected(self.post("/flip", "1", "heads", heads_pct=value), message)

    def test_settings_are_checked_before_the_bet(self):
        # An invalid setting is reported even if the bet is also invalid.
        self.assert_rejected(
            self.post("/flip", "not-a-number", "heads", time_limit="0"),
            "Time limit must be between 1 and 60 minutes.",
        )

    def test_valid_settings_are_locked_in_on_first_flip(self):
        self.post("/flip", "1", "heads", time_limit="10", heads_pct="75")
        state = self.state()
        self.assertEqual(state["time_limit_minutes"], 10)
        self.assertEqual(state["heads_pct"], 75)
        self.assertIn("started_at", state)

    def test_settings_are_ignored_on_later_flips(self):
        self.post("/flip", "1", "heads", time_limit="10", heads_pct="75")
        self.post("/flip", "1", "heads", time_limit="1", heads_pct="1")
        state = self.state()
        self.assertEqual(state["time_limit_minutes"], 10)
        self.assertEqual(state["heads_pct"], 75)

    def test_configured_odds_affect_the_coin(self):
        # heads_pct=90: random.random() of 0.85 (85%) is heads, 0.95 (95%) is tails.
        with mock.patch("coin_toss.random.random", side_effect=[0.85, 0.95]):
            self.post("/flip", "1", "heads", heads_pct="90")
            self.post("/flip", "1", "heads")
        state = self.state()
        self.assertEqual((state["heads"], state["tails"]), (1, 1))

    def test_rejected_settings_are_remembered_for_redisplay(self):
        self.post("/flip", "1", "heads", time_limit="abc", heads_pct="75")
        page = self.client.get("/").get_data(as_text=True)  # the flip's own redirect
        self.assertIn('value="abc"', page)
        self.assertIn('value="75"', page)

    def test_settings_form_shown_before_first_flip(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn('name="time_limit"', page)
        self.assertIn('name="heads_pct"', page)
        self.assertIn(f'value="{coin_toss.DEFAULT_TIME_LIMIT_MINUTES}"', page)
        self.assertIn(f'value="{coin_toss.DEFAULT_HEADS_PCT}"', page)

    def test_settings_locked_display_after_first_flip(self):
        self.post("/flip", "1", "heads", time_limit="10", heads_pct="75")
        page = self.client.get("/").get_data(as_text=True)
        self.assertNotIn('name="time_limit"', page)
        self.assertNotIn('name="heads_pct"', page)
        self.assertIn("Time limit: 10 min", page)
        self.assertIn("TTTQ Breakout Win odds: 75% / TTTQ Breakout Fail 25%", page)

    def test_odds_line_follows_configured_probability(self):
        self.post("/flip", "1", "heads", heads_pct="35")
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn("TTTQ Breakout Win 35% &middot; TTTQ Breakout Fail 65%", page)


class TimeLimitTests(CoinTossTestCase):
    START = 1_000_000.0

    # Replace the `time` module only inside coin_toss. Patching time.time itself would
    # also move Flask's clock, and it rejects session cookies signed in the past/future.
    def clock(self, now):
        return mock.patch("coin_toss.time", mock.Mock(time=mock.Mock(return_value=now)))

    def flip_at(self, now, bet_pct="1", side="heads", outcome=HEADS, time_limit=None, heads_pct=None):
        with self.clock(now), mock.patch("coin_toss.random.random", return_value=outcome):
            return self.post("/flip", bet_pct, side, time_limit=time_limit, heads_pct=heads_pct)

    def page_at(self, now):
        with self.clock(now):
            return self.client.get("/").get_data(as_text=True)

    def test_clock_waits_for_first_flip(self):
        page = self.page_at(self.START)
        self.assertIn(">5:00<", page)
        self.assertIn("Starts on first flip", page)
        self.assertIn('data-running="no"', page)
        self.assertNotIn("started_at", self.state())

    def test_first_flip_starts_clock(self):
        self.flip_at(self.START)
        self.assertEqual(self.state()["started_at"], self.START)
        page = self.page_at(self.START)
        self.assertIn('data-running="yes"', page)
        self.assertNotIn("Starts on first flip", page)

    def test_later_flips_do_not_restart_clock(self):
        self.flip_at(self.START)
        self.flip_at(self.START + 100)
        self.assertEqual(self.state()["started_at"], self.START)

    def test_countdown_shows_time_remaining(self):
        for elapsed, shown in [(0, "5:00"), (61, "3:59"), (299, "0:01")]:
            with self.subTest(elapsed=elapsed):
                self.setUp()
                self.flip_at(self.START)
                page = self.page_at(self.START + elapsed)  # the page shown after the flip
                self.assertIn(f'data-left="{300 - elapsed}"', page)
                self.assertIn(f">{shown}<", page)
                self.assertIn('id="time-up" hidden', page)

    def test_refresh_resets_the_clock(self):
        self.flip_at(self.START)
        self.assertIn(">4:50<", self.page_at(self.START + 10))  # redirect after the flip
        page = self.page_at(self.START + 20)                    # user refreshes
        self.assertIn(">5:00<", page)
        self.assertIn("Starts on first flip", page)
        self.assertNotIn("started_at", self.state())

    def test_refresh_resets_balance_and_stats_too(self):
        self.flip_at(self.START)
        self.page_at(self.START)       # the flip's own redirect: state kept
        self.page_at(self.START + 20)  # a real refresh: everything resets
        state = self.state()
        self.assertEqual(state["balance"], str(STARTING_BALANCE))
        self.assertEqual((state["flips"], state["heads"], state["tails"]), (0, 0, 0))
        self.assertNotIn("time_limit_minutes", state)
        self.assertNotIn("heads_pct", state)

    def test_next_flip_after_refresh_is_a_new_game(self):
        self.flip_at(self.START)
        self.page_at(self.START)
        self.page_at(self.START + 200)  # refresh
        self.flip_at(self.START + 250)
        state = self.state()
        self.assertEqual(state["started_at"], self.START + 250)
        self.assertEqual(state["flips"], 1)
        self.assertIn(">4:00<", self.page_at(self.START + 310))

    def test_refresh_after_time_up_starts_a_fresh_game(self):
        self.flip_at(self.START)
        self.flip_at(self.START + 300)  # too late, ignored
        self.assertIn('data-running="no"', self.page_at(self.START + 300))
        self.assertIn(">5:00<", self.page_at(self.START + 301))  # refresh
        self.flip_at(self.START + 302)
        self.assertEqual(self.state()["flips"], 1)  # the first flip of the new game

    def test_rejected_bet_does_not_restart_clock(self):
        self.flip_at(self.START)
        self.page_at(self.START)
        self.flip_at(self.START + 50, bet_pct="abc")
        page = self.page_at(self.START + 50)
        self.assertIn(">4:10<", page)
        self.assertIn("Enter the bet as a percentage", page)

    def test_can_flip_just_before_limit(self):
        self.flip_at(self.START)
        self.flip_at(self.START + 299.9)
        self.assertEqual(self.state()["flips"], 2)

    def test_cannot_flip_after_limit(self):
        self.flip_at(self.START)  # 1% win: 100,000.00 -> 101,000.00
        expected_balance = STARTING_BALANCE + stake_for(STARTING_BALANCE, "1")
        for elapsed in (300, 301, 10_000):
            with self.subTest(elapsed=elapsed):
                self.flip_at(self.START + elapsed)
                state = self.state()
                self.assertEqual(state["flips"], 1)
                self.assertEqual(Decimal(state["balance"]), expected_balance)

    def test_time_up_is_checked_before_bet(self):
        self.flip_at(self.START)
        self.client.get("/")  # clear the flip's message
        self.flip_at(self.START + 300, bet_pct="abc")
        self.assertNotIn("message", self.state())

    def test_page_after_time_up(self):
        self.flip_at(self.START)                          # 1% win: 100,000 -> 101,000
        self.flip_at(self.START + 10, outcome=TAILS)       # 1% loss of 101,000 -> 99,990
        page = self.page_at(self.START + 300)
        self.assertIn("Time's up! You finished with $99,990.00 after 2 flips.", page)
        self.assertNotIn('id="time-up" hidden', page)
        self.assertIn(">0:00<", page)
        self.assertIn('data-running="no"', page)
        self.assertEqual(page.count("disabled>"), 2)  # bet input and Flip!
        self.assertRegex(page, r"disabled>\s*Time's up\s*</button>")

    def test_reset_restarts_clock(self):
        self.flip_at(self.START)
        self.client.post("/reset")
        self.assertIn(">5:00<", self.page_at(self.START + 100))
        self.flip_at(self.START + 100)
        self.assertEqual(self.state()["flips"], 1)

    def test_limit_follows_configured_minutes(self):
        self.flip_at(self.START, time_limit="1")
        self.assertEqual(self.state()["time_limit_minutes"], 1)
        self.assertIn(">0:50<", self.page_at(self.START + 10))
        self.flip_at(self.START + 60)  # time's up at 60s for a 1-minute game
        self.assertEqual(self.state()["flips"], 1)


class PageTests(CoinTossTestCase):
    def page(self):
        return self.client.get("/").get_data(as_text=True)

    def test_bet_input_has_browser_validation(self):
        page = self.page()
        self.assertIn('type="number" step="0.01" min="0.01" max="100"', page)
        self.assertIn("required", page)

    def test_side_is_required(self):
        self.assertIn('value="heads" required', self.page())

    def test_side_labels_use_tttq_terms(self):
        page = self.page()
        self.assertIn("TTTQ Breakout Win</label>", page)
        self.assertIn("TTTQ Breakout Fail</label>", page)

    def test_controls_disabled_when_broke(self):
        with mock.patch("coin_toss.random.random", return_value=TAILS):
            self.post("/flip", "100", "heads")  # bet it all and lose
        page = self.page()
        self.assertIn("Out of money", page)
        self.assertEqual(page.count("disabled>"), 2)  # bet input and Flip!

    def test_no_simulate_button(self):
        self.assertNotIn("Simulate", self.page())

    def test_default_odds_shown_before_first_flip(self):
        self.assertIn("TTTQ Breakout Win 60% &middot; TTTQ Breakout Fail 40%", self.page())

    def test_starting_balance_shown_with_thousands_separator(self):
        page = self.page()
        self.assertIn("$100,000.00", page)
        self.assertIn("Reset to $100,000.00", page)

    def test_bet_preview_data_carries_raw_balance(self):
        self.assertIn('data-balance="100000.00"', self.page())

    def test_heads_percentage(self):
        with mock.patch("coin_toss.random.random", side_effect=[HEADS, HEADS, TAILS]):
            self.post("/flip", "1", "heads")
            self.post("/flip", "1", "heads")
            self.post("/flip", "1", "heads")
        self.assertIn("66.7%", self.page())

    def test_message_shown_once(self):
        self.post("/flip", "abc", "heads")
        self.assertIn("Enter the bet as a percentage", self.page())
        self.assertNotIn("Enter the bet as a percentage", self.page())


if __name__ == "__main__":
    unittest.main()
