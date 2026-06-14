"""灵感助手 SQLite 仓储实现 — 作者：Axelton"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List, Optional

from domain.assist.entities import (
    InspireSession,
    InspireMessage,
    InspirationStrategy,
    SessionStatus,
)
from domain.assist.repository import InspireRepository
from infrastructure.persistence.database.connection import DatabaseConnection


class SqliteAssistRepository(InspireRepository):
    """灵感助手 SQLite 仓储实现"""

    def __init__(self, db: DatabaseConnection):
        self._db = db
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """建表迁移（幂等）"""
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS assist_sessions ("
            "  id TEXT PRIMARY KEY,"
            "  novel_id TEXT NOT NULL,"
            "  strategy TEXT NOT NULL,"
            "  status TEXT NOT NULL DEFAULT 'active',"
            "  created_at TEXT NOT NULL,"
            "  updated_at TEXT NOT NULL"
            ")"
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_assist_sessions_novel "
            "ON assist_sessions(novel_id)"
        )
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS assist_messages ("
            "  id TEXT PRIMARY KEY,"
            "  session_id TEXT NOT NULL,"
            "  role TEXT NOT NULL,"
            "  content TEXT NOT NULL,"
            "  field_suggestions TEXT DEFAULT '{}',"
            "  created_at TEXT NOT NULL,"
            "  updated_at TEXT NOT NULL"
            ")"
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_assist_messages_session "
            "ON assist_messages(session_id)"
        )
        self._db.commit()

    # ---- session helpers ----

    def _row_to_session(self, row: dict) -> InspireSession:
        session = InspireSession(
            id=row["id"],
            novel_id=row["novel_id"],
            strategy=InspirationStrategy(row["strategy"]),
            status=SessionStatus(row["status"]),
        )
        session.created_at = datetime.fromisoformat(row["created_at"])
        session.updated_at = datetime.fromisoformat(row["updated_at"])
        return session

    def _message_to_row(self, msg: InspireMessage) -> dict:
        return {
            "id": msg.id,
            "session_id": msg.session_id,
            "role": msg.role,
            "content": msg.content,
            "field_suggestions": json.dumps(msg.field_suggestions or {}, ensure_ascii=False),
            "created_at": msg.created_at.isoformat(),
            "updated_at": msg.updated_at.isoformat(),
        }

    def _row_to_message(self, row: dict) -> InspireMessage:
        msg = InspireMessage(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            field_suggestions=json.loads(row.get("field_suggestions", "{}")),
        )
        msg.created_at = datetime.fromisoformat(row["created_at"])
        msg.updated_at = datetime.fromisoformat(row["updated_at"])
        return msg

    # ---- public API ----

    async def create_session(self, session: InspireSession) -> InspireSession:
        self._db.execute(
            "INSERT INTO assist_sessions (id, novel_id, strategy, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                session.id,
                session.novel_id,
                session.strategy.value,
                session.status.value,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
            ),
        )
        self._db.commit()
        return session

    async def get_session(self, session_id: str) -> Optional[InspireSession]:
        row = self._db.fetch_one(
            "SELECT * FROM assist_sessions WHERE id = ?", (session_id,)
        )
        if row is None:
            return None
        return self._row_to_session(row)

    async def update_session(self, session: InspireSession) -> InspireSession:
        session.updated_at = datetime.now(timezone.utc)
        self._db.execute(
            "UPDATE assist_sessions SET status = ?, updated_at = ? WHERE id = ?",
            (session.status.value, session.updated_at.isoformat(), session.id),
        )
        self._db.commit()
        return session

    async def add_message(self, message: InspireMessage) -> InspireMessage:
        row = self._message_to_row(message)
        self._db.execute(
            "INSERT INTO assist_messages (id, session_id, role, content, field_suggestions, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                row["id"], row["session_id"], row["role"], row["content"],
                row["field_suggestions"], row["created_at"], row["updated_at"],
            ),
        )
        self._db.commit()
        return message

    async def get_messages(self, session_id: str) -> List[InspireMessage]:
        rows = self._db.fetch_all(
            "SELECT * FROM assist_messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        )
        return [self._row_to_message(r) for r in rows]

    async def get_latest_session(self, novel_id: str) -> Optional[InspireSession]:
        row = self._db.fetch_one(
            "SELECT * FROM assist_sessions WHERE novel_id = ? AND status = 'active' "
            "ORDER BY created_at DESC LIMIT 1",
            (novel_id,),
        )
        if row is None:
            return None
        return self._row_to_session(row)
