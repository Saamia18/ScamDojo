"""The ScamDojo pipeline: normalise -> text model + rules + link analysis + UPI/QR analysis -> one risk score with reasons.

    risk = 1 - (1 - 0.85*text) * (1 - rules) * (1 - 0.95*links) * (1 - 0.95*upi)   (noisy-OR: independent warning signs add up)

Highlights always point at the exact characters of the analysed text. An optional LLM may only REWORD the explanation
into plain language later; it never decides the verdict.
"""
import os
import time

from . import upi as upi_mod
from .entities import UPI_URI_RE, entity_counts, extract_entities
from .normalize import normalize, normalize_off
from .ocr import clean_ocr
from .rules import rule_score, run_rules
from .textclf import TextClassifier
from .urlcheck import analyze_url, find_urls

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "model", "model.json")
MODEL_VERSION = "scamdojo-0.2"
MAX_CHARS = 5000

SCAM_AT, SAFE_BELOW = 0.65, 0.35

ADVICE = {
    "scam": [
        "Do not tap links, call numbers or share any code from this message.",
        "Verify using the official app or the phone number printed on your card or bill.",
        "If money or details were already shared: call your bank immediately, then the National Cyber Crime Helpline 1930.",
        "Report it at cybercrime.gov.in.",
    ],
    "suspicious": [
        "Don't act on it yet. Check the claim in the official app or website (typed by you, not from the message).",
        "If it came from a number you don't know, don't reply or call back.",
        "Not sure? Ask a family member or call 1930 for guidance.",
    ],
    "safe": [
        "Nothing alarming was found, but stay careful with any message that asks for money, codes or urgent action.",
    ],
}
UPI_ADVICE = "Do not scan or approve it. Receiving money never needs a QR scan or your UPI PIN."

_model = None
_intel = None  # optional live threat-intelligence enricher (engine/intel.py), set by the server


def get_model():
    global _model
    if _model is None:
        _model = TextClassifier.load(MODEL_PATH)
    return _model


def set_model(m):
    global _model
    _model = m


def set_intel(i):
    global _intel
    _intel = i


def _label(risk):
    return "scam" if risk >= SCAM_AT else ("safe" if risk < SAFE_BELOW else "suspicious")


def combine(p_text, r_score, u_score, q_score=0.0):
    return 1 - (1 - 0.85 * p_text) * (1 - r_score) * (1 - 0.95 * u_score) * (1 - 0.95 * q_score)


def _merge_highlights(items):
    """Drop overlaps: rule/link spans win over model words. Returns sorted, non-overlapping highlights."""
    prio = {"rule": 0, "link": 1, "obfuscation": 2, "model": 3}
    items = sorted(items, key=lambda h: (prio[h["kind"]], h["start"]))
    kept = []
    for h in items:
        if any(h["start"] < k["end"] and k["start"] < h["end"] for k in kept):
            continue
        kept.append(h)
    return sorted(kept, key=lambda h: h["start"])


def analyze(text, model=None, normalizer=True, intent="unknown", qr=None, source="text", enrich=False):
    """text: the message. source: text | ocr | qr. intent: why the user scanned a QR (receive | pay | unknown). qr: decoded QR payloads."""
    t0 = time.perf_counter()
    text = (text or "")[:MAX_CHARS]
    if source == "ocr":
        text = clean_ocr(text)
    norm = normalize(text) if normalizer else normalize_off(text)
    model = model or get_model()
    has_text = bool(text.strip())

    # --- 1. text model ---
    p_text, up, down = 0.0, [], []
    if has_text:
        p_text = model.predict_proba(norm)
        up, down = model.explain(norm)

    def dedupe(items):
        seen, out = set(), []
        for w in items:
            if w["word"] not in seen:
                seen.add(w["word"])
                out.append(w)
        return out
    words_up, words_down = dedupe(up), dedupe(down)

    # --- 2. India-specific rules ---
    hits, safe_hits = run_rules(norm) if has_text else ([], [])
    r_score = rule_score(hits)

    # --- 3. links in the text ---
    links = []
    for a, b, url in find_urls(norm.text):
        res = analyze_url(url)
        s, e = norm.span(a, b)
        res["span"] = [s, e]
        res["url"] = text[s:e] if text[s:e].strip() else url
        links.append(res)

    # --- 4. UPI links in the text and decoded QR codes ---
    payloads = [m.group(0).rstrip(".,;)") for m in UPI_URI_RE.finditer(text)]
    from_text = len(payloads)
    payloads += [p for p in (qr or [])[:5] if isinstance(p, str) and p.strip()]
    qr_items = [upi_mod.analyze_payload(p, intent, text) for p in payloads]
    for item in qr_items:
        if item["type"] == "url":  # a QR that holds a web address gets the full link analysis
            res = analyze_url(item["raw"])
            res["span"] = None
            res["from_qr"] = True
            links.append(res)
    if enrich and _intel is not None and links:
        _intel.enrich_links(links)
    u_score = max([l["risk"] for l in links], default=0.0)
    if links and all(l["official"] for l in links):
        u_score = 0.0
    q_score = max([i["risk"] for i in qr_items], default=0.0)

    # --- 5. fusion ---
    risk = combine(p_text, r_score, u_score, q_score)
    strong = any(h["weight"] >= 0.7 for h in hits) or u_score >= 0.7 or q_score >= 0.7
    if safe_hits and not strong:
        risk *= (1 - min(0.5, sum(s["weight"] for s in safe_hits)))
    flags = norm.flags
    obf = (flags["homoglyph"] > 0) + (flags["zero_width"] > 0) + (flags["leet"] > 0) + (flags["spaced"] > 0)
    if obf and risk >= 0.25:
        risk = 1 - (1 - risk) * (1 - 0.1 * obf)
    risk = round(max(0.0, min(0.99, risk)), 3)
    verdict = _label(risk)

    # --- 6. confidence: how far from the line, and do the parts agree? ---
    votes = []
    if has_text:
        votes.append(1 if p_text > 0.7 else (-1 if p_text < 0.3 else 0))
        votes.append(1 if r_score >= 0.5 else (-1 if not hits else 0))
    if links:
        votes.append(1 if u_score >= 0.5 else (-1 if u_score < 0.2 else 0))
    if qr_items:
        votes.append(1 if q_score >= 0.5 else (-1 if q_score < 0.2 else 0))
    side = 1 if risk >= 0.5 else -1
    voters = [v for v in votes if v != 0]
    agreement = (sum(1 for v in voters if v == side) / len(voters)) if voters else 0.3
    margin = abs(risk - 0.5) * 2
    conf_score = round(0.6 * margin + 0.4 * agreement, 3)
    confidence = "high" if conf_score >= 0.7 else ("medium" if conf_score >= 0.45 else "low")

    # --- 7. highlights (positions in the analysed text) ---
    hl = []
    for h in hits:
        for a, b in h["spans"]:
            s, e = norm.span(a, b)
            hl.append({"start": s, "end": e, "kind": "rule", "id": h["id"], "label": h["title"]})
    for l in links:
        if l.get("span"):
            hl.append({"start": l["span"][0], "end": l["span"][1], "kind": "link", "id": "link",
                       "label": "Link looks %s" % l["verdict"] if not l["official"] else "Official link"})
    for m in UPI_URI_RE.finditer(text):
        hl.append({"start": m.start(), "end": m.end(), "kind": "link", "id": "upi", "label": "UPI payment link"})
    for w in up:
        s, e = norm.span(w["a"], w["b"])
        hl.append({"start": s, "end": e, "kind": "model", "id": "word", "label": "Scam-like word"})
    highlights = _merge_highlights(hl)

    # --- 8. reasons, ordered by weight ---
    reasons = [{"id": h["id"], "category": h["category"], "title": h["title"], "why": h["why"], "tip": h["tip"],
                "weight": h["weight"], "source": "rule",
                "evidence": [text[slice(*norm.span(a, b))] for a, b in h["spans"][:2]]} for h in hits]
    for l in links:
        for s in l["signals"]:
            if s["weight"] >= 0.3:
                reasons.append({"id": s["id"], "category": "link", "title": s["label"], "why": s["detail"],
                                "tip": "Open the official app or type the website yourself.", "weight": s["weight"],
                                "source": "link", "evidence": [l["url"]]})
    for item in qr_items:
        for s in item["signals"]:
            if s["weight"] >= 0.3:
                reasons.append({"id": s["id"], "category": "upi", "title": s["title"], "why": s["why"],
                                "tip": "Never scan a QR code or enter your UPI PIN to receive money.", "weight": s["weight"],
                                "source": "qr", "evidence": [item["raw"][:120]]})
    if flags["homoglyph"] or flags["zero_width"] or flags["leet"] or flags["spaced"]:
        reasons.append({"id": "obfuscation", "category": "obfuscation", "title": "Letters were disguised to dodge filters",
                        "why": "Look-alike letters, hidden characters or spaced-out words are used to slip past spam filters.",
                        "tip": "Honest senders don't hide their words.", "weight": 0.4, "source": "text", "evidence": []})
    reasons.sort(key=lambda r: -r["weight"])

    categories = sorted({r["category"] for r in reasons if r["category"] not in ("link", "obfuscation", "urgency")} |
                        ({"link"} if u_score >= 0.5 else set()) | ({"upi"} if q_score >= 0.5 else set()))

    ents = extract_entities(text + "\n" + "\n".join(payloads))
    advice = list(ADVICE[verdict])
    if q_score >= 0.5:
        advice.insert(0, UPI_ADVICE)

    return {
        "risk": risk, "verdict": verdict, "confidence": confidence, "confidence_score": conf_score,
        "components": {"text": round(p_text, 3), "rules": round(r_score, 3), "links": round(u_score, 3), "upi": round(q_score, 3)},
        "highlights": highlights, "reasons": reasons[:8], "links": links,
        "qr": [{"type": i["type"], "raw": i["raw"], "fields": i.get("fields"), "risk": i["risk"], "intent": i["intent"],
                "signals": [{"id": s["id"], "title": s["title"], "weight": s["weight"]} for s in i["signals"]]} for i in qr_items],
        "reassurance": [{"id": s["id"], "title": s["title"], "why": s["why"]} for s in safe_hits],
        "top_words": {"scam": [{"word": w["word"], "contribution": w["contribution"]} for w in words_up][:6],
                      "safe": [{"word": w["word"], "contribution": w["contribution"]} for w in words_down][:4]},
        "normalization": flags, "categories": categories, "advice": advice,
        "entities": ents, "entity_counts": entity_counts(ents), "source": source,
        "text_used": text if source == "ocr" else None,
        "model_version": MODEL_VERSION, "timing_ms": round((time.perf_counter() - t0) * 1000, 2), "length": len(text),
    }
