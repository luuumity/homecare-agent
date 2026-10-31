from __future__ import annotations

from fastapi import APIRouter, Query

from .. import repository as repo
from ..deps import Actor, DbConn
from ..schemas_v1 import (
    MemoryCreate,
    MemoryOut,
    MemoryUpdate,
    MemoryVersionOut,
    OkResponse,
)

router = APIRouter(prefix="/memories", tags=["记忆"])


@router.get("", response_model=list[MemoryOut])
def list_memories(conn: DbConn, q: str = Query("", max_length=100),
                  status: str | None = "active", kind: str | None = None,
                  limit: int = Query(50, ge=1, le=200),
                  offset: int = Query(0, ge=0)) -> list[dict]:
    return repo.list_memories(conn, q, status or None, kind, limit, offset)


@router.post("", response_model=MemoryOut, status_code=201)
def create_memory(payload: MemoryCreate, conn: DbConn, actor: Actor) -> dict:
    return repo.create_memory(conn, actor, payload.kind, payload.subject,
                              payload.content, payload.source, payload.confidence)


@router.get("/{memory_id}", response_model=MemoryOut)
def get_memory(memory_id: str, conn: DbConn) -> dict:
    return repo.get_memory(conn, memory_id)


@router.patch("/{memory_id}", response_model=MemoryOut)
def update_memory(memory_id: str, payload: MemoryUpdate, conn: DbConn,
                  actor: Actor) -> dict:
    changes = payload.model_dump(exclude_unset=True)
    reason = changes.pop("change_reason", None)
    return repo.update_memory(conn, actor, memory_id, changes, reason)


@router.delete("/{memory_id}", response_model=OkResponse)
def delete_memory(memory_id: str, conn: DbConn, actor: Actor) -> OkResponse:
    repo.delete_memory(conn, actor, memory_id)
    return OkResponse(id=memory_id)


@router.get("/{memory_id}/versions", response_model=list[MemoryVersionOut])
def list_memory_versions(memory_id: str, conn: DbConn) -> list[dict]:
    return repo.list_memory_versions(conn, memory_id)
