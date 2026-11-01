"""PIN 会话：HMAC 签名 Cookie，按来源 IP 失败计数并锁定。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from fastapi import HTTPException, Request

from .config import get_settings

COOKIE_NAME = "homecare_session"
MAX_FAILURES = 5
LOCK_SECONDS = 300

# ip -> (连续失败次数, 锁定截止时间)
_failures: dict[str, tuple[int, float]] = {}


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _secret() -> bytes:
    return get_settings().auth_secret.encode("utf-8")


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: str) -> str:
    digest = hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).digest()
    return _b64e(digest)


def create_session(role: str = "family") -> str:
    expires = int(time.time()) + get_settings().auth_cookie_seconds
    payload = _b64e(
        json.dumps({"role": role, "exp": expires}, separators=(",", ":")).encode("utf-8")
    )
    return f"{payload}.{_sign(payload)}"


def verify_session(token: str | None) -> str | None:
    if not token or "." not in token:
        return None
    payload, signature = token.rsplit(".", 1)
    if not hmac.compare_digest(signature, _sign(payload)):
        return None
    try:
        data = json.loads(_b64d(payload))
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or int(data.get("exp", 0)) < int(time.time()):
        return None
    role = data.get("role")
    return role if isinstance(role, str) and role else None


def require_session(request: Request) -> str:
    role = verify_session(request.cookies.get(COOKIE_NAME))
    if role is None:
        raise HTTPException(status_code=401, detail="请先登录")
    return role


def _check_lock(ip: str) -> None:
    count, locked_until = _failures.get(ip, (0, 0.0))
    now = time.time()
    if locked_until > now:
        wait = int(locked_until - now) + 1
        raise HTTPException(
            status_code=429,
            detail=f"尝试次数过多，请 {(wait + 59) // 60} 分钟后再试",
        )


def check_pin(pin: str, ip: str) -> None:
    """校验 PIN；连续失败 5 次后锁定 5 分钟（按 IP 计数，互不影响）。"""
    _check_lock(ip)
    if pin and hmac.compare_digest(pin, get_settings().auth_pin):
        _failures.pop(ip, None)
        return
    count, _ = _failures.get(ip, (0, 0.0))
    count += 1
    if count >= MAX_FAILURES:
        _failures[ip] = (0, time.time() + LOCK_SECONDS)
        raise HTTPException(status_code=429, detail="尝试次数过多，请 5 分钟后再试")
    _failures[ip] = (count, 0.0)
    raise HTTPException(status_code=401, detail=f"PIN 不正确，还可以试 {MAX_FAILURES - count} 次")
