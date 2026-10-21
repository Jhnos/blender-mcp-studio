"""SQLiteJobStore - design-run job records in SQLite (same shape as SQLiteSessionStore).

Database file path: config/tools.yaml design_jobs_db (DESIGN_JOBS_DB overrides), passed in by
the runtime; the constructor default is for tests and scripts. Each call opens a
short-lived aiosqlite connection.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

import aiosqlite

from src.core.domain.design_run import JobRecord, JobStatus, StageName
from src.core.ports.job_store_port import JobStorePort

_DEFAULT_DB = Path("data") / "jobs.db"
_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    status TEXT NOT NULL,
    stage TEXT,
    error TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
)
"""
_COLUMNS = "job_id, run_id, status, stage, error, created_at, updated_at"


def _record(row: tuple[Any, ...]) -> JobRecord:
    job_id, run_id, status, stage, error, created_at, updated_at = row
    return JobRecord(
        job_id=job_id,
        run_id=run_id,
        status=JobStatus(status),
        stage=None if stage is None else StageName(stage),
        error=error,
        created_at=created_at,
        updated_at=updated_at,
    )


class SQLiteJobStore(JobStorePort):
    def __init__(self, db_path: Path | None = None) -> None:
        self._db = db_path or _DEFAULT_DB

    async def _ensure_db(self) -> None:
        self._db.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._db) as conn:
            await conn.execute(_CREATE_TABLE)
            await conn.commit()

    async def create(self, run_id: str) -> JobRecord:
        await self._ensure_db()
        now = time.time()
        job_id = uuid.uuid4().hex
        async with aiosqlite.connect(self._db) as conn:
            await conn.execute(
                f"INSERT INTO jobs ({_COLUMNS}) VALUES (?, ?, ?, NULL, NULL, ?, ?)",
                (job_id, run_id, JobStatus.QUEUED.value, now, now),
            )
            await conn.commit()
        return JobRecord(job_id, run_id, JobStatus.QUEUED, None, None, now, now)

    async def update(
        self,
        job_id: str,
        *,
        status: JobStatus,
        stage: StageName | None = None,
        error: str | None = None,
    ) -> JobRecord:
        await self._ensure_db()
        async with aiosqlite.connect(self._db) as conn:
            cursor = await conn.execute(
                "UPDATE jobs SET status = ?, stage = COALESCE(?, stage), error = ?, updated_at = ? WHERE job_id = ?",
                (status.value, None if stage is None else stage.value, error, time.time(), job_id),
            )
            await conn.commit()
            if cursor.rowcount == 0:
                raise KeyError(f"unknown job: {job_id}")
        record = await self.get(job_id)
        assert record is not None  # row was just updated
        return record

    async def list_unfinished(self) -> tuple[JobRecord, ...]:
        await self._ensure_db()
        live = (JobStatus.QUEUED.value, JobStatus.RUNNING.value)
        async with (
            aiosqlite.connect(self._db) as conn,
            conn.execute(
                f"SELECT {_COLUMNS} FROM jobs WHERE status IN (?, ?) ORDER BY created_at", live
            ) as cursor,
        ):
            rows = await cursor.fetchall()
        return tuple(_record(tuple(row)) for row in rows)

    async def get(self, job_id: str) -> JobRecord | None:
        await self._ensure_db()
        async with (
            aiosqlite.connect(self._db) as conn,
            conn.execute(f"SELECT {_COLUMNS} FROM jobs WHERE job_id = ?", (job_id,)) as cursor,
        ):
            row = await cursor.fetchone()
        return None if row is None else _record(tuple(row))
