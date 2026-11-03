"""管理员邀请、账号权限、审计和发布控制。"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import CsrfPrincipal, Db, PrincipalDep
from app.core.security import utc_now
from app.models import AuditLog, Comment, User, UserSession
from app.repositories.users import UserRepository
from app.schemas.auth import (
    InvitationCreate,
    InvitationCreated,
    SessionUser,
    UserPermissionUpdate,
    UserStatusUpdate,
    UserSummary,
)
from app.services.auth import AuthService
from app.services.publication import PublicationService

router = APIRouter(prefix="/admin")


@router.post("/invitations", response_model=InvitationCreated, status_code=status.HTTP_201_CREATED)
def create_invitation(
    payload: InvitationCreate,
    principal: CsrfPrincipal,
    db: Db,
) -> InvitationCreated:
    code, invitation = AuthService(db).create_invitation(
        principal, payload.expires_in_hours, payload.permissions
    )
    return InvitationCreated(code=code, expires_at=invitation.expires_at)


@router.get("/users", response_model=list[UserSummary])
def list_users(principal: PrincipalDep, db: Db) -> list[UserSummary]:
    AuthService.require_admin(principal)
    repo = UserRepository(db)
    users = db.scalars(select(User).order_by(User.created_at.asc()))
    return [
        UserSummary(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
            player_id=user.player_id,
            permissions=sorted(repo.permissions(user.id)),
            enabled=user.enabled,
            created_at=user.created_at,
        )
        for user in users
    ]


@router.put("/users/{user_id}/permissions", response_model=SessionUser)
def update_permissions(
    user_id: str,
    payload: UserPermissionUpdate,
    principal: CsrfPrincipal,
    db: Db,
) -> SessionUser:
    service = AuthService(db)
    user = service.users.by_id(user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "账号不存在")
    service.set_permissions(principal, user, payload.permissions)
    return SessionUser(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        player_id=user.player_id,
        permissions=sorted(service.users.permissions(user.id)),
    )


@router.put("/users/{user_id}/status", status_code=status.HTTP_204_NO_CONTENT)
def update_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    principal: CsrfPrincipal,
    db: Db,
) -> None:
    service = AuthService(db)
    service.require_admin(principal)
    user = service.users.by_id(user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "账号不存在")
    if user.id == principal.user.id and not payload.enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "不能停用当前管理员账号")
    user.enabled = payload.enabled
    user.updated_at = utc_now()
    if not payload.enabled:
        for session in db.scalars(
            select(UserSession).where(
                UserSession.user_id == user.id, UserSession.revoked_at.is_(None)
            )
        ):
            session.revoked_at = utc_now()
    service.audit(
        principal.user.id,
        "user.enable" if payload.enabled else "user.disable",
        "user",
        user.id,
    )
    db.commit()


@router.get("/audit")
def list_audit(principal: PrincipalDep, db: Db) -> list[dict[str, object]]:
    AuthService.require_admin(principal)
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200))
    return [
        {
            "id": row.id,
            "actorUserId": row.actor_user_id,
            "action": row.action,
            "targetType": row.target_type,
            "targetId": row.target_id,
            "metadata": row.metadata_json,
            "createdAt": row.created_at,
        }
        for row in rows
    ]


@router.get("/comments")
def list_all_comments(principal: PrincipalDep, db: Db) -> list[dict[str, object]]:
    AuthService.require_admin(principal)
    rows = db.scalars(select(Comment).order_by(Comment.created_at.desc()).limit(200))
    return [
        {
            "id": row.id,
            "photoId": row.photo_id,
            "authorUserId": row.author_user_id,
            "body": row.body,
            "status": row.status,
            "hiddenReason": row.hidden_reason,
            "createdAt": row.created_at,
        }
        for row in rows
    ]


@router.post("/publish")
def publish_snapshot(principal: CsrfPrincipal, db: Db) -> dict[str, object]:
    return PublicationService(db).rebuild(principal)
