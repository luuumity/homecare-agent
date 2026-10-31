from __future__ import annotations

from fastapi import APIRouter, Query

from .. import repository as repo
from ..deps import Actor, DbConn
from ..schemas_v1 import CallLogCreate, CallLogOut

router = APIRouter(prefix="/calls", tags=["通话记录"])


@router.get("", response_model=list[CallLogOut])
def list_call_logs(conn: DbConn, contact_id: str | None = None,
                   limit: int = Query(50, ge=1, le=200),
                   offset: int = Query(0, ge=0)) -> list[dict]:
    return repo.list_call_logs(conn, contact_id, limit, offset)


@router.post("", response_model=CallLogOut, status_code=201)
def create_call_log(payload: CallLogCreate, conn: DbConn, actor: Actor) -> dict:
    return repo.create_call_log(
        conn, actor, payload.contact_id, payload.status, payload.started_at,
        payload.ended_at, payload.duration_seconds, payload.note,
    )
