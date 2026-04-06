"""Tests for Text3D port ISP contract and Hunyuan3DAdapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.adapters.text3d.hunyuan3d_adapter import Hunyuan3DAdapter, build_text3d_adapter
from src.core.ports.text3d_port import Text3DGenerationPort, Text3DResult

# ---------------------------------------------------------------------------
# Port ISP contract
# ---------------------------------------------------------------------------


class FakeText3DAdapter(Text3DGenerationPort):
    async def generate(self, prompt: str, *, negative_prompt: str = "", steps: int = 20, guidance_scale: float = 7.5) -> Text3DResult:
        return Text3DResult(
            glb_bytes=b"GLB",
            prompt=prompt,
            provider="fake",
            generation_time_s=0.1,
        )


def test_port_is_abstract():
    assert not hasattr(Text3DGenerationPort, "__abstractmethods__") or \
           "generate" in Text3DGenerationPort.__abstractmethods__


def test_fake_implements_port():
    adapter = FakeText3DAdapter()
    assert isinstance(adapter, Text3DGenerationPort)


@pytest.mark.asyncio
async def test_fake_generate_returns_result():
    adapter = FakeText3DAdapter()
    result = await adapter.generate("a cute cat phone stand")
    assert isinstance(result, Text3DResult)
    assert result.prompt == "a cute cat phone stand"
    assert result.glb_bytes == b"GLB"
    assert result.provider == "fake"
    assert result.generation_time_s >= 0.0


# ---------------------------------------------------------------------------
# Text3DResult dataclass
# ---------------------------------------------------------------------------


def test_result_frozen():
    r = Text3DResult(glb_bytes=b"x", prompt="p", provider="prov", generation_time_s=1.0)
    with pytest.raises(AttributeError):
        r.prompt = "new"  # type: ignore[misc]


def test_result_equality():
    r1 = Text3DResult(glb_bytes=b"x", prompt="p", provider="prov", generation_time_s=1.0)
    r2 = Text3DResult(glb_bytes=b"x", prompt="p", provider="prov", generation_time_s=1.0)
    assert r1 == r2


# ---------------------------------------------------------------------------
# Hunyuan3DAdapter — local mode (httpx mock)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_local_mode_binary_response(respx_mock):
    """Local server returns raw GLB bytes."""
    adapter = Hunyuan3DAdapter(mode="local", endpoint="http://localhost:8080")
    fake_glb = b"glTF\x02\x00\x00\x00"  # minimal glTF binary header

    import httpx

    respx_mock.post("http://localhost:8080/generate").mock(
        return_value=httpx.Response(200, content=fake_glb, headers={"content-type": "model/gltf-binary"})
    )
    result = await adapter.generate("a dragon", steps=10)

    assert result.glb_bytes == fake_glb
    assert result.provider == "hunyuan3d"
    assert result.prompt == "a dragon"


@pytest.mark.asyncio
async def test_local_mode_json_base64_response(respx_mock):
    """Local server returns JSON with glb_base64 field."""
    import base64

    import httpx

    fake_glb = b"glTF\x02\x00\x00\x00"
    b64 = base64.b64encode(fake_glb).decode()

    adapter = Hunyuan3DAdapter(mode="local", endpoint="http://localhost:8080")
    respx_mock.post("http://localhost:8080/generate").mock(
        return_value=httpx.Response(200, json={"glb_base64": b64})
    )
    result = await adapter.generate("a cube")

    assert result.glb_bytes == fake_glb


@pytest.mark.asyncio
async def test_local_mode_http_error_raises(respx_mock):
    """HTTP 500 from server raises RuntimeError (via raise_for_status)."""
    import httpx

    adapter = Hunyuan3DAdapter(mode="local", endpoint="http://localhost:8080")
    respx_mock.post("http://localhost:8080/generate").mock(
        return_value=httpx.Response(500, text="Server error")
    )
    with pytest.raises(httpx.HTTPStatusError):
        await adapter.generate("test")


# ---------------------------------------------------------------------------
# Hunyuan3DAdapter — gradio mode (mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gradio_mode_missing_package_raises():
    """If gradio_client not installed, RuntimeError with helpful message."""
    adapter = Hunyuan3DAdapter(mode="gradio", hf_space="tencent/Hunyuan3D-2")
    with patch("builtins.__import__", side_effect=ImportError("gradio_client")), pytest.raises(RuntimeError, match="gradio_client not installed"):
        await adapter._generate_gradio("test", "", 10, 7.5)


@pytest.mark.asyncio
async def test_gradio_mode_calls_client(tmp_path):
    """Gradio mode calls Client.predict and reads the returned file."""
    fake_glb = b"glTF\x02\x00\x00\x00"
    glb_file = tmp_path / "result.glb"
    glb_file.write_bytes(fake_glb)

    mock_client_instance = MagicMock()
    mock_client_instance.predict.return_value = str(glb_file)

    adapter = Hunyuan3DAdapter(mode="gradio", hf_space="tencent/Hunyuan3D-2")
    with patch.dict("sys.modules", {"gradio_client": MagicMock(Client=MagicMock(return_value=mock_client_instance))}):
        result = await adapter._generate_gradio("a dragon", "", 20, 7.5)

    assert result == fake_glb
    mock_client_instance.predict.assert_called_once()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def test_build_factory_no_env(monkeypatch):
    """build_text3d_adapter returns adapter (default: gradio mode, no env required)."""
    monkeypatch.delenv("HUNYUAN3D_MODE", raising=False)
    monkeypatch.delenv("HUNYUAN3D_ENDPOINT", raising=False)
    adapter = build_text3d_adapter()
    assert adapter is not None
    assert isinstance(adapter, Hunyuan3DAdapter)


def test_build_factory_local_no_endpoint_returns_none(monkeypatch):
    """Local mode without endpoint env → returns None (graceful degradation)."""
    monkeypatch.setenv("HUNYUAN3D_MODE", "local")
    monkeypatch.delenv("HUNYUAN3D_ENDPOINT", raising=False)
    adapter = build_text3d_adapter()
    assert adapter is None


def test_build_factory_local_with_endpoint(monkeypatch):
    """Local mode with endpoint env → returns adapter."""
    monkeypatch.setenv("HUNYUAN3D_MODE", "local")
    monkeypatch.setenv("HUNYUAN3D_ENDPOINT", "http://localhost:8080")
    adapter = build_text3d_adapter()
    assert adapter is not None
