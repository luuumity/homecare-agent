"""阶段 2 对话接口的请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("不能为空")
        return value


class ToolEvent(BaseModel):
    name: str
    ok: bool
    error: str | None = None


class ChatResponse(BaseModel):
    reply: str
    message_id: str
    created_at: str
    tool_calls: list[ToolEvent]
    pending_confirmation_ids: list[str]
    compressed: bool


class HistoryMessage(BaseModel):
    id: str
    role: str
    content: str
    tool_name: str | None = None
    tool_payload: str | None = None
    created_at: str


class ChatStatus(BaseModel):
    llm_configured: bool
    model: str
    message_count: int
    by_role: dict[str, int]
    has_summary: bool
    summary_count: int
    last_message_id: str | None = None
    last_summarized_message_id: str | None = None
