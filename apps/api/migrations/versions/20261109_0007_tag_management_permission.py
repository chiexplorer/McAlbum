"""增加管理员标签维护权限。"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261109_0007"
down_revision: str | None = "20261105_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO permissions "
        "(code, name_zh, group_name, description, sort_order) VALUES "
        "('tag.manage', '管理照片标签', '照片', '新增、重命名和删除照片标签', 145)"
    )
    op.execute(
        "INSERT INTO role_permissions (role_id, permission_code) "
        "SELECT id, 'tag.manage' FROM roles WHERE code = 'admin'"
    )


def downgrade() -> None:
    op.execute("DELETE FROM role_permissions WHERE permission_code = 'tag.manage'")
    op.execute("DELETE FROM permissions WHERE code = 'tag.manage'")
