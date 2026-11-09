"""从环境变量加载应用配置。"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    """应用配置；环境变量统一使用 MCALBUM_ 前缀。"""

    app_name: str = "McAlbum API"
    api_prefix: str = "/api"
    database_url: str = "mysql+pymysql://mcalbum:change-me@127.0.0.1:3306/mcalbum?charset=utf8mb4"
    media_root: Path = PROJECT_ROOT / "storage"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    session_cookie_name: str = "mcalbum_session"
    session_ttl_hours: int = 168
    registration_rate_window_seconds: int = 3600
    media_upload_limit_user: int = Field(default=20, ge=1, le=10000)
    media_upload_limit_admin: int = Field(default=100, ge=1, le=10000)
    cookie_secure: bool = False
    trusted_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    web_project_root: Path = PROJECT_ROOT / "apps" / "web"
    enable_build_trigger: bool = False

    model_config = SettingsConfigDict(
        env_prefix="MCALBUM_",
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / "apps" / "api" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """缓存配置实例，便于依赖注入和测试覆盖。"""

    return Settings()
