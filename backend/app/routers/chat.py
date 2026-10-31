"""主对话接口（阶段 2，纯文本）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..agent import conversation_repo as conv
from ..agent import llm, service
from ..config import get_settings
from ..deps import DbConn
from ..schemas_agent import ChatRequest, ChatResponse, ChatStatus, HistoryMessage

router = APIRouter(prefix="/chat", tags=["陪伴对话"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, conn: DbConn) -> dict:
    try:
        return service.chat(conn, payload.text)
    except llm.LlmError as exc:
        raise HTTPException(status_code=503, detail=f"模型暂时不可用：{exc}") from exc


@router.get("/history", response_model=list[HistoryMessage])
def history(conn: DbConn, limit: int = Query(50, ge=1, le=200),
            include_tool: bool = Query(False)) -> list[dict]:
    return conv.list_history(conn, limit, include_tool)


@router.get("/status", response_model=ChatStatus)
def status(conn: DbConn) -> dict:
    settings = get_settings()
    data = conv.status(conn)
    return {
        "llm_configured": settings.llm_configured,
        "model": settings.llm_model,
        **data,
    }
