"""Generate the browser-safe media projection consumed by the Nuxt app."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "content" / "media-assets"
OUTPUT_PATH = ROOT / "apps" / "web" / "app" / "generated" / "media-assets.json"
CONTENT_OUTPUT_PATH = ROOT / "apps" / "web" / "app" / "generated" / "content.json"
PUBLIC_DIR = ROOT / "apps" / "web" / "public"
PUBLIC_FIELDS = ("id", "altText", "focalPoint", "variants")


def read_collection(name: str) -> list[dict[str, object]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((ROOT / "content" / name).glob("*.json"))
    ]


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, newline="\n"
    ) as temporary_file:
        json.dump(value, temporary_file, ensure_ascii=False, indent=2)
        temporary_file.write("\n")
        temporary_path = Path(temporary_file.name)
    os.replace(temporary_path, path)


def public_content_projection() -> dict[str, object]:
    published_only = os.environ.get("MCALBUM_PUBLISHED_ONLY") == "1"
    players = [item for item in read_collection("players") if item.get("status") != "private"]
    public_player_ids = {str(item["id"]) for item in players}

    photos = deepcopy(read_collection("photos"))
    if published_only:
        photos = [item for item in photos if item.get("status") == "published"]
    for photo in photos:
        photo["playerIds"] = [item for item in photo.get("playerIds", []) if item in public_player_ids]
        if photo.get("photographerId") not in public_player_ids:
            photo["photographerId"] = None
        photo["comments"] = [
            comment
            for comment in photo.get("comments", [])
            if comment.get("status") == "published"
            and comment.get("authorPlayerId") in public_player_ids
        ]

    stories = deepcopy(read_collection("stories"))
    if published_only:
        stories = [item for item in stories if item.get("status") == "published"]
    for story in stories:
        story["playerIds"] = [item for item in story.get("playerIds", []) if item in public_player_ids]
        story["sections"] = [
            section
            for section in story.get("sections", [])
            if section.get("type") != "player-quote"
            or section.get("playerId") in public_player_ids
        ]

    return {
        "site": json.loads((ROOT / "content" / "site.json").read_text(encoding="utf-8")),
        "photos": photos,
        "stories": stories,
        "players": players,
    }


def entity_ids(collection: str) -> list[str]:
    return [path.stem for path in sorted((ROOT / "content" / collection).glob("*.json"))]


def write_discovery_files() -> None:
    site_url = os.environ.get("NUXT_PUBLIC_SITE_URL", "http://localhost:3000").rstrip("/")
    paths = ["/", "/album", "/stories", "/players"]
    paths += [f"/photos/{quote(item)}" for item in entity_ids("photos")]
    paths += [f"/stories/{quote(item)}" for item in entity_ids("stories")]
    paths += [f"/players/{quote(item)}" for item in entity_ids("players")]
    urls = "\n".join(f"  <url><loc>{site_url}{path}</loc></url>" for path in paths)
    sitemap = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n'
    robots = f"User-agent: *\nAllow: /\nSitemap: {site_url}/sitemap.xml\n"
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    (PUBLIC_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8", newline="\n")
    (PUBLIC_DIR / "robots.txt").write_text(robots, encoding="utf-8", newline="\n")


def main() -> None:
    public_assets = []
    for source_path in sorted(SOURCE_DIR.glob("*.json")):
        source = json.loads(source_path.read_text(encoding="utf-8"))
        public_assets.append({field: source[field] for field in PUBLIC_FIELDS})

    write_json_atomic(OUTPUT_PATH, public_assets)
    write_json_atomic(CONTENT_OUTPUT_PATH, public_content_projection())
    write_discovery_files()
    print(
        f"已生成 {len(public_assets)} 条公开媒体记录和脱敏内容投影："
        f"{OUTPUT_PATH.relative_to(ROOT)}、{CONTENT_OUTPUT_PATH.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
