"""SQLAlchemy 会话与声明式基类。"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """所有数据库模型的声明式基类。"""


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=1800)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """为单次请求提供数据库会话，并在结束时关闭连接。"""

    with SessionLocal() as session:
        yield session
