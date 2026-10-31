"""Agent 工具：模型只能通过这里读写业务数据，所有调用复用阶段 1 的校验与审计层。"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from .. import repository as repo
from ..errors import BadRequest, Conflict, NotFound
from ..utils import tz
from .retrieval import search_memories as retrieve_memories

MEMORY_KINDS = {"fact", "preference", "medical", "identity", "event"}
REPEAT_RULES = {"none", "daily", "weekly", "weekdays"}


class ToolError(ValueError):
    """工具参数不合法，返回给模型让其重试或追问。"""


def _text(args: dict, key: str, *, required: bool = True, max_length: int = 500) -> str | None:
    value = args.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ToolError(f"缺少参数 {key}")
        return None
    if not isinstance(value, str):
        raise ToolError(f"参数 {key} 必须是文本")
    value = value.strip()
    if len(value) > max_length:
        raise ToolError(f"参数 {key} 过长")
    return value


def _dt(args: dict, key: str) -> datetime:
    raw = _text(args, key, max_length=40)
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ToolError(f"参数 {key} 不是合法时间，请用 ISO 8601") from exc
    return value if value.tzinfo else value.replace(tzinfo=tz())


def _item_out(row: dict) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "location": row["location"],
        "note": row.get("note"),
        "updated_at": row["updated_at"],
    }


def _reminder_out(row: dict) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "remind_at": row["remind_at"],
        "repeat_rule": row["repeat_rule"],
        "enabled": bool(row["enabled"]),
    }


def _memory_out(row: dict) -> dict:
    return {
        "id": row["id"],
        "kind": row["kind"],
        "subject": row["subject"],
        "content": row["content"],
        "confidence": row["confidence"],
        "updated_at": row["updated_at"],
    }


# ---------------------------------------------------------------- 工具定义

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "find_items",
            "description": "按名称、位置或备注查找物品记录。用户问东西放在哪时先用它。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "关键词，如老花镜、降压药"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_item",
            "description": "新增一条物品位置记录。用户明确告知东西放在哪时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "物品名称"},
                    "location": {"type": "string", "description": "存放位置"},
                    "note": {"type": "string", "description": "可选备注"},
                },
                "required": ["name", "location"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_item",
            "description": "修改已有物品记录。需要先找到 item_id；不确定时先问用户。",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"},
                    "name": {"type": "string"},
                    "location": {"type": "string"},
                    "note": {"type": "string"},
                },
                "required": ["item_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_item",
            "description": "删除物品记录（软删除）。必须在用户明确确认删除后调用。",
            "parameters": {
                "type": "object",
                "properties": {"item_id": {"type": "string"}},
                "required": ["item_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_reminders",
            "description": "列出提醒，默认只列启用的。",
            "parameters": {
                "type": "object",
                "properties": {
                    "enabled_only": {"type": "boolean", "description": "默认 true"},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": "新建提醒。remind_at 用 ISO 8601 带时区；相对时间先按当前时间换算。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "remind_at": {"type": "string", "description": "例如 2026-11-01T08:00:00+08:00"},
                    "repeat_rule": {
                        "type": "string",
                        "enum": ["none", "daily", "weekly", "weekdays"],
                    },
                },
                "required": ["title", "remind_at"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_reminder",
            "description": "修改提醒的时间、内容、重复规则或启停。",
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder_id": {"type": "string"},
                    "title": {"type": "string"},
                    "remind_at": {"type": "string"},
                    "repeat_rule": {"type": "string"},
                    "enabled": {"type": "boolean"},
                },
                "required": ["reminder_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_reminder",
            "description": "删除提醒。必须在用户明确确认后调用。",
            "parameters": {
                "type": "object",
                "properties": {"reminder_id": {"type": "string"}},
                "required": ["reminder_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_contacts",
            "description": "列出可拨打的家属联系人，只返回脱敏号码。",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_call",
            "description": "请求给白名单家属拨打语音通话。只记录请求，不能声称已接通。",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {"type": "string"},
                    "note": {"type": "string", "description": "可选说明"},
                },
                "required": ["contact_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_memories",
            "description": "检索已确认的长期记忆（健康、偏好、事实等）。",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "记录新的事实/偏好/健康/身份信息。医疗与身份类会自动进入双确认流程。",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": ["fact", "preference", "medical", "identity", "event"],
                    },
                    "subject": {"type": "string", "description": "记忆主体，如爷爷、奶奶"},
                    "content": {"type": "string", "description": "要记住的内容"},
                },
                "required": ["kind", "subject", "content"],
                "additionalProperties": False,
            },
        },
    },
]


# ---------------------------------------------------------------- 工具执行

def _find_items(conn: sqlite3.Connection, args: dict) -> dict:
    query = _text(args, "query", max_length=100)
    rows = repo.list_items(conn, q=query, limit=10)
    return {"ok": True, "count": len(rows), "items": [_item_out(row) for row in rows]}


def _save_item(conn: sqlite3.Connection, args: dict) -> dict:
    name = _text(args, "name", max_length=100)
    location = _text(args, "location", max_length=200)
    note = _text(args, "note", required=False, max_length=500)
    row = repo.create_item(conn, "agent", name, location, note)
    return {"ok": True, "item": _item_out(row), "message": "物品记录已保存"}


def _update_item(conn: sqlite3.Connection, args: dict) -> dict:
    item_id = _text(args, "item_id", max_length=64)
    changes: dict = {}
    for key, limit in (("name", 100), ("location", 200), ("note", 500)):
        value = _text(args, key, required=False, max_length=limit)
        if value is not None:
            changes[key] = value
    if not changes:
        raise ToolError("没有提供要修改的字段")
    row = repo.update_item(conn, "agent", item_id, changes)
    return {"ok": True, "item": _item_out(row), "message": "物品记录已更新"}


def _delete_item(conn: sqlite3.Connection, args: dict) -> dict:
    item_id = _text(args, "item_id", max_length=64)
    repo.delete_item(conn, "agent", item_id)
    return {"ok": True, "deleted_id": item_id, "message": "物品记录已删除"}


def _list_reminders(conn: sqlite3.Connection, args: dict) -> dict:
    enabled_only = args.get("enabled_only", True)
    rows = repo.list_reminders(conn, enabled=True if enabled_only else None, limit=20)
    return {"ok": True, "count": len(rows), "reminders": [_reminder_out(row) for row in rows]}


def _create_reminder(conn: sqlite3.Connection, args: dict) -> dict:
    title = _text(args, "title", max_length=100)
    remind_at = _dt(args, "remind_at")
    repeat_rule = _text(args, "repeat_rule", required=False, max_length=20) or "none"
    if repeat_rule not in REPEAT_RULES:
        raise ToolError("repeat_rule 不合法")
    row = repo.create_reminder(conn, "agent", title, remind_at, repeat_rule)
    return {"ok": True, "reminder": _reminder_out(row), "message": "提醒已创建"}


def _update_reminder(conn: sqlite3.Connection, args: dict) -> dict:
    reminder_id = _text(args, "reminder_id", max_length=64)
    changes: dict = {}
    title = _text(args, "title", required=False, max_length=100)
    if title is not None:
        changes["title"] = title
    if args.get("remind_at") is not None:
        changes["remind_at"] = _dt(args, "remind_at")
    repeat_rule = _text(args, "repeat_rule", required=False, max_length=20)
    if repeat_rule is not None:
        if repeat_rule not in REPEAT_RULES:
            raise ToolError("repeat_rule 不合法")
        changes["repeat_rule"] = repeat_rule
    if args.get("enabled") is not None:
        changes["enabled"] = bool(args["enabled"])
    if not changes:
        raise ToolError("没有提供要修改的字段")
    row = repo.update_reminder(conn, "agent", reminder_id, changes)
    return {"ok": True, "reminder": _reminder_out(row), "message": "提醒已更新"}


def _delete_reminder(conn: sqlite3.Connection, args: dict) -> dict:
    reminder_id = _text(args, "reminder_id", max_length=64)
    repo.delete_reminder(conn, "agent", reminder_id)
    return {"ok": True, "deleted_id": reminder_id, "message": "提醒已删除"}


def _list_contacts(conn: sqlite3.Connection, _args: dict) -> dict:
    rows = repo.list_contacts(conn, limit=20)
    contacts = [
        {
            "id": row["id"],
            "name": row["name"],
            "relation": row["relation"],
            "phone_masked": row["phone_desensitized"],
        }
        for row in rows
    ]
    return {"ok": True, "count": len(contacts), "contacts": contacts}


def _request_call(conn: sqlite3.Connection, args: dict) -> dict:
    contact_id = _text(args, "contact_id", max_length=64)
    note = _text(args, "note", required=False, max_length=200)
    row = repo.create_call_log(conn, "agent", contact_id, "initiated", note=note)
    return {
        "ok": True,
        "call": {
            "id": row["id"],
            "contact_name": row["contact_name"],
            "status": row["status"],
            "phone_masked": row["phone_desensitized"],
        },
        "message": "通话请求已记录，等待大屏执行；不能据此认为已经接通",
    }


def _search_memories(conn: sqlite3.Connection, args: dict) -> dict:
    query = _text(args, "query", max_length=200)
    rows = retrieve_memories(conn, query, limit=8)
    return {"ok": True, "count": len(rows), "memories": [_memory_out(row) for row in rows]}


def _save_memory(conn: sqlite3.Connection, args: dict) -> dict:
    kind = _text(args, "kind", max_length=20)
    if kind not in MEMORY_KINDS:
        raise ToolError("kind 不合法")
    subject = _text(args, "subject", max_length=100)
    content = _text(args, "content", max_length=500)
    row = repo.create_memory(conn, "agent", kind, subject, content, source="agent")
    pending = row["status"] == "pending"
    return {
        "ok": True,
        "memory": {
            "id": row["id"],
            "kind": row["kind"],
            "status": row["status"],
            "confirmation_id": row["confirmation_id"],
        },
        "message": (
            "已记录，但医疗/身份信息需要老人和家属确认后才生效"
            if pending else "记忆已保存并生效"
        ),
    }


_EXECUTORS = {
    "find_items": _find_items,
    "save_item": _save_item,
    "update_item": _update_item,
    "delete_item": _delete_item,
    "list_reminders": _list_reminders,
    "create_reminder": _create_reminder,
    "update_reminder": _update_reminder,
    "delete_reminder": _delete_reminder,
    "list_contacts": _list_contacts,
    "request_call": _request_call,
    "search_memories": _search_memories,
    "save_memory": _save_memory,
}


def execute_tool(conn: sqlite3.Connection, name: str, args: dict) -> dict:
    executor = _EXECUTORS.get(name)
    if executor is None:
        return {"ok": False, "error": f"未知工具 {name}"}
    try:
        return executor(conn, args)
    except (ToolError, BadRequest, NotFound, Conflict) as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # 工具内部错误不中断整轮对话
        return {"ok": False, "error": f"工具执行失败：{exc}"}
