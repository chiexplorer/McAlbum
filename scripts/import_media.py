"""按 McAlbum 存储约定导入原图并生成响应式 WebP 变体。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from PIL import Image, ImageOps, UnidentifiedImageError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STORAGE_ROOT = PROJECT_ROOT / "storage"
CONTENT_ROOT = PROJECT_ROOT / "content"
MEDIA_CONTENT_ROOT = CONTENT_ROOT / "media-assets"
DEFAULT_SOURCE_ROOT = PROJECT_ROOT / "yang" / "files" / "imgs"
DEFAULT_MANIFEST = (
    PROJECT_ROOT / "scripts" / "media-manifests" / "2026-mid-autumn-night.json"
)
BEIJING_TIME_ZONE = "Asia/Shanghai"
MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_TOTAL_PIXELS = 80_000_000
VARIANT_WIDTHS = {
    "placeholder": 48,
    "w480": 480,
    "w960": 960,
    "w1440": 1440,
    "w1920": 1920,
}
FORMAT_INFO = {
    "PNG": ("image/png", "png"),
    "JPEG": ("image/jpeg", "jpg"),
    "WEBP": ("image/webp", "webp"),
}
CAPTURE_PATTERN = re.compile(
    r"^(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})_(?P<time>[0-9]{2}\.[0-9]{2}\.[0-9]{2})(?:_[0-9]+)?$"
)

Image.MAX_IMAGE_PIXELS = MAX_TOTAL_PIXELS


class ImportFailure(RuntimeError):
    """表示某个媒体文件无法安全导入。"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImportFailure(f"无法读取导入清单 {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ImportFailure(f"导入清单顶层必须是对象：{path}")
    return data


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_image(path: Path) -> tuple[str, str, int, int]:
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ImportFailure(f"文件超过 50 MiB 上限：{path.name}")
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image_format = image.format
            width, height = image.size
    except (OSError, UnidentifiedImageError) as exc:
        raise ImportFailure(f"无法识别或图片已损坏：{path.name}") from exc

    if image_format not in FORMAT_INFO:
        raise ImportFailure(f"不支持的图片格式 {image_format!r}：{path.name}")
    if width <= 0 or height <= 0 or width * height > MAX_TOTAL_PIXELS:
        raise ImportFailure(f"图片像素尺寸不安全：{path.name} ({width}x{height})")
    mime_type, extension = FORMAT_INFO[image_format]
    return mime_type, extension, width, height


def parse_captured_at(entry: dict[str, Any], source: Path, time_zone: str) -> str:
    explicit = entry.get("capturedAt")
    if isinstance(explicit, str):
        try:
            parsed = datetime.fromisoformat(explicit)
        except ValueError as exc:
            raise ImportFailure(f"capturedAt 不是合法 ISO 时间：{source.name}") from exc
        if parsed.tzinfo is None:
            raise ImportFailure(f"capturedAt 必须包含 UTC 偏移：{source.name}")
        return parsed.isoformat(timespec="seconds")

    match = CAPTURE_PATTERN.match(source.stem)
    if match is None:
        raise ImportFailure(
            f"无法从文件名推断拍摄时间，请提供 capturedAt：{source.name}"
        )
    local_time = datetime.strptime(
        f"{match.group('date')} {match.group('time').replace('.', ':')}",
        "%Y-%m-%d %H:%M:%S",
    ).replace(tzinfo=ZoneInfo(time_zone))
    return local_time.isoformat(timespec="seconds")


def validate_focal_point(entry: dict[str, Any], source: Path) -> dict[str, float]:
    value = entry.get("focalPoint", {"x": 0.5, "y": 0.5})
    if not isinstance(value, dict):
        raise ImportFailure(f"focalPoint 必须是对象：{source.name}")
    try:
        x = float(value["x"])
        y = float(value["y"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ImportFailure(f"focalPoint 必须包含数字 x/y：{source.name}") from exc
    if not 0 <= x <= 1 or not 0 <= y <= 1:
        raise ImportFailure(f"focalPoint 必须位于 0 到 1：{source.name}")
    return {"x": x, "y": y}


def existing_assets_by_hash() -> dict[str, dict[str, Any]]:
    assets: dict[str, dict[str, Any]] = {}
    if not MEDIA_CONTENT_ROOT.exists():
        return assets
    for path in MEDIA_CONTENT_ROOT.glob("*.json"):
        data = load_json(path)
        digest = data.get("sha256")
        if isinstance(digest, str):
            assets[digest] = data
    return assets


def unique_media_id() -> str:
    while True:
        media_id = f"media-{uuid.uuid4().hex}"
        if not (MEDIA_CONTENT_ROOT / f"{media_id}.json").exists():
            return media_id


def save_webp(
    image: Image.Image, target: Path, width: int, *, placeholder: bool
) -> None:
    target_width = min(width, image.width)
    target_height = max(1, round(image.height * target_width / image.width))
    resized = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
    resized.save(
        target,
        format="WEBP",
        quality=45 if placeholder else 82,
        method=6,
        exif=b"",
        icc_profile=None,
    )


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp-{uuid.uuid4().hex}")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def import_entry(
    entry: dict[str, Any],
    source_root: Path,
    time_zone: str,
    known_hashes: dict[str, dict[str, Any]],
) -> tuple[str, str, bool]:
    source_name = entry.get("source")
    alt_text = entry.get("altText")
    if not isinstance(source_name, str) or not source_name:
        raise ImportFailure("每个导入条目都必须包含 source")
    if not isinstance(alt_text, str) or not 1 <= len(alt_text) <= 240:
        raise ImportFailure(f"altText 必须为 1 到 240 个字符：{source_name}")

    source = (source_root / source_name).resolve()
    try:
        source.relative_to(source_root.resolve())
    except ValueError as exc:
        raise ImportFailure(f"source 越出素材根目录：{source_name}") from exc
    if not source.is_file():
        raise ImportFailure(f"素材文件不存在：{source_name}")

    digest = sha256_file(source)
    existing = known_hashes.get(digest)
    if existing is not None:
        return source_name, str(existing["id"]), False

    mime_type, extension, width, height = inspect_image(source)
    captured_at = parse_captured_at(entry, source, time_zone)
    capture_time = datetime.fromisoformat(captured_at)
    year = f"{capture_time.year:04d}"
    month = f"{capture_time.month:02d}"
    focal_point = validate_focal_point(entry, source)
    media_id = unique_media_id()

    stage_root = STORAGE_ROOT / "temporary" / f"import-{uuid.uuid4().hex}"
    staged_original = stage_root / f"{media_id}.{extension}"
    staged_variants = stage_root / "variants"
    final_original = STORAGE_ROOT / "originals" / year / month / staged_original.name
    final_variant_dir = STORAGE_ROOT / "variants" / year / month / media_id
    metadata_path = MEDIA_CONTENT_ROOT / f"{media_id}.json"

    moved_original = False
    moved_variants = False
    try:
        staged_variants.mkdir(parents=True)
        shutil.copyfile(source, staged_original)

        variants: list[dict[str, Any]] = []
        with Image.open(source) as opened:
            normalized = ImageOps.exif_transpose(opened).convert("RGB")
            for name, target_width in VARIANT_WIDTHS.items():
                staged_variant = staged_variants / f"{name}.webp"
                save_webp(
                    normalized,
                    staged_variant,
                    target_width,
                    placeholder=name == "placeholder",
                )
                with Image.open(staged_variant) as variant_image:
                    variant_width, variant_height = variant_image.size
                variants.append(
                    {
                        "name": name,
                        "storageKey": (
                            Path("variants")
                            / year
                            / month
                            / media_id
                            / staged_variant.name
                        ).as_posix(),
                        "mimeType": "image/webp",
                        "byteSize": staged_variant.stat().st_size,
                        "width": variant_width,
                        "height": variant_height,
                        "sha256": sha256_file(staged_variant),
                    }
                )

        final_original.parent.mkdir(parents=True, exist_ok=True)
        final_variant_dir.parent.mkdir(parents=True, exist_ok=True)
        if (
            final_original.exists()
            or final_variant_dir.exists()
            or metadata_path.exists()
        ):
            raise ImportFailure(f"目标媒体 ID 已存在：{media_id}")

        os.replace(staged_original, final_original)
        moved_original = True
        os.replace(staged_variants, final_variant_dir)
        moved_variants = True

        metadata = {
            "$schema": "../../contracts/json-schema/media-asset.schema.json",
            "id": media_id,
            "originalFilename": source.name,
            "storageKey": (
                Path("originals") / year / month / final_original.name
            ).as_posix(),
            "mimeType": mime_type,
            "extension": extension,
            "byteSize": final_original.stat().st_size,
            "width": width,
            "height": height,
            "sha256": digest,
            "capturedAt": captured_at,
            "timeZone": time_zone,
            "altText": alt_text,
            "focalPoint": focal_point,
            "editorialStatus": "draft",
            "processingStatus": "ready",
            "allowOriginalDownload": False,
            "variants": variants,
            "importedAt": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        atomic_write_json(metadata_path, metadata)
        known_hashes[digest] = metadata
        return source_name, media_id, True
    except Exception:
        if metadata_path.exists():
            metadata_path.unlink()
        if moved_variants and final_variant_dir.exists():
            shutil.rmtree(final_variant_dir)
        if moved_original and final_original.exists():
            final_original.unlink()
        raise
    finally:
        if stage_root.exists():
            shutil.rmtree(stage_root)


def validate_manifest(manifest: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    time_zone = manifest.get("timeZone")
    if time_zone != BEIJING_TIME_ZONE:
        raise ImportFailure(
            f"导入清单时区必须是中国北京对应的 {BEIJING_TIME_ZONE}，当前为 {time_zone!r}"
        )
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ImportFailure("导入清单 entries 必须是非空数组")
    if not all(isinstance(entry, dict) for entry in entries):
        raise ImportFailure("导入清单中的每个 entry 都必须是对象")
    sources = [entry.get("source") for entry in entries]
    if len(sources) != len(set(sources)):
        raise ImportFailure("导入清单包含重复 source")
    return time_zone, entries


def main() -> int:
    args = parse_args()
    try:
        manifest_path = args.manifest.resolve()
        source_root = args.source_root.resolve()
        manifest = load_json(manifest_path)
        time_zone, entries = validate_manifest(manifest)
        known_hashes = existing_assets_by_hash()
        results = [
            import_entry(entry, source_root, time_zone, known_hashes)
            for entry in entries
        ]
    except (ImportFailure, OSError) as exc:
        print(f"媒体导入失败：{exc}", file=sys.stderr)
        return 1

    for source_name, media_id, created in results:
        action = "已导入" if created else "已存在"
        print(f"{action}: {source_name} -> {media_id}")
    created_count = sum(1 for _, _, created in results if created)
    print(f"媒体导入完成：新增 {created_count}，复用 {len(results) - created_count}。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
