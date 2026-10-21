"""SQLiteJobStore round trip."""

from __future__ import annotations

import pytest

from src.adapters.jobs.sqlite_job_store import SQLiteJobStore
from src.core.domain.design_run import JobStatus, StageName


async def test_create_update_get_round_trip(tmp_path):
    store = SQLiteJobStore(tmp_path / "jobs.db")
    created = await store.create("a" * 32)
    assert created.status is JobStatus.QUEUED
    assert created.stage is None and created.error is None

    running = await store.update(created.job_id, status=JobStatus.RUNNING, stage=StageName.GEOMETRY)
    assert running.status is JobStatus.RUNNING and running.stage is StageName.GEOMETRY
    assert running.updated_at >= created.updated_at

    failed = await store.update(created.job_id, status=JobStatus.FAILED, error="boom")
    assert failed.error == "boom" and failed.stage is None

    again = await SQLiteJobStore(tmp_path / "jobs.db").get(created.job_id)  # survives a new store
    assert again == failed
    assert await store.get("missing") is None


async def test_update_unknown_job_raises(tmp_path):
    with pytest.raises(KeyError):
        await SQLiteJobStore(tmp_path / "jobs.db").update("nope", status=JobStatus.DONE)
