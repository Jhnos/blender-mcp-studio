"""REST surface of the design pipeline over the real use case and fake ports."""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from api.main import create_app
from tests.e2e.test_mcp_streamable_http import make_fake_runtime

_IDENTITY = {"x-mes-identity": "tester@example.com"}


def _artifact(tmp_path: Path) -> dict[str, object]:
    root = tmp_path / "artifact"
    (root / "STL").mkdir(parents=True)
    (root / "STL" / "a.stl").write_bytes(b"x")
    (root / "p.3mf").write_bytes(b"3mf")
    return {
        "spec_version": "1",
        "name": "demo",
        "source": {"root_dir": str(root), "project_3mf": "p.3mf"},
        "mechanism": {"suites": ["s1"]},
    }


def _client(tmp_path: Path, *, require_identity: bool = False) -> TestClient:
    app = create_app(runtime=make_fake_runtime(tmp_path), require_identity=require_identity)
    return TestClient(app, base_url="http://localhost")


def _wait_done(client: TestClient, job_id: str) -> dict[str, object]:
    for _ in range(200):
        body = client.get(f"/api/design/jobs/{job_id}").json()
        if body["status"] not in ("queued", "running"):
            return body
        time.sleep(0.02)
    raise AssertionError("job did not finish")


def test_submit_returns_job_and_report_is_reachable(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        response = client.post("/api/design/runs", json={"spec": _artifact(tmp_path)})
        assert response.status_code == 202
        job = response.json()
        assert set(job) == {
            "job_id",
            "run_id",
            "status",
            "stage",
            "error",
            "created_at",
            "updated_at",
        }
        done = _wait_done(client, job["job_id"])
        assert done["status"] == "done" and done["error"] is None
        report = client.get(f"/api/design/runs/{job['run_id']}/report")
        assert report.status_code == 200
        body = report.json()
        assert body["passed"] is True and body["spec_name"] == "demo"
        assert [s["name"] for s in body["stages"]] == [
            "import",
            "geometry",
            "mechanism",
            "print",
            "package",
        ]
        assert isinstance(body["stages"][0]["metrics"], list)
        spec = client.get(f"/api/design/runs/{job['run_id']}/files/spec.json")
        assert spec.status_code == 200
        assert spec.headers["content-type"].startswith("application/json")
        assert spec.headers["content-disposition"].startswith("attachment")
        assert 'filename="spec.json"' in spec.headers["content-disposition"]


def test_unknown_job_is_404(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        assert client.get("/api/design/jobs/nope").status_code == 404
        assert client.get(f"/api/design/runs/{'c' * 32}/report").status_code == 404
        assert client.get("/api/design/runs/not-hex/report").status_code == 404
        assert client.get(f"/api/design/runs/{'c' * 32}/files/report.json").status_code == 404


def test_run_file_download_rejects_traversal(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        run_id = "a" * 32
        for name in ("..%2Fsecret", "%2Fetc%2Fpasswd", "..%2F..%2Fx"):
            response = client.get(f"/api/design/runs/{run_id}/files/{name}")
            assert response.status_code == 400, name
        assert client.get("/api/design/runs/BAD/files/report.json").status_code == 400


def test_tools_endpoint_lists_slicer_availability(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        tools = client.get("/api/design/tools").json()
        assert tools == [
            {
                "name": "Bambu Studio",
                "available": True,
                "path": "/x/bs",
                "version": "02.06.00.51",
                "install_hint": "hint",
            }
        ]


def test_invalid_spec_is_422(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        bad = {"spec_version": "1", "name": "x", "source": {"root_dir": "/etc"}}
        response = client.post("/api/design/runs", json={"spec": bad})
        assert response.status_code == 422 and response.json()["detail"]


def test_design_routes_require_identity(tmp_path: Path) -> None:
    with _client(tmp_path, require_identity=True) as client:
        assert client.get("/api/design/tools").status_code == 401
        assert client.post("/api/design/runs", json={"spec": {}}).status_code == 401
        assert client.get("/api/design/tools", headers=_IDENTITY).status_code == 200


def test_lifespan_recovers_interrupted_jobs_and_cancels_on_shutdown(tmp_path: Path) -> None:
    pipeline = AsyncMock()
    pipeline.recover_interrupted.return_value = 3
    runtime = replace(make_fake_runtime(tmp_path), design_pipeline=pipeline)
    app = create_app(runtime=runtime, require_identity=False)
    with TestClient(app):
        pipeline.recover_interrupted.assert_awaited_once()
        pipeline.cancel_all.assert_not_awaited()
    pipeline.cancel_all.assert_awaited_once()
    pipeline.wait_idle.assert_not_awaited()
