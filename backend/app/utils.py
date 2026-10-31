"""时间、ID、号码脱敏等通用工具。"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import get_settings

ALLOWED_ACTORS = {"family", "elder", "agent", "system"}


def new_id() -> str:
    return uuid.uuid4().hex


def tz() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def now_iso() -> str:
    return datetime.now(tz()).isoformat(timespec="seconds")


def to_iso(value: datetime) -> str:
    """统一存成带时区的 ISO 字符串，保证字符串可比大小。"""
    if value.tzinfo is None:
        value = value.replace(tzinfo=tz())
    return value.astimezone(tz()).isoformat(timespec="seconds")


def desensitize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if len(digits) <= 4:
        return "****"
    if len(digits) <= 7:
        return f"{digits[:2]}****{digits[-2:]}"
    return f"{digits[:3]}****{digits[-4:]}"
