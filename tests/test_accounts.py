"""Run with:  python -m unittest discover -s tests -v"""
import os
os.environ.setdefault("SCAMDOJO_FEEDS", "0")  # no live feeds during tests
import json
import os
import tempfile
import unittest

import accounts


class Core(unittest.TestCase):
    def setUp(self):
        accounts.configure(os.path.join(tempfile.mkdtemp(), "t.db"))
        accounts.limiter.hits.clear()

    def test_register_login_and_password_rules(self):
        u, code = accounts.register("Asha_01", "monsoon rain 77", "Asha", "1.1.1.1")
        self.assertEqual(u["username"], "asha_01")
        self.assertRegex(code, r"^[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}$")
        self.assertEqual(accounts.login("ASHA_01", "monsoon rain 77", "1.1.1.1")["display_name"], "Asha")
        with self.assertRaises(accounts.AuthError) as cm:
            accounts.register("asha_01", "another password", "", "1.1.1.1")
        self.assertEqual(cm.exception.status, 409)
        for bad in ("short", "password", "x" * 200):
            with self.assertRaises(accounts.AuthError):
                accounts.register("someone", bad, "", "1.1.1.1")
        with self.assertRaises(accounts.AuthError):
            accounts.register("bad name!", "monsoon rain 77", "", "1.1.1.1")

    def test_passwords_are_not_stored_in_plain_text(self):
        accounts.register("rahul_k", "very secret pw 1", "", "1.1.1.1")
        with accounts.connect() as con:
            row = con.execute("SELECT * FROM users WHERE username='rahul_k'").fetchone()
        blob = b"".join(bytes(row[k]) for k in ("pw_salt", "pw_hash", "rec_salt", "rec_hash"))
        self.assertNotIn(b"very secret pw 1", blob)
        self.assertEqual(len(row["pw_hash"]), 32)

    def test_lockout_after_repeated_failures_and_generic_message(self):
        accounts.register("lock_me", "right password 1", "", "2.2.2.2")
        msgs = set()
        for _ in range(5):
            with self.assertRaises(accounts.AuthError) as cm:
                accounts.login("lock_me", "wrong", "2.2.2.2")
            msgs.add(str(cm.exception))
        with self.assertRaises(accounts.AuthError) as cm:
            accounts.login("nobody_here", "wrong", "3.3.3.3")
        msgs.add(str(cm.exception))
        self.assertEqual(msgs, {"Wrong username or password."})  # same text for wrong password and unknown user
        with self.assertRaises(accounts.AuthError) as cm:
            accounts.login("lock_me", "right password 1", "2.2.2.2")
        self.assertEqual(cm.exception.status, 429)

    def test_sessions_expire_and_end(self):
        u, _ = accounts.register("sess_user", "session pw 123", "", "1.1.1.1")
        tok = accounts.create_session(u["id"])
        self.assertEqual(accounts.user_for_token(tok)["username"], "sess_user")
        with accounts.connect() as con:  # the raw token is never stored
            self.assertIsNone(con.execute("SELECT 1 FROM sessions WHERE token_hash=?", (tok,)).fetchone())
            con.execute("UPDATE sessions SET expires_at=1")
        self.assertIsNone(accounts.user_for_token(tok))
        tok2 = accounts.create_session(u["id"]); accounts.end_session(tok2)
        self.assertIsNone(accounts.user_for_token(tok2))

    def test_reset_with_recovery_code_rotates_code_and_kills_sessions(self):
        u, code = accounts.register("reset_me", "old password 1", "", "1.1.1.1")
        tok = accounts.create_session(u["id"])
        with self.assertRaises(accounts.AuthError):
            accounts.reset_password("reset_me", "AAAA-BBBB-CCCC", "new password 1", "1.1.1.1")
        _, new_code = accounts.reset_password("reset_me", code.lower().replace("-", " "), "new password 1", "1.1.1.1")
        self.assertNotEqual(code, new_code)
        self.assertIsNone(accounts.user_for_token(tok))
        accounts.login("reset_me", "new password 1", "1.1.1.1")
        with self.assertRaises(accounts.AuthError):
            accounts.reset_password("reset_me", code, "third password 1", "1.1.1.1")  # old code is dead

    def test_change_password_signs_out_everywhere_and_delete_removes_all(self):
        u, _ = accounts.register("del_user", "first password 1", "", "1.1.1.1")
        tok = accounts.create_session(u["id"]); accounts.put_progress(u["id"], {"xp": 5})
        accounts.change_password(u["id"], "first password 1", "second password 1")
        self.assertIsNone(accounts.user_for_token(tok))
        with self.assertRaises(accounts.AuthError):
            accounts.delete_account(u["id"], "wrong")
        accounts.delete_account(u["id"], "second password 1")
        self.assertEqual(accounts.get_progress(u["id"]), (None, None))
        with accounts.connect() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 0)

    def test_progress_is_sanitised(self):
        u, _ = accounts.register("prog_user", "progress pw 123", "", "1.1.1.1")
        clean, _ = accounts.put_progress(u["id"], {"xp": -50, "rushBest": 10 ** 12, "evil": "<script>", "lang": "xx",
                                                    "days": ["2026-11-12", "not-a-date"], "badges": {"first": "2026-11-12", "x": "bad"},
                                                    "miss": {"otp": {"seen": 4, "miss": 2}, "": "junk"}, "stats": {"seen": 3, "hack": 9}})
        self.assertEqual(clean["xp"], 0); self.assertEqual(clean["rushBest"], 10 ** 7); self.assertNotIn("evil", clean)
        self.assertEqual(clean["lang"], "en"); self.assertEqual(clean["days"], ["2026-11-12"]); self.assertEqual(clean["badges"], {"first": "2026-11-12"})
        self.assertEqual(clean["miss"], {"otp": {"seen": 4, "miss": 2}}); self.assertEqual(clean["stats"]["seen"], 3); self.assertNotIn("hack", clean["stats"])
        with self.assertRaises(accounts.AuthError):
            accounts.put_progress(u["id"], "not an object")


class Http(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import server
        accounts.configure(os.path.join(tempfile.mkdtemp(), "http.db"))
        cls.app = server.app

    def setUp(self):
        accounts.limiter.hits.clear()
        self.app.config["TESTING"] = False

    def test_full_flow_and_cookie_flags(self):
        c = self.app.test_client()
        r = c.post("/api/auth/register", json={"username": "http_user", "password": "http password 1", "display_name": "H", "progress": {"xp": 40}})
        self.assertEqual(r.status_code, 201)
        cookie = r.headers["Set-Cookie"]
        for flag in ("HttpOnly", "SameSite=Lax", "Path=/"):
            self.assertIn(flag, cookie)
        self.assertEqual(c.get("/api/me").json["progress"]["xp"], 40)
        self.assertEqual(c.put("/api/progress", json={"progress": {"xp": 90}}).status_code, 200)
        self.assertEqual(c.get("/api/progress").json["progress"]["xp"], 90)
        self.assertEqual(c.post("/api/progress", json={"progress": {"xp": 95}}).status_code, 200)
        self.assertEqual(self.app.test_client().put("/api/progress", json={"progress": {"xp": 1}}).status_code, 401)
        self.assertEqual(c.post("/api/auth/logout", json={}).status_code, 200)
        self.assertIsNone(c.get("/api/me").json["user"])

    def test_csrf_content_type_and_cors(self):
        c = self.app.test_client()
        self.assertEqual(c.post("/api/auth/login", json={"username": "a", "password": "b"}, headers={"Origin": "http://evil.example"}).status_code, 403)
        self.assertEqual(c.post("/api/auth/login", data='{"username": "a"}', headers={"Content-Type": "text/plain"}).status_code, 415)
        self.assertNotIn("Access-Control-Allow-Origin", c.get("/api/me").headers)

    def test_leaderboard_and_history_are_opt_in_and_metadata_only(self):
        c = self.app.test_client()
        c.post("/api/auth/register", json={"username": "opt_user", "password": "opt in password 1", "display_name": "Opty"})
        c.post("/api/scan", json={"text": "Your KYC expired, update at http://sbi-kyc.xyz within 2 hours"})
        self.assertEqual(c.get("/api/history").json["rows"], [])  # off by default
        c.put("/api/progress", json={"progress": {"xp": 300, "saveHistory": True, "leaderboard": True}})
        c.post("/api/scan", json={"text": "Your KYC expired, update at http://sbi-kyc.xyz within 2 hours"})
        rows = c.get("/api/history").json["rows"]
        self.assertEqual(len(rows), 1)
        self.assertNotIn("text", rows[0])
        self.assertNotIn("KYC expired", json.dumps(rows))  # the message itself is never stored
        self.assertIn("Opty", [r["name"] for r in self.app.test_client().get("/api/leaderboard").json["rows"]])
        self.assertNotIn("opt_user", json.dumps(self.app.test_client().get("/api/leaderboard").json))  # username never exposed
        c.delete("/api/history")
        self.assertEqual(c.get("/api/history").json["rows"], [])


if __name__ == "__main__":
    unittest.main()
