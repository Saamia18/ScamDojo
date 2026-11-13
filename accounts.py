"""Accounts for ScamDojo: standard library only (sqlite3, hashlib.scrypt, secrets).

What is stored per user: username, display name, password hash, recovery-code hash, and a small progress blob
(XP, badges, streak, language, checkup scores). Pasted messages are NEVER stored. Optional, opt-in extras live in history.py.

Security choices
  * passwords: scrypt (n=2^14, r=8, p=1) with a random salt per user; constant-time comparison
  * sessions: random 256-bit token in an HttpOnly, SameSite=Lax cookie; only a SHA-256 hash of the token is stored
  * no email: password reset uses a one-time recovery code shown at signup (stored hashed, rotated after use)
  * login/reset attempts are rate limited per username and per client address
  * the progress blob is validated against a whitelist and size-capped
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from collections import defaultdict, deque

SESSION_DAYS = 30
MAX_PROGRESS_BYTES = 60_000
USERNAME_RE = re.compile(r"^[a-z0-9_.]{3,30}$")
COMMON_PASSWORDS = {"password", "password1", "12345678", "123456789", "1234567890", "qwertyuiop", "iloveyou", "abcd1234", "11111111",
                    "00000000", "scamdojo", "scamdojo1", "welcome1", "letmein123", "admin1234", "passw0rd", "qwerty123", "india1234"}
RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I

_lock = threading.Lock()


class AuthError(Exception):
    """A user-facing problem (bad input, wrong password...). The message is safe to show."""
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


# ---------------- storage (see db.py) ----------------
import db  # noqa: E402
from db import configure, connect, init  # noqa: E402,F401  (kept here so older imports keep working)


# ---------------- rate limiting (in memory) ----------------
class Limiter:
    def __init__(self):
        self.hits = defaultdict(deque)

    def blocked(self, key, limit, window):
        now, q = time.time(), self.hits[key]
        while q and now - q[0] > window:
            q.popleft()
        return len(q) >= limit

    def add(self, key):
        self.hits[key].append(time.time())

    def clear(self, key):
        self.hits.pop(key, None)


limiter = Limiter()


# ---------------- hashing ----------------
def _scrypt(secret, salt):
    return hashlib.scrypt(secret.encode("utf-8"), salt=salt, n=2 ** 14, r=8, p=1, dklen=32, maxmem=64 * 1024 * 1024)


_DUMMY_SALT = os.urandom(16)
_DUMMY_HASH = _scrypt("not-a-real-password", _DUMMY_SALT)


def _norm_code(code):
    return re.sub(r"[^A-Z0-9]", "", (code or "").upper())


def _new_recovery_code():
    raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(12))
    return "-".join(raw[i:i + 4] for i in range(0, 12, 4))


def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------- validation ----------------
def clean_username(u):
    u = (u or "").strip().lower()
    if not USERNAME_RE.match(u):
        raise AuthError("Username must be 3 to 30 characters: letters, numbers, dot or underscore.")
    return u


def check_password(pw, username=""):
    if not isinstance(pw, str) or len(pw) < 8:
        raise AuthError("Password must be at least 8 characters.")
    if len(pw) > 128:
        raise AuthError("Password is too long (128 characters at most).")
    if pw.lower() in COMMON_PASSWORDS or (username and pw.lower() == username.lower()):
        raise AuthError("That password is too easy to guess. Pick something different.")


def clean_display(name, fallback):
    name = re.sub(r"[\x00-\x1f\x7f<>]", "", (name or "")).strip()[:40]
    return name or fallback


# ---------------- accounts ----------------
def public_user(row):
    return {"id": row["id"], "username": row["username"], "display_name": row["display_name"], "created_at": row["created_at"]}


def register(username, password, display_name, ip):
    username = clean_username(username)
    check_password(password, username)
    if limiter.blocked("reg:" + ip, 6, 3600):
        raise AuthError("Too many accounts created from this connection. Try again later.", 429)
    salt, rsalt = os.urandom(16), os.urandom(16)
    code = _new_recovery_code()
    now = int(time.time())
    with _lock, connect() as con:
        if con.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            raise AuthError("That username is taken.", 409)
        cur = con.execute("INSERT INTO users(username, display_name, pw_salt, pw_hash, rec_salt, rec_hash, created_at, last_login) VALUES(?,?,?,?,?,?,?,?)",
                          (username, clean_display(display_name, username), salt, _scrypt(password, salt), rsalt, _scrypt(_norm_code(code), rsalt), now, now))
        row = con.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
    limiter.add("reg:" + ip)
    return public_user(row), code


def login(username, password, ip):
    try:
        username = clean_username(username)
    except AuthError:
        raise AuthError("Wrong username or password.", 401)
    if limiter.blocked("fail:" + username, 5, 600) or limiter.blocked("failip:" + ip, 30, 600):
        raise AuthError("Too many attempts. Wait 10 minutes and try again.", 429)
    with connect() as con:
        row = con.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    # always do one scrypt so the response time does not reveal whether the username exists
    ok = hmac.compare_digest(_scrypt(password or "", row["pw_salt"] if row else _DUMMY_SALT), row["pw_hash"] if row else _DUMMY_HASH) and row is not None
    if not ok:
        limiter.add("fail:" + username); limiter.add("failip:" + ip)
        raise AuthError("Wrong username or password.", 401)
    limiter.clear("fail:" + username)
    with connect() as con:
        con.execute("UPDATE users SET last_login=? WHERE id=?", (int(time.time()), row["id"]))
    return public_user(row)


def create_session(user_id):
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    with connect() as con:
        con.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
        con.execute("INSERT INTO sessions(token_hash, user_id, created_at, expires_at) VALUES(?,?,?,?)", (_token_hash(token), user_id, now, now + SESSION_DAYS * 86400))
    return token


def user_for_token(token):
    if not token:
        return None
    with connect() as con:
        row = con.execute("SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?", (_token_hash(token), int(time.time()))).fetchone()
    return public_user(row) if row else None


def end_session(token):
    if token:
        with connect() as con:
            con.execute("DELETE FROM sessions WHERE token_hash=?", (_token_hash(token),))


def change_password(user_id, current, new):
    with connect() as con:
        row = con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not row or not hmac.compare_digest(_scrypt(current or "", row["pw_salt"]), row["pw_hash"]):
            raise AuthError("Your current password is wrong.", 401)
        check_password(new, row["username"])
        salt = os.urandom(16)
        con.execute("UPDATE users SET pw_salt=?, pw_hash=? WHERE id=?", (salt, _scrypt(new, salt), user_id))
        con.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))  # sign out everywhere


def reset_password(username, code, new, ip):
    """Reset with the recovery code. Returns (user, new_recovery_code). The old code stops working."""
    try:
        username = clean_username(username)
    except AuthError:
        raise AuthError("Username or recovery code is wrong.", 401)
    if limiter.blocked("reset:" + username, 5, 3600) or limiter.blocked("resetip:" + ip, 20, 3600):
        raise AuthError("Too many attempts. Try again in an hour.", 429)
    with connect() as con:
        row = con.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    ok = hmac.compare_digest(_scrypt(_norm_code(code), row["rec_salt"] if row else _DUMMY_SALT), row["rec_hash"] if row else _DUMMY_HASH) and row is not None
    if not ok:
        limiter.add("reset:" + username); limiter.add("resetip:" + ip)
        raise AuthError("Username or recovery code is wrong.", 401)
    check_password(new, username)
    salt, rsalt, new_code = os.urandom(16), os.urandom(16), _new_recovery_code()
    with _lock, connect() as con:
        con.execute("UPDATE users SET pw_salt=?, pw_hash=?, rec_salt=?, rec_hash=? WHERE id=?", (salt, _scrypt(new, salt), rsalt, _scrypt(_norm_code(new_code), rsalt), row["id"]))
        con.execute("DELETE FROM sessions WHERE user_id=?", (row["id"],))
    limiter.clear("reset:" + username)
    return public_user(row), new_code


def delete_account(user_id, password):
    with connect() as con:
        row = con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not row or not hmac.compare_digest(_scrypt(password or "", row["pw_salt"]), row["pw_hash"]):
            raise AuthError("Password is wrong.", 401)
        con.execute("DELETE FROM users WHERE id=?", (user_id,))  # sessions and progress go with it (ON DELETE CASCADE)


# ---------------- progress ----------------
_INT_KEYS = ("xp", "rushBest", "duelWins", "duelPlayed", "perfect")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _int(v, hi=10 ** 7):
    return max(0, min(hi, int(v))) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0


def _dates(d, limit=400):
    out = {}
    if isinstance(d, dict):
        for k, v in list(d.items())[:limit]:
            if isinstance(k, str) and len(k) <= 40:
                out[k] = v if isinstance(v, str) and _DATE.match(v) else None
    return out


def sanitize_progress(d):
    """Keep only the fields the app uses, with sane types and sizes. Anything else is dropped."""
    if not isinstance(d, dict):
        raise AuthError("Progress must be an object.")
    out = {k: _int(d.get(k)) for k in _INT_KEYS}
    out["lang"] = d.get("lang") if d.get("lang") in ("en", "hi", "kn") else "en"
    out["saveHistory"] = bool(d.get("saveHistory", False)); out["leaderboard"] = bool(d.get("leaderboard", False))
    out["sound"] = bool(d.get("sound", True)); out["autoread"] = bool(d.get("autoread", False))
    out["days"] = [x for x in (d.get("days") or [])[-400:] if isinstance(x, str) and _DATE.match(x)]
    out["bossDone"] = {k: v for k, v in _dates(d.get("bossDone"), 30).items() if v}
    out["badges"] = {k: v for k, v in _dates(d.get("badges"), 40).items() if v}
    st = d.get("stats") if isinstance(d.get("stats"), dict) else {}
    out["stats"] = {k: _int(st.get(k)) for k in ("seen", "correct", "crits", "bossWins")}
    ct = d.get("cats") if isinstance(d.get("cats"), dict) else {}
    out["cats"] = {k: _int(ct.get(k)) for k in ("otp", "link")}
    miss = {}
    if isinstance(d.get("miss"), dict):
        for k, v in list(d["miss"].items())[:60]:
            if isinstance(k, str) and len(k) <= 30 and isinstance(v, dict):
                miss[k] = {"seen": _int(v.get("seen")), "miss": _int(v.get("miss"))}
    out["miss"] = miss
    daily = {}
    if isinstance(d.get("daily"), dict):
        for k, v in list(d["daily"].items())[-400:]:
            if isinstance(k, str) and _DATE.match(k) and isinstance(v, dict):
                daily[k] = {"correct": bool(v.get("correct"))}
    out["daily"] = daily
    checks = []
    for c in (d.get("checkups") or [])[-30:]:
        if isinstance(c, dict) and isinstance(c.get("date"), str) and _DATE.match(c["date"]):
            checks.append({"date": c["date"], "good": _int(c.get("good"), 50), "total": max(1, _int(c.get("total"), 50))})
    out["checkups"] = checks
    return out


def get_progress(user_id):
    with connect() as con:
        row = con.execute("SELECT data, updated_at FROM progress WHERE user_id=?", (user_id,)).fetchone()
    return (json.loads(row["data"]), row["updated_at"]) if row else (None, None)


def put_progress(user_id, data):
    clean = sanitize_progress(data)
    blob = json.dumps(clean, separators=(",", ":"))
    if len(blob.encode("utf-8")) > MAX_PROGRESS_BYTES:
        raise AuthError("Progress is too large.", 413)
    now = int(time.time())
    with connect() as con:
        con.execute("INSERT INTO progress(user_id, data, updated_at) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at", (user_id, blob, now))
        row = con.execute("SELECT display_name FROM users WHERE id=?", (user_id,)).fetchone()
    if row:
        import history
        history.sync_leaderboard(user_id, row["display_name"], clean)
    return clean, now
