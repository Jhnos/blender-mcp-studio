"""Tests for V4 scene graph object endpoints (PUT/DELETE/POST select).

Uses TestClient with mocked Blender adapter — no Blender connection required.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from api.main import create_app
from src.core.domain.command import Command
from src.core.domain.exceptions import SceneOperationError
from src.core.domain.scene_operations import SceneObjectSummary, SceneSummary, Vector3
from src.core.use_cases.scene_operations import SceneOperationsService


def _make_client(blender_success: bool = True, blender_response: dict | None = None) -> TestClient:
    app = create_app()

    # Build a mock result object with .success, .output, .error attrs
    mock_result = MagicMock()
    mock_result.success = blender_response["success"] if blender_response else True
    mock_result.output = (blender_response or {}).get("output", "")
    mock_result.error = (blender_response or {}).get("error", None)

    mock_blender = AsyncMock()
    mock_blender.execute = AsyncMock(return_value=mock_result)
    # The port answers typed DTOs; decoding the addon's reply is the adapter's
    # job and is tested there (D-001).
    mock_blender.scene_summary = AsyncMock(
        return_value=SceneSummary(
            name="Scene",
            object_count=1,
            materials_count=0,
            objects=(SceneObjectSummary("Cube", "MESH", Vector3()),),
        )
    )

    app.state.blender = mock_blender
    app.state.scene_operations = SceneOperationsService(mock_blender)
    # Other state attrs required by the app
    app.state.event_bus = MagicMock()
    app.state.adapter_factory = MagicMock()
    app.state.sandbox = MagicMock(sanitize=lambda x: x)
    app.state.sanitizer = MagicMock(sanitize=lambda x: x)
    app.state.vision = None
    app.state.prompt_builder = MagicMock()
    app.state.session_store = MagicMock()
    app.state.snapshot_store = MagicMock()
    app.state.polyhaven = MagicMock()
    app.state.text3d = None

    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# PUT /api/object/{name}  — rename/visibility
# ---------------------------------------------------------------------------


def test_rename_object_success():
    client = _make_client()
    resp = client.put("/api/object/Cube", json={"new_name": "MyCube"})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("updated") is True or "name" in data
    command = client.app.state.blender.execute.await_args.args[0]
    assert command.tool_name == "execute_code"


def test_rename_object_not_found():
    client = _make_client(
        blender_response={
            "success": False,
            "output": "",
            "error": "Object not found",
            "screenshot": None,
        }
    )
    resp = client.put("/api/object/NotExist", json={"new_name": "X"})
    assert resp.status_code in (404, 422, 500)


def test_set_visibility_success():
    client = _make_client()
    resp = client.put("/api/object/Cube", json={"visible": False})
    assert resp.status_code == 200
    assert client.app.state.blender.execute.await_args.args == (
        Command(tool_name="modify_object", arguments={"name": "Cube", "visible": False}),
    )


# ---------------------------------------------------------------------------
# DELETE /api/object/{name}
# ---------------------------------------------------------------------------


def test_delete_object_success():
    client = _make_client()
    resp = client.delete("/api/object/Cube")
    assert resp.status_code == 200
    data = resp.json()
    assert "deleted" in data or "success" in str(data)
    assert client.app.state.blender.execute.await_args.args == (
        Command(tool_name="delete_object", arguments={"name": "Cube"}),
    )


def test_delete_object_not_found():
    client = _make_client(
        blender_response={"success": False, "output": "", "error": "not found", "screenshot": None}
    )
    resp = client.delete("/api/object/Ghost")
    assert resp.status_code == 422


def test_get_scene_uses_shared_scene_service() -> None:
    client = _make_client()

    response = client.get("/api/scene")

    assert response.status_code == 200
    assert response.json()["objects"] == [
        {"name": "Cube", "type": "MESH", "location": [0.0, 0.0, 0.0]}
    ]
    client.app.state.blender.scene_summary.assert_awaited_once_with()


def test_get_scene_does_not_silently_hide_invalid_blender_data() -> None:
    """The adapter refuses an unusable reply with a domain error; REST shows it as 422."""
    client = _make_client()
    client.app.state.blender.scene_summary.side_effect = SceneOperationError(
        "Blender scene info is missing: name"
    )

    response = client.get("/api/scene")

    assert response.status_code == 422
    assert "missing" in response.json()["detail"]


def test_preview_rejects_non_png_blender_output() -> None:
    client = _make_client()

    client.app.state.blender.viewport_screenshot.side_effect = SceneOperationError(
        "Blender screenshot is not a PNG file"
    )

    response = client.get("/api/preview")

    assert response.status_code == 422
    assert response.json()["detail"] == "Blender screenshot is not a PNG file"


# ---------------------------------------------------------------------------
# POST /api/undo and /api/redo
# ---------------------------------------------------------------------------


def test_undo_response_message_is_always_text() -> None:
    client = _make_client(blender_response={"success": True, "output": "undo ok\n"})

    response = client.post("/api/undo")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "action": "undo",
        "message": "undo ok\n",
    }


def test_redo_failure_response_preserves_error_text() -> None:
    client = _make_client(
        blender_response={"success": False, "output": None, "error": "nothing to redo"}
    )

    response = client.post("/api/redo")

    assert response.status_code == 200
    assert response.json() == {
        "success": False,
        "action": "redo",
        "message": "nothing to redo",
    }


# ---------------------------------------------------------------------------
# POST /api/object/{name}/select
# ---------------------------------------------------------------------------


def test_select_object_success():
    client = _make_client()
    resp = client.post("/api/object/Cube/select")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("selected") is True or "selected" in str(data)


def test_select_object_not_found():
    client = _make_client(
        blender_response={"success": False, "output": "", "error": "not found", "screenshot": None}
    )
    resp = client.post("/api/object/Ghost/select")
    assert resp.status_code in (404, 500)


# ---------------------------------------------------------------------------
# Object name escaping (SQL-injection style protection for bpy code)
# ---------------------------------------------------------------------------


def test_object_name_with_quotes():
    """Object names with single quotes should not crash the endpoint."""
    client = _make_client()
    # URL encode the name; the router should handle it safely
    resp = client.put("/api/object/Cube%27s", json={"visible": True})
    # Either succeeds or returns 4xx — must not 500 with SyntaxError
    assert resp.status_code != 500 or "SyntaxError" not in resp.text
