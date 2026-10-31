"""FastAPI 依赖：每请求一个 SQLite 连接，统一解析操作者。"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from .config import get_settings
from .db import connect
from .utils import ALLOWED_ACTORS


def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect(get_settings().db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_actor(x_actor: Annotated[str | None, Header(alias="X-Actor")] = None) -> str:
    actor = (x_actor or "family").strip()
    if actor not in ALLOWED_ACTORS:
        raise HTTPException(status_code=400, detail="无效的 X-Actor")
    return actor


DbConn = Annotated[sqlite3.Connection, Depends(get_db)]
Actor = Annotated[str, Depends(get_actor)]
