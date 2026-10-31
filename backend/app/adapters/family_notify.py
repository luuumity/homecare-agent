"""家属通知通道适配层（占位）。

阶段 1 不接短信，只返回“未配置”。后续接短信签名链接时，在此实现
send_confirmation_link(confirmation) 并返回同样的结构，调用方无需改动。
"""

from __future__ import annotations


def notify_family(confirmation: dict) -> dict:
    return {
        "channel": "none",
        "sent": False,
        "detail": "家属通知通道未配置（短信确认按计划暂缓）",
        "confirmation_id": confirmation.get("id"),
    }
