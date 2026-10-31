"""业务数据访问层：所有写操作带审计与同步队列，删除均为软删除。"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from .adapters.family_notify import notify_family
from .audit import decode_json, write_audit, write_outbox
from .errors import BadRequest, Conflict, NotFound
from .utils import desensitize_phone, new_id, now_iso, to_iso

REQUIRES_CONFIRMATION = {"medical", "identity"}

# ---------------------------------------------------------------- 通用

def _row(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row else None


def _query_one(conn: sqlite3.Connection, sql: str, params=()) -> dict | None:
    return _row(conn.execute(sql, params).fetchone())


# ---------------------------------------------------------------- 物品

def _item(conn, item_id: str, include_deleted: bool = False) -> dict | None:
    sql = "SELECT * FROM items WHERE id = ?"
    if not include_deleted:
        sql += " AND deleted_at IS NULL"
    return _query_one(conn, sql, (item_id,))


def get_item(conn, item_id: str) -> dict:
    item = _item(conn, item_id)
    if not item:
        raise NotFound("物品不存在")
    return item


def create_item(conn, actor: str, name: str, location: str, note: str | None = None) -> dict:
    item_id, now = new_id(), now_iso()
    conn.execute(
        "INSERT INTO items (id, name, location, note, created_by, created_at,"
        " updated_at, deleted_at) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)",
        (item_id, name, location, note, actor, now, now),
    )
    after = _item(conn, item_id)
    write_audit(conn, actor, "create", "item", item_id, after=after)
    write_outbox(conn, "item", item_id, "upsert", after)
    conn.commit()
    return after


def list_items(conn, q: str = "", limit: int = 50, offset: int = 0) -> list[dict]:
    where = ["deleted_at IS NULL"]
    params: list = []
    if q:
        like = f"%{q}%"
        where.append("(name LIKE ? OR location LIKE ? OR COALESCE(note, '') LIKE ?)")
        params.extend([like, like, like])
    rows = conn.execute(
        "SELECT * FROM items WHERE " + " AND ".join(where)
        + " ORDER BY updated_at DESC LIMIT ? OFFSET ?",
        (*params, limit, offset),
    ).fetchall()
    return [dict(row) for row in rows]


def update_item(conn, actor: str, item_id: str, changes: dict) -> dict:
    before = _item(conn, item_id)
    if not before:
        raise NotFound("物品不存在")
    updates = {k: v for k, v in changes.items() if k in {"name", "location", "note"}}
    if not updates:
        raise BadRequest("没有需要修改的字段")
    if any(not updates[k] for k in ("name", "location") if k in updates):
        raise BadRequest("名称和位置不能为空")
    sets = ", ".join(f"{key} = ?" for key in updates)
    conn.execute(
        f"UPDATE items SET {sets}, updated_at = ? WHERE id = ?",
        (*updates.values(), now_iso(), item_id),
    )
    after = _item(conn, item_id)
    write_audit(conn, actor, "update", "item", item_id, before=before, after=after)
    write_outbox(conn, "item", item_id, "upsert", after)
    conn.commit()
    return after


def delete_item(conn, actor: str, item_id: str) -> None:
    before = _item(conn, item_id)
    if not before:
        raise NotFound("物品不存在")
    now = now_iso()
    conn.execute("UPDATE items SET deleted_at = ?, updated_at = ? WHERE id = ?", (now, now, item_id))
    write_audit(conn, actor, "delete", "item", item_id, before=before, after={"deleted_at": now})
    write_outbox(conn, "item", item_id, "delete", {"deleted_at": now})
    conn.commit()


# ---------------------------------------------------------------- 提醒

def _reminder(conn, reminder_id: str, include_deleted: bool = False) -> dict | None:
    sql = "SELECT * FROM reminders WHERE id = ?"
    if not include_deleted:
        sql += " AND deleted_at IS NULL"
    return _query_one(conn, sql, (reminder_id,))


def get_reminder(conn, reminder_id: str) -> dict:
    reminder = _reminder(conn, reminder_id)
    if not reminder:
        raise NotFound("提醒不存在")
    return reminder


def create_reminder(conn, actor: str, title: str, remind_at: datetime,
                    repeat_rule: str = "none") -> dict:
    reminder_id, now = new_id(), now_iso()
    conn.execute(
        "INSERT INTO reminders (id, title, remind_at, repeat_rule, enabled,"
        " created_by, created_at, updated_at, last_fired_at, deleted_at)"
        " VALUES (?, ?, ?, ?, 1, ?, ?, ?, NULL, NULL)",
        (reminder_id, title, to_iso(remind_at), repeat_rule, actor, now, now),
    )
    after = _reminder(conn, reminder_id)
    write_audit(conn, actor, "create", "reminder", reminder_id, after=after)
    write_outbox(conn, "reminder", reminder_id, "upsert", after)
    conn.commit()
    return after


def list_reminders(conn, enabled: bool | None = None, limit: int = 50,
                   offset: int = 0) -> list[dict]:
    where = ["deleted_at IS NULL"]
    params: list = []
    if enabled is not None:
        where.append("enabled = ?")
        params.append(1 if enabled else 0)
    rows = conn.execute(
        "SELECT * FROM reminders WHERE " + " AND ".join(where)
        + " ORDER BY remind_at ASC LIMIT ? OFFSET ?",
        (*params, limit, offset),
    ).fetchall()
    return [dict(row) for row in rows]


def update_reminder(conn, actor: str, reminder_id: str, changes: dict) -> dict:
    before = _reminder(conn, reminder_id)
    if not before:
        raise NotFound("提醒不存在")
    updates: dict = {}
    if "title" in changes and changes["title"] is not None:
        updates["title"] = changes["title"]
    if "remind_at" in changes and changes["remind_at"] is not None:
        updates["remind_at"] = to_iso(changes["remind_at"])
    if "repeat_rule" in changes and changes["repeat_rule"] is not None:
        updates["repeat_rule"] = changes["repeat_rule"]
    if "enabled" in changes and changes["enabled"] is not None:
        updates["enabled"] = 1 if changes["enabled"] else 0
    if not updates:
        raise BadRequest("没有需要修改的字段")
    sets = ", ".join(f"{key} = ?" for key in updates)
    conn.execute(
        f"UPDATE reminders SET {sets}, updated_at = ? WHERE id = ?",
        (*updates.values(), now_iso(), reminder_id),
    )
    after = _reminder(conn, reminder_id)
    write_audit(conn, actor, "update", "reminder", reminder_id, before=before, after=after)
    write_outbox(conn, "reminder", reminder_id, "upsert", after)
    conn.commit()
    return after


def delete_reminder(conn, actor: str, reminder_id: str) -> None:
    before = _reminder(conn, reminder_id)
    if not before:
        raise NotFound("提醒不存在")
    now = now_iso()
    conn.execute(
        "UPDATE reminders SET deleted_at = ?, updated_at = ? WHERE id = ?",
        (now, now, reminder_id),
    )
    write_audit(conn, actor, "delete", "reminder", reminder_id,
                before=before, after={"deleted_at": now})
    write_outbox(conn, "reminder", reminder_id, "delete", {"deleted_at": now})
    conn.commit()


# ---------------------------------------------------------------- 联系人

def _contact(conn, contact_id: str, include_deleted: bool = False) -> dict | None:
    sql = "SELECT * FROM contacts WHERE id = ?"
    if not include_deleted:
        sql += " AND deleted_at IS NULL"
    return _query_one(conn, sql, (contact_id,))


def get_contact(conn, contact_id: str) -> dict:
    contact = _contact(conn, contact_id)
    if not contact:
        raise NotFound("联系人不存在")
    return contact


def create_contact(conn, actor: str, name: str, phone: str, relation: str | None = None,
                   sort_order: int = 0) -> dict:
    contact_id, now = new_id(), now_iso()
    conn.execute(
        "INSERT INTO contacts (id, name, relation, phone, phone_desensitized,"
        " sort_order, created_at, updated_at, deleted_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
        (contact_id, name, relation, phone, desensitize_phone(phone),
         sort_order, now, now),
    )
    after = _contact(conn, contact_id)
    write_audit(conn, actor, "create", "contact", contact_id, after=after)
    write_outbox(conn, "contact", contact_id, "upsert", after)
    conn.commit()
    return after


def list_contacts(conn, limit: int = 50, offset: int = 0) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM contacts WHERE deleted_at IS NULL"
        " ORDER BY sort_order ASC, created_at ASC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    return [dict(row) for row in rows]


def update_contact(conn, actor: str, contact_id: str, changes: dict) -> dict:
    before = _contact(conn, contact_id)
    if not before:
        raise NotFound("联系人不存在")
    updates: dict = {}
    for key in ("name", "relation", "sort_order"):
        if key in changes and (changes[key] is not None or key == "relation"):
            updates[key] = changes[key]
    if "phone" in changes and changes["phone"] is not None:
        updates["phone"] = changes["phone"]
        updates["phone_desensitized"] = desensitize_phone(changes["phone"])
    if not updates:
        raise BadRequest("没有需要修改的字段")
    sets = ", ".join(f"{key} = ?" for key in updates)
    conn.execute(
        f"UPDATE contacts SET {sets}, updated_at = ? WHERE id = ?",
        (*updates.values(), now_iso(), contact_id),
    )
    after = _contact(conn, contact_id)
    write_audit(conn, actor, "update", "contact", contact_id, before=before, after=after)
    write_outbox(conn, "contact", contact_id, "upsert", after)
    conn.commit()
    return after


def delete_contact(conn, actor: str, contact_id: str) -> None:
    before = _contact(conn, contact_id)
    if not before:
        raise NotFound("联系人不存在")
    now = now_iso()
    conn.execute(
        "UPDATE contacts SET deleted_at = ?, updated_at = ? WHERE id = ?",
        (now, now, contact_id),
    )
    write_audit(conn, actor, "delete", "contact", contact_id,
                before=before, after={"deleted_at": now})
    write_outbox(conn, "contact", contact_id, "delete", {"deleted_at": now})
    conn.commit()


# ---------------------------------------------------------------- 通话记录

def create_call_log(conn, actor: str, contact_id: str, status: str,
                    started_at: datetime | None = None, ended_at: datetime | None = None,
                    duration_seconds: int | None = None, note: str | None = None) -> dict:
    contact = _contact(conn, contact_id)
    if not contact:
        raise NotFound("联系人不存在")
    log_id, now = new_id(), now_iso()
    conn.execute(
        "INSERT INTO call_logs (id, contact_id, contact_name, phone_desensitized,"
        " status, started_at, ended_at, duration_seconds, note, created_by, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            log_id,
            contact_id,
            contact["name"],
            desensitize_phone(contact["phone"]),
            status,
            to_iso(started_at) if started_at else None,
            to_iso(ended_at) if ended_at else None,
            duration_seconds,
            note,
            actor,
            now,
        ),
    )
    after = _query_one(conn, "SELECT * FROM call_logs WHERE id = ?", (log_id,))
    write_audit(conn, actor, "create", "call_log", log_id, after=after)
    write_outbox(conn, "call_log", log_id, "upsert", after)
    conn.commit()
    return after


def list_call_logs(conn, contact_id: str | None = None, limit: int = 50,
                   offset: int = 0) -> list[dict]:
    where, params = [], []
    if contact_id:
        where.append("contact_id = ?")
        params.append(contact_id)
    sql = "SELECT * FROM call_logs"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    rows = conn.execute(sql, (*params, limit, offset)).fetchall()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------- 记忆

def _memory(conn, memory_id: str, include_deleted: bool = False) -> dict | None:
    sql = "SELECT * FROM memories WHERE id = ?"
    if not include_deleted:
        sql += " AND deleted_at IS NULL"
    return _query_one(conn, sql, (memory_id,))


def get_memory(conn, memory_id: str) -> dict:
    memory = _memory(conn, memory_id)
    if not memory:
        raise NotFound("记忆不存在")
    return memory


def _insert_confirmation(conn, actor: str, kind: str, entity_type: str, entity_id: str,
                         payload: dict, expires_at: datetime | None = None) -> str:
    cid, now = new_id(), now_iso()
    conn.execute(
        "INSERT INTO pending_confirmations (id, kind, entity_type, entity_id, payload,"
        " requested_by, status, elder_confirmed_by, elder_confirmed_at,"
        " family_confirmed_by, family_confirmed_at, rejected_by, reject_reason,"
        " expires_at, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, 'pending', NULL, NULL, NULL, NULL, NULL, NULL,"
        " ?, ?, ?)",
        (
            cid, kind, entity_type, entity_id,
            json.dumps(payload, ensure_ascii=False),
            actor, to_iso(expires_at) if expires_at else None, now, now,
        ),
    )
    after = _confirmation(conn, cid)
    write_audit(conn, actor, "create", "pending_confirmation", cid, after=after)
    write_outbox(conn, "pending_confirmation", cid, "upsert", after)
    return cid


def create_memory(conn, actor: str, kind: str, subject: str, content: str,
                  source: str = "family", confidence: float = 0.5) -> dict:
    memory_id, now = new_id(), now_iso()
    status = "pending" if kind in REQUIRES_CONFIRMATION else "active"
    confirmation_id = None
    if kind in REQUIRES_CONFIRMATION:
        confirmation_id = _insert_confirmation(
            conn,
            actor,
            f"{kind}_memory",
            "memory",
            memory_id,
            {"proposed": {"kind": kind, "subject": subject, "content": content}},
        )

    conn.execute(
        "INSERT INTO memories (id, kind, subject, content, confidence, source,"
        " status, version, confirmation_id, confirmed_by, confirmed_at,"
        " created_by, created_at, updated_at, deleted_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, NULL, NULL, ?, ?, ?, NULL)",
        (memory_id, kind, subject, content, confidence, source, status,
         confirmation_id, actor, now, now),
    )
    conn.execute(
        "INSERT INTO memory_versions (id, memory_id, version, kind, subject, content,"
        " changed_by, change_reason, created_at) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)",
        (new_id(), memory_id, kind, subject, content, actor, "创建", now),
    )
    after = _memory(conn, memory_id)
    write_audit(conn, actor, "create", "memory", memory_id, after=after)
    write_outbox(conn, "memory", memory_id, "upsert", after)
    conn.commit()
    return after


def list_memories(conn, q: str = "", status: str | None = "active",
                  kind: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
    q = q.strip()
    if q:
        return _search_memories(conn, q, status, kind, limit, offset)

    where = ["deleted_at IS NULL"]
    params: list = []
    if status:
        where.append("status = ?")
        params.append(status)
    if kind:
        where.append("kind = ?")
        params.append(kind)
    rows = conn.execute(
        "SELECT * FROM memories WHERE " + " AND ".join(where)
        + " ORDER BY updated_at DESC LIMIT ? OFFSET ?",
        (*params, limit, offset),
    ).fetchall()
    return [dict(row) for row in rows]


def _search_memories(conn, q: str, status: str | None, kind: str | None,
                     limit: int, offset: int) -> list[dict]:
    if len(q) >= 3:
        sql = (
            "SELECT m.* FROM memories_fts f JOIN memories m ON m.rowid = f.rowid"
            " WHERE f MATCH ? AND m.deleted_at IS NULL"
        )
        params: list = ['"' + q.replace('"', '""') + '"']
        if status:
            sql += " AND m.status = ?"
            params.append(status)
        if kind:
            sql += " AND m.kind = ?"
            params.append(kind)
        sql += " ORDER BY f.rank LIMIT ? OFFSET ?"
        try:
            rows = conn.execute(sql, (*params, limit, offset)).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.OperationalError:
            pass

    where = ["deleted_at IS NULL", "(content LIKE ? OR subject LIKE ?)"]
    params = [f"%{q}%", f"%{q}%"]
    if status:
        where.append("status = ?")
        params.append(status)
    if kind:
        where.append("kind = ?")
        params.append(kind)
    rows = conn.execute(
        "SELECT * FROM memories WHERE " + " AND ".join(where)
        + " ORDER BY updated_at DESC LIMIT ? OFFSET ?",
        (*params, limit, offset),
    ).fetchall()
    return [dict(row) for row in rows]


def update_memory(conn, actor: str, memory_id: str, changes: dict,
                  change_reason: str | None = None) -> dict:
    before = _memory(conn, memory_id)
    if not before:
        raise NotFound("记忆不存在")

    allowed = {"kind", "subject", "content", "confidence", "source"}
    updates = {k: v for k, v in changes.items() if k in allowed and v is not None}
    if not updates:
        raise BadRequest("没有需要修改的字段")

    new_kind = updates.get("kind", before["kind"])
    risky_change = new_kind in REQUIRES_CONFIRMATION and any(
        key in updates for key in ("kind", "subject", "content")
    )
    confirmation_id = before["confirmation_id"]
    new_status = before["status"]
    if risky_change:
        new_status = "pending"
        confirmation_id = _insert_confirmation(
            conn,
            actor,
            f"{new_kind}_memory",
            "memory",
            memory_id,
            {
                "proposed": {
                    "kind": new_kind,
                    "subject": updates.get("subject", before["subject"]),
                    "content": updates.get("content", before["content"]),
                },
                "previous_confirmation_id": before["confirmation_id"],
            },
        )

    version = before["version"] + 1
    now = now_iso()
    sets = ", ".join(f"{key} = ?" for key in updates)
    conn.execute(
        f"UPDATE memories SET {sets}, status = ?, version = ?, confirmation_id = ?,"
        " updated_at = ? WHERE id = ?",
        (*updates.values(), new_status, version, confirmation_id, now, memory_id),
    )
    after = _memory(conn, memory_id)
    conn.execute(
        "INSERT INTO memory_versions (id, memory_id, version, kind, subject, content,"
        " changed_by, change_reason, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            new_id(), memory_id, version, after["kind"], after["subject"],
            after["content"], actor, change_reason, now,
        ),
    )
    write_audit(conn, actor, "update", "memory", memory_id, before=before, after=after)
    write_outbox(conn, "memory", memory_id, "upsert", after)
    conn.commit()
    return after


def delete_memory(conn, actor: str, memory_id: str) -> None:
    before = _memory(conn, memory_id)
    if not before:
        raise NotFound("记忆不存在")
    now = now_iso()
    conn.execute(
        "UPDATE memories SET deleted_at = ?, updated_at = ? WHERE id = ?",
        (now, now, memory_id),
    )
    write_audit(conn, actor, "delete", "memory", memory_id,
                before=before, after={"deleted_at": now})
    write_outbox(conn, "memory", memory_id, "delete", {"deleted_at": now})
    conn.commit()


def list_memory_versions(conn, memory_id: str) -> list[dict]:
    if not _memory(conn, memory_id, include_deleted=True):
        raise NotFound("记忆不存在")
    rows = conn.execute(
        "SELECT * FROM memory_versions WHERE memory_id = ? ORDER BY version ASC",
        (memory_id,),
    ).fetchall()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------- 待确认

def _confirmation(conn, confirmation_id: str) -> dict | None:
    row = _query_one(
        conn, "SELECT * FROM pending_confirmations WHERE id = ?", (confirmation_id,)
    )
    if row:
        row["payload"] = decode_json(row["payload"]) or {}
    return row


def list_confirmations(conn, status: str | None = None, limit: int = 50,
                       offset: int = 0) -> list[dict]:
    _expire_overdue(conn)
    where, params = [], []
    if status:
        where.append("status = ?")
        params.append(status)
    sql = "SELECT * FROM pending_confirmations"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    rows = conn.execute(sql, (*params, limit, offset)).fetchall()
    return [dict(row) | {"payload": decode_json(row["payload"]) or {}} for row in rows]


def get_confirmation(conn, confirmation_id: str) -> dict:
    _expire_overdue(conn)
    row = _confirmation(conn, confirmation_id)
    if not row:
        raise NotFound("待确认记录不存在")
    return row


def create_confirmation(conn, actor: str, kind: str, entity_type: str, entity_id: str,
                        payload: dict, expires_at: datetime | None = None) -> dict:
    cid = _insert_confirmation(conn, actor, kind, entity_type, entity_id, payload, expires_at)
    conn.commit()
    return _confirmation(conn, cid)


def elder_confirm(conn, actor: str, confirmation_id: str) -> dict:
    _expire_overdue(conn)
    current = get_confirmation(conn, confirmation_id)
    if current["status"] != "pending":
        raise Conflict("当前状态不可由老人确认")
    now = now_iso()
    conn.execute(
        "UPDATE pending_confirmations SET status = 'elder_confirmed',"
        " elder_confirmed_by = ?, elder_confirmed_at = ?, updated_at = ? WHERE id = ?",
        (actor, now, now, confirmation_id),
    )
    after = _confirmation(conn, confirmation_id)
    write_audit(conn, actor, "elder_confirm", "pending_confirmation", confirmation_id,
                before=current, after=after)
    notified = notify_family(after)
    write_audit(conn, "system", "family_notify", "pending_confirmation", confirmation_id,
                after=notified)
    write_outbox(conn, "pending_confirmation", confirmation_id, "upsert", after)
    conn.commit()
    return after


def family_confirm(conn, actor: str, confirmation_id: str) -> dict:
    _expire_overdue(conn)
    current = get_confirmation(conn, confirmation_id)
    if current["status"] == "pending":
        raise Conflict("需老人先确认，再由家属确认")
    if current["status"] != "elder_confirmed":
        raise Conflict("当前状态不可由家属确认")
    now = now_iso()
    conn.execute(
        "UPDATE pending_confirmations SET status = 'approved', family_confirmed_by = ?,"
        " family_confirmed_at = ?, updated_at = ? WHERE id = ?",
        (actor, now, now, confirmation_id),
    )
    after = _confirmation(conn, confirmation_id)
    _apply_confirmation_effect(conn, after, "approved", actor)
    write_audit(conn, actor, "approve", "pending_confirmation", confirmation_id,
                before=current, after=after)
    write_outbox(conn, "pending_confirmation", confirmation_id, "upsert", after)
    conn.commit()
    return after


def reject_confirmation(conn, actor: str, confirmation_id: str, reason: str | None = None) -> dict:
    _expire_overdue(conn)
    current = get_confirmation(conn, confirmation_id)
    if current["status"] not in {"pending", "elder_confirmed"}:
        raise Conflict("当前状态不可拒绝")
    now = now_iso()
    conn.execute(
        "UPDATE pending_confirmations SET status = 'rejected', rejected_by = ?,"
        " reject_reason = ?, updated_at = ? WHERE id = ?",
        (actor, reason, now, confirmation_id),
    )
    after = _confirmation(conn, confirmation_id)
    _apply_confirmation_effect(conn, after, "rejected", actor)
    write_audit(conn, actor, "reject", "pending_confirmation", confirmation_id,
                before=current, after=after)
    write_outbox(conn, "pending_confirmation", confirmation_id, "upsert", after)
    conn.commit()
    return after


def _expire_overdue(conn) -> None:
    rows = conn.execute(
        "SELECT * FROM pending_confirmations WHERE status IN ('pending', 'elder_confirmed')"
        " AND expires_at IS NOT NULL AND expires_at < ?",
        (now_iso(),),
    ).fetchall()
    if not rows:
        return
    for row in rows:
        data = dict(row)
        data["payload"] = decode_json(row["payload"]) or {}
        now = now_iso()
        conn.execute(
            "UPDATE pending_confirmations SET status = 'expired', updated_at = ? WHERE id = ?",
            (now, data["id"]),
        )
        write_audit(conn, "system", "expire", "pending_confirmation", data["id"],
                    before=data, after={"status": "expired", "expired_at": now})
        write_outbox(conn, "pending_confirmation", data["id"], "upsert",
                     {"id": data["id"], "status": "expired"})
        _apply_confirmation_effect(conn, data, "expired", "system")
    conn.commit()


def _apply_confirmation_effect(conn, confirmation: dict, outcome: str, actor: str) -> None:
    if confirmation.get("entity_type") != "memory":
        return
    memory_id = confirmation["entity_id"]
    before = _memory(conn, memory_id, include_deleted=True)
    if not before:
        return
    now = now_iso()
    if outcome == "approved":
        status, confirmed_by, confirmed_at = "active", actor, now
    elif outcome == "rejected":
        status, confirmed_by, confirmed_at = "rejected", None, None
    else:
        status, confirmed_by, confirmed_at = "archived", None, None
    conn.execute(
        "UPDATE memories SET status = ?, confirmed_by = ?, confirmed_at = ?,"
        " updated_at = ? WHERE id = ?",
        (status, confirmed_by, confirmed_at, now, memory_id),
    )
    after = _memory(conn, memory_id, include_deleted=True)
    action = {"approved": "approve", "rejected": "reject", "expired": "expire"}.get(
        outcome, outcome
    )
    write_audit(conn, actor, action, "memory", memory_id, before=before, after=after)
    write_outbox(conn, "memory", memory_id, "upsert", after)


# ---------------------------------------------------------------- 审计查询

def list_audit(conn, entity_type: str | None = None, entity_id: str | None = None,
               limit: int = 50, offset: int = 0) -> list[dict]:
    where, params = [], []
    if entity_type:
        where.append("entity_type = ?")
        params.append(entity_type)
    if entity_id:
        where.append("entity_id = ?")
        params.append(entity_id)
    sql = "SELECT * FROM audit_log"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    rows = conn.execute(sql, (*params, limit, offset)).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["before"] = decode_json(item["before"])
        item["after"] = decode_json(item["after"])
        items.append(item)
    return items
