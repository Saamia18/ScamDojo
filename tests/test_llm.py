"""Card generator tests: validation, the LLM path (mocked), the template fallback, and the endpoints."""
import os
os.environ.setdefault("SCAMDOJO_FEEDS", "0")
import json
import tempfile
import unittest

import accounts
import db
import llm


def llm_reply(cards):
    return lambda url, headers, payload, timeout=45: {"content": [{"type": "text", "text": "```json\n" + json.dumps({"cards": cards}) + "\n```"}]}


GOOD = {"sender": "AD-ELECBD", "channel": "sms", "text": "Your electricity will be disconnected tonight 9:30 pm. Call officer 9876543210 immediately to update bill.", "scam": True, "loss": 2000,
        "lesson": "Utilities do not disconnect power by SMS at night.", "flags": ["disconnected tonight"],
        "hi": {"text": "आज रात 9:30 बजे आपकी बिजली काट दी जाएगी। तुरंत अधिकारी को 9876543210 पर कॉल करें।", "lesson": "बिजली विभाग SMS से बिजली नहीं काटता।", "flags": ["बिजली काट दी जाएगी", "phrase that is not there"]}}


class Generator(unittest.TestCase):
    def setUp(self):
        db.configure(os.path.join(tempfile.mkdtemp(), "g.db"))
        os.environ.pop("ANTHROPIC_API_KEY", None)

    def tearDown(self):
        llm.transport = llm._post_json
        os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_template_fallback_gives_valid_cards_for_every_category(self):
        for cat in llm.CATEGORIES:
            cards, src = llm.generate(cat, "en", 3, 1)
            self.assertEqual(src, "template")
            self.assertTrue(cards, cat)
            for c in cards:
                self.assertTrue(c["generated"] and c["id"].startswith("gen-") and c["boss"] in ("kraken", "llama", "octopus", "jackal", "cobra"))
                self.assertNotRegex(c["text"], r"(?<!\d)[6-9]\d{9}(?!\d)")  # no full phone numbers

    def test_llm_path_masks_phones_validates_flags_and_translations(self):
        os.environ["ANTHROPIC_API_KEY"] = "test"
        llm.transport = llm_reply([GOOD])
        cards, src = llm.generate("electricity", "hi", 2, 1)
        self.assertEqual(src, "llm")
        c = cards[0]
        self.assertIn("98XXXXXX10", c["text"]); self.assertNotIn("9876543210", c["text"])
        self.assertEqual(c["i18n"]["hi"]["flags"], ["बिजली काट दी जाएगी"])  # the flag that is not in the translation is dropped
        self.assertIn("98XXXXXX10", c["i18n"]["hi"]["text"])

    def test_bad_cards_are_rejected(self):
        bad = [dict(GOOD, text="Update your KYC now at https://www.sbi.co.in/kyc or your account will be blocked today"),   # working official domain in a scam
               dict(GOOD, text="Hi"), dict(GOOD, lesson=""), "not a dict", dict(GOOD, text="Hello <script>alert(1)</script> your parcel is held, pay a fee now at bit.ly/abc"),
               dict(GOOD, text="See you at the cafe at five, bring the notes", scam=True)]  # a 'scam' with nothing the engine can flag
        for raw in bad:
            self.assertIsNone(llm.validate_card(raw, "electricity", "en"), raw)

    def test_if_the_llm_fails_the_templates_take_over(self):
        os.environ["ANTHROPIC_API_KEY"] = "test"
        def boom(*a, **k): raise OSError("network down")
        llm.transport = boom
        cards, src = llm.generate("kyc", "en", 2, 1)
        self.assertEqual(src, "template"); self.assertTrue(cards)

    def test_duplicates_are_not_stored_twice(self):
        os.environ["ANTHROPIC_API_KEY"] = "test"
        llm.transport = llm_reply([GOOD])
        llm.generate("electricity", "en", 2, 1)
        first = len(llm.latest())
        llm.transport = llm_reply([GOOD])
        llm.generate("electricity", "en", 2, 1)  # same text again: rejected, templates fill in instead
        texts = [c["text"] for c in llm.latest()]
        self.assertEqual(len([t for t in texts if "98XXXXXX10" in t]), 1)
        self.assertGreaterEqual(len(llm.latest()), first)


class Endpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import server
        accounts.configure(os.path.join(tempfile.mkdtemp(), "e.db"))
        cls.server = server

    def setUp(self):
        accounts.limiter.hits.clear(); self.server._limiter.hits.clear()
        self.c = self.server.app.test_client()

    def test_requires_login_and_valid_category(self):
        self.assertEqual(self.c.post("/api/cards/generate", json={"category": "kyc"}).status_code, 401)
        self.c.post("/api/auth/register", json={"username": "gen_user", "password": "generate pw 1"})
        self.assertEqual(self.c.post("/api/cards/generate", json={"category": "nope"}).status_code, 400)

    def test_generated_cards_join_the_deck_and_are_rate_limited(self):
        self.c.post("/api/auth/register", json={"username": "gen_user2", "password": "generate pw 2"})
        r = self.c.post("/api/cards/generate", json={"category": "digital_arrest", "lang": "en", "count": 2})
        self.assertEqual(r.status_code, 200)
        ids = [x["id"] for x in r.json["cards"]]
        deck = self.c.get("/api/cards").json["cards"]
        got = [x for x in deck if x["id"] in ids]
        self.assertEqual(len(got), len(ids)); self.assertTrue(all(x["generated"] and "ai" in x and x["ai"]["highlights"] is not None for x in got))
        self.assertEqual(len(self.c.get("/api/cards").json["cards"]) - len(got) >= 55, True)  # the 55 curated cards are still there
        for _ in range(6):
            last = self.c.post("/api/cards/generate", json={"category": "kyc"})
        self.assertEqual(last.status_code, 429)


if __name__ == "__main__":
    unittest.main()
