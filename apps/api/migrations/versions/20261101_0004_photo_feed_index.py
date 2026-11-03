"""为公开照片时间流增加稳定游标查询索引。"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261101_0004"
down_revision: str | None = "20261028_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """按发布状态、拍摄时间和稳定 ID 支撑倒序游标分页。"""

    op.create_index(
        "ix_photos_public_captured",
        "photos",
        ["status", "captured_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    """移除公开照片时间流索引。"""

    op.drop_index("ix_photos_public_captured", table_name="photos")
