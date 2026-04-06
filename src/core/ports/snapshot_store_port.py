"""SnapshotStorePort — abstract interface for scene snapshot persistence.

ISP: this port is narrow — only snapshot CRUD. Adapters are free to use
SQLite, filesystem, or any other backend.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SceneSnapshot:
    """Immutable value object representing one saved scene state."""

    id: str
    label: str                    # human-readable name (e.g. "After ears")
    blend_path: str               # absolute path to the .blend file
    thumbnail_b64: str            # base64-encoded PNG thumbnail (may be empty)
    created_at: str               # ISO 8601 UTC timestamp
    session_id: str = ""          # optional — links snapshot to a chat session


@dataclass(frozen=True)
class SnapshotList:
    snapshots: tuple[SceneSnapshot, ...] = field(default_factory=tuple)

    def __len__(self) -> int:
        return len(self.snapshots)


class SnapshotStorePort(ABC):
    """Port for storing and restoring Blender scene snapshots."""

    @abstractmethod
    async def save(self, snapshot: SceneSnapshot) -> None:
        """Persist a snapshot record."""

    @abstractmethod
    async def list_all(self) -> SnapshotList:
        """Return all snapshots ordered by creation time (newest first)."""

    @abstractmethod
    async def get(self, snapshot_id: str) -> SceneSnapshot | None:
        """Return a single snapshot by ID, or None if not found."""

    @abstractmethod
    async def delete(self, snapshot_id: str) -> None:
        """Remove a snapshot record (does NOT delete the .blend file)."""
