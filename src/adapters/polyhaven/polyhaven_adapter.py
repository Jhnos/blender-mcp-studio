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
from src.infrastructure.narrowing import as_int, as_str, as_str_keyed, dig

logger = logging.getLogger(__name__)

_TYPE_MAP = {"hdri": 0, "texture": 1, "model": 2}
_BASE = "https://api.polyhaven.com"
_CACHE_TTL = 300  # seconds
_CATALOGUE = "PolyHaven asset catalogue"


def _size(value: object) -> int:
    """PolyHaven omits `size` on some formats; absent or malformed reads as 0."""
    return as_int(value) or 0


def _str_tuple(value: object) -> tuple[str, ...]:
    """Read a list-of-strings field; empty when absent, and non-strings are dropped."""
    if not isinstance(value, list):  # narrow-ok: items filtered by isinstance(item, str) below
        return ()
    return tuple(item for item in value if isinstance(item, str))


class PolyHavenAdapter(PolyHavenPort):
    """Async HTTP adapter for the Poly Haven public API (no auth required)."""

    def __init__(self, timeout: float = 15.0) -> None:
        self._timeout = timeout
        self._assets_cache: dict[str, tuple[float, list[PolyHavenAsset]]] = {}
        self._files_cache: dict[str, tuple[float, dict[str, object]]] = {}

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
                a
                for a in assets
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
            file_node = dig(files_data, section_key, resolution, file_format)
            url = dig(file_node, "url")
            if isinstance(url, str) and url:
                return PolyHavenFile(
                    asset_id=asset_id,
                    resolution=resolution,
                    file_format=file_format,
                    url=url,
                    size_bytes=_size(dig(file_node, "size")),
                )

        # Fallback: return the first available format at requested resolution
        for section in files_data.values():
            res_data = dig(section, resolution)
            if not isinstance(res_data, dict):  # narrow-ok: fmt/url re-narrowed below
                continue
            for fmt, fdata in res_data.items():
                url = dig(fdata, "url")
                if isinstance(fmt, str) and isinstance(url, str) and url:
                    return PolyHavenFile(
                        asset_id=asset_id,
                        resolution=resolution,
                        file_format=fmt,
                        url=url,
                        size_bytes=_size(dig(fdata, "size")),
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
            payload: object = resp.json()
        except Exception as exc:
            logger.error("PolyHaven assets fetch failed: %s", exc)
            return []

        raw = as_str_keyed(payload, context=_CATALOGUE)
        if raw is None:
            logger.error("%s: expected a JSON object, got %s", _CATALOGUE, type(payload).__name__)
            return []

        assets = []
        for asset_id, info in raw.items():
            fields = as_str_keyed(info, context=_CATALOGUE)
            if fields is None:
                logger.warning("PolyHaven asset '%s' has unexpected shape — skipping", asset_id)
                continue
            assets.append(
                PolyHavenAsset(
                    id=asset_id,
                    name=as_str(fields.get("name")) or asset_id,
                    asset_type=asset_type,
                    categories=_str_tuple(fields.get("categories")),
                    tags=_str_tuple(fields.get("tags")),
                    thumbnail_url=as_str(fields.get("thumbnail_url")) or "",
                    download_count=_size(fields.get("download_count")),
                )
            )

        return sorted(assets, key=lambda a: a.download_count, reverse=True)

    async def _fetch_files(self, asset_id: str) -> dict[str, object]:
        cached = self._files_cache.get(asset_id)
        if cached and (time.monotonic() - cached[0]) < _CACHE_TTL:
            return cached[1]

        try:
            resp = await self._client.get(f"{_BASE}/files/{asset_id}")
            resp.raise_for_status()
            payload: object = resp.json()
        except Exception as exc:
            logger.error("PolyHaven files fetch failed for %s: %s", asset_id, exc)
            return {}

        data = as_str_keyed(payload, context=f"PolyHaven files/{asset_id}")
        if data is None:
            logger.error(
                "PolyHaven files/%s: expected a JSON object, got %s",
                asset_id,
                type(payload).__name__,
            )
            return {}

        self._files_cache[asset_id] = (time.monotonic(), data)
        return data
