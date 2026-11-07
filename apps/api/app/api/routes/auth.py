"""登录、注册申请、退出和当前会话接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.dependencies import CsrfPrincipal, Db, PrincipalDep
from app.core.config import get_settings
from app.core.rate_limit import check_limit, limit
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegistrationResponse,
    SessionResponse,
    SessionUser,
)
from app.services.auth import AuthService, Principal

router = APIRouter(prefix="/auth")
LoginLimited = Annotated[None, Depends(limit("login", 8, 300))]


def session_response(principal: Principal, csrf_token: str) -> SessionResponse:
    return SessionResponse(
        user=SessionUser(
            id=principal.user.id,
            username=principal.user.username,
            display_name=principal.user.display_name,
            role=principal.role_code,
            role_name=principal.role_name,
            status=principal.user.status,
            player_id=principal.user.player_id,
            permissions=sorted(principal.permissions),
        ),
        csrf_token=csrf_token,
        expires_at=principal.session.expires_at,
    )


def set_session_cookies(response: Response, token: str, csrf_token: str) -> None:
    settings = get_settings()
    max_age = settings.session_ttl_hours * 3600
    response.set_cookie(
        settings.session_cookie_name, token, max_age=max_age, httponly=True,
        secure=settings.cookie_secure, samesite="lax", path="/",
    )
    response.set_cookie(
        "mcalbum_csrf", csrf_token, max_age=max_age, httponly=False,
        secure=settings.cookie_secure, samesite="lax", path="/",
    )


@router.post("/login", response_model=SessionResponse)
def login(payload: LoginRequest, response: Response, db: Db,
          _limited: LoginLimited) -> SessionResponse:
    service = AuthService(db)
    user = service.authenticate(payload.username, payload.password)
    session, token, csrf_token = service.create_session(user)
    set_session_cookies(response, token, csrf_token)
    return session_response(service.principal(user, session), csrf_token)


@router.post("/register", response_model=RegistrationResponse,
             status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Db) -> RegistrationResponse:
    """创建待审核申请；同一 IP 和账号名每小时分别最多提交五次。"""

    address = request.client.host if request.client else "unknown"
    window = get_settings().registration_rate_window_seconds
    check_limit("register-ip", address, 5, window)
    check_limit("register-account", payload.username.strip().lower(), 5, window)
    if payload.website:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "注册申请无法提交")
    AuthService(db).register(
        payload.username, payload.display_name, payload.minecraft_name,
        payload.application_reason, payload.password,
    )
    return RegistrationResponse(message="申请已提交，请等待管理员审核后再登录")


@router.get("/session", response_model=SessionResponse)
def get_session(request: Request, principal: PrincipalDep) -> SessionResponse:
    return session_response(principal, request.cookies.get("mcalbum_csrf", ""))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, principal: CsrfPrincipal, db: Db) -> None:
    from app.core.security import utc_now

    principal.session.revoked_at = utc_now()
    db.commit()
    settings = get_settings()
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie("mcalbum_csrf", path="/")
