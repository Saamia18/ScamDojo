"""Database layer (SQLite, standard library). One place for the connection and the whole schema.

Tables: users, sessions, progress, scan_history, leaderboard, generated_cards.
Point SCAMDOJO_DB at a file on a persistent disk in production; use a PostgreSQL service only if you outgrow one process.
"""
import os
import sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("SCAMDOJO_DB", os.path.join(ROOT, "data", "scamdojo.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL,
    pw_salt BLOB NOT NULL, pw_hash BLOB NOT NULL, rec_salt BLOB NOT NULL, rec_hash BLOB NOT NULL,
    created_at INTEGER NOT NULL, last_login INTEGER);
CREATE TABLE IF NOT EXISTS sessions(
    token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS progress(
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, data TEXT NOT NULL, updated_at INTEGER NOT NULL);
-- Metadata only. The scanned message text is NEVER stored here. Written only when the user turned history on.
CREATE TABLE IF NOT EXISTS scan_history(
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL, source TEXT NOT NULL, verdict TEXT NOT NULL, risk REAL NOT NULL,
    categories TEXT NOT NULL, entity_counts TEXT NOT NULL);
-- Only users who opted in appear. display_name is what they chose to show; username is never exposed.
CREATE TABLE IF NOT EXISTS leaderboard(
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, display_name TEXT NOT NULL,
    xp INTEGER NOT NULL, level INTEGER NOT NULL, boss_wins INTEGER NOT NULL, updated_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS generated_cards(
    id TEXT PRIMARY KEY, category TEXT NOT NULL, lang TEXT NOT NULL, json TEXT NOT NULL, source TEXT NOT NULL,
    created_at INTEGER NOT NULL, created_by INTEGER);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_history_user ON scan_history(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leaderboard_xp ON leaderboard(xp DESC);
CREATE INDEX IF NOT EXISTS idx_generated_created ON generated_cards(created_at DESC);
"""


def configure(path):
    global DB_PATH
    DB_PATH = path
    init()


def connect():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init():
    with connect() as con:
        con.execute("PRAGMA journal_mode=WAL")
        con.executescript(SCHEMA)
