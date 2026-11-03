"""账号注册、会话认证和固定能力授权规则。"""

from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, new_secret, secret_hash, utc_now, verify_password
from app.models import AuditLog, Invitation, User, UserPermission, UserSession
from app.repositories.users import UserRepository

ALLOWED_PERMISSIONS = {
    "profile.self.update",
    "photo.create",
    "photo.publish",
    "story.create",
    "story.publish",
    "comment.create",
    "comment.moderate",
}


@dataclass(slots=True)
class Principal:
    """一次已认证请求的账号、会话与能力快照。"""

    user: User
    session: UserSession
    permissions: set[str]

    @property
    def is_admin(self) -> bool:
        return self.user.role == "admin"

    def can(self, permission: str) -> bool:
        return self.is_admin or permission in self.permissions


class AuthService:
    """集中处理密码、邀请、会话与权限变更，避免路由持有安全规则。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.settings = get_settings()

    def authenticate(self, username: str, password: str) -> User:
        user = self.users.by_username(username.strip().lower())
        if user is None or not user.enabled or not verify_password(user.password_hash, password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码不正确")
        return user

    def create_session(self, user: User) -> tuple[UserSession, str, str]:
        token = new_secret()
        csrf_token = new_secret()
        now = utc_now()
        session = UserSession(
            id=f"ses_{uuid4().hex}",
            user_id=user.id,
            token_hash=secret_hash(token),
            csrf_hash=secret_hash(csrf_token),
            expires_at=now + timedelta(hours=self.settings.session_ttl_hours),
            revoked_at=None,
            created_at=now,
            last_seen_at=now,
        )
        self.db.add(session)
        self.db.commit()
        return session, token, csrf_token

    def principal_from_token(self, token: str) -> Principal:
        session = self.users.session_by_hash(secret_hash(token))
        now = utc_now()
        if session is None or session.revoked_at is not None or session.expires_at <= now:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "登录状态已失效")
        user = self.users.by_id(session.user_id)
        if user is None or not user.enabled:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号不可用")
        session.last_seen_at = now
        self.db.commit()
        return Principal(user=user, session=session, permissions=self.users.permissions(user.id))

    def register(self, username: str, display_name: str, password: str, code: str) -> User:
        now = utc_now()
        invitation = self.db.scalar(
            select(Invitation).where(Invitation.code_hash == secret_hash(code))
        )
        if invitation is None or invitation.used_at is not None or invitation.expires_at <= now:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "邀请码无效或已过期")
        normalized = username.strip().lower()
        if self.users.by_username(normalized) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "用户名已存在")
        user = User(
            id=f"usr_{uuid4().hex}",
            username=normalized,
            display_name=display_name.strip(),
            password_hash=hash_password(password),
            role="user",
            enabled=True,
            player_id=None,
            created_at=now,
            updated_at=now,
        )
        self.db.add(user)
        self.db.flush()
        for permission in invitation.permissions:
            if permission in ALLOWED_PERMISSIONS:
                self.db.add(UserPermission(user_id=user.id, permission=permission))
        invitation.used_by = user.id
        invitation.used_at = now
        self.db.commit()
        return user

    def create_invitation(
        self, principal: Principal, expires_in_hours: int, permissions: list[str]
    ) -> tuple[str, Invitation]:
        self.require_admin(principal)
        invalid = set(permissions) - ALLOWED_PERMISSIONS
        if invalid:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, f"未知权限：{sorted(invalid)}"
            )
        code = new_secret(24)
        now = utc_now()
        invitation = Invitation(
            id=f"inv_{uuid4().hex}",
            code_hash=secret_hash(code),
            permissions=permissions,
            expires_at=now + timedelta(hours=expires_in_hours),
            created_by=principal.user.id,
            used_by=None,
            used_at=None,
            created_at=now,
        )
        self.db.add(invitation)
        self.audit(principal.user.id, "invitation.create", "invitation", invitation.id)
        self.db.commit()
        return code, invitation

    def set_permissions(self, principal: Principal, user: User, permissions: list[str]) -> None:
        self.require_admin(principal)
        invalid = set(permissions) - ALLOWED_PERMISSIONS
        if invalid:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, f"未知权限：{sorted(invalid)}"
            )
        self.db.execute(delete(UserPermission).where(UserPermission.user_id == user.id))
        self.db.add_all(
            UserPermission(user_id=user.id, permission=permission) for permission in permissions
        )
        user.updated_at = utc_now()
        self.audit(
            principal.user.id,
            "permission.update",
            "user",
            user.id,
            {"permissions": permissions},
        )
        self.db.commit()

    def audit(
        self,
        actor_user_id: str,
        action: str,
        target_type: str,
        target_id: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.db.add(
            AuditLog(
                id=f"aud_{uuid4().hex}",
                actor_user_id=actor_user_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                metadata_json=metadata or {},
                created_at=utc_now(),
            )
        )

    @staticmethod
    def require_admin(principal: Principal) -> None:
        if not principal.is_admin:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")

    @staticmethod
    def require(principal: Principal, permission: str) -> None:
        if not principal.can(permission):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "缺少所需功能权限")
