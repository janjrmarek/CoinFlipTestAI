"""Tests for coin_toss.py. Run from the repo root with:  python -m unittest discover -s tests"""

import os
import sys
import unittest
from decimal import Decimal
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import coin_toss  # noqa: E402

HEADS = 0.0  # random.random() values that force each outcome
TAILS = 0.99

INVALID_BETS = [
    ("", "Enter a bet amount."),
    ("   ", "Enter a bet amount."),
    ("abc", "Enter the bet as a number, like 1.50."),
    ("NaN", "Enter the bet as a number, like 1.50."),
    ("sNaN", "Enter the bet as a number, like 1.50."),
    ("Infinity", "Enter the bet as a number, like 1.50."),
    ("-Infinity", "Enter the bet as a number, like 1.50."),
    ("1e3", "Enter the bet as a number, like 1.50."),
    ("1e30", "Enter the bet as a number, like 1.50."),
    ("1,000", "Enter the bet as a number, like 1.50."),
    ("1_0", "Enter the bet as a number, like 1.50."),
    ("$5", "Enter the bet as a number, like 1.50."),
    ("5 5", "Enter the bet as a number, like 1.50."),
    ("١٢", "Enter the bet as a number, like 1.50."),  # Arabic-Indic digits
    (".", "Enter the bet as a number, like 1.50."),
    ("-", "Enter the bet as a number, like 1.50."),
    ("0", "Enter a bet greater than $0."),
    ("0.00", "Enter a bet greater than $0."),
    ("-0", "Enter a bet greater than $0."),
    ("-5", "Enter a bet greater than $0."),
    ("0.004", "Bets must be in whole cents."),  # used to round to $0.00
    ("1.999", "Bets must be in whole cents."),
    ("0.001", "Bets must be in whole cents."),
    ("25.01", "You only have $25.00 to bet."),
    ("100", "You only have $25.00 to bet."),
    ("9" * 100, "You only have $25.00 to bet."),
]

INVALID_SIDES = [None, "", "edge", "HEADS", "Tails", "heads "]


class CoinTossTestCase(unittest.TestCase):
    def setUp(self):
        coin_toss.app.config["TESTING"] = True
        self.client = coin_toss.app.test_client()
        self.client.get("/")  # initialise the session

    def post(self, route, bet=None, side=None):
        data = {}
        if bet is not None:
            data["bet"] = bet
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
        self.assertEqual(state["balance"], "25.00")
        self.assertEqual(state["flips"], 0)


class InvalidInputTests(CoinTossTestCase):
    def test_invalid_bets_are_rejected_on_flip(self):
        for bet, message in INVALID_BETS:
            with self.subTest(bet=bet):
                self.setUp()
                self.assert_rejected(self.post("/flip", bet, "heads"), message)

    def test_invalid_bets_are_rejected_on_simulate(self):
        for bet, message in INVALID_BETS:
            with self.subTest(bet=bet):
                self.setUp()
                self.assert_rejected(self.post("/simulate", bet, "heads"), message)

    def test_missing_bet_field(self):
        for route in ("/flip", "/simulate"):
            with self.subTest(route=route):
                self.setUp()
                self.assert_rejected(self.post(route, side="heads"), "Enter a bet amount.")

    def test_invalid_sides_are_rejected(self):
        for route in ("/flip", "/simulate"):
            for side in INVALID_SIDES:
                with self.subTest(route=route, side=side):
                    self.setUp()
                    self.assert_rejected(self.post(route, "1.00", side), "Pick heads or tails.")

    def test_rejected_input_never_causes_server_error(self):
        weird = ["\x00", "1" * 10000, "0x10", "1..2", "--1", "+1", "1.2.3", "🪙"]
        for route in ("/flip", "/simulate"):
            for bet in weird:
                with self.subTest(route=route, bet=bet[:20]):
                    self.setUp()
                    response = self.post(route, bet, "heads")
                    self.assertEqual(response.status_code, 302)
                    self.assertEqual(self.state()["flips"], 0)

    def test_broke_player_cannot_bet(self):
        self.set_balance("0")
        for route in ("/flip", "/simulate"):
            with self.subTest(route=route):
                self.post(route, "0.01", "heads")
                state = self.state()
                self.assertEqual(state["message"], "You only have $0.00 to bet.")
                self.assertEqual(state["flips"], 0)

    def test_get_on_post_only_routes_is_not_allowed(self):
        for route in ("/flip", "/simulate", "/reset"):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 405)

    def test_unknown_route_is_404(self):
        self.assertEqual(self.client.get("/nope").status_code, 404)


class ValidInputTests(CoinTossTestCase):
    def flip(self, bet, side, outcome):
        with mock.patch("coin_toss.random.random", return_value=outcome):
            return self.post("/flip", bet, side)

    def test_winning_flip_adds_bet(self):
        self.flip("5", "heads", HEADS)
        state = self.state()
        self.assertEqual(Decimal(state["balance"]), Decimal("30.00"))
        self.assertEqual((state["flips"], state["heads"], state["tails"]), (1, 1, 0))
        self.assertEqual(state["message_class"], "win")

    def test_losing_flip_subtracts_bet(self):
        self.flip("5", "heads", TAILS)
        state = self.state()
        self.assertEqual(Decimal(state["balance"]), Decimal("20.00"))
        self.assertEqual((state["flips"], state["heads"], state["tails"]), (1, 0, 1))
        self.assertEqual(state["message_class"], "lose")

    def test_accepted_bet_formats(self):
        for bet, expected in [("1", "26.00"), ("2.5", "27.50"), (".5", "25.50"),
                              ("1.50", "26.50"), (" 3 ", "28.00"), ("007", "32.00"),
                              ("1.500", "26.50"), ("25", "50.00"), ("0.01", "25.01")]:
            with self.subTest(bet=bet):
                self.setUp()
                self.flip(bet, "heads", HEADS)
                self.assertEqual(Decimal(self.state()["balance"]), Decimal(expected))

    def test_betting_whole_balance_and_losing_goes_broke(self):
        self.flip("25.00", "tails", HEADS)
        state = self.state()
        self.assertEqual(Decimal(state["balance"]), 0)
        self.assertEqual(state["last_bet"], "0")
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn("Out of money", page)

    def test_next_bet_is_capped_at_remaining_balance(self):
        self.flip("20", "heads", TAILS)
        self.assertEqual(Decimal(self.state()["last_bet"]), Decimal("5.00"))

    def test_side_is_remembered(self):
        self.flip("1", "tails", TAILS)
        self.assertEqual(self.state()["last_side"], "tails")

    def test_reset_clears_everything(self):
        self.flip("5", "heads", HEADS)
        self.client.post("/reset")
        self.client.get("/")
        state = self.state()
        self.assertEqual((state["balance"], state["flips"]), ("25.00", 0))


class SimulateTests(CoinTossTestCase):
    def simulate(self, bet, side, outcome):
        with mock.patch("coin_toss.random.random", return_value=outcome):
            return self.post("/simulate", bet, side)

    def test_runs_full_simulation(self):
        self.simulate("1", "heads", HEADS)
        state = self.state()
        self.assertEqual(state["flips"], 300)
        self.assertEqual(Decimal(state["balance"]), Decimal("325.00"))
        self.assertIn("Simulated 300 flips", state["message"])

    def test_stops_when_broke(self):
        self.simulate("1", "heads", TAILS)
        state = self.state()
        self.assertEqual(state["flips"], 25)
        self.assertEqual(Decimal(state["balance"]), 0)
        self.assertIn("Went broke early", state["message"])

    def test_bets_remaining_balance_when_short(self):
        self.simulate("10", "heads", TAILS)  # 25 -> 15 -> 5 -> 0 (last bet is only 5)
        state = self.state()
        self.assertEqual(state["flips"], 3)
        self.assertEqual(Decimal(state["balance"]), 0)

    def test_random_run_keeps_counts_consistent(self):
        self.post("/simulate", "0.50", "heads")
        state = self.state()
        self.assertEqual(state["heads"] + state["tails"], state["flips"])
        self.assertGreaterEqual(Decimal(state["balance"]), 0)


class PageTests(CoinTossTestCase):
    def page(self):
        return self.client.get("/").get_data(as_text=True)

    def test_bet_input_has_browser_validation(self):
        page = self.page()
        self.assertIn('type="number" step="0.01" min="0.01" max="25.00"', page)
        self.assertIn("required", page)

    def test_side_is_required(self):
        self.assertIn('value="heads" required', self.page())

    def test_controls_disabled_when_broke(self):
        self.set_balance("0")
        page = self.page()
        self.assertIn("Out of money", page)
        self.assertEqual(page.count("disabled>"), 3)  # bet input, Flip!, simulate

    def test_simulate_label_follows_setting(self):
        for minutes, label in [(1, "Simulate 1 minute (60 flips)"),
                               (5, "Simulate 5 minutes (300 flips)")]:
            with self.subTest(minutes=minutes), \
                    mock.patch.object(coin_toss, "SIMULATED_MINUTES", minutes):
                self.assertIn(label, self.page())

    def test_heads_percentage(self):
        with self.client.session_transaction() as sess:
            sess.update(flips=3, heads=2, tails=1)
        self.assertIn("66.7%", self.page())

    def test_message_shown_once(self):
        self.post("/flip", "abc", "heads")
        self.assertIn("Enter the bet as a number", self.page())
        self.assertNotIn("Enter the bet as a number", self.page())


if __name__ == "__main__":
    unittest.main()
