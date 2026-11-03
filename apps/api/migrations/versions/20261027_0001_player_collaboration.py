"""建立玩家协作、媒体与内容管理表。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261027_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def publication_columns() -> list[sa.Column]:
    return [
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("author_user_id", sa.String(40), nullable=False),
        sa.Column("published_at", sa.DateTime()),
        sa.Column("published_by", sa.String(40)),
        sa.Column("rejection_reason", sa.String(500)),
        *timestamps(),
    ]


def upgrade() -> None:
    op.create_table(
        "players",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("bio", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("avatar_asset_id", sa.String(80)),
        sa.Column("joined_at", sa.Date()),
        *timestamps(),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "player_id",
            sa.String(100),
            sa.ForeignKey("players.id", ondelete="SET NULL"),
            unique=True,
        ),
        *timestamps(),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "media_assets",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("owner_user_id", sa.String(40), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(500)),
        sa.Column("mime_type", sa.String(80), nullable=False),
        sa.Column("extension", sa.String(10), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.BigInteger(), nullable=False),
        sa.Column("height", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False, unique=True),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column("alt_text", sa.String(240), nullable=False),
        sa.Column("focal_x", sa.Numeric(5, 4), nullable=False),
        sa.Column("focal_y", sa.Numeric(5, 4), nullable=False),
        sa.Column("processing_status", sa.String(20), nullable=False),
        sa.Column("editorial_status", sa.String(20), nullable=False),
        sa.Column("allow_original_download", sa.Boolean(), nullable=False),
        *timestamps(),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_foreign_key(
        "fk_players_avatar_asset", "players", "media_assets", ["avatar_asset_id"], ["id"]
    )
    op.create_table(
        "media_variants",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "asset_id",
            sa.String(80),
            sa.ForeignKey("media_assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(24), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(80), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.BigInteger(), nullable=False),
        sa.Column("height", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.UniqueConstraint("asset_id", "name"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "user_permissions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id", sa.String(40), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("permission", sa.String(64), nullable=False),
        sa.UniqueConstraint("user_id", "permission"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "user_id", sa.String(40), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True)
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
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
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
        *timestamps(),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "photos",
        sa.Column("id", sa.String(120), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "asset_id", sa.String(80), sa.ForeignKey("media_assets.id"), nullable=False, unique=True
        ),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column("season_id", sa.String(100), sa.ForeignKey("seasons.id"), nullable=False),
        sa.Column("photographer_id", sa.String(100), sa.ForeignKey("players.id")),
        sa.Column("place_id", sa.String(100), sa.ForeignKey("places.id")),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("featured", sa.Boolean(), nullable=False),
        sa.Column("display_variant", sa.String(20), nullable=False),
        *publication_columns(),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["published_by"], ["users.id"]),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "stories",
        sa.Column("id", sa.String(120), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "cover_asset_id", sa.String(80), sa.ForeignKey("media_assets.id"), nullable=False
        ),
        sa.Column("season_id", sa.String(100), sa.ForeignKey("seasons.id"), nullable=False),
        sa.Column("sections", sa.JSON(), nullable=False),
        *publication_columns(),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["published_by"], ["users.id"]),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "timeline_events",
        sa.Column("id", sa.String(120), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("season_id", sa.String(100), sa.ForeignKey("seasons.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("world_day", sa.BigInteger()),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("story_id", sa.String(120), sa.ForeignKey("stories.id")),
        *publication_columns(),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["published_by"], ["users.id"]),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "photo_players",
        sa.Column(
            "photo_id",
            sa.String(120),
            sa.ForeignKey("photos.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("player_id", sa.String(100), sa.ForeignKey("players.id"), primary_key=True),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "photo_events",
        sa.Column(
            "photo_id",
            sa.String(120),
            sa.ForeignKey("photos.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "event_id",
            sa.String(120),
            sa.ForeignKey("timeline_events.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "photo_stories",
        sa.Column(
            "photo_id",
            sa.String(120),
            sa.ForeignKey("photos.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "story_id",
            sa.String(120),
            sa.ForeignKey("stories.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "story_players",
        sa.Column(
            "story_id",
            sa.String(120),
            sa.ForeignKey("stories.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("player_id", sa.String(100), sa.ForeignKey("players.id"), primary_key=True),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "story_places",
        sa.Column(
            "story_id",
            sa.String(120),
            sa.ForeignKey("stories.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("place_id", sa.String(100), sa.ForeignKey("places.id"), primary_key=True),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "story_events",
        sa.Column(
            "story_id",
            sa.String(120),
            sa.ForeignKey("stories.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "event_id",
            sa.String(120),
            sa.ForeignKey("timeline_events.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "event_places",
        sa.Column(
            "event_id",
            sa.String(120),
            sa.ForeignKey("timeline_events.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("place_id", sa.String(100), sa.ForeignKey("places.id"), primary_key=True),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "event_players",
        sa.Column(
            "event_id",
            sa.String(120),
            sa.ForeignKey("timeline_events.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("player_id", sa.String(100), sa.ForeignKey("players.id"), primary_key=True),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "player_places",
        sa.Column(
            "player_id",
            sa.String(100),
            sa.ForeignKey("players.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("place_id", sa.String(100), sa.ForeignKey("places.id"), primary_key=True),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "comments",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "photo_id",
            sa.String(120),
            sa.ForeignKey("photos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("author_user_id", sa.String(40), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("hidden_reason", sa.String(500)),
        *timestamps(),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("actor_user_id", sa.String(40), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("target_type", sa.String(40), nullable=False),
        sa.Column("target_id", sa.String(120), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("comments")
    op.drop_table("player_places")
    op.drop_table("event_players")
    op.drop_table("event_places")
    op.drop_table("story_events")
    op.drop_table("story_places")
    op.drop_table("story_players")
    op.drop_table("photo_stories")
    op.drop_table("photo_events")
    op.drop_table("photo_players")
    op.drop_table("timeline_events")
    op.drop_table("stories")
    op.drop_table("photos")
    op.drop_table("places")
    op.drop_table("seasons")
    op.drop_table("invitations")
    op.drop_index("ix_user_sessions_token_hash", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_table("user_permissions")
    op.drop_table("media_variants")
    op.drop_constraint("fk_players_avatar_asset", "players", type_="foreignkey")
    op.drop_table("media_assets")
    op.drop_table("users")
    op.drop_table("players")
