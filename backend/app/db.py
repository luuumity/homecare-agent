"""SQLite 连接与阶段 0 探针。

阶段 0 只建基础设施表 app_meta；业务表（messages/memories/items/reminders…）
在阶段 1 统一设计迁移，避免现在一次铺开。
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from .migrations import migrate

SCHEMA_VERSION = "0"


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=5, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db(db_path: Path) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS app_meta ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO app_meta (key, value) VALUES (?, ?)",
            ("schema_version", SCHEMA_VERSION),
        )
        conn.commit()
        return migrate(conn)
    finally:
        conn.close()


def check_fts5() -> tuple[bool, bool, str]:
    """返回 (FTS5 是否可用, trigram 分词是否可用, 说明)。"""
    conn = sqlite3.connect(":memory:")
    try:
        try:
            conn.execute("CREATE VIRTUAL TABLE probe_fts USING fts5(content)")
        except sqlite3.OperationalError as exc:
            return False, False, f"FTS5 不可用：{exc}"

        try:
            conn.execute(
                "CREATE VIRTUAL TABLE probe_trigram USING fts5("
                "content, tokenize='trigram')"
            )
        except sqlite3.OperationalError as exc:
            return True, False, f"FTS5 可用，但 trigram 分词不可用：{exc}"

        conn.executemany(
            "INSERT INTO probe_trigram(content) VALUES (?)",
            [
                ("下午三点提醒爷爷吃降压药",),
                ("奶奶的老花镜放在床头柜第二层",),
            ],
        )
        hit = conn.execute(
            "SELECT count(*) FROM probe_trigram WHERE content MATCH ?",
            ("提醒爷爷",),
        ).fetchone()[0]
        return True, True, f"FTS5 trigram 可用（中文子串检索命中 {hit} 条）"
    finally:
        conn.close()


def check_db(db_path: Path) -> dict:
    exists = db_path.exists()
    writable = False
    error: str | None = None
    if exists:
        try:
            conn = connect(db_path)
            conn.execute(
                "INSERT INTO app_meta (key, value) VALUES ('probe_writable', '1') "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
            )
            conn.commit()
            conn.close()
            writable = True
        except sqlite3.Error as exc:
            error = str(exc)
    else:
        writable = os.access(db_path.parent, os.W_OK) if db_path.parent.exists() else False

    return {
        "path": str(db_path),
        "exists": exists,
        "writable": writable,
        "error": error,
    }
