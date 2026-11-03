"""将照片标签从 JSON 列迁移到标签主表与关联表。"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "20261101_0005"
down_revision: str | None = "20261101_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tag_id(normalized_name: str) -> str:
    digest = hashlib.sha256(normalized_name.encode("utf-8")).hexdigest()[:32]
    return f"tag-{digest}"


def upgrade() -> None:
    """建立规范化标签结构，迁移既有关系后移除 JSON 列。"""

    op.create_table(
        "tags",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("normalized_name", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("normalized_name", name="uq_tags_normalized_name"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "photo_tags",
        sa.Column(
            "photo_id",
            sa.String(120),
            sa.ForeignKey("photos.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.String(40),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_photo_tags_tag_photo", "photo_tags", ["tag_id", "photo_id"])

    bind = op.get_bind()
    photos = sa.table(
        "photos",
        sa.column("id", sa.String(120)),
        sa.column("tags", sa.JSON()),
    )
    tags_table = sa.table(
        "tags",
        sa.column("id", sa.String(40)),
        sa.column("name", sa.String(64)),
        sa.column("normalized_name", sa.String(64)),
        sa.column("created_at", sa.DateTime()),
    )
    links = sa.table(
        "photo_tags",
        sa.column("photo_id", sa.String(120)),
        sa.column("tag_id", sa.String(40)),
    )
    known: dict[str, str] = {}
    tag_rows: list[dict[str, object]] = []
    link_rows: list[dict[str, str]] = []
    now = datetime.now(UTC).replace(tzinfo=None)
    for photo_id, raw_tags in bind.execute(sa.select(photos.c.id, photos.c.tags)):
        values = json.loads(raw_tags) if isinstance(raw_tags, str) else (raw_tags or [])
        seen: set[str] = set()
        for value in values:
            name = " ".join(str(value).strip().split())
            normalized = name.casefold()
            if not name or normalized in seen:
                continue
            seen.add(normalized)
            tag_id = known.get(normalized)
            if tag_id is None:
                tag_id = _tag_id(normalized)
                known[normalized] = tag_id
                tag_rows.append(
                    {
                        "id": tag_id,
                        "name": name[:64],
                        "normalized_name": normalized[:64],
                        "created_at": now,
                    }
                )
            link_rows.append({"photo_id": photo_id, "tag_id": tag_id})
    if tag_rows:
        bind.execute(sa.insert(tags_table), tag_rows)
    if link_rows:
        bind.execute(sa.insert(links), link_rows)
    op.drop_column("photos", "tags")


def downgrade() -> None:
    """把标签关系恢复为照片 JSON 列。"""

    op.add_column("photos", sa.Column("tags", sa.JSON(), nullable=True))
    bind = op.get_bind()
    photo_ids = [row[0] for row in bind.execute(sa.text("SELECT id FROM photos"))]
    for photo_id in photo_ids:
        names = [
            row[0]
            for row in bind.execute(
                sa.text(
                    "SELECT tags.name FROM tags "
                    "JOIN photo_tags ON photo_tags.tag_id = tags.id "
                    "WHERE photo_tags.photo_id = :photo_id ORDER BY tags.name"
                ),
                {"photo_id": photo_id},
            )
        ]
        bind.execute(
            sa.text("UPDATE photos SET tags = :tags WHERE id = :photo_id"),
            {"tags": json.dumps(names, ensure_ascii=False), "photo_id": photo_id},
        )
    op.alter_column("photos", "tags", existing_type=sa.JSON(), nullable=False)
    op.drop_index("ix_photo_tags_tag_photo", table_name="photo_tags")
    op.drop_table("photo_tags")
    op.drop_table("tags")
