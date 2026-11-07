"""校验随 Git 发布的内置作品集及其展示变体。"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTENT_ROOT = PROJECT_ROOT / "content" / "built-in-stories"
PUBLIC_ROOT = PROJECT_ROOT / "apps" / "web" / "public"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    errors: list[str] = []
    packages = sorted(CONTENT_ROOT.glob("*.json"))
    if not packages:
        errors.append("content/built-in-stories 中至少需要一个内置作品集")

    for package_path in packages:
        try:
            package: dict[str, Any] = json.loads(package_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{package_path.relative_to(PROJECT_ROOT)}: JSON 读取失败：{exc}")
            continue

        story = package.get("story")
        assets = package.get("assets")
        if not isinstance(story, dict) or story.get("id") != package.get("id"):
            errors.append(f"{package_path.relative_to(PROJECT_ROOT)}: story.id 与包 id 不一致")
            continue
        if not isinstance(assets, list) or not assets:
            errors.append(f"{package_path.relative_to(PROJECT_ROOT)}: assets 不能为空")
            continue

        asset_ids = {asset.get("id") for asset in assets if isinstance(asset, dict)}
        referenced_ids = {story.get("coverAssetId")}
        for section in story.get("sections", []):
            if not isinstance(section, dict):
                continue
            if isinstance(section.get("assetId"), str):
                referenced_ids.add(section["assetId"])
            referenced_ids.update(
                item for item in section.get("assetIds", []) if isinstance(item, str)
            )
        for missing_id in sorted(referenced_ids - asset_ids):
            errors.append(f"{package_path.relative_to(PROJECT_ROOT)}: 缺少媒体声明 {missing_id}")

        for asset in assets:
            if not isinstance(asset, dict):
                continue
            for variant in asset.get("variants", []):
                if not isinstance(variant, dict):
                    continue
                storage_key = variant.get("storageKey")
                if not isinstance(storage_key, str):
                    continue
                candidate = (PUBLIC_ROOT / storage_key).resolve()
                try:
                    candidate.relative_to(PUBLIC_ROOT.resolve())
                except ValueError:
                    errors.append(f"{package_path.relative_to(PROJECT_ROOT)}: 路径越出 public {storage_key}")
                    continue
                if not candidate.is_file():
                    errors.append(f"{package_path.relative_to(PROJECT_ROOT)}: 文件不存在 {storage_key}")
                    continue
                if candidate.stat().st_size != variant.get("byteSize"):
                    errors.append(f"{package_path.relative_to(PROJECT_ROOT)}: 文件大小不一致 {storage_key}")
                if sha256_file(candidate) != variant.get("sha256"):
                    errors.append(f"{package_path.relative_to(PROJECT_ROOT)}: SHA-256 不一致 {storage_key}")

    if errors:
        print("内置作品集校验失败：")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"内置作品集校验通过，共检查 {len(packages)} 个作品集。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
