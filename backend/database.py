"""
NovaDB SQLite layer (v3) — one object = one id + one token pair.
Single table: user_objects(data_id, user_id, token, label, private, data, updatetime)
"""

import json
import json
import sqlite3
import os
import random
import string
from datetime import datetime, timezone

DB_PATH = os.environ.get("NOVADB_DB_PATH", "./novadb.db")

ADJECTIVES = [
    "happy", "bright", "clever", "brave", "swift", "calm", "warm",
    "cool", "kind", "lucky", "sunny", "noble", "eager", "fresh",
    "bold", "wise", "merry", "sweet", "sharp", "jolly", "keen",
    "grand", "super", "swell", "brisk", "cheer", "dandy", "elite",
    "fancy", "glad", "handy", "ideal", "jaunty", "lively", "mellow",
    "neat", "perky", "quick", "ready", "snappy", "tidy",
]
ANIMALS = [
    "cat", "dog", "fox", "owl", "deer", "bear", "swan", "dove",
    "seal", "panda", "koala", "fawn", "lamb", "duck", "bunny",
    "wolf", "hawk", "otter", "whale", "finch", "crane", "robin",
    "loris", "moose", "tapir", "civet", "gecko", "heron", "lemur",
    "quail", "shrew", "trout", "coral", "fairy", "snail", "tiger",
    "zebra", "llama", "sloth", "eagle",
]


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _rand_data_id() -> str:
    adj = random.choice(ADJECTIVES)
    animal = random.choice(ANIMALS)
    num = random.randint(1000, 9999)
    return f"{adj}-{animal}-{num}"


def _rand_token() -> str:
    """8 hex chars."""
    return "".join(random.choices("0123456789abcdef", k=8))


def init_db() -> None:
    """Create table; migrate legacy data if any."""
    conn = get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS user_objects (
                data_id    TEXT PRIMARY KEY,
                user_id    TEXT DEFAULT '',
                token      TEXT UNIQUE NOT NULL,
                label      TEXT DEFAULT '',
                private    INTEGER DEFAULT 1,
                data       TEXT DEFAULT '{}',
                updatetime TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS object_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                data_id    TEXT NOT NULL,
                label      TEXT DEFAULT '',
                private    INTEGER DEFAULT 1,
                data       TEXT NOT NULL,
                changed_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_history_data_id ON object_history(data_id, changed_at DESC);
        """)
        conn.commit()
    finally:
        conn.close()


# ── CRUD ────────────────────────────────────────────────────────

def list_by_user(user_id: str) -> list[dict]:
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT data_id, token, label, private,
                      LENGTH(data) AS size_bytes, updatetime
               FROM user_objects WHERE user_id = ?
               ORDER BY updatetime DESC""",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_by_id(data_id: str) -> dict | None:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT data_id, user_id, token, label, private, data, updatetime FROM user_objects WHERE data_id = ?",
            (data_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create(user_id: str, label: str, private: bool, data_json: str) -> tuple[str, str]:
    """Create new object. Returns (data_id, token)."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    try:
        did, tok = None, None
        for _ in range(20):
            did = _rand_data_id()
            if not conn.execute("SELECT 1 FROM user_objects WHERE data_id = ?", (did,)).fetchone():
                break
        else:
            raise RuntimeError("data_id gen failed")
        for _ in range(20):
            tok = _rand_token()
            if not conn.execute("SELECT 1 FROM user_objects WHERE token = ?", (tok,)).fetchone():
                break
        else:
            raise RuntimeError("token gen failed")
        conn.execute(
            "INSERT INTO user_objects (data_id, user_id, token, label, private, data, updatetime) VALUES (?,?,?,?,?,?,?)",
            (did, user_id, tok, label, int(private), data_json, now),
        )
        conn.commit()
        # Initial creation — no history yet (nothing to compare against)
        return did, tok
    finally:
        conn.close()


def update(data_id: str, token: str, label: str, private: bool, data_json: str, force: bool = False) -> tuple[bool, bool, bool]:
    """Returns (found, changed, order_only). order_only=True means only key order differs."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    try:
        old = conn.execute(
            "SELECT label, private, data FROM user_objects WHERE data_id=? AND token=?",
            (data_id, token),
        ).fetchone()
        if not old:
            return False, False, False
        label_changed = old["label"] != label
        private_changed = bool(old["private"]) != bool(private)
        data_changed = old["data"] != data_json
        order_only = False
        if data_changed and not label_changed and not private_changed:
            try:
                old_norm = json.dumps(json.loads(old["data"]), sort_keys=True, separators=(',', ':'))
                new_norm = json.dumps(json.loads(data_json), sort_keys=True, separators=(',', ':'))
                if old_norm == new_norm:
                    order_only = True
                    if not force:
                        return True, False, True
            except Exception:
                pass
        changed = label_changed or private_changed or data_changed
        if changed:
            conn.execute(
                """UPDATE user_objects SET label=?, private=?, data=?, updatetime=?
                   WHERE data_id=? AND token=?""",
                (label, int(private), data_json, now, data_id, token),
            )
            _add_history(conn, data_id, old["label"], bool(old["private"]), old["data"])
        conn.commit()
        return True, changed, order_only
    finally:
        conn.close()


def delete(data_id: str, token: str) -> bool:
    conn = get_db()
    try:
        cur = conn.execute(
            "DELETE FROM user_objects WHERE data_id = ? AND token = ?",
            (data_id, token),
        )
        if cur.rowcount > 0:
            conn.execute("DELETE FROM object_history WHERE data_id = ?", (data_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ── History ─────────────────────────────────────────────────────
MAX_HISTORY = 50

def _add_history(conn, data_id: str, label: str, private: bool, data_json: str) -> None:
    """Insert a history entry and prune to MAX_HISTORY (uses existing connection)."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO object_history (data_id, label, private, data, changed_at) VALUES (?,?,?,?,?)",
        (data_id, label, int(private), data_json, now),
    )
    conn.execute("""
        DELETE FROM object_history WHERE id IN (
            SELECT id FROM object_history WHERE data_id = ?
            ORDER BY changed_at DESC LIMIT -1 OFFSET ?
        )
    """, (data_id, MAX_HISTORY))


def get_history(data_id: str, limit: int = 50) -> list[dict]:
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT id, label, private, data, LENGTH(data) AS size_bytes, changed_at
               FROM object_history WHERE data_id = ?
               ORDER BY changed_at DESC LIMIT ?""",
            (data_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_history_entry(history_id: int) -> dict | None:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM object_history WHERE id = ?", (history_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def restore_from_history(data_id: str, token: str, history_id: int) -> bool:
    """Restore an object to a historical version. Verifies token ownership."""
    conn = get_db()
    try:
        # Verify token
        obj = conn.execute(
            "SELECT 1 FROM user_objects WHERE data_id = ? AND token = ?",
            (data_id, token),
        ).fetchone()
        if not obj:
            return False
        entry = conn.execute(
            "SELECT * FROM object_history WHERE id = ? AND data_id = ?",
            (history_id, data_id),
        ).fetchone()
        if not entry:
            return False
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE user_objects SET label=?, private=?, data=?, updatetime=? WHERE data_id=?",
            (entry["label"], entry["private"], entry["data"], now, data_id),
        )
        # Also add a history entry for this restore action
        conn.execute(
            "INSERT INTO object_history (data_id, label, private, data, changed_at) VALUES (?,?,?,?,?)",
            (data_id, entry["label"], entry["private"], entry["data"], now),
        )
        conn.commit()
        return True, changed
    finally:
        conn.close()
