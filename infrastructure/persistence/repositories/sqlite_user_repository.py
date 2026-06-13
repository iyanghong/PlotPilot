"""SQLite 用户仓储实现

作者: Axelton
"""
import logging
from typing import Optional
from domain.auth.entities.user import User, UserRole
from domain.auth.repositories.user_repository import UserRepository
from infrastructure.persistence.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class SqliteUserRepository(UserRepository):
    """SQLite 用户仓储实现"""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    def save(self, user: User) -> None:
        """保存用户（新增或更新）"""
        sql = """
            INSERT INTO users (id, username, password_hash, role, created_at, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                username = excluded.username,
                password_hash = excluded.password_hash,
                role = excluded.role,
                updated_at = datetime('now')
        """
        self.db.execute(sql, (
            user.id,
            user.username,
            user.password_hash,
            user.role.value,
        ))
        self.db.get_connection().commit()

    def get_by_id(self, user_id: str) -> Optional[User]:
        """根据 ID 获取用户"""
        sql = "SELECT * FROM users WHERE id = ?"
        row = self.db.fetch_one(sql, (user_id,))
        if not row:
            return None
        return self._row_to_user(row)

    def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        sql = "SELECT * FROM users WHERE username = ?"
        row = self.db.fetch_one(sql, (username,))
        if not row:
            return None
        return self._row_to_user(row)

    def exists_by_username(self, username: str) -> bool:
        """检查用户名是否已存在"""
        sql = "SELECT 1 FROM users WHERE username = ? LIMIT 1"
        row = self.db.fetch_one(sql, (username,))
        return row is not None

    def count(self) -> int:
        """获取用户总数"""
        sql = "SELECT COUNT(*) as cnt FROM users"
        row = self.db.fetch_one(sql)
        return row["cnt"] if row else 0

    @staticmethod
    def _row_to_user(row: dict) -> User:
        """将数据库行转换为 User 实体"""
        raw_role = row.get("role", "user")
        try:
            role = UserRole(raw_role)
        except ValueError:
            role = UserRole.USER
        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            role=role,
        )
