"""密码、令牌和同源请求保护工具。"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

password_hasher = PasswordHasher()


def utc_now() -> datetime:
    """返回去除时区信息的 UTC 时间，匹配 MySQL DATETIME。"""

    return datetime.now(UTC).replace(tzinfo=None)


def hash_password(password: str) -> str:
    """使用 Argon2id 哈希密码。"""

    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """以恒定比较路径验证密码，不向调用方暴露哈希细节。"""

    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def new_secret(bytes_count: int = 32) -> str:
    """生成适合会话、CSRF 或邀请码的不可预测字符串。"""

    return secrets.token_urlsafe(bytes_count)


def secret_hash(value: str) -> str:
    """使用 SHA-256 保存一次性秘密的不可逆摘要。"""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def secrets_equal(left: str, right: str) -> bool:
    """恒定时间比较两个摘要字符串。"""

    return hmac.compare_digest(left, right)
