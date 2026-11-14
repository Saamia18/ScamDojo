"""Evasion transforms: ways a scammer might disguise a message to slip past a filter.
Each transform is deterministic, so the benchmark is repeatable."""
import re

KEYWORDS = ["kyc", "otp", "upi", "bank", "account", "blocked", "verify", "refund", "prize", "lottery", "link", "click", "update", "expired", "urgent",
            "claim", "payment", "reward", "winner", "fee", "pin", "parcel", "customs", "suspended", "password"]
KW_RE = re.compile(r"\b(" + "|".join(KEYWORDS) + r")\b", re.I)
HOMO = {"a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "x": "х", "i": "і", "y": "у"}
LEET = {"a": "4", "e": "3", "o": "0", "i": "1", "s": "5"}


def _in_url(text, pos):
    start = max(text.rfind(" ", 0, pos), text.rfind("\n", 0, pos)) + 1
    return bool(re.match(r"(?i)(https?://|www\.)|[\w-]+\.(com|in|xyz|top|click|live|shop|cfd|site|online|vip|buzz)", text[start:start + 60]))


def _map_keywords(text, fn):
    out, last = [], 0
    for m in KW_RE.finditer(text):
        if _in_url(text, m.start()):
            continue
        out.append(text[last:m.start()]); out.append(fn(m.group(0))); last = m.end()
    out.append(text[last:])
    return "".join(out)


def zero_width(t):  # hide a zero-width space inside every sensitive word
    return _map_keywords(t, lambda w: w[:max(1, len(w) // 2)] + "\u200b" + w[max(1, len(w) // 2):])


def homoglyph(t):  # swap Latin letters for look-alike Cyrillic letters inside sensitive words
    return _map_keywords(t, lambda w: "".join(HOMO.get(c.lower(), c) if k % 2 == 0 else c for k, c in enumerate(w)))


def spaced(t):  # K Y C, O T P ...
    return _map_keywords(t, lambda w: " ".join(w) if len(w) <= 8 else w)


def leet(t):  # b4nk, acc0unt, bl0cked
    return _map_keywords(t, lambda w: "".join(LEET.get(c.lower(), c) if k % 2 == 1 else c for k, c in enumerate(w)))


def mixed(t):  # spacing on some words, homoglyphs on others
    return homoglyph(zero_width(t))


def casing_noise(t):  # hArD tO rEaD cAsE
    return "".join(c.upper() if k % 2 else c.lower() for k, c in enumerate(t))


TRANSFORMS = [("zero_width", "Hidden zero-width characters", zero_width), ("homoglyph", "Look-alike letters (Cyrillic)", homoglyph),
              ("spaced", "Spaced-out words (K Y C)", spaced), ("leet", "Leetspeak (b4nk, acc0unt)", leet),
              ("mixed", "Hidden characters + look-alike letters", mixed), ("casing", "aLtErNaTiNg cAsE", casing_noise)]
