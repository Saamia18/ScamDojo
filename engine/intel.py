"""Live threat intelligence for the link analyzer. Every source FAILS SOFT: if a feed or API is unreachable the engine simply
continues with its built-in heuristics, and a hard time budget keeps scans fast.

Sources
  * OpenPhish public feed   (no key)        refreshed in the background every 6 hours, lookups are in-memory sets
  * Google Safe Browsing    (GSB_API_KEY)    live lookup, 5-minute cache
  * RDAP domain age         (SCAMDOJO_RDAP=1) flags domains registered in the last 30 days, 24-hour cache
  * Short-link expansion    (always on)       reads the Location header of known shorteners only (never follows into arbitrary hosts)
Lookups run in a small thread pool with a deadline (default 150 ms); slow lookups keep running and fill the cache for next time.
"""
import json
import os
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime, timezone
from urllib.parse import urlsplit

from .brands import SHORTENERS
from .urlcheck import analyze_url, split_host

OPENPHISH_URL = "https://openphish.com/feed.txt"
GSB_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find?key=%s"
RDAP_URL = "https://rdap.org/domain/%s"
USER_AGENT = "ScamDojo/0.2 (+scam-awareness project)"


class TTLCache:
    def __init__(self, ttl, maxsize=5000):
        self.ttl, self.maxsize, self.data, self.lock = ttl, maxsize, {}, threading.Lock()

    def get(self, key):
        with self.lock:
            item = self.data.get(key)
            if item and item[0] > time.time():
                return True, item[1]
            self.data.pop(key, None)
            return False, None

    def set(self, key, value, ttl=None):
        with self.lock:
            if len(self.data) >= self.maxsize:
                self.data.pop(next(iter(self.data)))
            self.data[key] = (time.time() + (ttl or self.ttl), value)


def http_fetch(method, url, headers=None, body=None, timeout=0.15, follow=True):
    """Tiny HTTP helper. Returns (status, headers, body). With follow=False redirects are returned, not followed."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, data=body, method=method, headers=dict({"User-Agent": USER_AGENT}, **(headers or {})))
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read(5_000_000)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), b""


def _norm_host(url):
    u = url if "://" in url else "http://" + url
    h = (urlsplit(u).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


class Intel:
    def __init__(self, fetch=http_fetch, feeds=True, gsb_key=None, rdap=False, budget_ms=150, workers=6):
        self.fetch, self.feeds_on, self.gsb_key, self.rdap_on, self.budget = fetch, feeds, gsb_key, rdap, budget_ms / 1000.0
        self.urls, self.hosts, self.feed_loaded_at, self.feed_error = set(), set(), None, None
        self.cache_gsb, self.cache_rdap, self.cache_short = TTLCache(300), TTLCache(86400), TTLCache(3600)
        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="intel")
        self._stop = threading.Event()

    # ---------- OpenPhish feed ----------
    def refresh_feed(self):
        try:
            status, _, body = self.fetch("GET", OPENPHISH_URL, timeout=15)
            if status != 200:
                raise RuntimeError("HTTP %s" % status)
            urls, hosts = set(), set()
            for line in body.decode("utf-8", "ignore").splitlines()[:200000]:
                line = line.strip()
                if line.startswith("http"):
                    urls.add(line.lower().rstrip("/"))
                    hosts.add(_norm_host(line))
            self.urls, self.hosts, self.feed_loaded_at, self.feed_error = urls, hosts, time.time(), None
        except Exception as e:  # network down, blocked, rate limited...
            self.feed_error = str(e)[:80]

    def start_background(self, every_hours=6):
        def loop():
            while not self._stop.is_set():
                self.refresh_feed()
                self._stop.wait(every_hours * 3600)
        if self.feeds_on:
            threading.Thread(target=loop, daemon=True, name="intel-feed").start()

    def feed_hit(self, url):
        if not self.urls:
            return None
        u = url.lower().rstrip("/")
        if (u if "://" in u else "http://" + u) in self.urls:
            return "url"
        return "host" if _norm_host(url) in self.hosts else None

    # ---------- Google Safe Browsing ----------
    def gsb(self, url):
        if not self.gsb_key:
            return None
        hit, val = self.cache_gsb.get(url)
        if hit:
            return val
        body = json.dumps({"client": {"clientId": "scamdojo", "clientVersion": "0.2"},
                           "threatInfo": {"threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"], "platformTypes": ["ANY_PLATFORM"],
                                          "threatEntryTypes": ["URL"], "threatEntries": [{"url": url}]}}).encode()
        try:
            status, _, data = self.fetch("POST", GSB_URL % self.gsb_key, headers={"Content-Type": "application/json"}, body=body, timeout=0.4)
            matches = json.loads(data or b"{}").get("matches") if status == 200 else None
            val = matches[0]["threatType"] if matches else ""
        except Exception:
            return None
        self.cache_gsb.set(url, val)
        return val

    # ---------- domain age (RDAP) ----------
    def domain_age_days(self, registered):
        if not self.rdap_on or not registered or "." not in registered:
            return None
        hit, val = self.cache_rdap.get(registered)
        if hit:
            return val
        try:
            status, _, data = self.fetch("GET", RDAP_URL % registered, headers={"Accept": "application/rdap+json"}, timeout=2.0)
            if status != 200:
                self.cache_rdap.set(registered, None, ttl=600)
                return None
            for ev in json.loads(data).get("events", []):
                if ev.get("eventAction") == "registration":
                    when = datetime.fromisoformat(ev["eventDate"].replace("Z", "+00:00"))
                    days = (datetime.now(timezone.utc) - when).days
                    self.cache_rdap.set(registered, days)
                    return days
        except Exception:
            self.cache_rdap.set(registered, None, ttl=600)
        return None

    # ---------- short-link expansion ----------
    def expand(self, url):
        """Follow up to 3 hops, and only through KNOWN shorteners, reading the Location header. Returns the final URL or None."""
        hit, val = self.cache_short.get(url)
        if hit:
            return val
        cur, final = url if "://" in url else "https://" + url, None
        for _ in range(3):
            host = _norm_host(cur)
            sub, name, suffix = split_host(host)
            if (name + "." + suffix) not in SHORTENERS:
                break  # never contact a host we do not recognise as a shortener
            try:
                status, headers, _ = self.fetch("HEAD", cur, timeout=0.12, follow=False)
            except Exception:
                break
            loc = next((v for k, v in headers.items() if k.lower() == "location"), None)
            if status not in (301, 302, 303, 307, 308) or not loc:
                break
            if "://" not in loc:
                break
            final, cur = loc, loc
        self.cache_short.set(url, final)
        return final

    # ---------- the one call the engine makes ----------
    def _one(self, link):
        out = {"signals": [], "expanded": None}
        host_url = link["url"]
        reg = link.get("registered") or _norm_host(host_url)
        if link.get("official"):
            return out  # never second-guess an allow-listed official domain
        kind = self.feed_hit(host_url)
        if kind:
            out["signals"].append({"id": "phish_feed", "label": "Listed in the OpenPhish phishing feed", "weight": 0.95, "detail": "This address is on a public list of confirmed phishing links.", "part": "domain"})
            out["feed_hit"] = True
        threat = self.gsb(host_url) if self.gsb_key else None
        if threat:
            out["signals"].append({"id": "gsb", "label": "Flagged by Google Safe Browsing (%s)" % threat.lower().replace("_", " "), "weight": 0.95, "detail": "Google's safe-browsing service lists this address as dangerous.", "part": "domain"})
        if _norm_host(host_url) and (reg in SHORTENERS):
            target = self.expand(host_url)
            if target:
                out["expanded"] = target
                t = analyze_url(target)
                if t["official"]:
                    out["signals"].append({"id": "short_official", "label": "Short link leads to an official site", "weight": -1.0, "detail": "It resolves to " + t["registered"], "part": "domain"})
                elif t["risk"] >= 0.5:
                    out["signals"].append({"id": "short_bad_target", "label": "Short link leads to a dangerous site", "weight": min(0.95, t["risk"]), "detail": "It resolves to %s (%s)." % (t["registered"], "; ".join(s["label"] for s in t["signals"][:2])), "part": "domain"})
        if self.rdap_on and reg not in SHORTENERS and not out.get("feed_hit"):
            days = self.domain_age_days(reg)
            if days is not None and days < 30:
                out["signals"].append({"id": "new_domain", "label": "Domain registered only %d days ago" % days, "weight": 0.5, "detail": "Scam sites are often brand-new domains.", "part": "domain"})
        return out

    def enrich_links(self, links, budget_ms=None):
        """Adds intel signals to link dicts in place, within the time budget. Slow lookups keep running and fill the cache."""
        deadline = (budget_ms / 1000.0) if budget_ms else self.budget
        futures = {self.pool.submit(self._one, l): l for l in links[:6]}
        done, _ = wait(futures, timeout=deadline)
        for f in done:
            link = futures[f]
            try:
                res = f.result()
            except Exception:
                continue
            if res.get("expanded"):
                link["expanded_to"] = res["expanded"]
            if res.get("feed_hit"):
                link["feed_hit"] = True
            if not res["signals"]:
                continue
            if any(s["weight"] < 0 for s in res["signals"]):  # resolved to an official site: it is safe after all
                link["risk"], link["verdict"] = 0.05, "unknown"
                link["signals"] = [s for s in link["signals"] if s["id"] != "shortener"] + [dict(s, weight=0.0) for s in res["signals"]]
                continue
            link["signals"] = link["signals"] + res["signals"]
            miss = 1.0
            for s in link["signals"]:
                miss *= (1 - s["weight"])
            link["risk"] = round(min(0.99, 1 - miss), 3)
            link["verdict"] = "dangerous" if link["risk"] >= 0.65 else ("suspicious" if link["risk"] >= 0.3 else "unknown")

    def status(self):
        return {"feed": {"source": "OpenPhish", "enabled": self.feeds_on, "loaded": bool(self.urls), "entries": len(self.urls),
                         "age_hours": round((time.time() - self.feed_loaded_at) / 3600, 1) if self.feed_loaded_at else None, "error": self.feed_error},
                "safe_browsing": bool(self.gsb_key), "domain_age": self.rdap_on, "shortener_expansion": True, "budget_ms": int(self.budget * 1000)}


def from_env():
    return Intel(feeds=os.environ.get("SCAMDOJO_FEEDS", "1") == "1", gsb_key=os.environ.get("GSB_API_KEY") or None,
                 rdap=os.environ.get("SCAMDOJO_RDAP", "0") == "1", budget_ms=int(os.environ.get("SCAMDOJO_INTEL_BUDGET_MS", "150")))
