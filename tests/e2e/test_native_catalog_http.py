"""REST and Streamable HTTP MCP expose the same selected native identity receipt."""

import hashlib
import json
import shutil
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from api.main import create_app
from src.adapters.artifacts.native_source import FilesystemNativeSource
from src.core.use_cases.artifact_catalog import ArtifactCatalog
from tests.e2e.test_mcp_streamable_http import _MCP_HEADERS, _json_rpc_payload, make_fake_runtime


def test_native_receipt_and_corruption_are_identical_across_transports(tmp_path):
    root = tmp_path / "artifact"
    (root / "STL").mkdir(parents=True)
    assets = {
        "native.blend": b"opaque-native",
        "STL/a.stl": b"a",
        "STL/b.stl": b"b",
        "p.3mf": b"plate",
    }
    for name, data in assets.items():
        (root / name).write_bytes(data)
    manifest = {n: hashlib.sha256(v).hexdigest() for n, v in assets.items()}
    (root / "SHA256.json").write_text(json.dumps(manifest))
    next_root = tmp_path / "next-artifact"
    shutil.copytree(root, next_root)
    (next_root / "native.blend").write_bytes(b"next-native")
    next_manifest = {**manifest, "native.blend": hashlib.sha256(b"next-native").hexdigest()}
    (next_root / "SHA256.json").write_text(json.dumps(next_manifest))
    spec = {
        "spec_version": "1",
        "name": "first",
        "source": {"root_dir": "artifact", "stl_glob": "STL/*.stl", "project_3mf": "p.3mf"},
    }
    runtime = make_fake_runtime(tmp_path, selected_spec=lambda: spec)
    runtime.design_pipeline._artifacts = ArtifactCatalog(
        (tmp_path,),
        565,
        lambda: spec,
        native_sources=FilesystemNativeSource((tmp_path,), runtime.tools.import_limits),
    )
    runtime.blender.execute = AsyncMock(
        side_effect=AssertionError("native identity queried Blender")
    )
    runtime.blender.call_tool = AsyncMock(
        side_effect=AssertionError("native identity queried Blender")
    )
    with TestClient(create_app(runtime=runtime, require_identity=False)) as client:

        def both():
            rest = client.get("/api/design/artifacts")
            assert rest.status_code == 200
            response = client.post(
                "/mcp",
                headers=_MCP_HEADERS,
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "list_artifacts", "arguments": {}},
                },
            )
            assert response.status_code == 200
            rpc = _json_rpc_payload(response)["result"]
            assert not rpc.get("isError", False)
            mcp = rpc.get("structuredContent") or json.loads(rpc["content"][0]["text"])
            if set(mcp) == {"result"}:
                mcp = mcp["result"]
            assert mcp == rest.json()
            assert str(tmp_path) not in json.dumps(mcp)
            return mcp

        for name, selected_root, expected in (
            ("first", root, manifest),
            ("changed-current", next_root, next_manifest),
        ):
            spec["source"]["root_dir"] = selected_root.name
            spec["name"] = name
            reply = both()
            assert reply["default_native"]["available"] is True
            assert reply["default_native"]["model_name"] == name
            assert reply["default_native"]["native"]["sha256"] == expected["native.blend"]
            assert len(reply["default_native"]["parts"]) == 2
            assert reply["default_native"]["scope"] == "file_identity_only"
        (next_root / "native.blend").write_bytes(b"stale")
        assert (
            hashlib.sha256((root / "native.blend").read_bytes()).hexdigest()
            == manifest["native.blend"]
        )
        reply = both()
        assert (
            reply["default_spec"]["name"] == "changed-current"
            and reply["default_available"] is True
        )
        assert reply["default_native"]["available"] is False
        assert "checksum mismatch" in reply["default_native"]["reason"]
    runtime.blender.execute.assert_not_awaited()
    runtime.blender.call_tool.assert_not_awaited()
