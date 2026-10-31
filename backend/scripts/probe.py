"""离线探针：无需启动服务，检查数据库与中文检索能力。

用法（在 backend/ 下）：python scripts/probe.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.db import check_db, check_fts5, init_db  # noqa: E402


def main() -> int:
    settings = get_settings()
    init_db(settings.db_path)
    fts5_ok, trigram_ok, detail = check_fts5()
    result = {
        "app_version": settings.app_version,
        "api_version": settings.api_version,
        "min_shell_version": settings.min_shell_version,
        "timezone": settings.timezone,
        "sqlite_version": sqlite3.sqlite_version,
        "db": check_db(settings.db_path),
        "fts5_available": fts5_ok,
        "fts5_trigram_available": trigram_ok,
        "fts5_detail": detail,
        "llm_configured": settings.llm_configured,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if (fts5_ok and trigram_ok and result["db"]["writable"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
