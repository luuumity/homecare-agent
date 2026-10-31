"""主对话编排：脱敏 -> 检索记忆 -> 组装上下文 -> 工具循环 -> 落库 -> 压缩。"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from typing import Any

from ..errors import BadRequest
from ..utils import tz
from . import compression, conversation_repo as conv, llm, tools
from .privacy import Desensitizer
from .prompts import build_system_prompt
from .retrieval import search_memories

logger = logging.getLogger("eldercare.agent")

MAX_TOOL_ROUNDS = 4
MAX_INPUT_CHARS = 2000
RECENT_CONTEXT = 12
_WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


def _now_text() -> str:
    now = datetime.now(tz())
    return f"{now.year}年{now.month}月{now.day}日 {now:%H:%M}，{_WEEKDAYS[now.weekday()]}"


def _unmask_obj(value: Any, desensitizer: Desensitizer) -> Any:
    if isinstance(value, str):
        return desensitizer.unmask(value)
    if isinstance(value, list):
        return [_unmask_obj(item, desensitizer) for item in value]
    if isinstance(value, dict):
        return {key: _unmask_obj(item, desensitizer) for key, item in value.items()}
    return value


def _memory_line(memory: dict, desensitizer: Desensitizer) -> str:
    subject = desensitizer.mask(memory["subject"])
    content = desensitizer.mask(memory["content"])
    return f"- [{memory['kind']}] {subject}：{content}"


def chat(conn: sqlite3.Connection, text: str) -> dict:
    text = (text or "").strip()
    if not text:
        raise BadRequest("说的话不能为空")
    if len(text) > MAX_INPUT_CHARS:
        raise BadRequest("单次输入过长")

    desensitizer = Desensitizer()
    conv.add_message(conn, "user", text)

    memories = search_memories(conn, text)
    summary = conv.latest_summary(conn)
    system_prompt = build_system_prompt(
        _now_text(),
        desensitizer.mask(summary["content"]) if summary else None,
        [_memory_line(memory, desensitizer) for memory in memories],
    )

    history = conv.recent_messages(conn, RECENT_CONTEXT)
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    for message in history:
        messages.append({"role": message["role"], "content": desensitizer.mask(message["content"])})

    tool_events: list[dict] = []
    pending_ids: list[str] = []
    final = ""

    for round_index in range(MAX_TOOL_ROUNDS):
        result = llm.chat_completion(messages, tools=tools.TOOL_SPECS)
        calls = result.get("tool_calls") or []
        content = (result.get("content") or "").strip()

        if not calls:
            final = content
            break

        assistant_entry: dict[str, Any] = {
            "role": "assistant",
            "content": content,
            "tool_calls": [],
        }
        prepared_calls = []
        for call_index, call in enumerate(calls):
            call_id = call.get("id") or f"call_{round_index}_{call_index}"
            raw_arguments = call.get("raw_arguments") or json.dumps(
                call.get("arguments") or {}, ensure_ascii=False
            )
            assistant_entry["tool_calls"].append(
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": call["name"], "arguments": raw_arguments},
                }
            )
            prepared_calls.append((call_id, call["name"], call.get("arguments") or {}))
        messages.append(assistant_entry)

        for call_id, name, arguments in prepared_calls:
            args = _unmask_obj(arguments, desensitizer)
            tool_result = tools.execute_tool(conn, name, args)
            conv.add_message(
                conn,
                "tool",
                json.dumps(tool_result, ensure_ascii=False, default=str),
                tool_name=name,
                tool_payload={"arguments": args, "result": tool_result},
            )
            event: dict[str, Any] = {"name": name, "ok": bool(tool_result.get("ok"))}
            if not tool_result.get("ok"):
                event["error"] = tool_result.get("error")
            tool_events.append(event)
            memory = tool_result.get("memory") or {}
            if memory.get("status") == "pending" and memory.get("confirmation_id"):
                pending_ids.append(memory["confirmation_id"])
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": desensitizer.mask(
                        json.dumps(tool_result, ensure_ascii=False, default=str)
                    ),
                }
            )

    if not final:
        final = "我这边刚才没处理完，您再说一遍好吗？"

    reply = desensitizer.unmask(final)
    assistant_message = conv.add_message(conn, "assistant", reply)
    compressed = compression.maybe_compress(conn)

    return {
        "reply": reply,
        "message_id": assistant_message["id"],
        "created_at": assistant_message["created_at"],
        "tool_calls": tool_events,
        "pending_confirmation_ids": pending_ids,
        "compressed": compressed,
    }
