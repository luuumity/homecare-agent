"""API 响应模型（阶段 0：健康检查 / 版本 / 诊断）。"""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app_version: str
    api_version: str
    server_time: str


class VersionResponse(BaseModel):
    app_version: str
    api_version: str
    min_shell_version: str


class DbDiagnose(BaseModel):
    path: str
    exists: bool
    writable: bool
    sqlite_version: str
    fts5_available: bool
    fts5_trigram_available: bool
    detail: str
    error: str | None = None


class LlmDiagnose(BaseModel):
    base_url: str
    model: str
    api_key_set: bool
    configured: bool


class DiagnoseResponse(BaseModel):
    server_time: str
    timezone: str
    db: DbDiagnose
    llm: LlmDiagnose
