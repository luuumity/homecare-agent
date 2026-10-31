from __future__ import annotations

from fastapi import APIRouter, Query

from .. import repository as repo
from ..deps import DbConn
from ..schemas_v1 import AuditOut

router = APIRouter(prefix="/audit", tags=["审计"])


@router.get("", response_model=list[AuditOut])
def list_audit(conn: DbConn, entity_type: str | None = None,
               entity_id: str | None = None,
               limit: int = Query(50, ge=1, le=200),
               offset: int = Query(0, ge=0)) -> list[dict]:
    return repo.list_audit(conn, entity_type, entity_id, limit, offset)
