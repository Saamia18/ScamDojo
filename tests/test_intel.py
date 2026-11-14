"""Threat-intelligence tests with simulated feeds (no network)."""
import os
os.environ.setdefault("SCAMDOJO_FEEDS", "0")
import json
import time
import unittest

from engine import fusion
from engine.intel import Intel, TTLCache
from engine.urlcheck import analyze_url


def make_fetch(calls):
    def fake(method, url, headers=None, body=None, timeout=0.15, follow=True):
        calls.append((method, url))
        if "openphish.com" in url:
            return 200, {}, b"http://evil-bank-login.top/verify\nhttps://www.paytm-reward.xyz/claim/\n# comment\n"
        if method == "HEAD" and "bit.ly/ok" in url:
            return 301, {"Location": "https://www.sbi.co.in/web/home"}, b""
        if method == "HEAD" and "bit.ly/bad" in url:
            return 301, {"Location": "https://hdfc-kyc-update.in/login"}, b""
        if method == "HEAD" and "tinyurl.com/chain" in url:
            return 301, {"Location": "https://bit.ly/bad"}, b""
        if method == "HEAD" and "bit.ly/internal" in url:
            return 302, {"Location": "http://169.254.169.254/latest/meta-data"}, b""
        if "safebrowsing" in url:
            return 200, {}, (json.dumps({"matches": [{"threatType": "SOCIAL_ENGINEERING"}]}).encode() if "flagged.example" in body.decode() else b"{}")
        if "rdap.org" in url:
            return 200, {}, json.dumps({"events": [{"eventAction": "registration", "eventDate": "2026-11-05T10:00:00Z"}]}).encode()
        return 404, {}, b""
    return fake


class Intelligence(unittest.TestCase):
    def tearDown(self):
        fusion.set_intel(None)

    def intel(self, **kw):
        self.calls = []
        i = Intel(fetch=make_fetch(self.calls), **dict({"feeds": True}, **kw))
        i.refresh_feed()
        fusion.set_intel(i)
        return i

    def link(self, text):
        return fusion.analyze(text, enrich=True)["links"][0]

    def test_feed_hit_and_fail_soft(self):
        self.intel()
        l = self.link("Verify at http://evil-bank-login.top/verify now")
        self.assertTrue(l["feed_hit"]); self.assertIn("phish_feed", [s["id"] for s in l["signals"]])
        broken = Intel(fetch=lambda *a, **k: (_ for _ in ()).throw(OSError("offline")), feeds=True)
        broken.refresh_feed(); fusion.set_intel(broken)
        self.assertTrue(broken.status()["feed"]["error"])
        self.assertGreater(self.link("Verify at http://evil-bank-login.top/verify")["risk"], 0.3)  # heuristics alone still flag it as suspicious

    def test_short_links_resolve_and_chain(self):
        self.intel()
        ok = self.link("pay at bit.ly/ok")
        self.assertEqual(ok["expanded_to"], "https://www.sbi.co.in/web/home"); self.assertLess(ok["risk"], 0.2)
        bad = self.link("pay at bit.ly/bad")
        self.assertGreater(bad["risk"], 0.8)
        self.assertEqual(self.link("go tinyurl.com/chain")["expanded_to"], "https://hdfc-kyc-update.in/login")  # two hops

    def test_never_contacts_hosts_that_are_not_known_shorteners(self):
        self.intel()
        self.link("pay at bit.ly/internal")
        heads = [u for m, u in self.calls if m == "HEAD"]
        self.assertTrue(heads and all("bit.ly" in u or "tinyurl.com" in u for u in heads))
        self.assertFalse(any("169.254" in u for _, u in self.calls))  # the redirect target is analysed, never fetched

    def test_safe_browsing_and_domain_age_are_optional(self):
        self.intel()
        self.assertNotIn("gsb", [s["id"] for s in self.link("visit https://flagged.example/x")["signals"]])  # no key, no lookup
        self.intel(gsb_key="k", rdap=True)
        ids = [s["id"] for s in self.link("visit https://flagged.example/x")["signals"]]
        self.assertIn("gsb", ids); self.assertIn("new_domain", ids)

    def test_official_domains_are_never_second_guessed(self):
        self.intel(gsb_key="k", rdap=True)
        self.assertLess(self.link("open https://www.sbi.co.in/web/home")["risk"], 0.1)

    def test_slow_lookups_do_not_block_scans(self):
        slow = Intel(fetch=lambda *a, **k: time.sleep(1) or (200, {}, b"{}"), feeds=False, gsb_key="k", budget_ms=150)
        fusion.set_intel(slow)
        t0 = time.perf_counter(); fusion.analyze("check https://slow.example/x", enrich=True)
        self.assertLess(time.perf_counter() - t0, 0.5)

    def test_cache_expires(self):
        c = TTLCache(0.05); c.set("a", 1)
        self.assertEqual(c.get("a"), (True, 1)); time.sleep(0.08); self.assertEqual(c.get("a"), (False, None))

    def test_brand_lookalike_heuristics(self):
        for u in ("https://hdfc-kyc-update.in/login", "https://paytrn.com/pay", "https://bhim-upi-refund.top/claim", "https://unionbank-kyc.xyz/"):
            self.assertGreaterEqual(analyze_url(u)["risk"], 0.65, u)


if __name__ == "__main__":
    unittest.main()
