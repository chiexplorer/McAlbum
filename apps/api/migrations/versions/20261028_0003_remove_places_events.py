"""移除暂不维护的地点与事件领域。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261028_0003"
down_revision: str | None = "20261028_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """删除地点、事件及其全部关联结构。"""

    for table_name in (
        "photo_events",
        "story_events",
        "story_places",
        "event_places",
        "event_players",
        "player_places",
    ):
        op.drop_table(table_name)
    op.drop_constraint("photos_ibfk_6", "photos", type_="foreignkey")
    op.drop_column("photos", "place_id")
    op.drop_table("timeline_events")
    op.drop_table("places")
    op.execute(sa.text("DELETE FROM user_permissions WHERE permission LIKE 'event.%'"))


def downgrade() -> None:
    """恢复兼容旧版的地点、事件表和关联列。"""

    op.create_table(
        "places",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("dimension", sa.String(30), nullable=False),
        sa.Column("coordinates_public", sa.Boolean(), nullable=False),
        sa.Column("coordinates", sa.JSON()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("is_mock", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.add_column("photos", sa.Column("place_id", sa.String(100)))
    op.create_foreign_key("photos_ibfk_6", "photos", "places", ["place_id"], ["id"])
    op.create_table(
        "timeline_events",
        sa.Column("id", sa.String(120), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("world_day", sa.BigInteger()),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("story_id", sa.String(120), sa.ForeignKey("stories.id")),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("author_user_id", sa.String(40), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("published_at", sa.DateTime()),
        sa.Column("published_by", sa.String(40), sa.ForeignKey("users.id")),
        sa.Column("rejection_reason", sa.String(500)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    relation_tables = (
        ("photo_events", "photo_id", "photos", "event_id", "timeline_events"),
        ("story_events", "story_id", "stories", "event_id", "timeline_events"),
        ("story_places", "story_id", "stories", "place_id", "places"),
        ("event_places", "event_id", "timeline_events", "place_id", "places"),
        ("event_players", "event_id", "timeline_events", "player_id", "players"),
        ("player_places", "player_id", "players", "place_id", "places"),
    )
    lengths = {
        "photo_id": 120,
        "story_id": 120,
        "event_id": 120,
        "player_id": 100,
        "place_id": 100,
    }
    for table, left, left_target, right, right_target in relation_tables:
        op.create_table(
            table,
            sa.Column(
                left,
                sa.String(lengths[left]),
                sa.ForeignKey(f"{left_target}.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                right,
                sa.String(lengths[right]),
                sa.ForeignKey(f"{right_target}.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
