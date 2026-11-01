"""陪伴大屏后端入口：阶段 1 业务接口 + 阶段 2 陪伴对话。"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .auth import require_session
from .config import get_settings
from .db import check_db, check_fts5, init_db
from .errors import BadRequest, Conflict, NotFound
from .routers import audit as audit_routes
from .routers import auth as auth_routes
from .routers import calls, chat, confirmations, contacts, items, memories, reminders
from .schemas import (
    DbDiagnose,
    DiagnoseResponse,
    HealthResponse,
    LlmDiagnose,
    VersionResponse,
)

logger = logging.getLogger("eldercare")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

settings = get_settings()


def now_iso() -> str:
    return datetime.now(ZoneInfo(settings.timezone)).isoformat(timespec="seconds")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        version = init_db(settings.db_path)
        logger.info("SQLite 初始化完成（schema v%s）：%s", version, settings.db_path)
    except (OSError, sqlite3.Error):
        logger.exception("SQLite 初始化失败，服务仍启动，/api/diagnose 会显示详情")
    yield


app = FastAPI(
    title="陪伴大屏 API",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)


@app.exception_handler(NotFound)
async def handle_not_found(_request: Request, exc: NotFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(Conflict)
async def handle_conflict(_request: Request, exc: Conflict) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(BadRequest)
async def handle_bad_request(_request: Request, exc: BadRequest) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


app.include_router(auth_routes.router, prefix="/api/v1")

for router in (
    items.router,
    reminders.router,
    contacts.router,
    calls.router,
    memories.router,
    confirmations.router,
    audit_routes.router,
    chat.router,
):
    app.include_router(router, prefix="/api/v1", dependencies=[Depends(require_session)])


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_version=settings.app_version,
        api_version=settings.api_version,
        server_time=now_iso(),
    )


@app.get("/api/version", response_model=VersionResponse)
def version() -> VersionResponse:
    return VersionResponse(
        app_version=settings.app_version,
        api_version=settings.api_version,
        min_shell_version=settings.min_shell_version,
    )


@app.get("/api/diagnose", response_model=DiagnoseResponse, dependencies=[Depends(require_session)])
def diagnose() -> DiagnoseResponse:
    db = check_db(settings.db_path)
    fts5_ok, trigram_ok, fts_detail = check_fts5()

    return DiagnoseResponse(
        server_time=now_iso(),
        timezone=settings.timezone,
        db=DbDiagnose(
            path=db["path"],
            exists=db["exists"],
            writable=db["writable"],
            sqlite_version=sqlite3.sqlite_version,
            fts5_available=fts5_ok,
            fts5_trigram_available=trigram_ok,
            detail=fts_detail,
            error=db["error"],
        ),
        llm=LlmDiagnose(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            api_key_set=bool(settings.llm_api_key),
            configured=settings.llm_configured,
        ),
    )
