"""Fresh game cards: an LLM mutates real Indian scam patterns into new scenarios; a template mutator is the always-available fallback.

Whatever produces a card, it is VALIDATED before it is stored or shown: schema and length limits, phone numbers masked, no working
official domains in scam cards, translated red-flag phrases must exist in the translated text, scam cards must contain at least one
red flag the engine can find (so the tap-the-flags games work), genuine cards must not look like scams to the engine.

Set ANTHROPIC_API_KEY (and optionally SCAMDOJO_LLM_MODEL) to use an LLM. Without a key the template mutator is used.
"""
import hashlib
import json
import os
import random
import re
import secrets
import time
import urllib.request

import db
from engine import fusion
from engine.urlcheck import analyze_url, find_urls

# category -> (game boss, label for the prompt, template-id prefixes for the offline mutator, lesson for template cards)
CATEGORIES = {
    "kyc": ("kraken", "fake KYC / bank account block", ("kyc",), "Banks never ask you to complete KYC through a link or an unknown number. Check in the official app or at the branch."),
    "prize": ("llama", "lottery / lucky draw / prize with a fee", ("prize",), "You cannot win a draw you never entered, and real prizes never need a fee first."),
    "otp": ("octopus", "OTP / PIN request by a fake bank or agent", ("otp",), "Never share an OTP, PIN or CVV. Nobody genuine needs it."),
    "upi_refund": ("octopus", "UPI refund / collect-request / QR scam", ("upi",), "You never enter a PIN or approve a request to RECEIVE money. That only sends money out."),
    "part_time_job": ("jackal", "part-time / work-from-home task job", ("job",), "Real employers never charge a fee to hire you, and nobody pays for likes or ratings."),
    "investment": ("jackal", "guaranteed-return investment or trading tips group", ("invest", "loan"), "Nothing legitimate guarantees profit. Check advisers on the SEBI website."),
    "courier": ("cobra", "parcel held at customs / redelivery fee", ("courier",), "Track parcels only in the shop's own app. Customs never takes payment on a personal number."),
    "electricity": ("cobra", "electricity or gas bill disconnection threat", ("util",), "Utilities do not disconnect by SMS at night. Check the bill in the official app."),
    "digital_arrest": ("cobra", "fake police / CBI / customs 'digital arrest' threat", ("auth",), "No agency arrests or settles a case by chat or video call. Hang up and call 1930."),
}
LANG_NAMES = {"en": "English", "hi": "Hindi (Devanagari)", "kn": "Kannada"}
SENDERS_SMS = ["VK-ALERTS", "AD-NOTICE", "BZ-UPDATE", "TX-SUPPORT", "VM-INFOSM", "JD-CARING"]
SENDERS_CHAT = ["+91 98XXX 10234", "+91 70XXX 55120", "+91 99XXX 87001"]
OFFICIAL_OK_FOR_LEGIT = True
MODEL = os.environ.get("SCAMDOJO_LLM_MODEL", "claude-sonnet-5-5")
DAILY_CAP = int(os.environ.get("SCAMDOJO_LLM_DAILY_CAP", "200"))
_calls = {"day": None, "n": 0}


def llm_ready():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


# ------------------------------------------------------------------ transport (replaceable in tests)
def _post_json(url, headers, payload, timeout=45):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


transport = _post_json


def _budget_ok():
    today = time.strftime("%Y-%m-%d")
    if _calls["day"] != today:
        _calls["day"], _calls["n"] = today, 0
    return _calls["n"] < DAILY_CAP


def ask_llm(category, lang, n_scam, n_legit):
    label = CATEGORIES[category][1]
    system = ("You write FICTIONAL training examples for a scam-awareness game used in India. Output ONLY valid JSON, no commentary. "
              "Never use real phone numbers (mask like 98XXXXXX21), real people, or working or official web addresses. Use plausible but fake look-alike domains for scams. "
              "The goal is to help people RECOGNISE fraud, so every scam card must include the telltale red flags a learner can spot.")
    user = (
        'Create %d new scam messages and %d genuine look-alike messages about: %s.\n'
        'Mutate real Indian fraud patterns into fresh scenarios (different brand, amount, story, urgency). Keep each message under 280 characters. '
        'Genuine messages must be truly legitimate (no fee, no link asking for details, no threat).\n'
        'Return JSON exactly like: {"cards":[{"sender":"VK-SBIINB","channel":"sms","text":"...","scam":true,"loss":2500,'
        '"lesson":"one sentence on why it is a scam / why it is genuine","flags":["exact phrases copied from text that are red flags"]'
        '%s}]}\n'
        'Rules: channel is "sms" or "chat"; loss is a rupee amount between 500 and 4000 for scams and 0 for genuine; flags must be exact substrings of text (empty for genuine).'
        % (n_scam, n_legit, label, (', "%s":{"text":"translation of text","lesson":"translation of lesson","flags":["exact phrases from the TRANSLATED text"]}' % lang) if lang != "en" else "")
        + ("\nThe translation must be natural %s. Keep URLs, numbers and brand names unchanged." % LANG_NAMES[lang] if lang != "en" else ""))
    _calls["n"] += 1
    resp = transport("https://api.anthropic.com/v1/messages",
                     {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"},
                     {"model": MODEL, "max_tokens": 3000, "system": system, "messages": [{"role": "user", "content": user}]})
    text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)).get("cards", []) if m else []


# ------------------------------------------------------------------ validation
PHONE_RE = re.compile(r"(?<!\d)([6-9]\d)(\d{6})(\d{2})(?!\d)")
CTRL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f<>]")


def mask_phones(s):
    return PHONE_RE.sub(lambda m: m.group(1) + "XXXXXX" + m.group(3), s)


def _clean(s, lo, hi):
    if re.search(r"[<>]", str(s or "")):
        return None  # markup in a card is garbage or an injection attempt: reject it instead of repairing it
    s = mask_phones(CTRL_RE.sub("", str(s or ""))).strip()
    return s if lo <= len(s) <= hi else None


def validate_card(raw, category, lang, existing_texts=()):
    """Returns a clean card dict (without 'ai') or None."""
    if not isinstance(raw, dict):
        return None
    text, lesson = _clean(raw.get("text"), 20, 320), _clean(raw.get("lesson"), 10, 220)
    sender = _clean(raw.get("sender"), 2, 28) or random.choice(SENDERS_SMS)
    if not text or not lesson or text.lower() in existing_texts:
        return None
    scam = bool(raw.get("scam"))
    channel = raw.get("channel") if raw.get("channel") in ("sms", "chat") else "sms"
    try:
        loss = max(0, min(4000, int(raw.get("loss") or 0))) if scam else 0
    except (TypeError, ValueError):
        loss = 0
    if scam and loss == 0:
        loss = random.choice([1000, 1500, 2000, 2500, 3000])
    # links: scam cards must not contain a working official domain; genuine cards must not contain fake-looking ones
    for _, _, url in find_urls(text):
        res = analyze_url(url)
        if scam and res["official"]:
            return None
        if not scam and not res["official"] and res["risk"] >= 0.3:
            return None
    a = fusion.analyze(text)
    real = [h for h in a["highlights"] if h["kind"] in ("rule", "link")]
    if scam and not real:
        return None  # the tap-the-flags games need at least one flag the engine can find
    if not scam and a["risk"] >= fusion.SCAM_AT:
        return None
    card = {"boss": CATEGORIES[category][0], "sender": sender, "channel": channel, "text": text, "scam": scam, "loss": loss, "lesson": lesson, "i18n": {}, "generated": True, "category": category}
    tr = raw.get(lang) if lang != "en" else None
    if isinstance(tr, dict):
        ttext, tlesson = _clean(tr.get("text"), 10, 420), _clean(tr.get("lesson"), 5, 300)
        flags = [f for f in (tr.get("flags") or []) if isinstance(f, str) and f and ttext and f in ttext][:6]
        if ttext and tlesson and (flags or not scam):
            card["i18n"][lang] = {"text": ttext, "lesson": tlesson, "flags": flags}
    card["id"] = "gen-" + hashlib.sha1(text.encode()).hexdigest()[:10]
    return card


# ------------------------------------------------------------------ offline template mutator (always available)
def template_cards(category, n_scam, n_legit):
    from engine.data import gen_dataset as g
    g.rnd.seed(secrets.randbits(32))
    prefixes = CATEGORIES[category][2]
    scam_pool = [t for t in g.SCAM if t[0].startswith(prefixes)] or g.SCAM
    legit_hint = {"kraken": ("kyc_l", "txn"), "llama": ("promo", "friend3"), "octopus": ("otp_l", "txn", "pay"), "jackal": ("hr",), "cobra": ("deliv", "bill", "govt")}[CATEGORIES[category][0]]
    legit_pool = [t for t in g.LEGIT if t[0].startswith(legit_hint)] or g.LEGIT
    out = []
    for _ in range(n_scam):
        tid, tpl = random.choice(scam_pool)
        out.append({"sender": random.choice(SENDERS_SMS + SENDERS_CHAT), "channel": "sms", "text": g.fill(tpl, 1), "scam": True, "loss": random.choice([1000, 1500, 2000, 2500, 3000]),
                    "lesson": CATEGORIES[category][3]})
    for _ in range(n_legit):
        tid, tpl = random.choice(legit_pool)
        out.append({"sender": random.choice(SENDERS_SMS), "channel": "sms", "text": g.fill(tpl, 0), "scam": False, "loss": 0, "lesson": "Genuine: it asks for nothing risky, has no suspicious link and no pressure."})
    return out


# ------------------------------------------------------------------ public API
def existing_texts():
    with db.connect() as con:
        rows = con.execute("SELECT json FROM generated_cards").fetchall()
    return {json.loads(r["json"])["text"].lower() for r in rows}


def generate(category, lang, count, user_id):
    """Returns (cards, source). Stores accepted cards in the database."""
    if category not in CATEGORIES:
        raise ValueError("Unknown category.")
    lang = lang if lang in LANG_NAMES else "en"
    count = max(1, min(3, int(count or 2)))
    n_legit = 1 if count >= 2 else 0
    n_scam = count - n_legit
    seen = existing_texts()
    raw, source = [], "template"
    if llm_ready() and _budget_ok():
        try:
            raw, source = ask_llm(category, lang, n_scam, n_legit), "llm"
        except Exception:
            raw, source = [], "template"  # network, quota or JSON problems: fall back quietly
    cards = [c for c in (validate_card(r, category, lang, seen) for r in raw) if c]
    if not cards:  # LLM unavailable or everything was rejected
        source = "template"
        for _ in range(4):
            cards = [c for c in (validate_card(r, category, lang, seen) for r in template_cards(category, n_scam, n_legit)) if c]
            if cards:
                break
    now = int(time.time())
    with db.connect() as con:
        for c in cards:
            con.execute("INSERT OR IGNORE INTO generated_cards(id, category, lang, json, source, created_at, created_by) VALUES(?,?,?,?,?,?,?)",
                        (c["id"], category, lang, json.dumps(c, ensure_ascii=False), source, now, user_id))
    return cards, source


def latest(limit=60):
    with db.connect() as con:
        rows = con.execute("SELECT json FROM generated_cards ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [json.loads(r["json"]) for r in rows]
