"""安全媒体导入、变体生成与非原子状态恢复。"""

from __future__ import annotations

import hashlib
import os
import shutil
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import utc_now
from app.models import MediaAsset, MediaVariant
from app.schemas.content import MediaAssetResponse, MediaVariantResponse
from app.services.auth import AuthService, Principal

MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_TOTAL_PIXELS = 80_000_000
VARIANT_WIDTHS = {"placeholder": 48, "w480": 480, "w960": 960, "w1440": 1440, "w1920": 1920}
FORMAT_INFO = {
    "PNG": ("image/png", "png"),
    "JPEG": ("image/jpeg", "jpg"),
    "WEBP": ("image/webp", "webp"),
}


class MediaService:
    """把上传先放入隔离临时区，验证后再原子移动到持久化目录。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.root = get_settings().media_root.resolve()

    def upload(
        self,
        principal: Principal,
        upload: UploadFile,
        alt_text: str,
        captured_at: datetime,
        focal_x: float,
        focal_y: float,
    ) -> MediaAsset:
        AuthService.require(principal, "photo.create")
        if not 1 <= len(alt_text) <= 240:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "替代文本长度必须为 1 到 240")
        if not 0 <= focal_x <= 1 or not 0 <= focal_y <= 1:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "焦点坐标必须位于 0 到 1")
        if captured_at.tzinfo is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "拍摄时间必须包含时区")

        stage = self.root / "temporary" / f"upload-{uuid4().hex}"
        stage.mkdir(parents=True, exist_ok=False)
        incoming = stage / "incoming"
        try:
            digest, byte_size = self._copy_and_hash(upload, incoming)
            duplicate = self.db.scalar(select(MediaAsset).where(MediaAsset.sha256 == digest))
            if duplicate is not None:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail={"message": "该图片已导入", "assetId": duplicate.id},
                )
            mime_type, extension, width, height = self._inspect(incoming)
            asset_id = f"media-{uuid4().hex}"
            now = utc_now()
            utc_captured = captured_at.astimezone(UTC).replace(tzinfo=None)
            asset = MediaAsset(
                id=asset_id,
                owner_user_id=principal.user.id,
                original_filename=Path(upload.filename or "upload").name[:255],
                storage_key=None,
                mime_type=mime_type,
                extension=extension,
                byte_size=byte_size,
                width=width,
                height=height,
                sha256=digest,
                captured_at=utc_captured,
                alt_text=alt_text,
                focal_x=focal_x,
                focal_y=focal_y,
                processing_status="pending",
                editorial_status="draft",
                allow_original_download=False,
                created_at=now,
                updated_at=now,
            )
            self.db.add(asset)
            self.db.commit()

            try:
                self._process(asset, incoming, stage, extension)
            except Exception:
                self.db.rollback()
                asset = self.db.get(MediaAsset, asset.id)
                if asset is None:
                    raise
                asset.processing_status = "failed"
                asset.updated_at = utc_now()
                self.db.commit()
                raise
            return asset
        finally:
            if stage.exists():
                shutil.rmtree(stage)

    @staticmethod
    def _copy_and_hash(upload: UploadFile, target: Path) -> tuple[str, int]:
        digest = hashlib.sha256()
        size = 0
        with target.open("wb") as destination:
            while chunk := upload.file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    raise HTTPException(
                        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "图片不能超过 50 MiB"
                    )
                digest.update(chunk)
                destination.write(chunk)
        return digest.hexdigest(), size

    @staticmethod
    def _inspect(path: Path) -> tuple[str, str, int, int]:
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                image_format = image.format
                width, height = image.size
        except (OSError, UnidentifiedImageError) as exc:
            raise HTTPException(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "文件不是可识别的图片"
            ) from exc
        if image_format not in FORMAT_INFO:
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "仅支持 PNG、JPEG 和 WebP")
        if width <= 0 or height <= 0 or width * height > MAX_TOTAL_PIXELS:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "图片像素尺寸不安全")
        mime_type, extension = FORMAT_INFO[image_format]
        return mime_type, extension, width, height

    def _process(self, asset: MediaAsset, incoming: Path, stage: Path, extension: str) -> None:
        capture = asset.captured_at
        relative_dir = Path(f"{capture.year:04d}") / f"{capture.month:02d}"
        original_key = Path("originals") / relative_dir / f"{asset.id}.{extension}"
        variant_base = Path("variants") / relative_dir / asset.id
        staged_variants = stage / "variants"
        staged_variants.mkdir()
        variants: list[MediaVariant] = []
        with Image.open(incoming) as opened:
            normalized = ImageOps.exif_transpose(opened).convert("RGB")
            for name, requested_width in VARIANT_WIDTHS.items():
                target_width = min(requested_width, normalized.width)
                target_height = max(1, round(normalized.height * target_width / normalized.width))
                output = staged_variants / f"{name}.webp"
                normalized.resize((target_width, target_height), Image.Resampling.LANCZOS).save(
                    output,
                    format="WEBP",
                    quality=45 if name == "placeholder" else 82,
                    method=6,
                    exif=b"",
                    icc_profile=None,
                )
                variants.append(
                    MediaVariant(
                        asset_id=asset.id,
                        name=name,
                        storage_key=(variant_base / output.name).as_posix(),
                        mime_type="image/webp",
                        byte_size=output.stat().st_size,
                        width=target_width,
                        height=target_height,
                        sha256=self._hash_file(output),
                    )
                )

        final_original = self.root / original_key
        final_variants = self.root / variant_base
        final_original.parent.mkdir(parents=True, exist_ok=True)
        final_variants.parent.mkdir(parents=True, exist_ok=True)
        if final_original.exists() or final_variants.exists():
            raise RuntimeError("媒体目标路径已经存在")
        os.replace(incoming, final_original)
        try:
            os.replace(staged_variants, final_variants)
        except Exception:
            final_original.unlink(missing_ok=True)
            raise
        asset.storage_key = original_key.as_posix()
        asset.processing_status = "ready"
        asset.updated_at = utc_now()
        self.db.add_all(variants)
        self.db.commit()

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def response(self, asset: MediaAsset) -> MediaAssetResponse:
        variants = self.db.scalars(
            select(MediaVariant)
            .where(MediaVariant.asset_id == asset.id)
            .order_by(MediaVariant.width)
        )
        return MediaAssetResponse(
            id=asset.id,
            alt_text=asset.alt_text,
            captured_at=asset.captured_at.replace(tzinfo=UTC).astimezone(
                timezone(timedelta(hours=8), "Asia/Shanghai")
            ),
            focal_x=float(asset.focal_x),
            focal_y=float(asset.focal_y),
            width=asset.width,
            height=asset.height,
            processing_status=asset.processing_status,
            editorial_status=asset.editorial_status,
            variants=[
                MediaVariantResponse(
                    name=item.name,
                    url=f"/media/{item.storage_key.removeprefix('variants/')}",
                    width=item.width,
                    height=item.height,
                )
                for item in variants
            ],
        )
