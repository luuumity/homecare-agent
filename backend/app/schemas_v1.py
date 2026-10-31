"""阶段 1 业务接口的请求/响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

RepeatRule = Literal["none", "daily", "weekly", "weekdays"]
MemoryKind = Literal["fact", "preference", "medical", "identity", "event"]
MemoryStatus = Literal["pending", "active", "rejected", "archived"]
CallStatus = Literal["initiated", "completed", "failed", "cancelled"]
ConfirmationKind = Literal["medical_memory", "identity_memory", "memory_change", "other"]

PHONE_PATTERN = r"^[0-9+\-\s()]{5,20}$"


def _strip(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("不能为空")
    return value


class OkResponse(BaseModel):
    ok: bool = True
    id: str


# ---------------------------------------------------------------- 物品

class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("name", "location")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return _strip(value)


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    location: str | None = Field(default=None, min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("name", "location")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return _strip(value) if value is not None else None


class ItemOut(BaseModel):
    id: str
    name: str
    location: str
    note: str | None
    created_by: str
    created_at: str
    updated_at: str
    deleted_at: str | None


# ---------------------------------------------------------------- 提醒

class ReminderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    remind_at: datetime
    repeat_rule: RepeatRule = "none"

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return _strip(value)


class ReminderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    remind_at: datetime | None = None
    repeat_rule: RepeatRule | None = None
    enabled: bool | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        return _strip(value) if value is not None else None


class ReminderOut(BaseModel):
    id: str
    title: str
    remind_at: str
    repeat_rule: str
    enabled: bool
    created_by: str
    created_at: str
    updated_at: str
    last_fired_at: str | None
    deleted_at: str | None


# ---------------------------------------------------------------- 联系人

class ContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    phone: str = Field(pattern=PHONE_PATTERN)
    relation: str | None = Field(default=None, max_length=50)
    sort_order: int = Field(default=0, ge=0, le=999)

    @field_validator("name", "phone")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return _strip(value)


class ContactUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    relation: str | None = Field(default=None, max_length=50)
    sort_order: int | None = Field(default=None, ge=0, le=999)

    @field_validator("name", "phone")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return _strip(value) if value is not None else None


class ContactOut(BaseModel):
    id: str
    name: str
    relation: str | None
    phone: str
    phone_desensitized: str
    sort_order: int
    created_at: str
    updated_at: str
    deleted_at: str | None


# ---------------------------------------------------------------- 通话记录

class CallLogCreate(BaseModel):
    contact_id: str = Field(min_length=1, max_length=64)
    status: CallStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=500)


class CallLogOut(BaseModel):
    id: str
    contact_id: str
    contact_name: str
    phone_desensitized: str
    status: str
    started_at: str | None
    ended_at: str | None
    duration_seconds: int | None
    note: str | None
    created_by: str
    created_at: str


# ---------------------------------------------------------------- 记忆

class MemoryCreate(BaseModel):
    kind: MemoryKind
    subject: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=1000)
    source: str = Field(default="family", max_length=50)
    confidence: float = Field(default=0.5, ge=0, le=1)

    @field_validator("subject", "content")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return _strip(value)


class MemoryUpdate(BaseModel):
    kind: MemoryKind | None = None
    subject: str | None = Field(default=None, min_length=1, max_length=100)
    content: str | None = Field(default=None, min_length=1, max_length=1000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    source: str | None = Field(default=None, max_length=50)
    change_reason: str | None = Field(default=None, max_length=200)

    @field_validator("subject", "content")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return _strip(value) if value is not None else None


class MemoryOut(BaseModel):
    id: str
    kind: str
    subject: str
    content: str
    confidence: float
    source: str
    status: str
    version: int
    confirmation_id: str | None
    confirmed_by: str | None
    confirmed_at: str | None
    created_by: str
    created_at: str
    updated_at: str
    deleted_at: str | None


class MemoryVersionOut(BaseModel):
    id: str
    memory_id: str
    version: int
    kind: str
    subject: str
    content: str
    changed_by: str
    change_reason: str | None
    created_at: str


# ---------------------------------------------------------------- 待确认

class ConfirmationCreate(BaseModel):
    kind: ConfirmationKind
    entity_type: str = Field(min_length=1, max_length=50)
    entity_id: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None


class ConfirmationReject(BaseModel):
    reason: str | None = Field(default=None, max_length=200)


class ConfirmationOut(BaseModel):
    id: str
    kind: str
    entity_type: str
    entity_id: str
    payload: dict[str, Any]
    requested_by: str
    status: str
    elder_confirmed_by: str | None
    elder_confirmed_at: str | None
    family_confirmed_by: str | None
    family_confirmed_at: str | None
    rejected_by: str | None
    reject_reason: str | None
    expires_at: str | None
    created_at: str
    updated_at: str


# ---------------------------------------------------------------- 审计

class AuditOut(BaseModel):
    id: str
    actor: str
    action: str
    entity_type: str
    entity_id: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    created_at: str
