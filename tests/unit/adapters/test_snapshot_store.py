"""Tests for SQLiteSnapshotStore and snapshot endpoints."""

from __future__ import annotations

import pytest
import pytest_asyncio

from src.core.ports.snapshot_store_port import SceneSnapshot, SnapshotList, SnapshotStorePort


# ---------------------------------------------------------------------------
# Port contract
# ---------------------------------------------------------------------------

class TestSnapshotStorePortContract:
    def test_is_abstract(self):
        assert hasattr(SnapshotStorePort, "save")
        assert hasattr(SnapshotStorePort, "list_all")
        assert hasattr(SnapshotStorePort, "get")
        assert hasattr(SnapshotStorePort, "delete")

    def test_scene_snapshot_is_immutable(self):
        snap = SceneSnapshot(
            id="s1", label="Test", blend_path="/tmp/t.blend",
            thumbnail_b64="", created_at="2026-01-01T00:00:00Z"
        )
        with pytest.raises((AttributeError, TypeError)):
            snap.label = "mutated"  # type: ignore[misc]

    def test_snapshot_list_len(self):
        snap = SceneSnapshot(
            id="s1", label="A", blend_path="/tmp/a.blend",
            thumbnail_b64="", created_at="2026-01-01T00:00:00Z"
        )
        sl = SnapshotList(snapshots=(snap,))
        assert len(sl) == 1


# ---------------------------------------------------------------------------
# SQLiteSnapshotStore unit tests
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_store(tmp_path):
    from src.adapters.snapshot.sqlite_snapshot_store import SQLiteSnapshotStore
    return SQLiteSnapshotStore(db_path=tmp_path / "test_snapshots.db")


def _make_snap(snap_id: str = "snap-1", label: str = "Test") -> SceneSnapshot:
    return SceneSnapshot(
        id=snap_id,
        label=label,
        blend_path=f"/tmp/{snap_id}.blend",
        thumbnail_b64="abc123",
        created_at="2026-01-01T12:00:00+00:00",
        session_id="sess-1",
    )


@pytest.mark.asyncio
async def test_save_and_get(tmp_store):
    snap = _make_snap()
    await tmp_store.save(snap)
    fetched = await tmp_store.get("snap-1")
    assert fetched is not None
    assert fetched.id == "snap-1"
    assert fetched.label == "Test"
    assert fetched.thumbnail_b64 == "abc123"


@pytest.mark.asyncio
async def test_get_nonexistent_returns_none(tmp_store):
    result = await tmp_store.get("does-not-exist")
    assert result is None


@pytest.mark.asyncio
async def test_list_all_newest_first(tmp_store):
    snap1 = SceneSnapshot(
        id="a", label="A", blend_path="/tmp/a.blend",
        thumbnail_b64="", created_at="2026-01-01T10:00:00+00:00"
    )
    snap2 = SceneSnapshot(
        id="b", label="B", blend_path="/tmp/b.blend",
        thumbnail_b64="", created_at="2026-01-01T11:00:00+00:00"
    )
    await tmp_store.save(snap1)
    await tmp_store.save(snap2)

    result = await tmp_store.list_all()
    assert len(result) == 2
    assert result.snapshots[0].id == "b"  # newer first
    assert result.snapshots[1].id == "a"


@pytest.mark.asyncio
async def test_delete_removes_snapshot(tmp_store):
    snap = _make_snap()
    await tmp_store.save(snap)
    await tmp_store.delete("snap-1")
    result = await tmp_store.get("snap-1")
    assert result is None


@pytest.mark.asyncio
async def test_save_upserts_on_conflict(tmp_store):
    snap = _make_snap(label="Original")
    await tmp_store.save(snap)

    updated = SceneSnapshot(
        id="snap-1",
        label="Updated",
        blend_path="/tmp/snap-1.blend",
        thumbnail_b64="xyz",
        created_at="2026-01-02T00:00:00+00:00",
        session_id="sess-2",
    )
    await tmp_store.save(updated)

    fetched = await tmp_store.get("snap-1")
    assert fetched is not None
    assert fetched.label == "Updated"


@pytest.mark.asyncio
async def test_list_all_empty_db(tmp_store):
    result = await tmp_store.list_all()
    assert len(result) == 0


# ---------------------------------------------------------------------------
# Snapshot API endpoint tests (using TestClient — no real Blender)
# ---------------------------------------------------------------------------

@pytest.fixture
def client_with_mock_store(tmp_path):
    """FastAPI TestClient with a real SQLiteSnapshotStore but mocked Blender."""
    from unittest.mock import AsyncMock, MagicMock
    from fastapi.testclient import TestClient
    from api.main import create_app
    from src.adapters.snapshot.sqlite_snapshot_store import SQLiteSnapshotStore

    app = create_app()
    snapshot_store = SQLiteSnapshotStore(db_path=tmp_path / "api_test.db")

    # Override lifespan app state directly
    mock_blender = MagicMock()
    mock_blender.connect = AsyncMock()
    mock_blender.disconnect = AsyncMock()
    mock_blender.execute = AsyncMock()
    mock_blender.call_tool = AsyncMock()

    with TestClient(app, raise_server_exceptions=True) as client:
        # Inject snapshot store after startup
        app.state.snapshot_store = snapshot_store
        app.state.blender = mock_blender
        yield client, snapshot_store, mock_blender


class TestSnapshotEndpoints:

    def test_list_snapshots_empty(self, client_with_mock_store):
        client, _, _ = client_with_mock_store
        resp = client.get("/api/snapshots")
        assert resp.status_code == 200
        assert resp.json()["snapshots"] == []

    @pytest.mark.asyncio
    async def test_list_snapshots_after_insert(self, client_with_mock_store):
        client, store, _ = client_with_mock_store
        snap = _make_snap("direct-insert", "Direct")
        await store.save(snap)

        resp = client.get("/api/snapshots")
        assert resp.status_code == 200
        snaps = resp.json()["snapshots"]
        assert len(snaps) == 1
        assert snaps[0]["id"] == "direct-insert"

    def test_restore_snapshot_not_found(self, client_with_mock_store):
        client, _, _ = client_with_mock_store
        resp = client.post("/api/snapshot/nonexistent/restore")
        assert resp.status_code == 404

    def test_delete_snapshot_not_found(self, client_with_mock_store):
        client, _, _ = client_with_mock_store
        resp = client.delete("/api/snapshot/nonexistent")
        assert resp.status_code == 404
