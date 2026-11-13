"""UPI QR / link analysis.

The key idea: a UPI *pay* QR code (upi://pay?pa=...) SENDS money. Scammers send "scan this QR to receive your refund / prize /
cashback", but scanning and approving it pays them. So when the person expects to RECEIVE money, any payment QR is a red flag.
"""
import re
from urllib.parse import parse_qs, unquote, urlsplit

from .entities import UPI_HANDLES

SCAM_NOTE_RE = re.compile(r"refund|reward|cashback|prize|lottery|lucky|kyc|verify|bonus|gift|claim|winning|reversal|insurance|customs", re.I)
RECEIVE_RE = re.compile(r"\b(?:receive|received|refund|cashback|credit(?:ed)?|reward|prize|won|winning|bonus|reversal|get\s+paid|collect)\b", re.I)


def looks_like_receive(text):
    """Does the surrounding text promise money coming IN?"""
    return bool(RECEIVE_RE.search(text or ""))


def parse_upi(payload):
    """Parse a upi:// link. Returns None if it is not one."""
    raw = (payload or "").strip()
    if not raw.lower().startswith("upi://"):
        return None
    parts = urlsplit(raw)
    kind = (parts.netloc or parts.path.strip("/")).lower()
    q = {k.lower(): unquote(v[0]) for k, v in parse_qs(parts.query, keep_blank_values=True).items() if v}
    pa = q.get("pa", "").strip()
    handle = pa.split("@", 1)[1].lower() if "@" in pa else ""
    try:
        amount = float(q["am"]) if q.get("am") else None
    except ValueError:
        amount = None
    return {"kind": kind if kind in ("pay", "collect", "mandate") else "other", "pa": pa, "pn": q.get("pn", "")[:80], "am": amount, "tn": q.get("tn", "")[:120],
            "mc": q.get("mc", ""), "tr": q.get("tr", "")[:40], "handle": handle, "handle_bank": UPI_HANDLES.get(handle), "raw": raw[:300]}


def analyze_payload(payload, intent="unknown", context_text=""):
    """Returns a dict describing one QR payload and the signals it triggers."""
    if intent == "unknown" and looks_like_receive(context_text):
        intent = "receive"
    info = parse_upi(payload)
    if info is None:
        kind = "url" if re.match(r"(?i)https?://|www\.", payload.strip()) else "other"
        return {"type": kind, "raw": payload.strip()[:300], "signals": [], "risk": 0.0, "intent": intent}
    sig = []

    def add(sid, title, weight, why):
        sig.append({"id": sid, "title": title, "weight": weight, "why": why})

    if info["kind"] in ("collect", "mandate"):
        add("upi_collect_qr", "This QR asks to PULL money from your account" if info["kind"] == "collect" else "This QR sets up an auto-debit mandate", 0.9,
            "A collect or mandate request takes money out of your account when you approve it. You never need to approve anything to receive money.")
    elif info["kind"] == "pay":
        if intent == "receive":
            add("upi_pay_qr_receive", "You expect to RECEIVE money, but this QR sends it OUT", 0.95,
                "Scanning a payment QR and entering your PIN pays the person named below. Receiving money never needs a QR scan or a PIN.")
        elif intent == "unknown":
            add("upi_pay_qr", "This is a payment QR: only scan it to pay someone", 0.55,
                "If anyone asked you to scan this to get money, refund or a prize, it is a scam. Check the payee name before you pay.")
    if info["tn"] and SCAM_NOTE_RE.search(info["tn"]):
        add("upi_note_bait", "The payment note uses bait words", 0.5, "Notes like 'refund' or 'reward' on a payment request are used to make it look harmless.")
    if info["handle"] and info["handle"] not in UPI_HANDLES:
        add("upi_unknown_handle", "Unusual UPI handle @" + info["handle"], 0.15, "Most people use well-known handles (@ybl, @okicici, @paytm...). Check the name shown before paying.")
    if info["pa"] and not info["mc"] and info["kind"] == "pay" and intent == "pay" and re.match(r"^\d{10}@", info["pa"]):
        add("upi_personal_payee", "Payee looks like a personal number, not a shop", 0.2, "A shop QR normally carries a merchant code. Make sure you know this person.")
    if info["am"] and info["am"] >= 10000 and intent in ("receive", "unknown"):
        add("upi_big_amount", "The QR already has a large amount filled in", 0.2, "Scammers pre-fill large amounts so you only have to enter your PIN.")
    miss = 1.0
    for s in sig:
        miss *= (1 - s["weight"])
    return {"type": "upi_" + info["kind"], "raw": info["raw"], "fields": {k: info[k] for k in ("pa", "pn", "am", "tn", "mc", "handle_bank")},
            "signals": sig, "risk": round(1 - miss, 3), "intent": intent}
