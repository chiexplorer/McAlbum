"""以固定角色权限和账号状态替代邀请码及逐用户权限。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261105_0006"
down_revision: str | None = "20261101_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSIONS = (
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
    ("user.review", "审核注册申请", "账号管理", "通过或拒绝注册申请"),
    ("user.role.assign", "分配用户角色", "账号管理", "为账号分配固定角色"),
    ("user.ban", "封禁或解封账号", "账号管理", "变更账号封禁状态"),
    ("role.permissions.manage", "管理角色权限", "角色管理", "调整固定角色的能力集合"),
    ("audit.read", "查看审计记录", "系统管理", "查看重要管理操作记录"),
    ("snapshot.publish", "生成归档快照", "系统管理", "同步并生成静态归档快照"),
)


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("name_zh", sa.String(40), nullable=False),
        sa.Column("description", sa.String(240), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.true()),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_table(
        "permissions",
        sa.Column("code", sa.String(64), primary_key=True),
        sa.Column("name_zh", sa.String(80), nullable=False),
        sa.Column("group_name", sa.String(40), nullable=False),
        sa.Column("description", sa.String(240), nullable=False),
        sa.Column("sort_order", sa.BigInteger(), nullable=False),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_table(
        "role_permissions",
        sa.Column(
            "role_id", sa.String(40), sa.ForeignKey("roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "permission_code", sa.String(64),
            sa.ForeignKey("permissions.code", ondelete="CASCADE"), primary_key=True,
        ),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    roles = sa.table("roles", sa.column("id"), sa.column("code"), sa.column("name_zh"),
                     sa.column("description"), sa.column("is_system"))
    permissions = sa.table("permissions", sa.column("code"), sa.column("name_zh"),
                           sa.column("group_name"), sa.column("description"),
                           sa.column("sort_order"))
    role_permissions = sa.table("role_permissions", sa.column("role_id"),
                                sa.column("permission_code"))
    op.bulk_insert(roles, [
        {"id": "role-admin", "code": "admin", "name_zh": "管理员",
         "description": "管理账号、角色和全部内容", "is_system": True},
        {"id": "role-user", "code": "user", "name_zh": "普通用户",
         "description": "维护并发布自己的内容", "is_system": True},
    ])
    op.bulk_insert(permissions, [
        {"code": code, "name_zh": name, "group_name": group,
         "description": description, "sort_order": index}
        for index, (code, name, group, description) in enumerate(PERMISSIONS, start=1)
    ])
    user_permissions = {
        code for code, *_ in PERMISSIONS
        if not code.endswith(".any")
        and not code.startswith(("user.", "role.", "audit."))
        and code != "snapshot.publish"
    }
    op.bulk_insert(role_permissions, [
        *({"role_id": "role-admin", "permission_code": code} for code, *_ in PERMISSIONS),
        *({"role_id": "role-user", "permission_code": code} for code in user_permissions),
    ])

    op.add_column("users", sa.Column("role_id", sa.String(40), nullable=True))
    op.add_column("users", sa.Column("status", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("minecraft_name", sa.String(16), nullable=True))
    op.add_column("users", sa.Column("application_reason", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("review_reason", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("reviewed_by", sa.String(40), nullable=True))
    op.add_column("users", sa.Column("banned_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("banned_by", sa.String(40), nullable=True))
    op.add_column("users", sa.Column("ban_reason", sa.String(500), nullable=True))
    op.execute("UPDATE users SET role_id = IF(role = 'admin', 'role-admin', 'role-user')")
    op.execute("UPDATE users SET status = IF(enabled = 1, 'active', 'banned')")
    op.execute("UPDATE users SET application_reason = ''")
    op.alter_column("users", "role_id", nullable=False, existing_type=sa.String(40))
    op.alter_column("users", "status", nullable=False, existing_type=sa.String(20))
    op.alter_column("users", "application_reason", nullable=False, existing_type=sa.Text())
    op.create_unique_constraint("uq_users_minecraft_name", "users", ["minecraft_name"])
    op.create_foreign_key("fk_users_role_id", "users", "roles", ["role_id"], ["id"])
    op.create_foreign_key("fk_users_reviewed_by", "users", "users", ["reviewed_by"], ["id"])
    op.create_foreign_key("fk_users_banned_by", "users", "users", ["banned_by"], ["id"])

    op.add_column("comments", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.add_column("comments", sa.Column("deleted_by", sa.String(40), nullable=True))
    op.alter_column("comments", "hidden_reason", new_column_name="deletion_reason",
                    existing_type=sa.String(500), nullable=True)
    op.create_foreign_key("fk_comments_deleted_by", "comments", "users", ["deleted_by"], ["id"])
    op.execute(
        "UPDATE comments SET status = 'deleted', deleted_at = updated_at "
        "WHERE status = 'hidden'"
    )
    op.execute("UPDATE photos SET status = 'draft' WHERE status = 'pending'")
    op.execute("UPDATE stories SET status = 'draft' WHERE status = 'pending'")

    op.drop_table("user_permissions")
    op.drop_table("invitations")
    op.drop_column("users", "role")
    op.drop_column("users", "enabled")


def downgrade() -> None:
    op.execute("UPDATE comments SET status = 'hidden' WHERE status = 'deleted'")
    op.add_column("users", sa.Column("role", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("enabled", sa.Boolean(), nullable=True))
    op.execute("UPDATE users JOIN roles ON users.role_id = roles.id SET users.role = roles.code")
    op.execute("UPDATE users SET enabled = IF(status = 'active', 1, 0)")
    op.alter_column("users", "role", nullable=False, existing_type=sa.String(20))
    op.alter_column("users", "enabled", nullable=False, existing_type=sa.Boolean())

    op.create_table(
        "invitations",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("code_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(40), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("used_by", sa.String(40), sa.ForeignKey("users.id")),
        sa.Column("used_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "user_permissions",
        sa.Column(
            "user_id", sa.String(40), sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("permission", sa.String(80), primary_key=True),
    )
    op.drop_constraint("fk_comments_deleted_by", "comments", type_="foreignkey")
    op.alter_column("comments", "deletion_reason", new_column_name="hidden_reason",
                    existing_type=sa.String(500), nullable=True)
    op.drop_column("comments", "deleted_by")
    op.drop_column("comments", "deleted_at")
    op.drop_constraint("fk_users_banned_by", "users", type_="foreignkey")
    op.drop_constraint("fk_users_reviewed_by", "users", type_="foreignkey")
    op.drop_constraint("fk_users_role_id", "users", type_="foreignkey")
    op.drop_constraint("uq_users_minecraft_name", "users", type_="unique")
    for column in ("ban_reason", "banned_by", "banned_at", "reviewed_by", "reviewed_at",
                   "review_reason", "application_reason", "minecraft_name", "status", "role_id"):
        op.drop_column("users", column)
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
