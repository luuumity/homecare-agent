"""上下文压缩：把较早的对话滚动摘要，保留最近消息原文。"""

from __future__ import annotations

import logging
import sqlite3

from . import conversation_repo as conv
from . import llm
from .privacy import Desensitizer

logger = logging.getLogger("eldercare.agent")

KEEP_RECENT = 12
TRIGGER_UNSUMMARIZED = 30
MAX_TRANSCRIPT_CHARS = 6000


def maybe_compress(conn: sqlite3.Connection, force: bool = False) -> bool:
    messages = conv.unsummarized_messages(conn)
    threshold = KEEP_RECENT + 1 if force else TRIGGER_UNSUMMARIZED
    if len(messages) <= threshold:
        return False

    older = messages[:-KEEP_RECENT]
    if not older:
        return False

    desensitizer = Desensitizer()
    lines = []
    for message in older:
        speaker = "老人" if message["role"] == "user" else "助手"
        lines.append(f"{speaker}：{desensitizer.mask(message['content'])}")
    transcript = "\n".join(lines)
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        transcript = "……（前略）\n" + transcript[-MAX_TRANSCRIPT_CHARS:]

    prompt = [
        {
            "role": "system",
            "content": (
                "你是对话摘要器。把下面的照护对话压缩成不超过 300 字的中文摘要，"
                "保留人物、健康情况、偏好、约定和待办；不要编造；"
                "电话号码、身份证等用 [PHONE_1]、[ID_1] 之类占位符保留。"
                "只输出摘要正文，不要加标题。"
            ),
        },
        {"role": "user", "content": transcript},
    ]
    try:
        result = llm.chat_completion(prompt, temperature=0.2, max_tokens=400)
    except llm.LlmError as exc:
        logger.warning("上下文压缩跳过：%s", exc)
        return False

    content = (result.get("content") or "").strip()
    if not content:
        logger.warning("上下文压缩跳过：摘要为空")
        return False

    conv.save_summary(conn, content, older[0]["id"], older[-1]["id"])
    logger.info("上下文压缩完成：%s 条消息 -> 摘要", len(older))
    return True
