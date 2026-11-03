"""认证、CSRF 与权限请求依赖。"""

from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import secret_hash, secrets_equal
from app.services.auth import AuthService, Principal

Db = Annotated[Session, Depends(get_db)]


def current_principal(
    db: Db,
    request: Request,
) -> Principal:
    """解析 HttpOnly Cookie 并返回当前账号权限快照。"""

    session_token = request.cookies.get(get_settings().session_cookie_name)
    if not session_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "需要登录")
    return AuthService(db).principal_from_token(session_token)


PrincipalDep = Annotated[Principal, Depends(current_principal)]


def csrf_protected(
    request: Request,
    principal: PrincipalDep,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
    csrf_cookie: Annotated[str | None, Cookie(alias="mcalbum_csrf")] = None,
) -> Principal:
    """同时校验可信 Origin、双提交 Cookie 与会话内 CSRF 摘要。"""

    settings = get_settings()
    origin = request.headers.get("origin")
    if origin not in settings.trusted_origins:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "请求来源不受信任")
    if not csrf_header or not csrf_cookie or not secrets_equal(csrf_header, csrf_cookie):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "CSRF 校验失败")
    if not secrets_equal(secret_hash(csrf_header), principal.session.csrf_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "CSRF 校验失败")
    return principal


CsrfPrincipal = Annotated[Principal, Depends(csrf_protected)]
