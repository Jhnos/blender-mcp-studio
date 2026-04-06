"""SQLiteSessionStore — persistent session storage using SQLite + aiosqlite.

Serializes Session (Pydantic model) to/from JSON. Sessions survive API restarts.
Database file path: data/sessions.db (configurable via constructor).

Thread-safe: each async call opens a short-lived connection via aiosqlite context manager.
"""

from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite

from src.core.domain.session import Session
from src.core.ports.session_store_port import SessionStorePort

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path("data") / "sessions.db"
_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
)
"""


class SQLiteSessionStore(SessionStorePort):
    """Async SQLite-backed session store. Auto-creates the database and table."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db = db_path or _DEFAULT_DB

    async def _ensure_db(self) -> None:
        self._db.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._db) as conn:
            await conn.execute(_CREATE_TABLE)
            await conn.commit()

    async def get(self, session_id: str) -> Session | None:
        await self._ensure_db()
        async with aiosqlite.connect(self._db) as conn, conn.execute(
            "SELECT data FROM sessions WHERE id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            try:
                return Session.model_validate_json(row[0])
            except Exception as e:
                logger.error("Failed to deserialize session %s: %s", session_id, e)
                return None

    async def save(self, session: Session) -> None:
        await self._ensure_db()
        data = session.model_dump_json()
        async with aiosqlite.connect(self._db) as conn:
            await conn.execute(
                """
                INSERT INTO sessions (id, data) VALUES (?, ?)
                ON CONFLICT(id) DO UPDATE SET data = excluded.data,
                    updated_at = datetime('now')
                """,
                (session.id, data),
            )
            await conn.commit()

    async def delete(self, session_id: str) -> None:
        await self._ensure_db()
        async with aiosqlite.connect(self._db) as conn:
            await conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await conn.commit()

    async def create(self) -> Session:
        session = Session()
        await self.save(session)
        return session
