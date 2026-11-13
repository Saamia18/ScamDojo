"""Opt-in scan history (metadata only) and the opt-in leaderboard."""
import json
import time

import db

HISTORY_KEEP = 200
XP_PER_HOUR_CAP = 6000  # plausibility cap: progress is reported by the browser, so the board is for fun, not tamper-proof


def add_scan(user_id, source, verdict, risk, categories, entity_counts):
    with db.connect() as con:
        con.execute("INSERT INTO scan_history(user_id, created_at, source, verdict, risk, categories, entity_counts) VALUES(?,?,?,?,?,?,?)",
                    (user_id, int(time.time()), source, verdict, round(float(risk), 3), json.dumps(list(categories)[:8]), json.dumps(entity_counts)))
        con.execute("DELETE FROM scan_history WHERE user_id=? AND id NOT IN (SELECT id FROM scan_history WHERE user_id=? ORDER BY created_at DESC, id DESC LIMIT ?)",
                    (user_id, user_id, HISTORY_KEEP))


def list_scans(user_id, limit=50):
    with db.connect() as con:
        rows = con.execute("SELECT * FROM scan_history WHERE user_id=? ORDER BY created_at DESC, id DESC LIMIT ?", (user_id, limit)).fetchall()
    return [{"created_at": r["created_at"], "source": r["source"], "verdict": r["verdict"], "risk": r["risk"],
             "categories": json.loads(r["categories"]), "entities": json.loads(r["entity_counts"])} for r in rows]


def clear_scans(user_id):
    with db.connect() as con:
        con.execute("DELETE FROM scan_history WHERE user_id=?", (user_id,))


def sync_leaderboard(user_id, display_name, progress):
    """Add, update or remove the user's leaderboard row depending on their opt-in flag."""
    now = int(time.time())
    with db.connect() as con:
        if not progress.get("leaderboard"):
            con.execute("DELETE FROM leaderboard WHERE user_id=?", (user_id,))
            return
        xp = int(progress.get("xp", 0))
        prev = con.execute("SELECT xp, updated_at FROM leaderboard WHERE user_id=?", (user_id,)).fetchone()
        if prev:
            allowed = prev["xp"] + int(XP_PER_HOUR_CAP * max(1.0, (now - prev["updated_at"]) / 3600.0))
            xp = min(xp, allowed)
        level = 1 + xp // 100
        wins = int(progress.get("stats", {}).get("bossWins", 0))
        con.execute("INSERT INTO leaderboard(user_id, display_name, xp, level, boss_wins, updated_at) VALUES(?,?,?,?,?,?) "
                    "ON CONFLICT(user_id) DO UPDATE SET display_name=excluded.display_name, xp=excluded.xp, level=excluded.level, boss_wins=excluded.boss_wins, updated_at=excluded.updated_at",
                    (user_id, display_name, xp, level, wins, now))


def top(limit=20):
    with db.connect() as con:
        rows = con.execute("SELECT display_name, xp, level, boss_wins FROM leaderboard ORDER BY xp DESC, updated_at ASC LIMIT ?", (limit,)).fetchall()
    return [{"rank": i + 1, "name": r["display_name"], "xp": r["xp"], "level": r["level"], "boss_wins": r["boss_wins"]} for i, r in enumerate(rows)]
