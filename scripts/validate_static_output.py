"""校验 Nuxt 静态产物的路由、可访问性、媒体边界与体积预算。"""

from __future__ import annotations

import argparse
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "apps" / "web" / ".output" / "public"
CONTENT = ROOT / "content"
TEXT_SUFFIXES = {".html", ".js", ".json", ".xml", ".txt"}
FORBIDDEN_TOKENS = (
    "storage/originals",
    "storage/temporary",
    "storage/quarantine",
    "yang/files",
    "originalFilename",
    "allowOriginalDownload",
)
MAX_SINGLE_FILE_BYTES = 512 * 1024
MAX_NUXT_BYTES = 1024 * 1024


class PageInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.html_lang: str | None = None
        self.canonical_count = 0
        self.description_count = 0
        self.h1_count = 0
        self.image_errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html":
            self.html_lang = values.get("lang")
        elif tag == "link" and values.get("rel") == "canonical":
            self.canonical_count += 1
        elif tag == "meta" and values.get("name") == "description":
            self.description_count += 1
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "img":
            for attribute in ("alt", "width", "height"):
                if attribute not in values:
                    self.image_errors.append(f"img 缺少 {attribute}")


def collection_ids(name: str) -> list[str]:
    return [path.stem for path in sorted((CONTENT / name).glob("*.json"))]


def route_file(route: str) -> Path:
    return OUTPUT / ("index.html" if route == "/" else f"{route.strip('/')}/index.html")


def expected_routes() -> list[str]:
    routes = ["/", "/album", "/stories", "/players"]
    routes.extend(f"/photos/{item}" for item in collection_ids("photos"))
    routes.extend(f"/stories/{item}" for item in collection_ids("stories"))
    routes.extend(f"/players/{item}" for item in collection_ids("players"))
    return routes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release",
        action="store_true",
        help="额外禁止 localhost 出现在 Canonical、站点地图和 robots 中",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    if not OUTPUT.is_dir():
        print("静态产物不存在，请先运行 npm run generate:web")
        return 1

    routes = expected_routes()
    for route in routes:
        page_path = route_file(route)
        if not page_path.is_file():
            errors.append(f"缺少静态路由：{route}")
            continue
        inspector = PageInspector()
        inspector.feed(page_path.read_text(encoding="utf-8"))
        if inspector.html_lang != "zh-CN":
            errors.append(f"{route}: html lang 不是 zh-CN")
        if inspector.canonical_count != 1:
            errors.append(f"{route}: Canonical 数量应为 1，实际为 {inspector.canonical_count}")
        if inspector.description_count != 1:
            errors.append(f"{route}: description 数量应为 1，实际为 {inspector.description_count}")
        if inspector.h1_count != 1:
            errors.append(f"{route}: h1 数量应为 1，实际为 {inspector.h1_count}")
        errors.extend(f"{route}: {message}" for message in inspector.image_errors)

    for filename in ("404.html", "sitemap.xml", "robots.txt"):
        if not (OUTPUT / filename).is_file():
            errors.append(f"缺少发布文件：{filename}")

    for path in OUTPUT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(OUTPUT)
        if path.stat().st_size > MAX_SINGLE_FILE_BYTES:
            errors.append(f"单文件超过 512 KiB：{relative}")
        if path.suffix.lower() in TEXT_SUFFIXES:
            content = path.read_text(encoding="utf-8", errors="ignore")
            for token in FORBIDDEN_TOKENS:
                if token.lower() in content.lower():
                    errors.append(f"{relative}: 发现不应公开的标识 {token}")
            if (
                args.release
                and path.suffix.lower() in {".html", ".xml", ".txt"}
                and "http://localhost" in content
            ):
                errors.append(f"{relative}: 正式发布地址仍是 localhost")

    media_files = [
        path
        for path in (OUTPUT / "media").rglob("*")
        if path.is_file() and not path.name.startswith(".")
    ]
    invalid_media = [path for path in media_files if path.suffix.lower() != ".webp"]
    errors.extend(f"公开媒体不是 WebP：{path.relative_to(OUTPUT)}" for path in invalid_media)

    nuxt_bytes = sum(path.stat().st_size for path in (OUTPUT / "_nuxt").rglob("*") if path.is_file())
    if nuxt_bytes > MAX_NUXT_BYTES:
        errors.append(f"前端静态资源总量超过 1 MiB：{nuxt_bytes} bytes")

    if errors:
        print("静态产物校验失败：")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        f"静态产物校验通过：{len(routes)} 条内容路由，"
        f"{len(media_files)} 个公开媒体文件，前端资源 {nuxt_bytes} bytes。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
