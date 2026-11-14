"""ScamDojo web server (Flask). Serves the app and the JSON API.

    pip install -r requirements.txt
    python server.py                       # development, http://localhost:8000
    gunicorn server:app -c gunicorn.conf.py  # production (see Procfile)

Public endpoints (readable from other sites): /api/health /api/samples /api/cards /api/metrics /api/config /api/leaderboard
    POST /api/analyze   {"text": "..."}                                   (text only, kept for compatibility)
    POST /api/scan      {"text", "source": text|ocr|qr, "intent": receive|pay|unknown, "qr": ["upi://..."]}
    POST /api/evidence  {...}   builds a 1930 / cybercrime.gov.in evidence packet (stateless, nothing stored)
Account endpoints (cookie session, same-origin only)
    POST /api/auth/register | login | logout | password | reset | delete
    GET  /api/me, GET|PUT|POST /api/progress, GET|DELETE /api/history, POST /api/cards/generate
Real-time duels: WebSocket /ws/duel/<code> (see duel.py).
Pasted message text is processed in memory and never written to disk or logged.

Environment: PORT, SCAMDOJO_DB, SCAMDOJO_SECURE=1, SCAMDOJO_TRUST_PROXY=1 (behind Render/nginx), SCAMDOJO_LOG=1,
             ANTHROPIC_API_KEY (+ SCAMDOJO_LLM_MODEL), SCAMDOJO_FEEDS, GSB_API_KEY, SCAMDOJO_RDAP.
"""
import hashlib
import json
import logging
import os
import re
import time

from flask import Flask, abort, jsonify, make_response, request, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

import accounts
import db
import duel
import history
import llm
import ws_transport
from engine import evidence as evidence_mod
from engine import fusion
from engine import intel as intel_mod

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, "web")
METRICS_PATH = os.path.join(ROOT, "engine", "model", "metrics.json")
CARDS_PATH = os.path.join(WEB, "data", "cards.json")
RATE_LIMIT, RATE_WINDOW = int(os.environ.get("SCAMDOJO_RATE_LIMIT", "120")), 60  # API requests per client per minute (override with SCAMDOJO_RATE_LIMIT)
COOKIE = "sd_session"
PUBLIC = ("/api/health", "/api/samples", "/api/cards", "/api/metrics", "/api/config", "/api/leaderboard", "/api/analyze", "/api/scan")

SAMPLES = [
    {"label": "Fake KYC", "text": "Dear SBI user, your YONO account is restricted. Complete KYC today: http://yono-sbi-care.top/kyc or your account will be blocked within 2 hours."},
    {"label": "OTP request", "text": "Sir I'm from the bank fraud team. A payment of Rs 49,999 is pending. Please share the OTP you just received to stop it."},
    {"label": "Lucky draw", "text": "CONGRATULATIONS! Your number won Rs 15,00,000 in the Jio Diwali Bumper draw. Pay Rs 2,500 tax to claim. Call 7331088224."},
    {"label": "Parcel fee", "text": "India Post: your parcel is held, address incomplete. Pay Rs 25 redelivery fee at bit.ly/ip-reship within 12 hours."},
    {"label": "Genuine OTP", "text": "845120 is your OTP for HDFC NetBanking login. Valid for 5 minutes. Do not share it with anyone. HDFC Bank never asks for it."},
    {"label": "Friend chat", "text": "Bhai kal movie chalte hain? Show 7 baje ka hai, main tickets book kar deta hoon."},
]

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
app.json.ensure_ascii = False
app.json.sort_keys = False
if os.environ.get("SCAMDOJO_TRUST_PROXY"):  # Render, Railway, nginx: believe X-Forwarded-For / -Proto / -Host from ONE proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
if not os.environ.get("SCAMDOJO_LOG"):
    logging.getLogger("werkzeug").setLevel(logging.ERROR)  # never log request lines; bodies are never logged at all

_limiter = accounts.Limiter()
_cards_cache = None


# ---------------------------------------------------------------- helpers
def client_ip():
    return request.remote_addr or "0.0.0.0"


def secure_cookie():
    return bool(os.environ.get("SCAMDOJO_SECURE")) or request.is_secure


def json_error(message, status):
    return jsonify({"error": message}), status


def strict_json():
    """State-changing account endpoints: JSON object only, same-origin only."""
    if "application/json" not in (request.content_type or ""):
        abort(415, "Send JSON with Content-Type: application/json.")
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, "Body must be a JSON object.")
    return data


def origin_ok():
    origin = request.headers.get("Origin")
    return (not origin) or re.sub(r"^https?://", "", origin) == request.host


def current_user():
    token = request.cookies.get(COOKIE)
    return accounts.user_for_token(token), token


def set_session_cookie(resp, token, clear=False):
    resp.set_cookie(COOKIE, "" if clear else token, max_age=0 if clear else accounts.SESSION_DAYS * 86400, path="/",
                    httponly=True, samesite="Lax", secure=secure_cookie())
    return resp


def load_cards_with_ai():
    """Score every base game card with the real engine once at startup, so the game shows live engine output."""
    global _cards_cache
    with open(CARDS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    for c in data["cards"]:
        c["ai"] = card_ai(c["text"])
    _cards_cache = data
    return data


def card_ai(text):
    r = fusion.analyze(text)
    return {"risk": r["risk"], "verdict": r["verdict"], "confidence": r["confidence"], "components": r["components"],
            "highlights": r["highlights"], "categories": r["categories"], "reasons": r["reasons"][:3],
            "links": [{"url": l["url"], "risk": l["risk"], "official": l["official"], "verdict": l["verdict"]} for l in r["links"]]}


# ---------------------------------------------------------------- request hooks
@app.before_request
def guard():
    if request.path.startswith("/api/") and request.path != "/api/health":
        if request.method == "OPTIONS":
            return None
        now = time.time()
        key = "api:" + client_ip()
        if _limiter.blocked(key, RATE_LIMIT, RATE_WINDOW):
            return json_error("Too many requests. Please wait a moment.", 429)
        _limiter.add(key)
        if request.method in ("POST", "PUT", "DELETE") and not request.path.startswith(("/api/analyze", "/api/scan", "/api/evidence")) and not origin_ok():
            return json_error("Cross-site request blocked.", 403)
    return None


@app.after_request
def headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    path = request.path
    if path.startswith("/api/"):
        if path in PUBLIC:  # only public, cookie-free endpoints are readable from other sites
            resp.headers["Access-Control-Allow-Origin"] = "*"
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers.setdefault("Cache-Control", "no-cache" if path in PUBLIC else "no-store")
    else:
        resp.headers.setdefault("Cache-Control", "no-cache")
    return resp


@app.errorhandler(HTTPException)
def http_error(e):
    return json_error(e.description or e.name, e.code or 500)


@app.errorhandler(accounts.AuthError)
def auth_error(e):
    return json_error(str(e), e.status)


@app.errorhandler(Exception)
def unexpected(e):  # never leak a stack trace to the client
    app.logger.exception("unhandled error")
    return json_error("Something went wrong on the server.", 500)


# ---------------------------------------------------------------- public API
@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "model": fusion.MODEL_VERSION})


@app.get("/api/config")
def config():
    feats = dict(app.config.get("FEATURES", {}), threat_intel=INTEL.status(), llm_cards=llm.llm_ready())
    return jsonify({"ws_path": "/ws/duel", "ws_port": app.config.get("WS_PORT"), "features": feats, "model": fusion.MODEL_VERSION})


@app.get("/api/samples")
def samples():
    return jsonify(SAMPLES)


@app.get("/api/metrics")
def metrics():
    try:
        with open(METRICS_PATH, encoding="utf-8") as f:
            return app.response_class(f.read(), mimetype="application/json")
    except OSError:
        return json_error("Run `python -m engine.train` to create metrics.json", 404)


_gen_ai = {}  # id -> engine analysis of a generated card, computed once


def _with_generated():
    base = _cards_cache or load_cards_with_ai()
    extra = []
    for c in llm.latest(60):
        if c["id"] not in _gen_ai:
            _gen_ai[c["id"]] = card_ai(c["text"])
        extra.append(dict(c, ai=_gen_ai[c["id"]]))
    return {"bosses": base["bosses"], "cards": base["cards"] + extra}


@app.get("/api/cards")
def cards():
    return jsonify(_with_generated())


@app.post("/api/cards/generate")
def generate_cards():
    """Fresh adversarial cards. Needs a login (it can cost money when an LLM key is set) and is rate limited per user."""
    user, _ = current_user()
    if not user:
        return json_error("Log in to generate fresh scam scenarios.", 401)
    data = strict_json()
    category = data.get("category")
    if category not in llm.CATEGORIES:
        return json_error("Pick one of: " + ", ".join(llm.CATEGORIES), 400)
    key = "gen:%d" % user["id"]
    if _limiter.blocked(key, 6, 3600):
        return json_error("You can generate fresh scenarios 6 times an hour. Try again later.", 429)
    _limiter.add(key)
    cards_out, source = llm.generate(category, data.get("lang"), data.get("count", 2), user["id"])
    out = []
    for c in cards_out:
        _gen_ai.setdefault(c["id"], card_ai(c["text"]))
        out.append(dict(c, ai=_gen_ai[c["id"]]))
    return jsonify({"cards": out, "source": source})


def _scan_payload():
    data = request.get_json(force=True, silent=True)
    if not isinstance(data, dict):
        abort(400, 'Body must be JSON like {"text": "message"}.')
    text = data.get("text", "")
    qr = [str(x)[:2000] for x in (data.get("qr") or [])[:5] if isinstance(x, (str, int))]
    if (not isinstance(text, str) or not text.strip()) and not qr:
        abort(400, "Paste a message, or scan a QR code, to analyse.")
    source = data.get("source") if data.get("source") in ("text", "ocr", "qr") else "text"
    intent = data.get("intent") if data.get("intent") in ("receive", "pay", "unknown") else "unknown"
    return (text if isinstance(text, str) else ""), source, intent, qr


@app.post("/api/analyze")
def analyze_text():
    text, source, intent, qr = _scan_payload()
    return jsonify(fusion.analyze(text, intent=intent, qr=qr, source=source, enrich=True))


@app.post("/api/scan")
def scan():
    text, source, intent, qr = _scan_payload()
    result = fusion.analyze(text, intent=intent, qr=qr, source=source, enrich=True)
    user, _ = current_user()
    if user:  # history is opt-in and stores NO message text, only the verdict, the scam types and entity counts
        prog, _ = accounts.get_progress(user["id"])
        if prog and prog.get("saveHistory"):
            history.add_scan(user["id"], source, result["verdict"], result["risk"], result["categories"], result.get("entity_counts", {}))
    return jsonify(result)


@app.post("/api/evidence")
def evidence():
    """Stateless: builds the 1930 / cybercrime.gov.in packet from what the user sends. Same-origin only, nothing is stored."""
    data = request.get_json(force=True, silent=True)
    text, source, intent, qr = _scan_payload()
    return jsonify(evidence_mod.build_packet(text, source, intent, qr, data.get("details")))


@app.get("/api/leaderboard")
def leaderboard():
    return jsonify({"rows": history.top(20), "note": "Only players who opted in appear. Scores are reported by the browser, so this board is for fun."})


# ---------------------------------------------------------------- accounts
@app.post("/api/auth/register")
def auth_register():
    data = strict_json()
    user, code = accounts.register(data.get("username"), data.get("password"), data.get("display_name"), client_ip())
    token = accounts.create_session(user["id"])
    if isinstance(data.get("progress"), dict):
        accounts.put_progress(user["id"], data["progress"])
    return set_session_cookie(make_response(jsonify({"user": user, "recovery_code": code}), 201), token)


@app.post("/api/auth/login")
def auth_login():
    data = strict_json()
    user = accounts.login(data.get("username"), data.get("password"), client_ip())
    token = accounts.create_session(user["id"])
    prog, _ = accounts.get_progress(user["id"])
    return set_session_cookie(make_response(jsonify({"user": user, "progress": prog})), token)


@app.post("/api/auth/reset")
def auth_reset():
    data = strict_json()
    _, code = accounts.reset_password(data.get("username"), data.get("recovery_code"), data.get("new_password"), client_ip())
    return set_session_cookie(make_response(jsonify({"ok": True, "recovery_code": code})), "", clear=True)


@app.post("/api/auth/logout")
def auth_logout():
    strict_json()
    _, token = current_user()
    accounts.end_session(token)
    return set_session_cookie(make_response(jsonify({"ok": True})), "", clear=True)


@app.post("/api/auth/password")
def auth_password():
    data = strict_json()
    user, _ = current_user()
    if not user:
        return json_error("Log in first.", 401)
    accounts.change_password(user["id"], data.get("current"), data.get("new"))
    return set_session_cookie(make_response(jsonify({"ok": True})), accounts.create_session(user["id"]))


@app.post("/api/auth/delete")
def auth_delete():
    data = strict_json()
    user, _ = current_user()
    if not user:
        return json_error("Log in first.", 401)
    accounts.delete_account(user["id"], data.get("password"))
    return set_session_cookie(make_response(jsonify({"ok": True})), "", clear=True)


@app.get("/api/me")
def me():
    user, _ = current_user()
    if not user:
        return jsonify({"user": None})
    prog, updated = accounts.get_progress(user["id"])
    return jsonify({"user": user, "progress": prog, "updated_at": updated})


@app.route("/api/progress", methods=["GET", "PUT", "POST"])
def progress():
    user, _ = current_user()
    if not user:
        return json_error("Log in to save progress.", 401)
    if request.method == "GET":
        prog, updated = accounts.get_progress(user["id"])
        return jsonify({"progress": prog, "updated_at": updated})
    data = strict_json()
    _, updated = accounts.put_progress(user["id"], data.get("progress"))
    return jsonify({"ok": True, "updated_at": updated})


@app.route("/api/history", methods=["GET", "DELETE"])
def scan_history():
    user, _ = current_user()
    if not user:
        return json_error("Log in to see your history.", 401)
    if request.method == "DELETE":
        history.clear_scans(user["id"])
        return jsonify({"ok": True})
    return jsonify({"rows": history.list_scans(user["id"]), "note": "History stores the verdict and scam type only. Message text is never saved."})


# ---------------------------------------------------------------- PWA service worker
def _shell_files():
    out = ["/", "/index.html", "/manifest.json", "/api/cards", "/api/samples", "/api/config"]
    sig = []
    for base, _, files in os.walk(WEB):
        for fn in sorted(files):
            full = os.path.join(base, fn)
            rel = "/" + os.path.relpath(full, WEB).replace(os.sep, "/")
            if rel.startswith(("/js/", "/css/", "/icons/")) or rel in ("/data/cards.json", "/data/offline_pack.json"):
                out.append(rel)
            if rel != "/sw.js":
                sig.append("%s:%d:%d" % (rel, os.path.getsize(full), int(os.path.getmtime(full))))
    return sorted(set(out)), hashlib.sha1("|".join(sorted(sig)).encode()).hexdigest()[:10]


@app.get("/sw.js")
def service_worker():
    """web/sw.js with the real file list and a content hash injected, so every release gets a fresh cache."""
    with open(os.path.join(WEB, "sw.js"), encoding="utf-8") as f:
        src = f.read()
    files, version = _shell_files()
    src = re.sub(r"/\*VERSION\*/.*?/\*END\*/", lambda m: "'%s'" % version, src, count=1, flags=re.S)
    src = re.sub(r"/\*PRECACHE\*/.*?/\*END\*/", lambda m: json.dumps(files), src, count=1, flags=re.S)
    resp = make_response(src)
    resp.headers["Content-Type"] = "application/javascript; charset=utf-8"
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


# ---------------------------------------------------------------- static app
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def static_files(path):
    if path.startswith(("api/", "ws/")):
        abort(404, "not found")
    target = os.path.realpath(os.path.join(WEB, path or "index.html"))
    if not target.startswith(os.path.realpath(WEB) + os.sep) or not os.path.isfile(target):
        if os.path.splitext(path)[1]:  # a missing asset is a 404, not the app shell
            abort(404, "not found")
        target = os.path.join(WEB, "index.html")  # single-page-app fallback
    resp = send_from_directory(os.path.dirname(target), os.path.basename(target), max_age=0)
    if path == "sw.js":
        resp.headers["Service-Worker-Allowed"] = "/"
    return resp


# ---------------------------------------------------------------- startup
# ---------------------------------------------------------------- real-time duels
app.config["FEATURES"] = {"live_duel": False}
INTEL = intel_mod.from_env()  # live threat feeds; every source fails soft
try:  # production transport: WebSockets on the same port, through flask-sock (works with gunicorn threads)
    from flask_sock import Sock
except ImportError:  # development fallback: ws_transport.py on PORT+1, started below when run with `python server.py`
    Sock = None

if Sock is not None:
    app.config["SOCK_SERVER_OPTIONS"] = {"ping_interval": 25}
    sock = Sock(app)

    @sock.route("/ws/duel/<code>")
    def ws_duel(ws, code):
        if not origin_ok():  # only pages served by this site may open a duel connection
            ws.close()
            return
        duel.serve(ws, code, request.args.get("name", ""))

    app.config["FEATURES"]["live_duel"] = True


# ---------------------------------------------------------------- startup
def startup():
    db.init()
    fusion.get_model()  # fail fast if the model is missing
    load_cards_with_ai()
    duel.configure(_cards_cache["cards"])
    fusion.set_intel(INTEL)
    INTEL.start_background()


startup()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    if Sock is None and os.environ.get("SCAMDOJO_DEV_WS", "1") == "1":
        ws_transport.start(port + 1)
        app.config["WS_PORT"] = port + 1
        app.config["FEATURES"]["live_duel"] = True
        print("Live duels: built-in development WebSocket server on port %d (install flask-sock for production)." % (port + 1))
    print("ScamDojo (development server) on http://localhost:%d  accounts db: %s" % (port, db.DB_PATH))
    print("For production use gunicorn, see the Procfile.")
    app.run(host="0.0.0.0", port=port, threaded=True)
