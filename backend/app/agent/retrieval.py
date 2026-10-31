"""中文口语的轻量记忆检索：按 2–3 字片段召回已确认记忆。

没有分词库，采用停用字过滤 + 三字滑窗，够用且可解释；只检索 active 记忆，
避免未确认的医疗/身份信息进入模型上下文。
"""

from __future__ import annotations

import re
import sqlite3

from .. import repository as repo

_SPLIT_RE = re.compile(r"[^\u4e00-\u9fffA-Za-z0-9]+")
_STOP_CHARS = set("的了吗呢吧啊呀是在有我你他她它这那哪么怎请帮告诉记得还要想能可以一下")
_STOP_TERMS = {"我的", "你的", "什么", "怎么", "哪里", "哪儿", "请问", "告诉", "记得", "可以", "这个", "那个"}
_MAX_TERMS = 24


def _terms(text: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()

    def add(term: str) -> None:
        if term and term not in seen:
            seen.add(term)
            terms.append(term)

    for chunk in _SPLIT_RE.split(text):
        if not chunk:
            continue
        if 2 <= len(chunk) <= 8:
            add(chunk)
        if len(chunk) >= 3:
            for index in range(len(chunk) - 2):
                gram = chunk[index:index + 3]
                if gram in _STOP_TERMS or any(char in _STOP_CHARS for char in gram):
                    continue
                add(gram)
        if len(terms) >= _MAX_TERMS:
            break
    return terms[:_MAX_TERMS]


def search_memories(conn: sqlite3.Connection, text: str, limit: int = 8) -> list[dict]:
    terms = _terms(text)
    if not terms:
        return []

    scored: dict[str, dict] = {}
    for term in terms:
        try:
            rows = repo.list_memories(conn, q=term, status="active", limit=5)
        except Exception:  # 检索失败不应阻断对话
            continue
        for row in rows:
            if row["id"] not in scored:
                scored[row["id"]] = {"memory": row, "score": 0}
            scored[row["id"]]["score"] += 1

    ranked = sorted(
        scored.values(),
        key=lambda item: (item["score"], item["memory"]["updated_at"]),
        reverse=True,
    )
    return [item["memory"] for item in ranked[:limit]]
