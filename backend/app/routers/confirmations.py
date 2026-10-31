from __future__ import annotations

from fastapi import APIRouter, Query

from .. import repository as repo
from ..deps import Actor, DbConn
from ..schemas_v1 import ConfirmationCreate, ConfirmationOut, ConfirmationReject

router = APIRouter(prefix="/confirmations", tags=["待确认"])


@router.get("", response_model=list[ConfirmationOut])
def list_confirmations(conn: DbConn, status: str | None = None,
                       limit: int = Query(50, ge=1, le=200),
                       offset: int = Query(0, ge=0)) -> list[dict]:
    return repo.list_confirmations(conn, status, limit, offset)


@router.post("", response_model=ConfirmationOut, status_code=201)
def create_confirmation(payload: ConfirmationCreate, conn: DbConn, actor: Actor) -> dict:
    return repo.create_confirmation(conn, actor, payload.kind, payload.entity_type,
                                    payload.entity_id, payload.payload, payload.expires_at)


@router.get("/{confirmation_id}", response_model=ConfirmationOut)
def get_confirmation(confirmation_id: str, conn: DbConn) -> dict:
    return repo.get_confirmation(conn, confirmation_id)


@router.post("/{confirmation_id}/elder-confirm", response_model=ConfirmationOut)
def elder_confirm(confirmation_id: str, conn: DbConn, actor: Actor) -> dict:
    return repo.elder_confirm(conn, actor, confirmation_id)


@router.post("/{confirmation_id}/family-confirm", response_model=ConfirmationOut)
def family_confirm(confirmation_id: str, conn: DbConn, actor: Actor) -> dict:
    return repo.family_confirm(conn, actor, confirmation_id)


@router.post("/{confirmation_id}/reject", response_model=ConfirmationOut)
def reject_confirmation(confirmation_id: str, conn: DbConn, actor: Actor,
                        payload: ConfirmationReject | None = None) -> dict:
    reason = payload.reason if payload else None
    return repo.reject_confirmation(conn, actor, confirmation_id, reason)
