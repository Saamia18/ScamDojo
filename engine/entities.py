"""Forensic entity extraction: the things a cyber-crime officer needs from a scam message.
Phone numbers, UPI IDs, links, e-mails, amounts, dates/times, IFSC codes and long numbers (possible account or transaction ids)."""
import re

from .urlcheck import find_urls

# Payment-service-provider handles that appear after the @ in a UPI ID. An unknown handle is only a weak signal.
UPI_HANDLES = {
    "okicici": "ICICI Bank (Google Pay)", "okhdfcbank": "HDFC Bank (Google Pay)", "oksbi": "SBI (Google Pay)", "okaxis": "Axis Bank (Google Pay)",
    "ybl": "Yes Bank (PhonePe)", "ibl": "ICICI Bank (PhonePe)", "axl": "Axis Bank (PhonePe)", "paytm": "Paytm Payments Bank", "ptyes": "Yes Bank (Paytm)",
    "ptsbi": "SBI (Paytm)", "pthdfc": "HDFC Bank (Paytm)", "ptaxis": "Axis Bank (Paytm)", "apl": "Axis Bank (Amazon Pay)", "yapl": "Amazon Pay",
    "rapl": "RBL Bank (Amazon Pay)", "upi": "BHIM", "sbi": "SBI", "icici": "ICICI Bank", "hdfcbank": "HDFC Bank", "axisbank": "Axis Bank", "kotak": "Kotak",
    "pnb": "Punjab National Bank", "boi": "Bank of India", "cnrb": "Canara Bank", "idfcbank": "IDFC First Bank", "indus": "IndusInd Bank", "yesbank": "Yes Bank",
    "fbl": "Federal Bank", "federal": "Federal Bank", "rbl": "RBL Bank", "aubank": "AU Small Finance Bank", "postbank": "India Post Payments Bank",
    "jio": "Jio Payments Bank", "airtel": "Airtel Payments Bank", "freecharge": "Freecharge", "abfspay": "Aditya Birla", "waicici": "WhatsApp Pay (ICICI)",
    "waaxis": "WhatsApp Pay (Axis)", "wahdfcbank": "WhatsApp Pay (HDFC)", "wasbi": "WhatsApp Pay (SBI)", "ikwik": "MobiKwik", "barodampay": "Bank of Baroda",
    "unionbank": "Union Bank", "ubi": "Union Bank", "uco": "UCO Bank", "idbi": "IDBI Bank", "iob": "Indian Overseas Bank", "kvb": "Karur Vysya Bank",
    "sib": "South Indian Bank", "tmb": "Tamilnad Mercantile Bank", "cbin": "Central Bank of India", "hsbc": "HSBC", "dbs": "DBS", "psb": "Punjab & Sind Bank",
    "mahb": "Bank of Maharashtra", "allbank": "Indian Bank", "okbizaxis": "Axis Bank (Google Pay for Business)", "tapicici": "ICICI Bank (Tap)", "slc": "Slice",
}

PHONE_RE = re.compile(r"(?<![\d@])(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
TOLLFREE_RE = re.compile(r"(?<!\d)1800[\s-]?\d{3}[\s-]?\d{3,4}(?!\d)")
UPI_ID_RE = re.compile(r"(?<![\w.@-])[a-z0-9][a-z0-9._-]{1,48}@[a-z][a-z0-9]{1,22}(?![\w.@-])", re.I)
UPI_URI_RE = re.compile(r"upi://[^\s<>\"']+", re.I)
EMAIL_RE = re.compile(r"(?<![\w.@-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w@-])")
AMOUNT_RE = re.compile(r"(?:₹|\brs\.?|\binr)\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:lakh|lac|crore|cr|k)\b)?|\b\d[\d,]*(?:\.\d+)?\s?(?:lakh|lac|crore)\b", re.I)
DATE_RE = re.compile(r"\b\d{1,2}[-/. ](?:\d{1,2}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[-/. ]\d{2,4}\b|\b\d{1,2}\s?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*(?:\s\d{2,4})?\b", re.I)
TIME_RE = re.compile(r"\b\d{1,2}[:.]\d{2}\s?(?:am|pm|hrs)?\b|\b\d{1,2}\s?(?:am|pm)\b", re.I)
IFSC_RE = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")
LONG_NUM_RE = re.compile(r"(?<![\d.])\d{9,18}(?![\d])")


def _digits(s):
    return re.sub(r"\D", "", s)


def extract_entities(text):
    """Returns a dict of lists. Each item is a plain string (nothing is masked: the user is building a report)."""
    text = text or ""
    ents = {"phones": [], "upi_ids": [], "upi_links": [], "urls": [], "emails": [], "amounts": [], "dates": [], "times": [], "ifsc": [], "long_numbers": []}
    seen = set()

    def add(kind, value):
        key = (kind, value.lower())
        if value and key not in seen:
            seen.add(key)
            ents[kind].append(value)

    for m in UPI_URI_RE.finditer(text):
        add("upi_links", m.group(0).rstrip(".,;)"))
    spans_taken = [(m.start(), m.end()) for m in UPI_URI_RE.finditer(text)]
    for a, b, url in find_urls(text):
        if not url.lower().startswith("upi://"):
            add("urls", url)
    for m in EMAIL_RE.finditer(text):
        add("emails", m.group(0))
    email_spans = [(m.start(), m.end()) for m in EMAIL_RE.finditer(text)]
    for m in UPI_ID_RE.finditer(text):
        if any(a <= m.start() < b for a, b in spans_taken + email_spans):
            continue
        handle = m.group(0).split("@", 1)[1].lower()
        if handle in UPI_HANDLES or not re.search(r"\.[a-z]{2,}$", m.group(0), re.I):
            add("upi_ids", m.group(0))
    for rx in (PHONE_RE, TOLLFREE_RE):
        for m in rx.finditer(text):
            if any(a <= m.start() < b for a, b in spans_taken):
                continue
            d = _digits(m.group(0))
            add("phones", ("+91 " + d[-10:]) if len(d) >= 10 and not d.startswith("1800") else d)
    phone_digits = {_digits(p)[-10:] for p in ents["phones"]}
    for m in AMOUNT_RE.finditer(text):
        add("amounts", m.group(0).strip())
    for m in DATE_RE.finditer(text):
        add("dates", m.group(0).strip())
    for m in TIME_RE.finditer(text):
        add("times", m.group(0).strip())
    for m in IFSC_RE.finditer(text):
        add("ifsc", m.group(0))
    for m in LONG_NUM_RE.finditer(text):
        d = m.group(0)
        if d[-10:] not in phone_digits and not (len(d) == 10 and d[0] in "6789"):
            add("long_numbers", d)
    return ents


def entity_counts(ents):
    return {k: len(v) for k, v in ents.items() if v}
