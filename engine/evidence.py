"""Builds a 1930 / cybercrime.gov.in evidence packet from a scanned message.

Stateless: nothing is stored. The packet has a plain-text brief (to read out to 1930 or paste into the complaint form) and a
self-contained, printable HTML report (print it to PDF). Every value is HTML-escaped. The text is only a DRAFT to help a victim
in the first hours; the person still files the complaint themselves.
"""
import hashlib
import html
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from . import fusion

IST = timezone(timedelta(hours=5, minutes=30))
HELPLINE, PORTAL = "1930", "https://cybercrime.gov.in"

# engine category -> (suggested portal-style label, severity for picking the primary one)
TAXONOMY = {
    "upi": ("Online financial fraud: UPI / QR payment scam", 9), "otp": ("Online financial fraud: OTP / PIN social engineering", 9),
    "credential": ("Online financial fraud: card / net-banking credentials stolen", 9), "kyc": ("Online financial fraud: fake KYC / bank impersonation", 8),
    "refund": ("Online financial fraud: refund / reversal scam", 8), "fee": ("Online financial fraud: advance-fee scam", 7),
    "prize": ("Online financial fraud: fake prize / lottery", 7), "invest": ("Online financial fraud: fake investment / trading", 8),
    "loan": ("Online financial fraud: fake loan offer", 7), "job": ("Online financial fraud: fake job / task scam", 7),
    "authority": ("Impersonation of police / government agency (digital-arrest style)", 8), "courier": ("Impersonation of courier / customs (parcel scam)", 7),
    "utility": ("Impersonation of a utility company (bill disconnection scam)", 6), "remote": ("Remote-access scam (screen-sharing app)", 9),
    "apk": ("Malicious app installed from a link", 9), "link": ("Phishing website / link", 6), "family": ("Impersonation of a relative", 7),
    "sim": ("SIM / telecom fraud", 6), "giftcard": ("Gift-card payment scam", 6), "secrecy": ("Coercion: told to keep it secret", 4),
}
PAYMENT = {"upi": "UPI", "card": "Debit / credit card", "netbanking": "Net banking", "cash": "Cash or other", "": "Not stated"}


def _clip(v, n):
    return re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", str(v or "")).strip()[:n]


def _clean_details(d):
    d = d if isinstance(d, dict) else {}
    amount = re.sub(r"[^\d.,]", "", str(d.get("amount", "")))[:14]
    return {"amount": amount, "when": _clip(d.get("when"), 60), "payment": d.get("payment") if d.get("payment") in PAYMENT else "",
            "txn_id": _clip(d.get("txn_id"), 40), "note": _clip(d.get("note"), 600),
            "lost_money": bool(d.get("lost_money")), "shared_otp": bool(d.get("shared_otp")), "installed_app": bool(d.get("installed_app")), "clicked_link": bool(d.get("clicked_link"))}


def _steps(det, res):
    steps = []
    if det["lost_money"]:
        steps += ["CALL 1930 NOW. The first hours matter most: banks can still freeze the receiving account.",
                  "Call your bank (number on your card) and ask to block the card / UPI and to put a hold on the transaction. Give them the transaction ID / UTR."]
    else:
        steps.append("You have not lost money yet. Do not reply, do not call back, do not pay anything. Block the sender.")
    if det["shared_otp"]:
        steps.append("You shared an OTP or PIN: change the PIN and password of the affected app and bank now, and tell the bank.")
    if det["installed_app"]:
        steps.append("You installed an app from a link: uninstall it, turn off mobile data, change passwords from another device, and run a security scan.")
    if det["clicked_link"] and not det["installed_app"]:
        steps.append("You opened a link: do not enter any details there. Clear the browser history and change passwords if you did.")
    steps += ["Take screenshots of the chat, caller number, payment screen and receipts. Do not delete the messages.",
              "Report at %s (choose the category closest to the suggestions below) and keep the acknowledgement number." % PORTAL,
              "Never pay anyone who offers to 'recover' your money for a fee."]
    return steps


def build_packet(text, source="text", intent="unknown", qr=None, details=None, now=None):
    now = now or datetime.now(timezone.utc)
    res = fusion.analyze(text, intent=intent, qr=qr or [], source=source, enrich=True)
    used = res.get("text_used") or (text or "")
    det = _clean_details(details)
    ents = res["entities"]
    cats = res["categories"]
    labelled = sorted(((TAXONOMY[c][1], TAXONOMY[c][0]) for c in cats if c in TAXONOMY), reverse=True)
    fingerprint = hashlib.sha256((used + "\n" + "\n".join(qr or [])).encode("utf-8")).hexdigest()

    link_findings = []
    for l in res["links"]:
        link_findings.append({"url": l["url"], "registered_domain": l.get("registered", ""), "risk": l["risk"], "official": l["official"], "brand": l.get("brand"),
                              "findings": [s["label"] for s in l["signals"]], "expanded_to": l.get("expanded_to"), "feed_hit": bool(l.get("feed_hit"))})
    signals = [{"title": r["title"], "why": r["why"]} for r in res["reasons"][:8]]
    timeline = [{"label": "Message mentions", "value": v} for v in (ents["dates"] + ents["times"])[:6]]
    if det["when"]:
        timeline.append({"label": "Incident time (reported by you)", "value": det["when"]})
    timeline.append({"label": "Evidence generated", "value": now.astimezone(IST).strftime("%d %b %Y, %H:%M IST") + " / " + now.strftime("%H:%M UTC")})

    packet = {
        "generated_at": now.isoformat(), "fingerprint_sha256": fingerprint,
        "summary": {"verdict": res["verdict"], "risk": res["risk"], "confidence": res["confidence"], "categories": cats,
                    "suggested_category": labelled[0][1] if labelled else "Online fraud (type not clear)", "also_matches": [x[1] for x in labelled[1:4]]},
        "entities": ents, "links": link_findings, "qr": res["qr"], "signals": signals, "timeline": timeline,
        "victim": {k: v for k, v in det.items() if v not in ("", False)}, "message_text": used, "steps": _steps(det, res),
        "portal": {"helpline": HELPLINE, "url": PORTAL},
        "disclaimer": "Draft prepared with ScamDojo to help you file a complaint. It is not an official document. The category above is a suggestion; use the closest option on the portal.",
    }
    packet["brief_text"] = _text(packet)
    packet["html"] = _html(packet)
    return packet


def _lines(label, items):
    return ["%s:" % label] + ["  - %s" % i for i in items] if items else []


def _text(p):
    e, v, s = p["entities"], p["victim"], p["summary"]
    out = ["CYBER FRAUD COMPLAINT BRIEF (draft)", "Helpline %s | %s" % (HELPLINE, PORTAL), "Generated: %s" % p["timeline"][-1]["value"], "",
           "SUGGESTED CATEGORY: %s" % s["suggested_category"]]
    if s["also_matches"]:
        out.append("Also matches: " + "; ".join(s["also_matches"]))
    out += ["Assessment: %s (risk %d%%, confidence %s)" % (s["verdict"].upper(), round(s["risk"] * 100), s["confidence"]), ""]
    out += ["WHAT HAPPENED (from the victim)"] + (["  Paid by: %s" % PAYMENT.get(v.get("payment", ""), "Not stated")] if v.get("payment") else [])
    for k, label in (("amount", "Amount lost: Rs "), ("when", "When: "), ("txn_id", "Transaction ID / UTR: "), ("note", "Notes: ")):
        if v.get(k):
            out.append("  " + label + v[k])
    flags = [t for k, t in (("lost_money", "money was lost"), ("shared_otp", "OTP/PIN was shared"), ("installed_app", "an app was installed"), ("clicked_link", "a link was opened")) if v.get(k)]
    if flags:
        out.append("  Victim states: " + ", ".join(flags))
    out += [""] + ["SCAMMER DETAILS FOUND IN THE MESSAGE"]
    for key, label in (("phones", "Phone numbers"), ("upi_ids", "UPI IDs"), ("upi_links", "UPI payment links"), ("urls", "Links"), ("emails", "E-mail addresses"),
                       ("ifsc", "IFSC codes"), ("long_numbers", "Long numbers (possible account / transaction ids)"), ("amounts", "Amounts mentioned")):
        out += _lines(label, e.get(key))
    if p["links"]:
        out += ["", "LINK ANALYSIS"] + ["  - %s: risk %d%%%s" % (l["url"], round(l["risk"] * 100), (" (" + "; ".join(l["findings"]) + ")") if l["findings"] else "") for l in p["links"]]
    if p["qr"]:
        out += ["", "QR CODE FINDINGS"] + ["  - %s%s" % (q["type"], (": payee %s (%s)" % (q["fields"].get("pa"), q["fields"].get("pn"))) if q.get("fields") else "") for q in p["qr"]]
    out += ["", "WHY IT IS SUSPECTED"] + ["  - %s" % x["title"] for x in p["signals"]]
    out += ["", "ORIGINAL MESSAGE (SHA-256 %s)" % p["fingerprint_sha256"][:16] + "...", p["message_text"] or "(none: QR code only)"]
    out += ["", "NEXT STEPS"] + ["  %d. %s" % (i + 1, x) for i, x in enumerate(p["steps"])] + ["", p["disclaimer"]]
    return "\n".join(out)


def _e(x):
    return html.escape(str(x), quote=True)


def _list(items, empty="None found"):
    return "<ul>" + "".join("<li>%s</li>" % _e(i) for i in items) + "</ul>" if items else "<p class=muted>%s</p>" % _e(empty)


def _html(p):
    e, v, s = p["entities"], p["victim"], p["summary"]
    rows = []
    for key, label in (("phones", "Phone numbers"), ("upi_ids", "UPI IDs"), ("upi_links", "UPI payment links"), ("urls", "Links"), ("emails", "E-mail addresses"),
                       ("ifsc", "IFSC codes"), ("long_numbers", "Long numbers"), ("amounts", "Amounts mentioned")):
        if e.get(key):
            rows.append("<tr><th>%s</th><td>%s</td></tr>" % (_e(label), "<br>".join(_e(i) for i in e[key])))
    victim = []
    for k, label in (("amount", "Amount lost (Rs)"), ("when", "When"), ("payment", "Paid by"), ("txn_id", "Transaction ID / UTR"), ("note", "Notes")):
        if v.get(k):
            victim.append("<tr><th>%s</th><td>%s</td></tr>" % (_e(label), _e(PAYMENT.get(v[k], v[k]) if k == "payment" else v[k])))
    flags = [t for k, t in (("lost_money", "Money was lost"), ("shared_otp", "OTP / PIN was shared"), ("installed_app", "An app was installed"), ("clicked_link", "A link was opened")) if v.get(k)]
    links = "".join("<li><b>%s</b>: risk %d%%%s</li>" % (_e(l["url"]), round(l["risk"] * 100), _e(" - " + "; ".join(l["findings"]) if l["findings"] else "")) for l in p["links"])
    qrs = "".join("<li>%s</li>" % _e(q["type"] + (": payee " + str(q["fields"].get("pa")) + " (" + str(q["fields"].get("pn")) + ")" if q.get("fields") else "")) for q in p["qr"])
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>1930 evidence packet</title><style>
body{font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif;color:#1B1F4B;max-width:820px;margin:24px auto;padding:0 18px}
h1{font-size:1.5rem;margin:0 0 4px}h2{font-size:1.05rem;border-bottom:2px solid #1B1F4B;padding-bottom:3px;margin-top:22px}
table{border-collapse:collapse;width:100%%}th,td{border:1px solid #9aa0c4;padding:6px 9px;text-align:left;vertical-align:top}th{width:32%%;background:#eef1f6}
pre{white-space:pre-wrap;word-break:break-word;background:#eef1f6;border:1px solid #9aa0c4;padding:10px;border-radius:6px}
.muted{color:#4A4F7A}.box{border:2px solid #1B1F4B;border-radius:8px;padding:10px 14px;background:#FFE9A6}.tag{display:inline-block;border:2px solid #1B1F4B;border-radius:999px;padding:0 10px;font-weight:700}
li{margin:3px 0}.steps li::marker{content:"\\2610  "}@media print{body{margin:0}.noprint{display:none}}
</style></head><body>
<h1>Cyber fraud: evidence packet <span class="tag">DRAFT</span></h1>
<p class="muted">National Cyber Crime Helpline <b>%(helpline)s</b> &middot; %(portal)s &middot; Generated %(when)s</p>
<div class="box"><b>Suggested category:</b> %(cat)s%(also)s<br><b>Assessment:</b> %(verdict)s (risk %(risk)d%%, confidence %(conf)s)</div>
<h2>Scammer details found in the message</h2>%(entities)s
<h2>Links and QR codes</h2>%(linkblock)s
<h2>Why this is suspected</h2>%(signals)s
<h2>Timeline</h2>%(timeline)s
<h2>Details you reported</h2>%(victim)s
<h2>Original message</h2><p class="muted">SHA-256 fingerprint: %(fp)s</p><pre>%(text)s</pre>
<h2>What to do now</h2><ol class="steps">%(steps)s</ol>
<p class="muted">%(disclaimer)s</p></body></html>""" % {
        "helpline": HELPLINE, "portal": _e(PORTAL), "when": _e(p["timeline"][-1]["value"]), "cat": _e(s["suggested_category"]),
        "also": ("<br><b>Also matches:</b> " + _e("; ".join(s["also_matches"]))) if s["also_matches"] else "", "verdict": _e(s["verdict"].upper()), "risk": round(s["risk"] * 100), "conf": _e(s["confidence"]),
        "entities": ("<table>" + "".join(rows) + "</table>") if rows else "<p class=muted>No phone numbers, UPI IDs or links were found in the message.</p>",
        "linkblock": ("<ul>" + links + qrs + "</ul>") if (links or qrs) else "<p class=muted>None found</p>",
        "signals": _list([x["title"] + ": " + x["why"] for x in p["signals"]]), "timeline": "<table>" + "".join("<tr><th>%s</th><td>%s</td></tr>" % (_e(t["label"]), _e(t["value"])) for t in p["timeline"]) + "</table>",
        "victim": ("<table>" + "".join(victim) + "</table>" + (("<p><b>Victim states:</b> " + _e(", ".join(flags)) + "</p>") if flags else "")) if (victim or flags) else "<p class=muted>Nothing added.</p>",
        "fp": _e(p["fingerprint_sha256"]), "text": _e(p["message_text"] or "(QR code only, no text)"), "steps": "".join("<li>%s</li>" % _e(x) for x in p["steps"]), "disclaimer": _e(p["disclaimer"]),
    }
