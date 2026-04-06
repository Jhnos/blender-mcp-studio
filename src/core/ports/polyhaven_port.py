"""PolyHavenPort — abstract interface for the Poly Haven public asset API.

ISP: narrow port, only what the use cases need:
  - search assets by query / type
  - get download URL for a specific resolution
  - apply HDRI/texture in Blender via execute_code

Adapters may add caching; the port does not.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PolyHavenAsset:
    """Minimal asset record from the Poly Haven catalogue."""

    id: str                          # e.g. "abandoned_church"
    name: str                        # human-readable e.g. "Abandoned Church"
    asset_type: str                  # "hdri" | "texture" | "model"
    categories: tuple[str, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    thumbnail_url: str = ""
    download_count: int = 0


@dataclass(frozen=True)
class PolyHavenFile:
    """Download URL for a resolved resolution/format of an asset."""

    asset_id: str
    resolution: str    # e.g. "1k", "2k", "4k"
    file_format: str   # e.g. "hdr", "exr"
    url: str
    size_bytes: int = 0


class PolyHavenPort(ABC):
    """Port for browsing and downloading Poly Haven assets."""

    @abstractmethod
    async def search(
        self,
        query: str = "",
        asset_type: str = "hdri",
        limit: int = 20,
    ) -> list[PolyHavenAsset]:
        """Return assets matching the query (substring match on name/tags)."""

    @abstractmethod
    async def get_download_url(
        self,
        asset_id: str,
        resolution: str = "1k",
        file_format: str = "hdr",
    ) -> PolyHavenFile | None:
        """Resolve a download URL for the given asset at requested resolution."""
