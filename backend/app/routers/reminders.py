from __future__ import annotations

from fastapi import APIRouter, Query

from .. import repository as repo
from ..deps import Actor, DbConn
from ..schemas_v1 import OkResponse, ReminderCreate, ReminderOut, ReminderUpdate

router = APIRouter(prefix="/reminders", tags=["提醒"])


@router.get("", response_model=list[ReminderOut])
def list_reminders(conn: DbConn, enabled: bool | None = None,
                   limit: int = Query(50, ge=1, le=200),
                   offset: int = Query(0, ge=0)) -> list[dict]:
    return repo.list_reminders(conn, enabled, limit, offset)


@router.post("", response_model=ReminderOut, status_code=201)
def create_reminder(payload: ReminderCreate, conn: DbConn, actor: Actor) -> dict:
    return repo.create_reminder(conn, actor, payload.title, payload.remind_at,
                                payload.repeat_rule)


@router.get("/{reminder_id}", response_model=ReminderOut)
def get_reminder(reminder_id: str, conn: DbConn) -> dict:
    return repo.get_reminder(conn, reminder_id)


@router.patch("/{reminder_id}", response_model=ReminderOut)
def update_reminder(reminder_id: str, payload: ReminderUpdate, conn: DbConn,
                    actor: Actor) -> dict:
    return repo.update_reminder(conn, actor, reminder_id,
                                payload.model_dump(exclude_unset=True))


@router.delete("/{reminder_id}", response_model=OkResponse)
def delete_reminder(reminder_id: str, conn: DbConn, actor: Actor) -> OkResponse:
    repo.delete_reminder(conn, actor, reminder_id)
    return OkResponse(id=reminder_id)
