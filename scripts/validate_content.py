"""校验 McAlbum JSON 内容、实体引用和媒体文件完整性。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTENT_ROOT = PROJECT_ROOT / "content"
CONTRACT_ROOT = PROJECT_ROOT / "contracts" / "json-schema"
STORAGE_ROOT = PROJECT_ROOT / "storage"
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COLLECTIONS = (
    "media-assets",
    "photos",
    "stories",
    "players",
)

SCHEMA_FILES: dict[str, str] = {
    "site": "site.schema.json",
    "media-assets": "media-asset.schema.json",
    "photos": "photo.schema.json",
    "stories": "story.schema.json",
    "players": "player.schema.json",
}

REFERENCE_FIELDS: dict[str, str] = {
    "assetId": "media-assets",
    "assetIds": "media-assets",
    "coverAssetId": "media-assets",
    "avatarAssetId": "media-assets",
    "photographerId": "players",
    "playerId": "players",
    "playerIds": "players",
    "authorPlayerId": "players",
    "photoIds": "photos",
    "storyId": "stories",
    "storyIds": "stories",
    "workIds": "stories",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release",
        action="store_true",
        help="额外阻止 Mock 或尚未核实的媒体进入发布快照",
    )
    return parser.parse_args()


def load_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    """读取一个 JSON 对象，并把解析错误追加到 errors。"""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.relative_to(PROJECT_ROOT)}: 无法读取 JSON：{exc}")
        return None

    if not isinstance(data, dict):
        errors.append(f"{path.relative_to(PROJECT_ROOT)}: 顶层必须是 JSON 对象")
        return None
    return data


def load_validators(errors: list[str]) -> dict[str, Draft202012Validator]:
    """加载并自检所有 JSON Schema。"""

    validators: dict[str, Draft202012Validator] = {}
    for collection, filename in SCHEMA_FILES.items():
        schema_path = CONTRACT_ROOT / filename
        schema = load_json(schema_path, errors)
        if schema is None:
            continue
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            errors.append(
                f"{schema_path.relative_to(PROJECT_ROOT)}: Schema 无效：{exc.message}"
            )
            continue
        validators[collection] = Draft202012Validator(
            schema, format_checker=FormatChecker()
        )
    return validators


def schema_key_for(path: Path) -> str | None:
    relative = path.relative_to(CONTENT_ROOT)
    if relative == Path("site.json"):
        return "site"
    return path.parent.name if path.parent.name in COLLECTIONS else None


def format_json_path(parts: Any) -> str:
    return "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}" for part in parts
    )


def validate_schema(
    path: Path,
    data: dict[str, Any],
    validators: dict[str, Draft202012Validator],
    errors: list[str],
) -> None:
    key = schema_key_for(path)
    if key is None:
        errors.append(f"{path.relative_to(PROJECT_ROOT)}: 无法确定对应的 JSON Schema")
        return
    validator = validators.get(key)
    if validator is None:
        errors.append(f"{path.relative_to(PROJECT_ROOT)}: 缺少 {key} 的 JSON Schema")
        return

    for error in sorted(
        validator.iter_errors(data),
        key=lambda item: tuple(map(str, item.absolute_path)),
    ):
        location = format_json_path(error.absolute_path)
        errors.append(f"{path.relative_to(PROJECT_ROOT)}{location}: {error.message}")


def collect_entities(
    validators: dict[str, Draft202012Validator], errors: list[str]
) -> tuple[dict[str, set[str]], list[tuple[Path, dict[str, Any]]]]:
    """收集实体 ID，并检查 Schema、文件名、格式和重复值。"""

    entity_ids = {collection: set() for collection in COLLECTIONS}
    documents: list[tuple[Path, dict[str, Any]]] = []

    for path in sorted(CONTENT_ROOT.rglob("*.json")):
        data = load_json(path, errors)
        if data is None:
            continue
        documents.append((path, data))
        validate_schema(path, data, validators, errors)

        collection = path.parent.name
        if collection not in entity_ids:
            continue

        entity_id = data.get("id")
        relative_path = path.relative_to(PROJECT_ROOT)
        if not isinstance(entity_id, str) or not ID_PATTERN.fullmatch(entity_id):
            errors.append(f"{relative_path}: id 必须使用小写 kebab-case")
            continue
        if path.stem != entity_id:
            errors.append(f"{relative_path}: 文件名必须与 id 一致")
        if entity_id in entity_ids[collection]:
            errors.append(f"{relative_path}: {collection} 中存在重复 id：{entity_id}")
        entity_ids[collection].add(entity_id)

    return entity_ids, documents


def iter_references(data: Any) -> list[tuple[str, str]]:
    """递归提取受支持的单值和数组引用字段。"""

    references: list[tuple[str, str]] = []
    if isinstance(data, dict):
        for key, value in data.items():
            target_collection = REFERENCE_FIELDS.get(key)
            if target_collection and isinstance(value, str):
                references.append((target_collection, value))
            elif target_collection and isinstance(value, list):
                references.extend(
                    (target_collection, item) for item in value if isinstance(item, str)
                )
            references.extend(iter_references(value))
    elif isinstance(data, list):
        for item in data:
            references.extend(iter_references(item))
    return references


def validate_references(
    entity_ids: dict[str, set[str]],
    documents: list[tuple[Path, dict[str, Any]]],
    errors: list[str],
) -> None:
    """确保 JSON 中的实体引用指向已存在的对象。"""

    for path, data in documents:
        for target_collection, target_id in iter_references(data):
            if target_id not in entity_ids[target_collection]:
                relative_path = path.relative_to(PROJECT_ROOT)
                errors.append(
                    f"{relative_path}: 引用不存在的 {target_collection}/{target_id}"
                )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_storage_key(storage_key: str) -> Path | None:
    candidate = (STORAGE_ROOT / storage_key).resolve()
    try:
        candidate.relative_to(STORAGE_ROOT.resolve())
    except ValueError:
        return None
    return candidate


def validate_media_files(
    documents: list[tuple[Path, dict[str, Any]]], errors: list[str]
) -> None:
    """检查媒体资产声明的原图和变体是否存在且与清单一致。"""

    for document_path, data in documents:
        if document_path.parent.name != "media-assets":
            continue

        entries = [
            (
                "原图",
                data.get("storageKey"),
                data.get("byteSize"),
                data.get("sha256"),
            )
        ]
        variant_names: set[str] = set()
        for variant in data.get("variants", []):
            if not isinstance(variant, dict):
                continue
            name = variant.get("name")
            if isinstance(name, str):
                if name in variant_names:
                    errors.append(
                        f"{document_path.relative_to(PROJECT_ROOT)}: 变体名称重复：{name}"
                    )
                variant_names.add(name)
            entries.append(
                (
                    f"变体 {name}",
                    variant.get("storageKey"),
                    variant.get("byteSize"),
                    variant.get("sha256"),
                )
            )

        for label, storage_key, expected_size, expected_hash in entries:
            if not isinstance(storage_key, str):
                continue
            media_path = resolve_storage_key(storage_key)
            if media_path is None:
                errors.append(
                    f"{document_path.relative_to(PROJECT_ROOT)}: {label}路径越出 storage：{storage_key}"
                )
                continue
            if not media_path.is_file():
                errors.append(
                    f"{document_path.relative_to(PROJECT_ROOT)}: {label}文件不存在：{storage_key}"
                )
                continue
            if (
                isinstance(expected_size, int)
                and media_path.stat().st_size != expected_size
            ):
                errors.append(
                    f"{document_path.relative_to(PROJECT_ROOT)}: {label}大小与清单不一致"
                )
            if (
                isinstance(expected_hash, str)
                and sha256_file(media_path) != expected_hash
            ):
                errors.append(
                    f"{document_path.relative_to(PROJECT_ROOT)}: {label}SHA-256 与清单不一致"
                )


def validate_privacy_and_release(
    documents: list[tuple[Path, dict[str, Any]]], release: bool, errors: list[str]
) -> None:
    for path, data in documents:
        relative_path = path.relative_to(PROJECT_ROOT)
        if not release:
            continue
        if data.get("isMock") is True:
            errors.append(f"{relative_path}: Mock 内容不能进入发布快照")
        if (
            path.parent.name in {"photos", "stories"}
            and data.get("status") != "published"
        ):
            errors.append(f"{relative_path}: 内容状态不是 published，不能进入发布快照")
        if (
            path.parent.name == "media-assets"
            and data.get("editorialStatus") != "verified"
        ):
            errors.append(f"{relative_path}: 媒体说明尚未核实，不能进入发布快照")


def main() -> int:
    """运行内容校验并返回适合 CI 使用的退出码。"""

    args = parse_args()
    errors: list[str] = []
    validators = load_validators(errors)
    entity_ids, documents = collect_entities(validators, errors)
    validate_references(entity_ids, documents, errors)
    validate_media_files(documents, errors)
    validate_privacy_and_release(documents, args.release, errors)

    if errors:
        print("内容校验失败：")
        for error in errors:
            print(f"- {error}")
        return 1

    mode = "发布" if args.release else "开发"
    print(f"内容校验通过（{mode}模式），共检查 {len(documents)} 个 JSON 文件。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
