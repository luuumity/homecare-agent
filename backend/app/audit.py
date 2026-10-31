"""审计与同步队列写入。所有业务写操作都必须调用。"""

from __future__ import annotations

import json
import sqlite3

from .utils import new_id, now_iso


def _dumps(value) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)


def write_audit(
    conn: sqlite3.Connection,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str | None,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    conn.execute(
        "INSERT INTO audit_log (id, actor, action, entity_type, entity_id,"
        " before, after, ip, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?)",
        (
            new_id(),
            actor,
            action,
            entity_type,
            entity_id,
            _dumps(before),
            _dumps(after),
            now_iso(),
        ),
    )


def write_outbox(
    conn: sqlite3.Connection,
    entity_type: str,
    entity_id: str,
    op: str,
    payload: dict | None = None,
) -> None:
    conn.execute(
        "INSERT INTO sync_outbox (id, entity_type, entity_id, op, payload,"
        " created_at, processed_at) VALUES (?, ?, ?, ?, ?, ?, NULL)",
        (new_id(), entity_type, entity_id, op, _dumps(payload), now_iso()),
    )


def decode_json(value: str | None) -> dict | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
