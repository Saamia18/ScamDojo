"""Text normalisation that keeps a map back to the original characters.

Scammers hide keywords with zero-width characters, look-alike letters, leetspeak ("KY C", "b4nk") and spacing.
We normalise for matching, but every character of the normalised text remembers which character of the
original it came from, so highlights can be drawn on exactly what the user pasted.
"""
import re
import unicodedata

ZERO_WIDTH = set("\u200b\u200c\u200d\u200e\u200f\u2060\ufeff\u00ad")

# Cyrillic / Greek / other letters that look like Latin letters.
HOMOGLYPHS = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d",
    "һ": "h", "ԛ": "q", "ԝ": "w", "к": "k", "м": "m", "т": "t", "в": "b", "н": "h",
    "ο": "o", "ν": "v", "ι": "i", "κ": "k", "α": "a", "ε": "e", "ρ": "p", "τ": "t", "υ": "u", "χ": "x",
    "ɡ": "g", "ɑ": "a", "ǝ": "e",
}
QUOTES = {"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "\u00a0": " "}

LEET = {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b", "$": "s", "@": "a"}
# We only undo leetspeak when the result is a word scammers actually use, which keeps normal text untouched.
SENSITIVE = {
    "kyc", "bank", "otp", "account", "verify", "urgent", "blocked", "paytm", "update", "link", "click", "prize",
    "lottery", "refund", "reward", "expire", "expired", "suspend", "suspended", "password", "login", "upi", "pan",
    "aadhaar", "free", "offer", "claim", "winner", "won", "alert", "secure", "customer", "card", "debit", "credit",
    "loan", "invest", "profit", "cashback", "congratulations", "dear", "immediately", "package", "parcel",
}

_SPACED_RE = re.compile(r"(?<![a-z0-9])(?:[a-z][ .\-_*]){2,}[a-z](?![a-z0-9])")
_REPEAT_RE = re.compile(r"([a-z])\1{2,}")
_WORDISH_RE = re.compile(r"[a-z0-9$@]{4,}")


class Norm:
    """Normalised text plus a map from each normalised character to its index in the original text."""

    def __init__(self, raw, text, index_map, flags):
        self.raw = raw
        self.text = text
        self.map = index_map
        self.flags = flags

    def span(self, a, b):
        """Convert a [a, b) span in normalised text to a [start, end) span in the original text."""
        if not self.map or a >= b:
            return (0, 0)
        a = max(0, min(a, len(self.map) - 1))
        b = max(a + 1, min(b, len(self.map)))
        return (self.map[a], self.map[b - 1] + 1)


def normalize(raw):
    flags = {"zero_width": 0, "homoglyph": 0, "leet": 0, "spaced": 0, "repeats": 0}
    chars, idx = [], []

    for i, ch in enumerate(raw):
        if ch in ZERO_WIDTH:
            flags["zero_width"] += 1
            continue
        for c in unicodedata.normalize("NFKC", ch):
            c = QUOTES.get(c, c).lower()
            if c in HOMOGLYPHS:
                c = HOMOGLYPHS[c]
                flags["homoglyph"] += 1
            chars.append(c)
            idx.append(i)

    text = "".join(chars)

    # Undo leetspeak, but only inside plain words and only when the result is a known scam-vocabulary word.
    out = list(text)
    for m in _WORDISH_RE.finditer(text):
        word = m.group(0)
        if not any(c in LEET for c in word[1:-1]) or sum(c.isalpha() for c in word) < 3:
            continue
        # skip things that look like part of a URL or an email
        before = text[max(0, m.start() - 1):m.start()]
        after = text[m.end():m.end() + 1]
        if (before and before in "/@.") or (after and after in "./@"):
            continue
        fixed = None
        for one in ("i", "l"):  # a "1" can stand for either letter
            cand = "".join(({**LEET, "1": one}.get(c, c)) if 0 < k < len(word) - 1 else c for k, c in enumerate(word))
            if cand != word and cand in SENSITIVE:
                fixed = cand
                break
        if fixed:
            out[m.start():m.end()] = list(fixed)
            flags["leet"] += 1
    text = "".join(out)

    # Collapse spaced-out letters: "k y c" -> "kyc".
    def collapse(pattern, text, idx, kind):
        pieces, new_idx, last = [], [], 0
        for m in pattern.finditer(text):
            pieces.append(text[last:m.start()])
            new_idx.extend(idx[last:m.start()])
            keep = [(c, idx[m.start() + k]) for k, c in enumerate(m.group(0)) if kind == "repeats" or c.isalpha()]
            if kind == "repeats":
                keep = keep[:2]
            pieces.append("".join(c for c, _ in keep))
            new_idx.extend(i for _, i in keep)
            last = m.end()
            flags[kind] += 1
        pieces.append(text[last:])
        new_idx.extend(idx[last:])
        return "".join(pieces), new_idx

    text, idx = collapse(_SPACED_RE, text, idx, "spaced")
    text, idx = collapse(_REPEAT_RE, text, idx, "repeats")
    return Norm(raw, text, idx, flags)


def normalize_off(raw):
    """No defences: just lower-case. Used only to measure how much the real normaliser helps."""
    text = "".join((c.lower() or c)[0] for c in raw)
    return Norm(raw, text, list(range(len(raw))), {"zero_width": 0, "homoglyph": 0, "leet": 0, "spaced": 0, "repeats": 0})
