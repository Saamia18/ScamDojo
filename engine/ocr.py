"""Cleans up text read from a screenshot by OCR so the normal engine can handle it.
OCR output has hard line breaks, stray symbols and broken links. We repair those without changing the meaning."""
import re

_BULLETS = re.compile(r"^[\s•·●○▪■▶►\-–—_|]+(?=\S)", re.M)


def clean_ocr(text):
    t = (text or "").replace("\r", "\n").replace("\u00a0", " ")
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)                      # re-join words split across lines
    t = _BULLETS.sub("", t)
    t = re.sub(r"(?i)\bh\s*t\s*t\s*p\s*(s?)\s*:\s*/\s*/\s*", lambda m: "http" + m.group(1).lower() + "://", t)
    t = re.sub(r"(?i)\b(https?)\s*:\s*/\s*/\s*", lambda m: m.group(1).lower() + "://", t)
    t = re.sub(r"(?i)\b(www)\s*\.\s*", "www.", t)
    # "sbi - kyc . top / login" -> "sbi-kyc.top/login" when it clearly is a link
    t = re.sub(r"(?i)\b([a-z0-9]+(?:\s?-\s?[a-z0-9]+)*)\s?\.\s?(com|in|xyz|top|click|live|shop|online|site|cfd|icu|vip|buzz|co\.in|gov\.in)\b(?:\s?/\s?([\w\-./?=&%]+))?",
               lambda m: re.sub(r"\s", "", m.group(1)) + "." + m.group(2) + ("/" + m.group(3) if m.group(3) else ""), t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n\n", t)
    t = re.sub(r"(?<![.!?:\n])\n(?!\n)", " ", t)                # single line breaks inside a sentence -> space
    return t.strip()
