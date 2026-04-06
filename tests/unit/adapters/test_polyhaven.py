"""Tests for PolyHavenPort, PolyHavenAdapter, and API endpoints."""

from __future__ import annotations

import pytest

from src.core.ports.polyhaven_port import PolyHavenAsset, PolyHavenFile, PolyHavenPort


# ---------------------------------------------------------------------------
# Port contract
# ---------------------------------------------------------------------------

class TestPolyHavenPortContract:
    def test_is_abstract(self):
        assert not issubclass(PolyHavenPort, type(None))
        assert hasattr(PolyHavenPort, "search")
        assert hasattr(PolyHavenPort, "get_download_url")

    def test_asset_is_immutable(self):
        a = PolyHavenAsset(id="test", name="Test", asset_type="hdri")
        with pytest.raises((AttributeError, TypeError)):
            a.name = "mutated"  # type: ignore[misc]

    def test_file_is_immutable(self):
        f = PolyHavenFile(asset_id="x", resolution="1k", file_format="hdr", url="http://x")
        with pytest.raises((AttributeError, TypeError)):
            f.url = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PolyHavenAdapter unit tests (mocked httpx)
# ---------------------------------------------------------------------------

_FAKE_ASSETS_RESPONSE = {
    "forest_slope": {
        "type": 0,
        "name": "Forest Slope",
        "categories": ["outdoor", "nature"],
        "tags": ["tree", "forest", "green"],
        "thumbnail_url": "https://cdn.polyhaven.com/asset_img/thumbs/forest_slope.png",
        "download_count": 50000,
    },
    "studio_small": {
        "type": 0,
        "name": "Studio Small",
        "categories": ["indoor", "studio"],
        "tags": ["studio", "neutral", "soft"],
        "thumbnail_url": "https://cdn.polyhaven.com/asset_img/thumbs/studio_small.png",
        "download_count": 120000,
    },
}

_FAKE_FILES_RESPONSE = {
    "hdri": {
        "1k": {
            "hdr": {
                "url": "https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/1k/forest_slope_1k.hdr",
                "size": 1500000,
            },
            "exr": {
                "url": "https://dl.polyhaven.org/file/ph-assets/HDRIs/exr/1k/forest_slope_1k.exr",
                "size": 1200000,
            },
        },
        "2k": {
            "hdr": {
                "url": "https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/2k/forest_slope_2k.hdr",
                "size": 5000000,
            },
        },
    }
}


@pytest.fixture
def adapter():
    from src.adapters.polyhaven.polyhaven_adapter import PolyHavenAdapter
    return PolyHavenAdapter(timeout=5.0)


@pytest.mark.asyncio
async def test_search_returns_all_when_no_query(adapter, respx_mock):
    import httpx
    import json

    respx_mock.get("https://api.polyhaven.com/assets").mock(
        return_value=httpx.Response(200, text=json.dumps(_FAKE_ASSETS_RESPONSE))
    )

    results = await adapter.search(query="", asset_type="hdri", limit=10)
    assert len(results) == 2
    # Sorted by download count desc
    assert results[0].id == "studio_small"
    assert results[1].id == "forest_slope"


@pytest.mark.asyncio
async def test_search_filters_by_name(adapter, respx_mock):
    import httpx, json
    respx_mock.get("https://api.polyhaven.com/assets").mock(
        return_value=httpx.Response(200, text=json.dumps(_FAKE_ASSETS_RESPONSE))
    )
    results = await adapter.search(query="forest", asset_type="hdri")
    assert len(results) == 1
    assert results[0].id == "forest_slope"


@pytest.mark.asyncio
async def test_search_filters_by_tag(adapter, respx_mock):
    import httpx, json
    respx_mock.get("https://api.polyhaven.com/assets").mock(
        return_value=httpx.Response(200, text=json.dumps(_FAKE_ASSETS_RESPONSE))
    )
    results = await adapter.search(query="studio", asset_type="hdri")
    assert any(r.id == "studio_small" for r in results)


@pytest.mark.asyncio
async def test_search_respects_limit(adapter, respx_mock):
    import httpx, json
    respx_mock.get("https://api.polyhaven.com/assets").mock(
        return_value=httpx.Response(200, text=json.dumps(_FAKE_ASSETS_RESPONSE))
    )
    results = await adapter.search(limit=1)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_get_download_url_returns_correct_file(adapter, respx_mock):
    import httpx, json
    respx_mock.get("https://api.polyhaven.com/files/forest_slope").mock(
        return_value=httpx.Response(200, text=json.dumps(_FAKE_FILES_RESPONSE))
    )
    ph_file = await adapter.get_download_url("forest_slope", resolution="1k", file_format="hdr")
    assert ph_file is not None
    assert "forest_slope_1k.hdr" in ph_file.url
    assert ph_file.resolution == "1k"
    assert ph_file.size_bytes == 1500000


@pytest.mark.asyncio
async def test_get_download_url_falls_back_to_available_format(adapter, respx_mock):
    import httpx, json
    respx_mock.get("https://api.polyhaven.com/files/forest_slope").mock(
        return_value=httpx.Response(200, text=json.dumps(_FAKE_FILES_RESPONSE))
    )
    # exr format at 1k exists
    ph_file = await adapter.get_download_url("forest_slope", resolution="1k", file_format="exr")
    assert ph_file is not None
    assert "exr" in ph_file.url


@pytest.mark.asyncio
async def test_get_download_url_returns_none_when_not_found(adapter, respx_mock):
    import httpx, json
    respx_mock.get("https://api.polyhaven.com/files/forest_slope").mock(
        return_value=httpx.Response(200, text=json.dumps(_FAKE_FILES_RESPONSE))
    )
    ph_file = await adapter.get_download_url("forest_slope", resolution="8k", file_format="hdr")
    assert ph_file is None


@pytest.mark.asyncio
async def test_search_returns_empty_on_http_error(adapter, respx_mock):
    import httpx
    respx_mock.get("https://api.polyhaven.com/assets").mock(
        return_value=httpx.Response(503)
    )
    results = await adapter.search()
    assert results == []


@pytest.mark.asyncio
async def test_search_uses_cache_on_second_call(adapter, respx_mock):
    import httpx, json
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, text=json.dumps(_FAKE_ASSETS_RESPONSE))

    respx_mock.get("https://api.polyhaven.com/assets").mock(side_effect=handler)

    await adapter.search()
    await adapter.search()
    assert call_count == 1  # second call served from cache


# ---------------------------------------------------------------------------
# API endpoint smoke tests
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client_with_polyhaven():
    from unittest.mock import AsyncMock, MagicMock
    from fastapi.testclient import TestClient
    from api.main import create_app

    app = create_app()

    mock_ph = MagicMock()
    mock_ph.search = AsyncMock(return_value=[
        PolyHavenAsset(id="forest_slope", name="Forest Slope", asset_type="hdri",
                       thumbnail_url="https://cdn.example.com/thumb.png")
    ])
    mock_ph.get_download_url = AsyncMock(return_value=PolyHavenFile(
        asset_id="forest_slope", resolution="1k", file_format="hdr",
        url="https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/1k/forest_slope_1k.hdr",
        size_bytes=1500000,
    ))

    with TestClient(app) as client:
        app.state.polyhaven = mock_ph
        yield client, mock_ph


class TestMaterialsEndpoints:

    def test_search_returns_results(self, api_client_with_polyhaven):
        client, _ = api_client_with_polyhaven
        resp = client.get("/api/materials/search?q=forest&asset_type=hdri")
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "forest"
        assert len(data["results"]) == 1
        assert data["results"][0]["id"] == "forest_slope"

    def test_search_no_polyhaven_returns_503(self):
        from fastapi.testclient import TestClient
        from api.main import create_app
        app = create_app()
        with TestClient(app) as client:
            app.state.polyhaven = None
            resp = client.get("/api/materials/search")
        assert resp.status_code == 503

    def test_apply_no_polyhaven_returns_503(self):
        from fastapi.testclient import TestClient
        from api.main import create_app
        app = create_app()
        with TestClient(app) as client:
            app.state.polyhaven = None
            resp = client.post("/api/materials/apply", json={"asset_id": "forest_slope"})
        assert resp.status_code == 503

    def test_apply_unknown_apply_as_returns_400(self, api_client_with_polyhaven):
        client, _ = api_client_with_polyhaven
        mock_blender = MagicMock()
        mock_blender.execute = AsyncMock()
        client.app.state.blender = mock_blender
        resp = client.post("/api/materials/apply", json={
            "asset_id": "forest_slope",
            "apply_as": "invalid_type",
        })
        assert resp.status_code == 400


from unittest.mock import AsyncMock, MagicMock
