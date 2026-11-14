"""Run with:  python -m unittest discover -s tests -v"""
import os
os.environ.setdefault("SCAMDOJO_FEEDS", "0")  # no live feeds during tests
import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from engine import fusion
from engine.normalize import normalize
from engine.rules import run_rules
from engine.urlcheck import analyze_url, find_urls


class Normalize(unittest.TestCase):
    def test_spaced_letters_and_offsets(self):
        n = normalize("Your K Y C is pending")
        i = n.text.index("kyc")
        a, b = n.span(i, i + 3)
        self.assertEqual(n.raw[a:b], "K Y C")

    def test_homoglyphs_and_zero_width(self):
        n = normalize("Раytm l\u200bink")  # Cyrillic Р, а + zero-width space
        self.assertIn("paytm", n.text)
        self.assertIn("link", n.text)
        self.assertGreater(n.flags["homoglyph"], 0)
        self.assertEqual(n.flags["zero_width"], 1)

    def test_leetspeak_only_for_scam_words(self):
        self.assertIn("account", normalize("your acc0unt").text)
        self.assertIn("r2d2", normalize("meet r2d2 today").text)


class Links(unittest.TestCase):
    def test_official_domains_are_safe(self):
        for u in ["https://www.sbi.co.in/web", "https://uidai.gov.in/en/", "meet.google.com/abc"]:
            self.assertTrue(analyze_url(u)["official"], u)

    def test_fake_domains_are_flagged(self):
        for u in ["http://sbi-kyc-update.xyz/login", "paytrn.com/refund", "https://secure.hdfcbank.com.verify-now.top/kyc", "http://192.168.4.7/pay"]:
            self.assertGreaterEqual(analyze_url(u)["risk"], 0.65, u)

    def test_find_urls_trims_punctuation(self):
        self.assertEqual([u for _, _, u in find_urls("Visit bit.ly/ab12, or http://x.xyz/a.")], ["bit.ly/ab12", "http://x.xyz/a"])


class Rules(unittest.TestCase):
    def ids(self, text):
        return {h["id"] for h in run_rules(normalize(text))[0]}

    def test_otp_request_vs_warning(self):
        self.assertIn("otp_ask", self.ids("Please share your OTP with our executive"))
        self.assertNotIn("otp_ask", self.ids("Do not share your OTP with anyone"))

    def test_as_requested_is_not_a_threat(self):
        self.assertNotIn("account_threat", self.ids("As requested, your card has been blocked."))

    def test_family_impersonation(self):
        self.assertIn("family_impersonation", self.ids("Hi Mom, I lost my phone, this is my new number. Send money urgently"))


class Pipeline(unittest.TestCase):
    def test_known_scam_and_known_genuine(self):
        scam = fusion.analyze("Dear SBI user, your KYC expired. Update at http://sbi-kyc.xyz/login within 2 hours or account blocked")
        self.assertEqual(scam["verdict"], "scam")
        self.assertTrue(scam["highlights"])
        ok = fusion.analyze("123456 is your OTP for login. Do not share it with anyone. -HDFC Bank")
        self.assertEqual(ok["verdict"], "safe")

    def test_highlights_point_into_original_text(self):
        text = "Your K Y C is expired, update now"
        r = fusion.analyze(text)
        for h in r["highlights"]:
            self.assertTrue(0 <= h["start"] < h["end"] <= len(text))

    def test_empty_and_long_input(self):
        self.assertIn("verdict", fusion.analyze("hi"))
        self.assertLessEqual(fusion.analyze("a " * 10000)["length"], fusion.MAX_CHARS)


class Report(unittest.TestCase):
    def test_bootstrap_interval_is_ordered_and_contains_estimate(self):
        from engine import report
        pairs = [(True, True)] * 20 + [(True, False)] * 5 + [(False, False)] * 20 + [(False, True)] * 5
        ci = report.bootstrap_ci(pairs, n=200)
        for lo, hi in ci.values():
            self.assertLessEqual(lo, hi)
        f1 = report._prf(pairs)[2]
        self.assertLessEqual(ci["f1"][0], f1)
        self.assertLessEqual(f1, ci["f1"][1])

    def test_normalizer_switch_changes_behaviour(self):
        text = "Your b4nk acc0unt is bl0cked, verify your O T P now"
        on = fusion.analyze(text, normalizer=True)
        off = fusion.analyze(text, normalizer=False)
        self.assertTrue(on["normalization"]["leet"] > 0 or on["normalization"]["spaced"] > 0)
        self.assertEqual(off["normalization"]["leet"] + off["normalization"]["spaced"], 0)

    def test_metrics_file_has_the_technical_sections(self):
        with open("engine/model/metrics.json", encoding="utf-8") as f:
            m = json.load(f)
        for key in ("evasion", "link_benchmark", "rule_stats", "performance"):
            self.assertIn(key, m)
        for name, s in m["sets"].items():
            for key in ("ci", "thresholds", "calibration", "confidence", "categories"):
                self.assertIn(key, s, (name, key))


class Translations(unittest.TestCase):
    def test_every_card_has_hindi_and_kannada_with_valid_flags(self):
        with open("web/data/cards.json", encoding="utf-8") as f:
            data = json.load(f)
        for c in data["cards"]:
            for lang in ("hi", "kn"):
                tr = c["i18n"][lang]
                self.assertTrue(tr["text"] and tr["lesson"], (c["id"], lang))
                for flag in tr["flags"]:
                    self.assertIn(flag, tr["text"], (c["id"], lang))
                if c["scam"]:
                    self.assertTrue(tr["flags"], "scam card needs at least one red flag: %s %s" % (c["id"], lang))
        for b in data["bosses"]:
            for lang in ("hi", "kn"):
                self.assertEqual(set(b["i18n"][lang]), {"tagline", "intro", "defeat", "lesson"})


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import server
        cls.client = server.app.test_client()

    def test_endpoints(self):
        self.assertEqual(self.client.get("/api/health").json["status"], "ok")
        self.assertEqual(len(self.client.get("/api/cards").json["cards"]), 55)
        self.assertIn("sets", self.client.get("/api/metrics").json)
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/missing.js").status_code, 404)
        self.assertEqual(self.client.get("/api/nope").status_code, 404)

    def test_analyze_scan_and_bad_input(self):
        for path in ("/api/analyze", "/api/scan"):
            r = self.client.post(path, json={"text": "You won a lottery, pay fee"})
            self.assertEqual(r.status_code, 200)
            self.assertIn("risk", r.json)
        self.assertEqual(self.client.post("/api/analyze", data=b"nope").status_code, 400)
        self.assertEqual(self.client.post("/api/analyze", json={"text": "   "}).status_code, 400)
        self.assertEqual(self.client.post("/api/analyze", data=b"x" * 70000).status_code, 413)

    def test_errors_are_json_and_never_leak_traces(self):
        r = self.client.get("/api/does-not-exist")
        self.assertEqual(r.content_type, "application/json")
        self.assertIn("error", r.json)

    def test_cors_only_on_public_endpoints(self):
        self.assertEqual(self.client.get("/api/health").headers["Access-Control-Allow-Origin"], "*")
        self.assertEqual(self.client.post("/api/analyze", json={"text": "hello there friend"}).headers["Access-Control-Allow-Origin"], "*")
        self.assertNotIn("Access-Control-Allow-Origin", self.client.get("/api/me").headers)


if __name__ == "__main__":
    unittest.main()
