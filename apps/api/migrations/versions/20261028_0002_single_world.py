"""移除多周目模型，将内容统一归入单一服务器世界。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261028_0002"
down_revision: str | None = "20261027_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """删除内容的周目外键与不再使用的周目表。"""

    op.drop_constraint("photos_ibfk_4", "photos", type_="foreignkey")
    op.drop_constraint("stories_ibfk_4", "stories", type_="foreignkey")
    op.drop_constraint("timeline_events_ibfk_3", "timeline_events", type_="foreignkey")
    op.drop_column("photos", "season_id")
    op.drop_column("stories", "season_id")
    op.drop_column("timeline_events", "season_id")
    op.drop_table("seasons")


def downgrade() -> None:
    """恢复兼容旧版的单条默认周目及内容关联。"""

    op.create_table(
        "seasons",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.Date(), nullable=False),
        sa.Column("world_day", sa.BigInteger()),
        sa.Column("minecraft_version", sa.String(80), nullable=False),
        sa.Column("fabric_version", sa.String(80), nullable=False),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.execute(
        sa.text(
            "INSERT INTO seasons "
            "(id, name, status, started_at, world_day, minecraft_version, fabric_version) "
            "VALUES ('season-1', '默认周目', 'active', '2026-10-25', NULL, '待确认', '待确认')"
        )
    )
    for table_name in ("photos", "stories", "timeline_events"):
        op.add_column(table_name, sa.Column("season_id", sa.String(100), nullable=True))
        op.execute(sa.text(f"UPDATE {table_name} SET season_id = 'season-1'"))
        op.alter_column(table_name, "season_id", existing_type=sa.String(100), nullable=False)

    op.create_foreign_key("photos_ibfk_4", "photos", "seasons", ["season_id"], ["id"])
    op.create_foreign_key("stories_ibfk_4", "stories", "seasons", ["season_id"], ["id"])
    op.create_foreign_key(
        "timeline_events_ibfk_3", "timeline_events", "seasons", ["season_id"], ["id"]
    )
