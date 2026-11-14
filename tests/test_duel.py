"""Live-duel room logic, tested with fake connections and short timers (no network)."""
import os
os.environ.setdefault("SCAMDOJO_FEEDS", "0")  # no live feeds during tests
import json
import queue
import threading
import time
import unittest

import duel


class FakeWS:
    def __init__(self):
        self.inbox, self.outbox, self.closed = queue.Queue(), [], False

    def send(self, data):
        if self.closed:
            raise ConnectionError("closed")
        self.outbox.append(json.loads(data))

    def receive(self, timeout=None):
        try:
            item = self.inbox.get(timeout=min(timeout or 1, 0.3))
        except queue.Empty:
            return None
        if item is None:
            raise ConnectionError("closed")
        return item

    def close(self):
        self.closed = True

    def say(self, **msg):
        self.inbox.put(json.dumps(msg))

    def hang_up(self):
        self.inbox.put(None)

    def wait_for(self, kind, timeout=6):
        end = time.time() + timeout
        seen = 0
        while time.time() < end:
            for m in self.outbox[seen:]:
                if m.get("t") == kind:
                    return m
            seen = len(self.outbox)
            time.sleep(0.02)
        raise AssertionError("never received %r; got %s" % (kind, [m.get("t") for m in self.outbox]))


def start(ws, code, name="Tester"):
    t = threading.Thread(target=duel.serve, args=(ws, code, name), daemon=True)
    t.start()
    return t


def card(i, scam=True):
    h = [{"start": 5, "end": 15, "kind": "rule", "label": "Fake KYC"}, {"start": 30, "end": 40, "kind": "link", "label": "Link"}] if scam else []
    return {"id": "c%d" % i, "sender": "VK-X", "channel": "sms", "text": "x" * 50, "scam": scam, "lesson": "lesson %d" % i, "ai": {"highlights": h}}


class Rooms(unittest.TestCase):
    def setUp(self):
        duel.configure([card(i) for i in range(6)] + [card(10 + i, False) for i in range(3)], rounds=3, seconds=2.0, bot_wait=0.6, between=0.25, countdown=0.1, bot_start=0.2, bot_gap=0.2)
        duel.MANAGER.rooms.clear()

    def scam_only(self):
        duel.configure([card(i) for i in range(6)], rounds=3, seconds=2.0, bot_wait=0.6, between=0.25, countdown=0.1, bot_start=0.2, bot_gap=0.2)

    def two_players(self):
        a, b = FakeWS(), FakeWS()
        start(a, "NEW", "Asha")
        code = a.wait_for("joined")["code"]
        start(b, code.lower(), "Bala")
        b.wait_for("joined")
        return a, b, code

    def test_code_format_and_second_player_joins(self):
        a, b, code = self.two_players()
        self.assertRegex(code, "^[A-HJKMNP-Z2-9]{4}$")
        self.assertEqual(a.wait_for("player_joined")["name"], "Bala")
        self.assertEqual(a.wait_for("round")["text"], b.wait_for("round")["text"])  # same message for both

    def test_first_claim_wins_and_late_claim_is_refused(self):
        self.scam_only()
        a, b, _ = self.two_players()
        a.wait_for("round")
        b.wait_for("round")
        a.say(t="claim", start=5, end=10)
        self.assertEqual(a.wait_for("claimed")["by"], "A")
        b.say(t="claim", start=6, end=9)
        self.assertEqual(b.wait_for("late")["by"], "A")
        c = b.wait_for("claimed")
        self.assertEqual(c["scores"]["A"], 2)
        self.assertEqual(c["scores"]["B"], 0)

    def test_wrong_tap_costs_a_point_but_not_below_zero(self):
        a, b, _ = self.two_players()
        a.wait_for("round")
        a.say(t="claim", start=20, end=25)
        self.assertEqual(a.wait_for("wrong")["scores"]["A"], 0)

    def test_round_ends_when_everyone_is_done(self):
        a, b, _ = self.two_players()
        first = a.wait_for("round")
        a.say(t="done"); b.say(t="done")
        end = a.wait_for("round_end")
        self.assertIn(end["truth"], ("scam", "genuine"))
        self.assertTrue(end["lesson"].startswith("lesson"))

    def test_bot_joins_after_waiting_and_plays(self):
        a = FakeWS()
        start(a, "NEW", "Solo")
        a.wait_for("joined")
        joined = a.wait_for("player_joined", timeout=4)
        self.assertTrue(joined.get("bot"))
        rnd = a.wait_for("round")
        end = a.wait_for("round_end", timeout=6)
        if end["truth"] == "scam":
            self.assertTrue(any(s["by"] == "B" for s in end["spans"]))  # the bot claimed flags
        else:
            self.assertEqual(end["spans"], [])

    def test_match_finishes_with_a_winner(self):
        a = FakeWS()
        start(a, "NEW", "Solo")
        a.wait_for("joined")
        # play every round quickly as a human: lock after each round starts
        for _ in range(3):
            a.wait_for("round", timeout=8)
            a.say(t="done")
            a.wait_for("round_end", timeout=8)
            time.sleep(0.05)
            a.outbox[:] = [m for m in a.outbox if m.get("t") not in ("round", "round_end")]
        m = a.wait_for("match_end", timeout=8)
        self.assertIn(m["winner"], ("A", "B", "tie"))

    def test_opponent_leaving_hands_the_seat_to_the_bot(self):
        a, b, _ = self.two_players()
        a.wait_for("round")
        b.hang_up()
        self.assertEqual(a.wait_for("opponent_left")["name"], "Bala")

    def test_errors_for_bad_codes_and_full_rooms(self):
        x = FakeWS(); start(x, "ZZZZ", "X")
        self.assertIn("No room", x.wait_for("error")["message"])
        a, b, code = self.two_players()
        c = FakeWS(); start(c, code, "Third")
        self.assertIn("full", c.wait_for("error")["message"])

    def test_names_are_sanitised_and_garbage_is_ignored(self):
        self.scam_only()
        self.assertEqual(duel.clean_name("<b>Hi</b>\x00" + "x" * 40), "bHi/bxxxxxxxxxxxxxxxx"[:20])
        a, b, _ = self.two_players()
        a.wait_for("round")
        for raw in ("not json", "[]", json.dumps({"t": "claim", "start": "x", "end": 3}), json.dumps({"t": "claim", "start": 9, "end": 2}), json.dumps({"t": "nope"})):
            a.inbox.put(raw)
        a.say(t="claim", start=5, end=10)
        self.assertEqual(a.wait_for("claimed")["by"], "A")  # still alive after garbage

    def test_oversized_messages_disconnect_the_sender(self):
        a, b, _ = self.two_players()
        a.wait_for("round")
        a.inbox.put("x" * 5000)
        end = time.time() + 3
        while not a.closed and time.time() < end:
            time.sleep(0.05)
        self.assertTrue(a.closed)
        self.assertEqual(b.wait_for("opponent_left")["name"], "Asha")


if __name__ == "__main__":
    unittest.main()
