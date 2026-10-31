"""SQLite 结构迁移：按版本递增，全部在同一事务内执行。

阶段 1 建立全部业务表；Agent 只在阶段 2 使用其中的 messages/memories 等。
"""

from __future__ import annotations

import sqlite3

MIGRATION_001 = """
CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    relation TEXT,
    phone TEXT NOT NULL,
    phone_desensitized TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    note TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS reminders (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    remind_at TEXT NOT NULL,
    repeat_rule TEXT NOT NULL DEFAULT 'none',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_fired_at TEXT,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS call_logs (
    id TEXT PRIMARY KEY,
    contact_id TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    phone_desensitized TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    duration_seconds INTEGER,
    note TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'note',
    file_path TEXT,
    mime_type TEXT,
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tool_name TEXT,
    tool_payload TEXT,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS summaries (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    covers_from_message_id TEXT,
    covers_to_message_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversation_state (
    id TEXT PRIMARY KEY,
    last_message_id TEXT,
    last_summarized_message_id TEXT,
    state TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    subject TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.5,
    source TEXT NOT NULL DEFAULT 'family',
    status TEXT NOT NULL DEFAULT 'pending',
    version INTEGER NOT NULL DEFAULT 1,
    confirmation_id TEXT,
    confirmed_by TEXT,
    confirmed_at TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS memory_versions (
    id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    kind TEXT NOT NULL,
    subject TEXT NOT NULL,
    content TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    change_reason TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (memory_id) REFERENCES memories(id),
    UNIQUE (memory_id, version)
);

CREATE TABLE IF NOT EXISTS pending_confirmations (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    elder_confirmed_by TEXT,
    elder_confirmed_at TEXT,
    family_confirmed_by TEXT,
    family_confirmed_at TEXT,
    rejected_by TEXT,
    reject_reason TEXT,
    expires_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    before TEXT,
    after TEXT,
    ip TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_outbox (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    op TEXT NOT NULL,
    payload TEXT,
    created_at TEXT NOT NULL,
    processed_at TEXT
);

CREATE TABLE IF NOT EXISTS sync_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_items_updated ON items(updated_at);
CREATE INDEX IF NOT EXISTS idx_reminders_at ON reminders(remind_at);
CREATE INDEX IF NOT EXISTS idx_contacts_sort ON contacts(sort_order);
CREATE INDEX IF NOT EXISTS idx_call_logs_contact ON call_logs(contact_id, created_at);
CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status, kind);
CREATE INDEX IF NOT EXISTS idx_memory_versions ON memory_versions(memory_id, version);
CREATE INDEX IF NOT EXISTS idx_confirmations_status ON pending_confirmations(status, expires_at);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_outbox_pending ON sync_outbox(processed_at, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content,
    subject,
    content='memories',
    content_rowid='rowid',
    tokenize='trigram'
);

CREATE TRIGGER IF NOT EXISTS memories_fts_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content, subject)
    VALUES (new.rowid, new.content, new.subject);
END;

CREATE TRIGGER IF NOT EXISTS memories_fts_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, subject)
    VALUES ('delete', old.rowid, old.content, old.subject);
END;

CREATE TRIGGER IF NOT EXISTS memories_fts_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, subject)
    VALUES ('delete', old.rowid, old.content, old.subject);
    INSERT INTO memories_fts(rowid, content, subject)
    VALUES (new.rowid, new.content, new.subject);
END;
"""

MIGRATIONS: tuple[tuple[int, str], ...] = ((1, MIGRATION_001),)


def schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT value FROM app_meta WHERE key = 'schema_version'"
    ).fetchone()
    return int(row["value"]) if row else 0


def migrate(conn: sqlite3.Connection) -> int:
    version = schema_version(conn)
    for target, sql in MIGRATIONS:
        if target <= version:
            continue
        try:
            conn.executescript(
                "BEGIN;\n"
                + sql
                + f"\nUPDATE app_meta SET value = '{target}' WHERE key = 'schema_version';"
                + "\nCOMMIT;"
            )
        except sqlite3.Error:
            conn.rollback()
            raise
        version = target
    return version
