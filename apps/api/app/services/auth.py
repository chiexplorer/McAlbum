"""账号注册、会话认证和固定角色授权规则。"""

from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, new_secret, secret_hash, utc_now, verify_password
from app.models import AuditLog, Role, RolePermission, User, UserSession
from app.repositories.users import UserRepository

PERMISSION_DEFINITIONS = (
    ("comment.create", "发表评论", "评论", "在照片下发表评论"),
    ("comment.withdraw.own", "撤回自己的评论", "评论", "撤回本人发表的评论"),
    ("comment.delete.any", "删除任意评论", "评论", "以软删除方式处理评论"),
    ("photo.create", "创建照片", "照片", "上传媒体并创建照片草稿"),
    ("photo.update.own", "修改自己的照片", "照片", "修改本人照片的编目信息"),
    ("photo.publish.own", "发布自己的照片", "照片", "发布本人创建的照片"),
    ("photo.archive.own", "归档自己的照片", "照片", "归档本人已发布的照片"),
    ("photo.delete.any", "删除任意照片", "照片", "以软删除方式处理照片"),
    ("story.create", "创建作品集", "作品集", "创建作品集草稿"),
    ("story.update.own", "修改自己的作品集", "作品集", "修改本人作品集"),
    ("story.publish.own", "发布自己的作品集", "作品集", "发布本人作品集"),
    ("story.archive.own", "归档自己的作品集", "作品集", "归档本人作品集"),
    ("story.delete.any", "删除任意作品集", "作品集", "以软删除方式处理作品集"),
    ("profile.manage.own", "管理自己的玩家档案", "玩家档案", "维护本人关联的玩家档案"),
    ("tag.manage", "管理照片标签", "照片", "新增、重命名和删除照片标签"),
    ("user.review", "审核注册申请", "账号管理", "通过或拒绝注册申请"),
    ("user.role.assign", "分配用户角色", "账号管理", "为账号分配固定角色"),
    ("user.ban", "封禁或解封账号", "账号管理", "变更账号封禁状态"),
    ("role.permissions.manage", "管理角色权限", "角色管理", "调整固定角色的能力集合"),
    ("audit.read", "查看审计记录", "系统管理", "查看重要管理操作记录"),
    ("snapshot.publish", "生成归档快照", "系统管理", "同步并生成静态归档快照"),
)
ALLOWED_PERMISSIONS = {item[0] for item in PERMISSION_DEFINITIONS}
USER_PERMISSIONS = {
    code for code in ALLOWED_PERMISSIONS
    if not code.endswith(".any")
    and not code.startswith(("user.", "role.", "audit."))
    and code not in {"snapshot.publish", "tag.manage"}
}


@dataclass(slots=True)
class Principal:
    """一次已认证请求的账号、角色、会话与能力快照。"""

    user: User
    session: UserSession
    role_code: str
    role_name: str
    permissions: set[str]

    @property
    def is_admin(self) -> bool:
        return self.role_code == "admin"

    def can(self, permission: str) -> bool:
        return permission in self.permissions


class AuthService:
    """集中处理注册审批、会话、角色和权限变更。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.settings = get_settings()

    def authenticate(self, username: str, password: str) -> User:
        user = self.users.by_username(username.strip().lower())
        if user is None or not verify_password(user.password_hash, password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码不正确")
        messages = {
            "pending": "账号申请正在等待管理员审核",
            "rejected": "账号申请未通过审核",
            "banned": "账号已被封禁",
        }
        if user.status != "active":
            raise HTTPException(status.HTTP_403_FORBIDDEN, messages.get(user.status, "账号不可用"))
        return user

    def principal(self, user: User, session: UserSession) -> Principal:
        role = self.users.role(user)
        return Principal(user, session, role.code, role.name_zh, self.users.permissions(user.id))

    def create_session(self, user: User) -> tuple[UserSession, str, str]:
        token, csrf_token, now = new_secret(), new_secret(), utc_now()
        session = UserSession(
            id=f"ses_{uuid4().hex}", user_id=user.id,
            token_hash=secret_hash(token), csrf_hash=secret_hash(csrf_token),
            expires_at=now + timedelta(hours=self.settings.session_ttl_hours),
            revoked_at=None, created_at=now, last_seen_at=now,
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
        if user is None or user.status != "active":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号不可用")
        session.last_seen_at = now
        self.db.commit()
        return self.principal(user, session)

    def register(self, username: str, display_name: str, minecraft_name: str,
                 application_reason: str, password: str) -> User:
        normalized = username.strip().lower()
        if self.users.by_username(normalized) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "用户名已存在")
        if self.users.by_minecraft_name(minecraft_name.strip()) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Minecraft 名称已提交过申请")
        default_role = self.users.role_by_code("user")
        if default_role is None:
            raise RuntimeError("系统缺少普通用户角色")
        now = utc_now()
        user = User(
            id=f"usr_{uuid4().hex}", username=normalized,
            display_name=display_name.strip(), password_hash=hash_password(password),
            role_id=default_role.id, status="pending", minecraft_name=minecraft_name.strip(),
            application_reason=application_reason.strip(), review_reason=None,
            reviewed_at=None, reviewed_by=None, banned_at=None, banned_by=None,
            ban_reason=None, player_id=None, created_at=now, updated_at=now,
        )
        self.db.add(user)
        self.db.commit()
        return user

    def set_role_permissions(self, principal: Principal, role_id: str,
                             permissions: list[str]) -> None:
        self.require(principal, "role.permissions.manage")
        role = self.db.get(Role, role_id)
        if role is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "角色不存在")
        invalid = set(permissions) - ALLOWED_PERMISSIONS
        if invalid:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, f"未知权限：{sorted(invalid)}"
            )
        if role.code == "admin" and "role.permissions.manage" not in permissions:
            raise HTTPException(status.HTTP_409_CONFLICT, "管理员角色必须保留角色权限管理能力")
        self.db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
        self.db.add_all(RolePermission(role_id=role.id, permission_code=p) for p in permissions)
        self.audit(principal.user.id, "role.permissions.update", "role", role.id,
                   {"permissions": permissions})
        self.db.commit()

    def review_user(self, principal: Principal, user: User, action: str,
                    reason: str | None) -> None:
        self.require(principal, "user.review")
        if user.status != "pending":
            raise HTTPException(status.HTTP_409_CONFLICT, "只能审核待处理的申请")
        target = self.users.role_by_code("user")
        if target is None:
            raise RuntimeError("系统缺少固定角色")
        user.role_id = target.id
        user.status = "active" if action == "approve" else "rejected"
        user.review_reason = (reason or "").strip() or None
        user.reviewed_at = user.updated_at = utc_now()
        user.reviewed_by = principal.user.id
        self.audit(principal.user.id, f"user.{action}", "user", user.id,
                   {"reason": user.review_reason})
        self.db.commit()

    def assign_role(self, principal: Principal, user: User, role_id: str) -> None:
        self.require(principal, "user.role.assign")
        role = self.db.get(Role, role_id)
        if role is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "角色不存在")
        if user.status != "active":
            raise HTTPException(status.HTTP_409_CONFLICT, "只能为已启用账号分配角色")
        removing_last_admin = (
            self.users.role(user).code == "admin"
            and role.code != "admin"
            and self._is_last_admin(user)
        )
        if removing_last_admin:
            raise HTTPException(status.HTTP_409_CONFLICT, "不能移除最后一名有效管理员")
        user.role_id, user.updated_at = role.id, utc_now()
        self.audit(principal.user.id, "user.role.assign", "user", user.id, {"role": role.code})
        self.db.commit()

    def set_user_ban(self, principal: Principal, user: User, banned: bool,
                     reason: str | None) -> None:
        self.require(principal, "user.ban")
        if user.id == principal.user.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "不能封禁当前账号")
        if banned and user.status != "active":
            raise HTTPException(status.HTTP_409_CONFLICT, "只能封禁正常使用中的账号")
        if banned and self.users.role(user).code == "admin" and self._is_last_admin(user):
            raise HTTPException(status.HTTP_409_CONFLICT, "不能封禁最后一名有效管理员")
        now = utc_now()
        if banned:
            user.status, user.banned_at, user.banned_by = "banned", now, principal.user.id
            user.ban_reason = (reason or "").strip()
            self.revoke_sessions(user.id)
        else:
            if user.status != "banned":
                raise HTTPException(status.HTTP_409_CONFLICT, "账号当前未被封禁")
            user.status, user.banned_at, user.banned_by = "active", None, None
            user.ban_reason = None
        user.updated_at = now
        self.audit(principal.user.id, "user.ban" if banned else "user.unban", "user", user.id,
                   {"reason": reason})
        self.db.commit()

    def revoke_sessions(self, user_id: str) -> None:
        now = utc_now()
        sessions = self.db.scalars(select(UserSession).where(
            UserSession.user_id == user_id, UserSession.revoked_at.is_(None)
        ))
        for session in sessions:
            session.revoked_at = now

    def _is_last_admin(self, user: User) -> bool:
        admin = self.users.role_by_code("admin")
        if admin is None or user.role_id != admin.id:
            return False
        count = self.db.scalar(select(func.count()).select_from(User).where(
            User.role_id == admin.id, User.status == "active"
        ))
        return (count or 0) <= 1

    def audit(self, actor_user_id: str, action: str, target_type: str, target_id: str,
              metadata: dict[str, object] | None = None) -> None:
        self.db.add(AuditLog(
            id=f"aud_{uuid4().hex}", actor_user_id=actor_user_id, action=action,
            target_type=target_type, target_id=target_id, metadata_json=metadata or {},
            created_at=utc_now(),
        ))

    @staticmethod
    def require_admin(principal: Principal) -> None:
        if not principal.is_admin:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员角色")

    @staticmethod
    def require(principal: Principal, permission: str) -> None:
        if not principal.can(permission):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "缺少所需功能权限")
