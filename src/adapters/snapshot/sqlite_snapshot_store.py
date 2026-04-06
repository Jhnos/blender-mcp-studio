"""SQLiteSnapshotStore — scene snapshot persistence via aiosqlite.

Stores snapshot metadata in SQLite; .blend files saved to data/snapshots/.
Thread-safe: each async call uses a short-lived aiosqlite connection.
"""

from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite

from src.core.ports.snapshot_store_port import SceneSnapshot, SnapshotList, SnapshotStorePort

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path("data") / "snapshots.db"
_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS snapshots (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    blend_path TEXT NOT NULL,
    thumbnail_b64 TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    session_id TEXT NOT NULL DEFAULT ''
)
"""


class SQLiteSnapshotStore(SnapshotStorePort):
    """Async SQLite-backed snapshot store. Auto-creates DB and table on first use."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db = db_path or _DEFAULT_DB

    async def _ensure_db(self) -> None:
        self._db.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._db) as conn:
            await conn.execute(_CREATE_TABLE)
            await conn.commit()

    async def save(self, snapshot: SceneSnapshot) -> None:
        await self._ensure_db()
        async with aiosqlite.connect(self._db) as conn:
            await conn.execute(
                """
                INSERT INTO snapshots (id, label, blend_path, thumbnail_b64, created_at, session_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    label = excluded.label,
                    blend_path = excluded.blend_path,
                    thumbnail_b64 = excluded.thumbnail_b64,
                    created_at = excluded.created_at,
                    session_id = excluded.session_id
                """,
                (
                    snapshot.id,
                    snapshot.label,
                    snapshot.blend_path,
                    snapshot.thumbnail_b64,
                    snapshot.created_at,
                    snapshot.session_id,
                ),
            )
            await conn.commit()

    async def list_all(self) -> SnapshotList:
        await self._ensure_db()
        async with aiosqlite.connect(self._db) as conn, conn.execute(
            "SELECT id, label, blend_path, thumbnail_b64, created_at, session_id "
            "FROM snapshots ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
        return SnapshotList(
            snapshots=tuple(
                SceneSnapshot(
                    id=r[0],
                    label=r[1],
                    blend_path=r[2],
                    thumbnail_b64=r[3],
                    created_at=r[4],
                    session_id=r[5],
                )
                for r in rows
            )
        )

    async def get(self, snapshot_id: str) -> SceneSnapshot | None:
        await self._ensure_db()
        async with aiosqlite.connect(self._db) as conn, conn.execute(
            "SELECT id, label, blend_path, thumbnail_b64, created_at, session_id "
            "FROM snapshots WHERE id = ?",
            (snapshot_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return SceneSnapshot(
            id=row[0],
            label=row[1],
            blend_path=row[2],
            thumbnail_b64=row[3],
            created_at=row[4],
            session_id=row[5],
        )

    async def delete(self, snapshot_id: str) -> None:
        await self._ensure_db()
        async with aiosqlite.connect(self._db) as conn:
            await conn.execute("DELETE FROM snapshots WHERE id = ?", (snapshot_id,))
            await conn.commit()
