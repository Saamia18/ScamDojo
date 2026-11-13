"""Link analyzer: finds URLs in a message and scores each one.

Signals: look-alike domains (edit distance + homoglyph skeletons), brand names in the wrong place, link shorteners,
IP hosts, punycode, risky endings, free hosting, '@' tricks and APK downloads. Official domains are allow-listed.
"""
import re
from urllib.parse import urlsplit

from .brands import (BRANDS, BRAND_OFFICIAL, FREE_HOSTING, KEYWORD_TO_BRAND, MULTI_SUFFIX, OFFICIAL_ALL, PATH_WORDS,
                     SHORTENERS, SUSPICIOUS_TLDS, TLD_LIST, TRUSTED_SUFFIXES)

URL_RE = re.compile(
    r"""(?ix)
    (?:https?://|www\.)[^\s<>"']+
    | (?<![\w@.-])(?:bit\.ly|tinyurl\.com|t\.co|goo\.gl|rb\.gy|cutt\.ly|is\.gd|tiny\.cc|shorturl\.at|ow\.ly|t\.ly|wa\.me|t\.me)/[^\s<>"']+
    | (?<![\w@.-])(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+(?:%s)(?![\w@-])(?:/[^\s<>"']*)?
    """ % TLD_LIST
)
_IP_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")
_TRAIL = ".,;:)]}!?'\""


def find_urls(text):
    """Return [(start, end, url)] for URLs in text, with trailing punctuation trimmed."""
    out = []
    for m in URL_RE.finditer(text):
        url = m.group(0)
        end = m.end()
        while url and url[-1] in _TRAIL:
            url, end = url[:-1], end - 1
        if url and "." in url:
            out.append((m.start(), end, url))
    return out


def damerau(a, b):
    """Optimal-string-alignment edit distance (insert, delete, substitute, swap)."""
    la, lb = len(a), len(b)
    d = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1):
        d[i][0] = i
    for j in range(lb + 1):
        d[0][j] = j
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[la][lb]


def skeleton(s):
    """Collapse the tricks used in look-alike domains: rn->m, vv->w, 0->o, 1->l, and so on."""
    s = s.lower().replace("-", "").replace("_", "")
    for a, b in (("rn", "m"), ("vv", "w"), ("cl", "d")):
        s = s.replace(a, b)
    return s.translate(str.maketrans({"0": "o", "1": "l", "3": "e", "5": "s", "4": "a", "7": "t"}))


def split_host(host):
    """Split a host into (subdomain, name, suffix) with India-aware two-label suffixes."""
    labels = host.split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in MULTI_SUFFIX:
        suffix, rest = ".".join(labels[-2:]), labels[:-2]
    elif len(labels) >= 2:
        suffix, rest = labels[-1], labels[:-1]
    else:
        return "", host, ""
    name = rest[-1] if rest else ""
    sub = ".".join(rest[:-1])
    return sub, name, suffix


def _impersonation(sub, name):
    """Return (brand, kind, keyword) if this domain imitates a known brand, else None."""
    tokens = [t for t in re.split(r"[-_.0-9]+", name) if t]
    sub_tokens = [t for t in re.split(r"[-_.0-9]+", sub) if t]
    sk_name = skeleton(name)
    for kw, brand in KEYWORD_TO_BRAND.items():
        if len(kw) >= 6 and kw in name:
            return brand, "brand_in_domain", kw
        if kw in tokens or (len(kw) >= 4 and (name.startswith(kw) or name.endswith(kw))):
            return brand, "brand_in_domain", kw
    for kw, brand in KEYWORD_TO_BRAND.items():
        if kw in sub_tokens or (len(kw) >= 5 and kw in sub):
            return brand, "brand_in_subdomain", kw
    for kw, brand in KEYWORD_TO_BRAND.items():
        if len(kw) < 5:
            continue
        cands = [name] + tokens
        for t in cands:
            if len(t) < 4 or t == kw:
                continue
            tt = skeleton(t)
            dist = damerau(tt, skeleton(kw))
            limit = 2 if len(kw) >= 8 else 1
            if dist <= limit and abs(len(t) - len(kw)) <= 2:
                return brand, "lookalike", kw
        if skeleton(kw) in sk_name and kw not in name:
            return brand, "lookalike", kw
    return None


def analyze_url(url):
    """Analyse one URL. Returns a dict with risk (0-1), signals and the parts of the link for the autopsy view."""
    raw = url
    has_scheme = bool(re.match(r"^[a-z]+://", url, re.I))
    parsed = urlsplit(url if has_scheme else "http://" + url)
    scheme = parsed.scheme.lower() if has_scheme else ""
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "") + (("?" + parsed.query) if parsed.query else "")
    signals = []

    def add(sid, label, weight, detail, part):
        signals.append({"id": sid, "label": label, "weight": weight, "detail": detail, "part": part})

    is_ip = bool(_IP_RE.match(host))
    sub, name, suffix = ("", host, "") if is_ip else split_host(host)
    registered = host if is_ip else (name + "." + suffix if suffix else host)

    official = registered in OFFICIAL_ALL or suffix in TRUSTED_SUFFIXES
    brand_match = None
    parts = []
    if scheme:
        parts.append({"label": "scheme", "text": scheme + "://", "flag": "warn" if scheme == "http" else None,
                      "note": "No encryption (http)" if scheme == "http" else None})
    if "@" in (parsed.netloc or ""):
        add("at_sign", "Has an @ in the address", 0.6, "Everything before the @ is ignored by the browser, a classic disguise.", "domain")

    if official:
        sig_note = "Official domain" if registered in OFFICIAL_ALL else "Government/education domain"
        if sub:
            parts.append({"label": "subdomain", "text": sub + ".", "flag": None, "note": None})
        parts.append({"label": "domain", "text": name, "flag": "ok", "note": sig_note})
        parts.append({"label": "suffix", "text": "." + suffix, "flag": "ok", "note": None})
        if path and path != "/":
            parts.append({"label": "path", "text": path, "flag": None, "note": None})
        return {"url": raw, "host": host, "registered": registered, "risk": 0.03, "official": True, "brand": None,
                "signals": [], "parts": parts, "verdict": "official"}

    if is_ip:
        add("ip_host", "Uses a raw IP address", 0.6, "Real services use names, not numbers.", "domain")
    if "xn--" in host:
        add("punycode", "Uses disguised (punycode) characters", 0.55, "Foreign look-alike letters can spoof real names.", "domain")
    if registered in SHORTENERS:
        add("shortener", "Shortened link hides the destination", 0.45, "You cannot see where it goes before you tap.", "domain")
    elif not is_ip:
        imp = _impersonation(sub, name)
        if imp:
            brand, kind, kw = imp
            brand_match = brand
            official_list = BRAND_OFFICIAL[brand][0]
            if kind == "brand_in_domain":
                add("brand_in_domain", "Uses the %s name but is not %s" % (brand, official_list), 0.8,
                    "The real %s website is %s. This domain only borrows the name." % (brand, official_list), "domain")
            elif kind == "brand_in_subdomain":
                add("brand_in_subdomain", "Puts %s in front to look official" % brand, 0.8,
                    "The real owner of this link is %s, not %s." % (registered, brand), "subdomain")
            else:
                add("lookalike", "Look-alike spelling of %s" % brand, 0.85,
                    "Letters were swapped to imitate the real site (%s)." % official_list, "domain")
        if suffix in SUSPICIOUS_TLDS:
            add("risky_tld", "Unusual ending .%s" % suffix, 0.3, "Cheap endings like .%s are common in scam sites." % suffix, "suffix")
        if registered in FREE_HOSTING or any(host.endswith("." + f) for f in FREE_HOSTING):
            add("free_hosting", "Hosted on a free site builder", 0.4, "Anyone can create a page here in minutes.", "domain")
        if host.count("-") >= 3:
            add("many_hyphens", "Many hyphens in the name", 0.25, "Long hyphenated names are typical of fake sites.", "domain")
        if sub and sub.count(".") >= 2:
            add("deep_subdomain", "Many sub-domains", 0.25, "Extra sub-domains are used to bury the real owner.", "subdomain")
        if len(name) > 28:
            add("long_name", "Very long domain name", 0.15, "Unusually long names are often auto-generated.", "domain")
        if re.search(r"\d{3,}", name):
            add("digits_name", "Lots of digits in the name", 0.15, "Digits in a name often mean a throw-away site.", "domain")

    lower_path = path.lower()
    if lower_path.endswith(".apk") or ".apk?" in lower_path:
        add("apk", "Downloads an app file (.apk)", 0.75, "Installing apps from links can hand over your phone.", "path")
    hits = [w for w in PATH_WORDS if w in lower_path]
    if hits and signals:
        add("path_words", "Asks you to %s" % hits[0], 0.2, "Words like login/verify/claim are used to bait a tap.", "path")
    if scheme == "http" and signals:
        add("no_tls", "Not encrypted (http)", 0.1, "Real banks and shops use https.", "scheme")

    # noisy-OR over signals, with a small floor for an unfamiliar domain
    miss = 1.0
    for s in signals:
        miss *= (1 - s["weight"])
    risk = 1 - miss
    if not signals:
        risk = 0.12  # unfamiliar but nothing wrong spotted
    risk = min(0.98, risk)

    flagged = {}
    for s in signals:
        flagged.setdefault(s["part"], []).append(s)
    if sub:
        sp = flagged.get("subdomain")
        parts.append({"label": "subdomain", "text": sub + ".", "flag": "warn" if sp else None, "note": sp[0]["label"] if sp else None})
    if is_ip:
        dp = flagged.get("domain")
        parts.append({"label": "domain", "text": host, "flag": "bad" if dp else None, "note": dp[0]["label"] if dp else None})
    else:
        dp = flagged.get("domain")
        bad = dp and max(s["weight"] for s in dp) >= 0.6
        parts.append({"label": "domain", "text": name, "flag": "bad" if bad else ("warn" if dp else None),
                      "note": dp[0]["label"] if dp else None})
        tp = flagged.get("suffix")
        parts.append({"label": "suffix", "text": "." + suffix if suffix else "", "flag": "warn" if tp else None,
                      "note": tp[0]["label"] if tp else None})
    if path and path != "/":
        pp = flagged.get("path")
        parts.append({"label": "path", "text": path, "flag": "warn" if pp else None, "note": pp[0]["label"] if pp else None})

    verdict = "dangerous" if risk >= 0.65 else ("suspicious" if risk >= 0.3 else "unknown")
    return {"url": raw, "host": host, "registered": registered, "risk": round(risk, 3), "official": False,
            "brand": brand_match, "signals": signals, "parts": parts, "verdict": verdict}
