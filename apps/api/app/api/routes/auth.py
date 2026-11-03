"""登录、退出、邀请注册和当前会话接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.dependencies import CsrfPrincipal, Db, PrincipalDep
from app.core.config import get_settings
from app.core.rate_limit import limit
from app.schemas.auth import LoginRequest, RegisterRequest, SessionResponse, SessionUser
from app.services.auth import AuthService, Principal

router = APIRouter(prefix="/auth")
login_limit = limit("login", 8, 300)
LoginLimited = Annotated[None, Depends(login_limit)]


def session_response(principal: Principal, csrf_token: str) -> SessionResponse:
    return SessionResponse(
        user=SessionUser(
            id=principal.user.id,
            username=principal.user.username,
            display_name=principal.user.display_name,
            role=principal.user.role,
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
        settings.session_cookie_name,
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "mcalbum_csrf",
        csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/login", response_model=SessionResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Db,
    _limited: LoginLimited,
) -> SessionResponse:
    service = AuthService(db)
    user = service.authenticate(payload.username, payload.password)
    session, token, csrf_token = service.create_session(user)
    set_session_cookies(response, token, csrf_token)
    return session_response(
        Principal(user=user, session=session, permissions=service.users.permissions(user.id)),
        csrf_token,
    )


@router.post("/register", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Db) -> SessionResponse:
    service = AuthService(db)
    user = service.register(
        payload.username, payload.display_name, payload.password, payload.invitation_code
    )
    session, token, csrf_token = service.create_session(user)
    set_session_cookies(response, token, csrf_token)
    return session_response(
        Principal(user=user, session=session, permissions=service.users.permissions(user.id)),
        csrf_token,
    )


@router.get("/session", response_model=SessionResponse)
def get_session(
    request: Request,
    principal: PrincipalDep,
) -> SessionResponse:
    csrf_token = request.cookies.get("mcalbum_csrf", "")
    return session_response(principal, csrf_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, principal: CsrfPrincipal, db: Db) -> None:
    from app.core.security import utc_now

    principal.session.revoked_at = utc_now()
    db.commit()
    settings = get_settings()
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie("mcalbum_csrf", path="/")
