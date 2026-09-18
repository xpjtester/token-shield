import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager

from app.config import settings


def init_db() -> None:
    os.makedirs(os.path.dirname(os.path.abspath(settings.database_path)), exist_ok=True)
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS cache (
          cache_key TEXT PRIMARY KEY, response TEXT NOT NULL, created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS requests (
          id INTEGER PRIMARY KEY AUTOINCREMENT, created_at INTEGER NOT NULL,
          model TEXT NOT NULL, before_tokens INTEGER NOT NULL, after_tokens INTEGER NOT NULL,
          output_tokens INTEGER NOT NULL DEFAULT 0, cache_hit INTEGER NOT NULL DEFAULT 0,
          actions TEXT NOT NULL
        );
        """)


@contextmanager
def connect():
    db = sqlite3.connect(settings.database_path)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()


def cache_key(payload: dict) -> str:
    stable = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(stable.encode()).hexdigest()


def cache_get(key: str) -> dict | None:
    with connect() as db:
        row = db.execute("SELECT response, created_at FROM cache WHERE cache_key=?", (key,)).fetchone()
        if not row or time.time() - row["created_at"] > settings.cache_ttl_seconds:
            return None
        return json.loads(row["response"])


def cache_put(key: str, response: dict) -> None:
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO cache VALUES (?, ?, ?)", (key, json.dumps(response), int(time.time())))


def log_request(model: str, before: int, after: int, output: int, cache_hit: bool, actions: list[str]) -> None:
    with connect() as db:
        db.execute(
            "INSERT INTO requests(created_at, model, before_tokens, after_tokens, output_tokens, cache_hit, actions) VALUES(?,?,?,?,?,?,?)",
            (int(time.time()), model, before, after, output, int(cache_hit), json.dumps(actions)),
        )


def stats() -> dict:
    with connect() as db:
        row = db.execute("""SELECT COUNT(*) requests, COALESCE(SUM(before_tokens),0) before_tokens,
          COALESCE(SUM(after_tokens),0) after_tokens, COALESCE(SUM(output_tokens),0) output_tokens,
          COALESCE(SUM(cache_hit),0) cache_hits FROM requests""").fetchone()
        daily = db.execute("""SELECT date(created_at, 'unixepoch') day,
          SUM(before_tokens-after_tokens) saved FROM requests GROUP BY day ORDER BY day DESC LIMIT 14""").fetchall()
    result = dict(row)
    result["saved_tokens"] = result["before_tokens"] - result["after_tokens"]
    result["saving_percent"] = round(result["saved_tokens"] / result["before_tokens"] * 100, 1) if result["before_tokens"] else 0
    result["daily"] = [dict(x) for x in reversed(daily)]
    return result

