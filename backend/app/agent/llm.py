"""OpenAI 兼容的对话补全客户端（DeepSeek），仅使用标准库。"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from ..config import get_settings

logger = logging.getLogger("eldercare.llm")


class LlmError(Exception):
    """模型不可用、超时或返回格式异常。"""


def _endpoint() -> str:
    base = get_settings().llm_base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"


def chat_completion(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    *,
    temperature: float = 0.3,
    max_tokens: int = 800,
    timeout: int = 60,
) -> dict[str, Any]:
    """返回 {content, tool_calls: [{id, name, arguments, raw_arguments}]}。"""
    settings = get_settings()
    if not settings.llm_configured:
        raise LlmError("未配置 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL")

    body: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    request = urllib.request.Request(
        _endpoint(),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
    )
    request.add_header("Content-Type", "application/json")
    request.add_header("Authorization", f"Bearer {settings.llm_api_key}")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise LlmError(f"模型接口返回 {exc.code}：{detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise LlmError(f"模型接口连接失败：{exc}") from exc
    except json.JSONDecodeError as exc:
        raise LlmError("模型接口返回的不是合法 JSON") from exc

    try:
        message = payload["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LlmError("模型接口返回结构异常") from exc

    tool_calls = []
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        raw_arguments = function.get("arguments") or "{}"
        try:
            arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
        except json.JSONDecodeError:
            arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        tool_calls.append(
            {
                "id": call.get("id") or "",
                "name": function.get("name") or "",
                "arguments": arguments,
                "raw_arguments": raw_arguments if isinstance(raw_arguments, str) else json.dumps(raw_arguments, ensure_ascii=False),
            }
        )

    return {
        "content": message.get("content") or "",
        "tool_calls": tool_calls,
        "usage": payload.get("usage") or {},
    }
