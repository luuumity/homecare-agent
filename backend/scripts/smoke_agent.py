"""阶段 2 冒烟测试：脱敏、记忆检索、工具、工具循环、压缩，可选真实模型联调。

用法（backend/ 下）：
    .venv/bin/python scripts/smoke_agent.py          # 离线（模拟模型）
    .venv/bin/python scripts/smoke_agent.py --live   # 额外跑真实 DeepSeek 联调
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

TMP_ROOT = Path(tempfile.mkdtemp(prefix="eldercare_agent_"))
os.environ["DB_PATH"] = str(TMP_ROOT / "unit.db")

from app import repository as repo  # noqa: E402
from app.agent import compression, conversation_repo as conv, service, tools  # noqa: E402
from app.agent.llm import chat_completion as real_chat_completion  # noqa: E402
from app.agent.privacy import Desensitizer  # noqa: E402
from app.agent.retrieval import search_memories  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import connect, init_db  # noqa: E402

get_settings.cache_clear()
failures: list[str] = []


def check(name: str, fn) -> None:
    try:
        fn()
        print(f"PASS  {name}")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"{name}: {exc}")
        print(f"FAIL  {name}: {exc}")


def main() -> int:
    base = TMP_ROOT / "unit.db"
    init_db(base)
    conn = connect(base)

    def privacy() -> None:
        des = Desensitizer()
        text = "手机13800138000，身份证110101199001011234，座机010-12345678，卡号6222020000000000000"
        masked = des.mask(text)
        for raw in ("13800138000", "110101199001011234", "010-12345678", "6222020000000000000"):
            assert raw not in masked, f"未脱敏：{raw}"
        assert "[PHONE_" in masked and "[ID_" in masked and "[BANK_" in masked
        assert des.unmask(masked) == text, "还原结果不一致"

    def retrieval() -> None:
        memory = repo.create_memory(conn, "family", "fact", "爷爷", "老花镜放在床头柜第二层")
        assert memory["status"] == "active"
        hits = search_memories(conn, "老花镜在哪里")
        assert any(item["id"] == memory["id"] for item in hits), "未召回已确认记忆"

        pending = repo.create_memory(conn, "family", "medical", "爷爷", "爷爷对青霉素过敏")
        assert pending["status"] == "pending"
        hits = search_memories(conn, "青霉素")
        assert all(item["id"] != pending["id"] for item in hits), "未确认记忆被注入上下文"

    def tool_layer() -> None:
        repo.create_item(conn, "family", "老花镜", "床头柜第二层")
        found = tools.execute_tool(conn, "find_items", {"query": "老花镜"})
        assert found["ok"] and found["items"], found

        saved = tools.execute_tool(conn, "save_item", {"name": "体温计", "location": "电视柜右边"})
        assert saved["ok"] and saved["item"]["name"] == "体温计"

        created = tools.execute_tool(
            conn,
            "create_reminder",
            {"title": "吃降压药", "remind_at": "2026-11-02T08:00:00+08:00", "repeat_rule": "daily"},
        )
        assert created["ok"] and created["reminder"]["repeat_rule"] == "daily"

        contact = repo.create_contact(conn, "family", "儿子", "13800138000", "儿子")
        listed = tools.execute_tool(conn, "list_contacts", {})
        assert listed["ok"] and listed["contacts"][0]["phone_masked"] == "138****8000"
        assert "13800138000" not in json.dumps(listed)

        called = tools.execute_tool(conn, "request_call", {"contact_id": contact["id"], "note": "测试"})
        assert called["ok"] and called["call"]["status"] == "initiated"

        pending = tools.execute_tool(
            conn,
            "save_memory",
            {"kind": "identity", "subject": "爷爷", "content": "爷爷的身份证号是110101199001011234"},
        )
        assert pending["ok"] and pending["memory"]["status"] == "pending"
        assert pending["memory"]["confirmation_id"], "医疗/身份记忆未进入确认流程"

        listed = tools.execute_tool(conn, "find_items", {})
        names = {item["name"] for item in listed["items"]}
        assert listed["ok"] and {"老花镜", "体温计"} <= names, listed

    def tool_loop() -> None:
        responses = [
            {
                "content": "",
                "tool_calls": [
                    {
                        "id": "tc1",
                        "name": "save_item",
                        "arguments": {"name": "血压计", "location": "客厅抽屉"},
                        "raw_arguments": json.dumps({"name": "血压计", "location": "客厅抽屉"}, ensure_ascii=False),
                    }
                ],
            },
            {"content": "已经记下了，血压计放在客厅抽屉。", "tool_calls": []},
        ]

        def fake(messages, tools=None, **kwargs):  # noqa: A002
            return responses.pop(0)

        service.llm.chat_completion = fake
        try:
            result = service.chat(conn, "帮我记一下，血压计放在客厅抽屉")
        finally:
            service.llm.chat_completion = real_chat_completion
        assert result["reply"] == "已经记下了，血压计放在客厅抽屉。"
        assert result["tool_calls"][0]["name"] == "save_item" and result["tool_calls"][0]["ok"]
        items = repo.list_items(conn, q="血压计")
        assert len(items) == 1 and items[0]["location"] == "客厅抽屉"
        history = conv.list_history(conn, 10, include_tool=True)
        assert any(row["role"] == "assistant" for row in history)
        assert any(row["role"] == "tool" and row["tool_name"] == "save_item" for row in history)

    def pending_flow() -> None:
        responses = [
            {
                "content": "",
                "tool_calls": [
                    {
                        "id": "tc2",
                        "name": "save_memory",
                        "arguments": {"kind": "medical", "subject": "爷爷", "content": "每天早饭后吃降压药"},
                        "raw_arguments": json.dumps(
                            {"kind": "medical", "subject": "爷爷", "content": "每天早饭后吃降压药"},
                            ensure_ascii=False,
                        ),
                    }
                ],
            },
            {"content": "这个重要，需要您和家人确认一下才生效。", "tool_calls": []},
        ]

        def fake(messages, tools=None, **kwargs):  # noqa: A002
            return responses.pop(0)

        service.llm.chat_completion = fake
        try:
            result = service.chat(conn, "记住我每天早饭后吃降压药")
        finally:
            service.llm.chat_completion = real_chat_completion
        assert result["pending_confirmation_ids"], result
        assert len(result["pending_confirmation_ids"]) == 1

    def compression_flow() -> None:
        for index in range(16):
            conv.add_message(conn, "user", f"测试消息 {index}")
            conv.add_message(conn, "assistant", f"测试回复 {index}")

        def fake(messages, tools=None, **kwargs):  # noqa: A002
            return {"content": "老人与助手聊了日常和用药安排。", "tool_calls": []}

        compression.llm.chat_completion = fake
        try:
            assert compression.maybe_compress(conn, force=True) is True
        finally:
            compression.llm.chat_completion = real_chat_completion
        summary = conv.latest_summary(conn)
        assert summary and "日常" in summary["content"]
        state = conv.status(conn)
        assert state["has_summary"] and state["last_summarized_message_id"]

    check("隐私脱敏与本地还原", privacy)
    check("记忆检索只召回已确认项", retrieval)
    check("工具层读写与确认流程", tool_layer)
    check("模拟模型工具循环", tool_loop)
    check("医疗记忆双确认提示", pending_flow)
    check("上下文压缩", compression_flow)
    conn.close()

    if "--live" in sys.argv:
        live = TMP_ROOT / "live.db"
        init_db(live)
        live_conn = connect(live)
        settings = get_settings()
        if not settings.llm_configured:
            failures.append("真实联调：未配置 LLM_API_KEY")
            print("FAIL  真实联调：未配置 LLM_API_KEY")
        else:
            repo.create_item(live_conn, "family", "老花镜", "床头柜第二层")
            repo.create_contact(live_conn, "family", "儿子", "13800138000", "儿子")
            repo.create_memory(live_conn, "family", "fact", "爷爷", "爷爷每天早饭后吃降压药")

            def live_case(name: str, text: str, expect_tool: str | None, expect_text: str | None) -> None:
                try:
                    result = service.chat(live_conn, text)
                    names = [event["name"] for event in result["tool_calls"]]
                    print(f"  [{name}] 回复：{result['reply']}")
                    print(f"  [{name}] 工具：{names or '无'}")
                    if expect_tool:
                        assert expect_tool in names, f"未调用 {expect_tool}"
                    if expect_text:
                        assert expect_text in result["reply"], f"回复未包含 {expect_text}"
                    print(f"PASS  {name}")
                except Exception as exc:  # noqa: BLE001
                    failures.append(f"{name}: {exc}")
                    print(f"FAIL  {name}: {exc}")

            print("开始真实模型联调（3 轮，使用临时库）")
            live_case("真实模型·查物品", "帮我查一下物品记录，我的老花镜放在哪里？", "find_items", "床头柜")
            live_case("真实模型·记忆问答", "我每天什么时候吃降压药？", None, None)
            live_case("真实模型·记物品", "记一下，奶奶的助听器放在电视柜左边。", "save_item", None)
            items = repo.list_items(live_conn, q="助听器")
            if not items:
                failures.append("真实模型·记物品：数据库没有助听器记录")
                print("FAIL  真实模型·记物品落库校验")
            else:
                print("PASS  真实模型·记物品落库校验")
        live_conn.close()

    shutil.rmtree(TMP_ROOT, ignore_errors=True)

    if failures:
        print(f"\n{len(failures)} 项失败：")
        for item in failures:
            print(f"- {item}")
        return 1
    print("\n全部通过；临时测试库已删除。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
