"""应用配置：从 backend/.env 与进程环境变量读取，不引入额外依赖。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
DEFAULT_DB_PATH = BASE_DIR / "data" / "eldercare.db"


def _load_dotenv(path: Path) -> None:
    """极简 .env 解析：KEY=VALUE，忽略空行与 # 注释，不覆盖已存在的环境变量。"""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


def _db_path() -> Path:
    raw = os.environ.get("DB_PATH", "").strip()
    if not raw:
        return DEFAULT_DB_PATH
    path = Path(raw)
    return path if path.is_absolute() else BASE_DIR / path


@dataclass(frozen=True)
class Settings:
    app_version: str
    api_version: str
    min_shell_version: str
    timezone: str
    db_path: Path
    llm_base_url: str
    llm_model: str
    llm_api_key: str
    cors_origins: tuple[str, ...]
    auth_pin: str
    auth_secret: str
    auth_cookie_seconds: int

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key and self.llm_base_url and self.llm_model)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_dotenv(ENV_FILE)
    origins = os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    )
    return Settings(
        app_version=os.environ.get("APP_VERSION", "0.4.0-stage3"),
        api_version=os.environ.get("API_VERSION", "v1"),
        min_shell_version=os.environ.get("MIN_SHELL_VERSION", "0.1.0"),
        timezone=os.environ.get("TIMEZONE", "Asia/Shanghai"),
        db_path=_db_path(),
        llm_base_url=os.environ.get("LLM_BASE_URL", "https://api.deepseek.com").strip(),
        llm_model=os.environ.get("LLM_MODEL", "deepseek-chat").strip(),
        llm_api_key=os.environ.get("LLM_API_KEY", "").strip(),
        cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        auth_pin=os.environ.get("AUTH_PIN", "202611").strip(),
        auth_secret=os.environ.get("AUTH_SECRET", "dev-insecure-secret-change-me").strip(),
        auth_cookie_seconds=int(os.environ.get("AUTH_COOKIE_DAYS", "30")) * 86400,
    )
