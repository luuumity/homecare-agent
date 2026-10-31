"""对话、摘要与会话状态的持久化。只存本地原文，发送模型前统一脱敏。"""

from __future__ import annotations

import sqlite3
from typing import Any

from ..utils import new_id, now_iso

MAIN_STATE_ID = "main"


def _ensure_state(conn: sqlite3.Connection, now: str) -> None:
    conn.execute(
        "INSERT INTO conversation_state (id, last_message_id, last_summarized_message_id,"
        " state, updated_at) VALUES (?, NULL, NULL, '{}', ?)"
        " ON CONFLICT(id) DO NOTHING",
        (MAIN_STATE_ID, now),
    )


def add_message(
    conn: sqlite3.Connection,
    role: str,
    content: str,
    tool_name: str | None = None,
    tool_payload: dict[str, Any] | None = None,
) -> dict:
    message_id, now = new_id(), now_iso()
    payload = None
    if tool_payload is not None:
        import json

        payload = json.dumps(tool_payload, ensure_ascii=False, default=str)
    conn.execute(
        "INSERT INTO messages (id, role, content, tool_name, tool_payload,"
        " created_at, deleted_at) VALUES (?, ?, ?, ?, ?, ?, NULL)",
        (message_id, role, content, tool_name, payload, now),
    )
    _ensure_state(conn, now)
    conn.execute(
        "UPDATE conversation_state SET last_message_id = ?, updated_at = ? WHERE id = ?",
        (message_id, now, MAIN_STATE_ID),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    return dict(row)


def recent_messages(conn: sqlite3.Connection, limit: int = 12) -> list[dict]:
    rows = conn.execute(
        "SELECT id, role, content, created_at FROM messages"
        " WHERE deleted_at IS NULL AND role IN ('user', 'assistant') AND content <> ''"
        " ORDER BY rowid DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in reversed(rows)]


def list_history(conn: sqlite3.Connection, limit: int = 50, include_tool: bool = False) -> list[dict]:
    roles = "('user', 'assistant', 'tool')" if include_tool else "('user', 'assistant')"
    rows = conn.execute(
        f"SELECT id, role, content, tool_name, tool_payload, created_at FROM messages"
        f" WHERE deleted_at IS NULL AND role IN {roles}"
        f" ORDER BY rowid DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in reversed(rows)]


def latest_summary(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute(
        "SELECT * FROM summaries ORDER BY rowid DESC LIMIT 1"
    ).fetchone()
    return dict(row) if row else None


def _state_row(conn: sqlite3.Connection) -> dict:
    row = conn.execute(
        "SELECT * FROM conversation_state WHERE id = ?", (MAIN_STATE_ID,)
    ).fetchone()
    return dict(row) if row else {}


def unsummarized_messages(conn: sqlite3.Connection) -> list[dict]:
    """按 rowid 返回尚未进入摘要的 user/assistant 消息。"""
    last_id = _state_row(conn).get("last_summarized_message_id")
    last_rowid = 0
    if last_id:
        row = conn.execute("SELECT rowid FROM messages WHERE id = ?", (last_id,)).fetchone()
        last_rowid = int(row["rowid"]) if row else 0
    rows = conn.execute(
        "SELECT rowid, id, role, content, created_at FROM messages"
        " WHERE deleted_at IS NULL AND role IN ('user', 'assistant') AND content <> ''"
        " AND rowid > ? ORDER BY rowid ASC",
        (last_rowid,),
    ).fetchall()
    return [dict(row) for row in rows]


def save_summary(conn: sqlite3.Connection, content: str, covers_from: str,
                 covers_to: str) -> dict:
    summary_id, now = new_id(), now_iso()
    conn.execute(
        "INSERT INTO summaries (id, content, covers_from_message_id,"
        " covers_to_message_id, created_at) VALUES (?, ?, ?, ?, ?)",
        (summary_id, content, covers_from, covers_to, now),
    )
    _ensure_state(conn, now)
    conn.execute(
        "UPDATE conversation_state SET last_summarized_message_id = ?, updated_at = ?"
        " WHERE id = ?",
        (covers_to, now, MAIN_STATE_ID),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM summaries WHERE id = ?", (summary_id,)).fetchone()
    return dict(row)


def status(conn: sqlite3.Connection) -> dict:
    counts = conn.execute(
        "SELECT role, count(*) AS total FROM messages WHERE deleted_at IS NULL GROUP BY role"
    ).fetchall()
    summary = latest_summary(conn)
    state = _state_row(conn)
    return {
        "message_count": sum(int(row["total"]) for row in counts),
        "by_role": {row["role"]: int(row["total"]) for row in counts},
        "has_summary": bool(summary),
        "summary_count": conn.execute("SELECT count(*) AS n FROM summaries").fetchone()["n"],
        "last_message_id": state.get("last_message_id"),
        "last_summarized_message_id": state.get("last_summarized_message_id"),
    }
