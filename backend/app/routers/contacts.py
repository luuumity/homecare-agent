from __future__ import annotations

from fastapi import APIRouter, Query

from .. import repository as repo
from ..deps import Actor, DbConn
from ..schemas_v1 import ContactCreate, ContactOut, ContactUpdate, OkResponse

router = APIRouter(prefix="/contacts", tags=["联系人"])


@router.get("", response_model=list[ContactOut])
def list_contacts(conn: DbConn, limit: int = Query(50, ge=1, le=200),
                  offset: int = Query(0, ge=0)) -> list[dict]:
    return repo.list_contacts(conn, limit, offset)


@router.post("", response_model=ContactOut, status_code=201)
def create_contact(payload: ContactCreate, conn: DbConn, actor: Actor) -> dict:
    return repo.create_contact(conn, actor, payload.name, payload.phone,
                               payload.relation, payload.sort_order)


@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: str, conn: DbConn) -> dict:
    return repo.get_contact(conn, contact_id)


@router.patch("/{contact_id}", response_model=ContactOut)
def update_contact(contact_id: str, payload: ContactUpdate, conn: DbConn,
                   actor: Actor) -> dict:
    return repo.update_contact(conn, actor, contact_id,
                               payload.model_dump(exclude_unset=True))


@router.delete("/{contact_id}", response_model=OkResponse)
def delete_contact(contact_id: str, conn: DbConn, actor: Actor) -> OkResponse:
    repo.delete_contact(conn, actor, contact_id)
    return OkResponse(id=contact_id)
