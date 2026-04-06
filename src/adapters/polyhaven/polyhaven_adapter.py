"""PolyHavenAdapter — fetches assets and download URLs from api.polyhaven.com.

Uses httpx async client with an in-memory TTL cache to avoid hammering the API.
Implements PolyHavenPort (DIP: zero concrete knowledge in routers or use cases).

Asset types:
  type=0  → HDRI
  type=1  → Texture
  type=2  → 3D Model
"""

from __future__ import annotations

import logging
import time
from functools import cached_property

import httpx

from src.core.ports.polyhaven_port import PolyHavenAsset, PolyHavenFile, PolyHavenPort

logger = logging.getLogger(__name__)

_TYPE_MAP = {"hdri": 0, "texture": 1, "model": 2}
_BASE = "https://api.polyhaven.com"
_CACHE_TTL = 300  # seconds


class PolyHavenAdapter(PolyHavenPort):
    """Async HTTP adapter for the Poly Haven public API (no auth required)."""

    def __init__(self, timeout: float = 15.0) -> None:
        self._timeout = timeout
        self._assets_cache: dict[str, tuple[float, list[PolyHavenAsset]]] = {}
        self._files_cache: dict[str, tuple[float, dict]] = {}

    @cached_property
    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self._timeout,
            headers={"User-Agent": "BlenderMCPStudio/1.0"},
        )

    async def search(
        self,
        query: str = "",
        asset_type: str = "hdri",
        limit: int = 20,
    ) -> list[PolyHavenAsset]:
        cache_key = asset_type
        cached = self._assets_cache.get(cache_key)
        if cached and (time.monotonic() - cached[0]) < _CACHE_TTL:
            assets = cached[1]
        else:
            assets = await self._fetch_all(asset_type)
            self._assets_cache[cache_key] = (time.monotonic(), assets)

        if query:
            q = query.lower()
            assets = [
                a for a in assets
                if q in a.name.lower()
                or any(q in t for t in a.tags)
                or any(q in c for c in a.categories)
            ]

        return assets[:limit]

    async def get_download_url(
        self,
        asset_id: str,
        resolution: str = "1k",
        file_format: str = "hdr",
    ) -> PolyHavenFile | None:
        files_data = await self._fetch_files(asset_id)
        if not files_data:
            return None

        # HDRI structure: files["hdri"][resolution][format]["url"]
        # Try both top-level keys
        for section_key in ("hdri", "blend", "gltf", "fbx"):
            section = files_data.get(section_key, {})
            res_data = section.get(resolution, {})
            fmt_data = res_data.get(file_format, {})
            if fmt_data.get("url"):
                return PolyHavenFile(
                    asset_id=asset_id,
                    resolution=resolution,
                    file_format=file_format,
                    url=fmt_data["url"],
                    size_bytes=fmt_data.get("size", 0),
                )

        # Fallback: return the first available format at requested resolution
        for section in files_data.values():
            if not isinstance(section, dict):
                continue
            res_data = section.get(resolution, {})
            for fmt, fdata in res_data.items():
                if isinstance(fdata, dict) and fdata.get("url"):
                    return PolyHavenFile(
                        asset_id=asset_id,
                        resolution=resolution,
                        file_format=fmt,
                        url=fdata["url"],
                        size_bytes=fdata.get("size", 0),
                    )

        logger.warning("No download URL found for %s @ %s/%s", asset_id, resolution, file_format)
        return None

    async def _fetch_all(self, asset_type: str) -> list[PolyHavenAsset]:
        type_id = _TYPE_MAP.get(asset_type, 0)
        try:
            resp = await self._client.get(
                f"{_BASE}/assets",
                params={"type": type_id},
            )
            resp.raise_for_status()
            raw: dict = resp.json()
        except Exception as exc:
            logger.error("PolyHaven assets fetch failed: %s", exc)
            return []

        assets = []
        for asset_id, info in raw.items():
            assets.append(PolyHavenAsset(
                id=asset_id,
                name=info.get("name", asset_id),
                asset_type=asset_type,
                categories=tuple(info.get("categories") or []),
                tags=tuple(info.get("tags") or []),
                thumbnail_url=info.get("thumbnail_url", ""),
                download_count=info.get("download_count", 0),
            ))

        return sorted(assets, key=lambda a: a.download_count, reverse=True)

    async def _fetch_files(self, asset_id: str) -> dict:
        cached = self._files_cache.get(asset_id)
        if cached and (time.monotonic() - cached[0]) < _CACHE_TTL:
            return cached[1]

        try:
            resp = await self._client.get(f"{_BASE}/files/{asset_id}")
            resp.raise_for_status()
            data: dict = resp.json()
        except Exception as exc:
            logger.error("PolyHaven files fetch failed for %s: %s", asset_id, exc)
            return {}

        self._files_cache[asset_id] = (time.monotonic(), data)
        return data
