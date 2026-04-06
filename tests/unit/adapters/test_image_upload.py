"""Tests for V4 multimodal image upload endpoint (/api/chat/image)."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from api.main import create_app


def _make_client_with_vision(vision_mock=None) -> TestClient:
    app = create_app()

    mock_blender = AsyncMock()
    mock_blender.execute_code.return_value = {"success": True, "output": "", "error": None, "screenshot": None}

    app.state.blender = mock_blender
    app.state.event_bus = MagicMock()
    app.state.adapter_factory = MagicMock()
    app.state.sandbox = MagicMock(sanitize=lambda x: x)
    app.state.sanitizer = MagicMock(sanitize=lambda x: x)
    app.state.vision = vision_mock
    app.state.prompt_builder = MagicMock()
    app.state.session_store = MagicMock()
    app.state.snapshot_store = MagicMock()
    app.state.polyhaven = MagicMock()
    app.state.text3d = None

    return TestClient(app, raise_server_exceptions=True)


def _fake_image_bytes() -> bytes:
    """Minimal 1x1 PNG."""
    import base64
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_image_upload_returns_description():
    analysis = MagicMock()
    analysis.description = "A cute black cat sits on a desk."
    analysis.suggestions = ["Add fur texture", "Add eyes"]
    analysis.provider = "openai"
    analysis.model = "gpt-4o"

    vision_mock = AsyncMock()
    vision_mock.analyze_image = AsyncMock(return_value=analysis)

    client = _make_client_with_vision(vision_mock)
    resp = client.post(
        "/api/chat/image",
        files={"image": ("test.png", BytesIO(_fake_image_bytes()), "image/png")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "A cute black cat sits on a desk."
    assert "Add fur texture" in data["suggestions"]
    assert data["provider"] == "openai"
    assert data["model"] == "gpt-4o"


def test_image_upload_with_custom_prompt():
    analysis = MagicMock()
    analysis.description = "A dragon model."
    analysis.suggestions = []
    analysis.provider = "anthropic"
    analysis.model = "claude-3-opus"

    vision_mock = AsyncMock()
    vision_mock.analyze_image = AsyncMock(return_value=analysis)

    client = _make_client_with_vision(vision_mock)
    resp = client.post(
        "/api/chat/image",
        files={"image": ("ref.jpg", BytesIO(_fake_image_bytes()), "image/jpeg")},
        data={"prompt": "What is the style of this model?"},
    )
    assert resp.status_code == 200
    # Check that analyze_image was called with the custom prompt
    call_kwargs = vision_mock.analyze_image.call_args
    assert "What is the style" in str(call_kwargs)


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_image_upload_no_vision_returns_503():
    """Without vision adapter, endpoint returns 503."""
    client = _make_client_with_vision(vision_mock=None)
    resp = client.post(
        "/api/chat/image",
        files={"image": ("test.png", BytesIO(_fake_image_bytes()), "image/png")},
    )
    assert resp.status_code == 503


def test_image_upload_no_file_returns_422():
    analysis = MagicMock()
    vision_mock = AsyncMock()
    vision_mock.analyze_image = AsyncMock(return_value=analysis)

    client = _make_client_with_vision(vision_mock)
    resp = client.post("/api/chat/image", data={"prompt": "hello"})
    assert resp.status_code == 422


def test_image_upload_vision_error_returns_500():
    vision_mock = AsyncMock()
    vision_mock.analyze_image = AsyncMock(side_effect=RuntimeError("API error"))

    client = _make_client_with_vision(vision_mock)
    resp = client.post(
        "/api/chat/image",
        files={"image": ("test.png", BytesIO(_fake_image_bytes()), "image/png")},
    )
    assert resp.status_code == 500
