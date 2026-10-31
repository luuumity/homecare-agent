from __future__ import annotations

from fastapi import APIRouter, Query

from .. import repository as repo
from ..deps import Actor, DbConn
from ..schemas_v1 import ItemCreate, ItemOut, ItemUpdate, OkResponse

router = APIRouter(prefix="/items", tags=["物品"])


@router.get("", response_model=list[ItemOut])
def list_items(conn: DbConn, q: str = Query("", max_length=100),
               limit: int = Query(50, ge=1, le=200),
               offset: int = Query(0, ge=0)) -> list[dict]:
    return repo.list_items(conn, q.strip(), limit, offset)


@router.post("", response_model=ItemOut, status_code=201)
def create_item(payload: ItemCreate, conn: DbConn, actor: Actor) -> dict:
    return repo.create_item(conn, actor, payload.name, payload.location, payload.note)


@router.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: str, conn: DbConn) -> dict:
    return repo.get_item(conn, item_id)


@router.patch("/{item_id}", response_model=ItemOut)
def update_item(item_id: str, payload: ItemUpdate, conn: DbConn, actor: Actor) -> dict:
    return repo.update_item(conn, actor, item_id, payload.model_dump(exclude_unset=True))


@router.delete("/{item_id}", response_model=OkResponse)
def delete_item(item_id: str, conn: DbConn, actor: Actor) -> OkResponse:
    repo.delete_item(conn, actor, item_id)
    return OkResponse(id=item_id)
