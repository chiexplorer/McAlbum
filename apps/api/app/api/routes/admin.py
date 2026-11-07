"""账号审批、角色权限、审计和归档快照管理。"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.dependencies import CsrfPrincipal, Db, PrincipalDep
from app.models import AuditLog, Comment, Role, RolePermission, User
from app.repositories.users import UserRepository
from app.schemas.auth import (
    PermissionSummary,
    RolePermissionUpdate,
    RoleSummary,
    UserBanUpdate,
    UserReviewRequest,
    UserRoleUpdate,
    UserSummary,
)
from app.services.auth import AuthService
from app.services.publication import PublicationService

router = APIRouter(prefix="/admin")


def user_summary(repo: UserRepository, user: User) -> UserSummary:
    role = repo.role(user)
    return UserSummary(
        id=user.id, username=user.username, display_name=user.display_name,
        minecraft_name=user.minecraft_name, application_reason=user.application_reason,
        review_reason=user.review_reason, ban_reason=user.ban_reason,
        role_id=role.id, role=role.code, role_name=role.name_zh,
        status=user.status, player_id=user.player_id,
        permissions=sorted(repo.permissions(user.id)), created_at=user.created_at,
    )


@router.get("/permissions", response_model=list[PermissionSummary])
def list_permissions(principal: PrincipalDep, db: Db) -> list[PermissionSummary]:
    AuthService.require(principal, "role.permissions.manage")
    return [PermissionSummary.model_validate(row, from_attributes=True)
            for row in UserRepository(db).permission_catalog()]


@router.get("/roles", response_model=list[RoleSummary])
def list_roles(principal: PrincipalDep, db: Db) -> list[RoleSummary]:
    if not principal.can("role.permissions.manage"):
        AuthService.require(principal, "user.role.assign")
    repo = UserRepository(db)
    return [RoleSummary(
        id=role.id, code=role.code, name_zh=role.name_zh,
        description=role.description,
        permissions=sorted(db.scalars(select(RolePermission.permission_code).where(
            RolePermission.role_id == role.id
        ))),
    ) for role in repo.roles()]


@router.put("/roles/{role_id}/permissions", response_model=RoleSummary)
def update_role_permissions(role_id: str, payload: RolePermissionUpdate,
                            principal: CsrfPrincipal, db: Db) -> RoleSummary:
    service = AuthService(db)
    service.set_role_permissions(principal, role_id, payload.permissions)
    role = db.get(Role, role_id)
    assert role is not None
    return RoleSummary(id=role.id, code=role.code, name_zh=role.name_zh,
                       description=role.description, permissions=sorted(payload.permissions))


@router.get("/users", response_model=list[UserSummary])
def list_users(principal: PrincipalDep, db: Db) -> list[UserSummary]:
    account_permissions = {
        "user.review", "user.role.assign", "user.ban", "role.permissions.manage"
    }
    if not account_permissions.intersection(principal.permissions):
        raise HTTPException(403, "缺少账号管理权限")
    repo = UserRepository(db)
    users = db.scalars(select(User).order_by(User.created_at.desc()))
    return [user_summary(repo, user) for user in users]


def find_user(service: AuthService, user_id: str) -> User:
    user = service.users.by_id(user_id)
    if user is None:
        raise HTTPException(404, "账号不存在")
    return user


@router.post("/users/{user_id}/review", response_model=UserSummary)
def review_user(user_id: str, payload: UserReviewRequest,
                principal: CsrfPrincipal, db: Db) -> UserSummary:
    service = AuthService(db)
    user = find_user(service, user_id)
    service.review_user(principal, user, payload.action, payload.reason)
    return user_summary(service.users, user)


@router.put("/users/{user_id}/role", response_model=UserSummary)
def update_user_role(user_id: str, payload: UserRoleUpdate,
                     principal: CsrfPrincipal, db: Db) -> UserSummary:
    service = AuthService(db)
    user = find_user(service, user_id)
    service.assign_role(principal, user, payload.role_id)
    return user_summary(service.users, user)


@router.put("/users/{user_id}/ban", response_model=UserSummary)
def update_user_ban(user_id: str, payload: UserBanUpdate,
                    principal: CsrfPrincipal, db: Db) -> UserSummary:
    service = AuthService(db)
    user = find_user(service, user_id)
    service.set_user_ban(principal, user, payload.banned, payload.reason)
    return user_summary(service.users, user)


@router.get("/audit")
def list_audit(principal: PrincipalDep, db: Db) -> list[dict[str, object]]:
    AuthService.require(principal, "audit.read")
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200))
    return [{"id": row.id, "actorUserId": row.actor_user_id, "action": row.action,
             "targetType": row.target_type, "targetId": row.target_id,
             "metadata": row.metadata_json, "createdAt": row.created_at} for row in rows]


@router.get("/comments")
def list_all_comments(principal: PrincipalDep, db: Db) -> list[dict[str, object]]:
    AuthService.require(principal, "comment.delete.any")
    rows = db.scalars(select(Comment).order_by(Comment.created_at.desc()).limit(200))
    return [{"id": row.id, "photoId": row.photo_id,
             "authorUserId": row.author_user_id, "body": row.body,
             "status": row.status, "deletionReason": row.deletion_reason,
             "createdAt": row.created_at} for row in rows]


@router.post("/publish")
def publish_snapshot(principal: CsrfPrincipal, db: Db) -> dict[str, object]:
    AuthService.require(principal, "snapshot.publish")
    return PublicationService(db).rebuild(principal)
