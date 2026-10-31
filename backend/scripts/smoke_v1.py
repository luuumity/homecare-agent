"""阶段 1 接口冒烟测试：需先启动后端。

用法（backend/ 下）：.venv/bin/python scripts/smoke_v1.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"
failures: list[str] = []


def req(method: str, path: str, body=None, actor: str | None = None, expect: int = 200):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if actor:
        request.add_header("X-Actor", actor)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            code, text = response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        code, text = exc.code, exc.read().decode("utf-8")
    if code != expect:
        raise AssertionError(f"{method} {path} -> {code}（期望 {expect}）：{text}")
    return json.loads(text) if text else None


def check(name: str, fn) -> None:
    try:
        fn()
        print(f"PASS  {name}")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"{name}: {exc}")
        print(f"FAIL  {name}: {exc}")


def main() -> int:
    def items() -> None:
        created = req("POST", "/api/v1/items",
                      {"name": "老花镜", "location": "床头柜第二层", "note": "黑色镜框"},
                      actor="family", expect=201)
        q = urllib.parse.quote("花镜")
        found = req("GET", f"/api/v1/items?q={q}")
        assert any(item["id"] == created["id"] for item in found), "搜索未命中"
        updated = req("PATCH", f"/api/v1/items/{created['id']}", {"location": "床头柜第一层"})
        assert updated["location"] == "床头柜第一层"
        req("DELETE", f"/api/v1/items/{created['id']}")
        after = req("GET", f"/api/v1/items?q={q}")
        assert all(item["id"] != created["id"] for item in after), "软删除后仍能搜到"
        req("GET", f"/api/v1/items/{created['id']}", expect=404)

    def contacts_calls() -> None:
        contact = req("POST", "/api/v1/contacts",
                      {"name": "儿子", "phone": "13800138000", "relation": "儿子", "sort_order": 1},
                      expect=201)
        log = req("POST", "/api/v1/calls",
                  {"contact_id": contact["id"], "status": "completed",
                   "started_at": "2026-10-31T20:00:00+08:00", "duration_seconds": 95},
                  actor="elder", expect=201)
        assert log["phone_desensitized"] == "138****8000", log["phone_desensitized"]
        logs = req("GET", f"/api/v1/calls?contact_id={contact['id']}")
        assert len(logs) == 1
        listed = req("GET", "/api/v1/contacts")
        match = next((row for row in listed if row["id"] == contact["id"]), None)
        assert match and match["phone"] == "13800138000"

    def reminders() -> None:
        reminder = req("POST", "/api/v1/reminders",
                       {"title": "吃降压药", "remind_at": "2026-11-01T08:00:00+08:00",
                        "repeat_rule": "daily"}, expect=201)
        updated = req("PATCH", f"/api/v1/reminders/{reminder['id']}", {"enabled": False})
        assert updated["enabled"] is False
        disabled = req("GET", "/api/v1/reminders?enabled=false")
        match = next((row for row in disabled if row["id"] == reminder["id"]), None)
        assert match and match["remind_at"] == "2026-11-01T08:00:00+08:00"

    def memories_and_confirmation() -> None:
        fact = req("POST", "/api/v1/memories",
                   {"kind": "fact", "subject": "奶奶",
                    "content": "奶奶喜欢听黄梅戏"}, expect=201)
        assert fact["status"] == "active"
        q = urllib.parse.quote("黄梅戏")
        hits = req("GET", f"/api/v1/memories?q={q}")
        assert any(row["id"] == fact["id"] for row in hits), hits
        versions = req("GET", f"/api/v1/memories/{fact['id']}/versions")
        assert len(versions) == 1
        req("PATCH", f"/api/v1/memories/{fact['id']}",
            {"content": "奶奶喜欢听黄梅戏，常在下午听", "change_reason": "补充时间"})
        versions = req("GET", f"/api/v1/memories/{fact['id']}/versions")
        assert len(versions) == 2 and versions[1]["change_reason"] == "补充时间"

        medical = req("POST", "/api/v1/memories",
                      {"kind": "medical", "subject": "爷爷",
                       "content": "爷爷对青霉素过敏"}, expect=201)
        assert medical["status"] == "pending" and medical["confirmation_id"]
        cid = medical["confirmation_id"]

        early = req("POST", f"/api/v1/confirmations/{cid}/family-confirm",
                    actor="family", expect=409)

        req("POST", f"/api/v1/confirmations/{cid}/elder-confirm", actor="elder")
        approved = req("POST", f"/api/v1/confirmations/{cid}/family-confirm", actor="family")
        assert approved["status"] == "approved"
        memory = req("GET", f"/api/v1/memories/{medical['id']}")
        assert memory["status"] == "active" and memory["confirmed_by"] == "family"
        q = urllib.parse.quote("青霉素")
        hits = req("GET", f"/api/v1/memories?q={q}")
        assert any(row["id"] == medical["id"] for row in hits), hits

        identity = req("POST", "/api/v1/memories",
                       {"kind": "identity", "subject": "奶奶",
                        "content": "奶奶身份证号 110101194001010001"}, expect=201)
        cid2 = identity["confirmation_id"]
        rejected = req("POST", f"/api/v1/confirmations/{cid2}/reject",
                       {"reason": "测试拒绝"}, actor="family")
        assert rejected["status"] == "rejected"
        memory = req("GET", f"/api/v1/memories/{identity['id']}")
        assert memory["status"] == "rejected"
        q = urllib.parse.quote("身份证号")
        assert all(row["id"] != identity["id"] for row in req("GET", f"/api/v1/memories?q={q}"))

        audit = req("GET", "/api/v1/audit?entity_type=memory&limit=100")
        assert len(audit) >= 4
        assert any(entry["action"] == "approve" for entry in audit)

    def confirmations_list() -> None:
        pending = req("GET", "/api/v1/confirmations?status=approved")
        assert len(pending) >= 1

    check("物品增删改查与软删除", items)
    check("联系人与通话记录脱敏", contacts_calls)
    check("提醒创建与停用", reminders)
    check("记忆检索、版本与医疗双确认", memories_and_confirmation)
    check("待确认列表", confirmations_list)

    if failures:
        print("\n失败：")
        for item in failures:
            print(" -", item)
        return 1
    print("\n全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
