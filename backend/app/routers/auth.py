"""PIN 登录接口：登录、查询当前身份、退出。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from ..auth import (
    COOKIE_NAME,
    check_pin,
    client_ip,
    create_session,
    require_session,
)
from ..config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginBody(BaseModel):
    pin: str = Field(min_length=1, max_length=12)


def _secure(request: Request) -> bool:
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    return proto.split(",")[0].strip() == "https"


@router.post("/login")
def login(body: LoginBody, request: Request, response: Response) -> dict:
    check_pin(body.pin.strip(), client_ip(request))
    token = create_session()
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=get_settings().auth_cookie_seconds,
        httponly=True,
        secure=_secure(request),
        samesite="lax",
        path="/",
    )
    return {"ok": True, "role": "family"}


@router.get("/me")
def me(role: str = Depends(require_session)) -> dict:
    return {"ok": True, "role": role}


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}
