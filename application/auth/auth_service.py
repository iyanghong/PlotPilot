"""认证服务：登录、注册、JWT Token 签发

作者: Axelton
"""
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Tuple

from domain.auth.entities.user import User, UserRole
from domain.auth.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

# JWT 密钥：优先使用环境变量，否则生成一个会话级随机密钥
_JWT_SECRET = os.environ.get("PLOTPILOT_JWT_SECRET") or os.urandom(32).hex()
_JWT_ALGORITHM = "HS256"
_TOKEN_EXPIRE_HOURS = 24 * 7  # Token 有效期 7 天


def _ensure_bcrypt() -> None:
    """确保 bcrypt 可用"""
    try:
        import bcrypt  # noqa: F401
    except ImportError:
        raise ImportError(
            "bcrypt 未安装，请执行: pip install bcrypt"
        )


def _ensure_pyjwt() -> None:
    """确保 PyJWT 可用"""
    try:
        import jwt  # noqa: F401
    except ImportError:
        raise ImportError(
            "PyJWT 未安装，请执行: pip install PyJWT"
        )


def _hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希"""
    _ensure_bcrypt()
    import bcrypt
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    _ensure_bcrypt()
    import bcrypt
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_token(user: User) -> str:
    """为用户创建 JWT Token"""
    _ensure_pyjwt()
    import jwt
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role.value,
        "iat": now,
        "exp": now + timedelta(hours=_TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """解析 JWT Token，失败返回 None"""
    _ensure_pyjwt()
    import jwt
    try:
        return jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
    except Exception:
        return None


class AuthService:
    """认证服务"""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def login(self, username: str, password: str) -> Tuple[User, str] | None:
        """登录：验证用户名密码，返回 (User, token) 或 None"""
        user = self.user_repository.get_by_username(username)
        if not user:
            return None
        if not _verify_password(password, user.password_hash):
            return None
        token = create_token(user)
        logger.info("用户 %s 登录成功", username)
        return user, token

    def register(
        self,
        username: str,
        password: str,
        role: UserRole = UserRole.USER,
        admin_user: User | None = None,
    ) -> User | None:
        """注册新用户

        Args:
            username: 用户名
            password: 密码
            role: 角色（仅管理员可指定）
            admin_user: 执行注册的管理员用户（None 表示首个用户可为管理员）

        Returns:
            注册成功的 User，失败返回 None
        """
        # 检查用户名是否已存在
        if self.user_repository.exists_by_username(username):
            logger.warning("注册失败：用户名 %s 已存在", username)
            return None

        # 权限检查：仅管理员可创建管理员用户
        if role == UserRole.ADMIN and admin_user and not admin_user.is_admin():
            logger.warning("注册失败：非管理员用户 %s 尝试创建管理员", admin_user.username)
            return None

        # 首个用户自动成为管理员
        if self.user_repository.count() == 0:
            role = UserRole.ADMIN
            logger.info("首个用户注册，自动授予管理员角色")

        user = User(
            id=uuid.uuid4().hex[:16],
            username=username,
            password_hash=_hash_password(password),
            role=role,
        )
        self.user_repository.save(user)
        logger.info("用户 %s 注册成功，角色 %s", username, role.value)
        return user

    def is_first_user(self) -> bool:
        """检查是否尚无任何用户（首个用户自动成为管理员）"""
        return self.user_repository.count() == 0

    def get_user_from_token(self, token: str) -> User | None:
        """从 JWT Token 中恢复 User 对象"""
        payload = decode_token(token)
        if not payload:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        return self.user_repository.get_by_id(user_id)
