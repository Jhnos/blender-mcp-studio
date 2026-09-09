"""The delivery path for building a registered mechanical instance.

Until this task the only way to run a generator was `scripts/verify/*.py`, a CI
entry point. These tests pin the product's own path: one slug in, typed parts
out, and nothing from the request body reaching the code Blender runs.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from src.core.domain.exceptions import BlenderConnectionError, MechanicalGenerationError
from src.core.domain.hand_instances import HAND_INSTANCES
from src.core.domain.mechanical_generation import BuiltPart, InstanceBuild
from src.core.use_cases.mechanical_generation import MechanicalGenerationService
from tests.e2e.test_mcp_streamable_http import make_fake_runtime


class RecordingBuilder:
    """Answers with exactly what the registry claims, unless told otherwise."""

    def __init__(self, *, parts: tuple[str, ...] | None = None, error: Exception | None = None):
        self.parts = parts
        self.error = error
        self.slugs: list[str] = []

    async def build_instance(self, instance) -> InstanceBuild:  # noqa: ANN001
        self.slugs.append(instance.slug)
        if self.error is not None:
            raise self.error
        names = self.parts if self.parts is not None else instance.stl_files
        return InstanceBuild(
            slug=instance.slug,
            output_dir=instance.output_dir,
            parts=tuple(
                BuiltPart(name=name, face_count=1000 + index, dimensions_mm=(10.0, 20.0, 30.0))
                for index, name in enumerate(names)
            ),
        )


def _app_with(builder: RecordingBuilder):
    app = create_app(runtime=make_fake_runtime(), require_identity=False)
    app.state.mechanical_generation = MechanicalGenerationService(builder)
    return app


def test_building_a_registered_instance_returns_the_parts_the_registry_claims() -> None:
    builder = RecordingBuilder()
    instance = HAND_INSTANCES["hand-compact"]

    with TestClient(_app_with(builder)) as client:
        response = client.post("/api/instances/hand-compact/build")

    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "hand-compact"
    assert [part["name"] for part in body["parts"]] == list(instance.stl_files)
    assert builder.slugs == ["hand-compact"]


def test_a_build_that_does_not_match_the_registry_claim_is_a_failure_not_a_result() -> None:
    """A generator that ships a different part list than the instance declares is
    not a successful build with surprising content — every downstream package
    test, manifest and README is written against the declared list."""
    builder = RecordingBuilder(parts=("only_one.stl",))

    with TestClient(_app_with(builder)) as client:
        response = client.post("/api/instances/hand-compact/build")

    assert response.status_code == 502


def test_an_unregistered_slug_is_not_found() -> None:
    builder = RecordingBuilder()

    with TestClient(_app_with(builder)) as client:
        response = client.post("/api/instances/../../etc/passwd/build")
        unknown = client.post("/api/instances/no-such-hand/build")

    assert unknown.status_code == 404
    assert response.status_code in (404, 405)
    assert builder.slugs == []


def test_blender_being_down_is_unavailable_not_a_server_error() -> None:
    builder = RecordingBuilder(error=BlenderConnectionError("socket refused"))

    with TestClient(_app_with(builder)) as client:
        response = client.post("/api/instances/hand-v3/build")

    assert response.status_code == 503


def test_a_generator_failure_inside_blender_is_a_bad_gateway() -> None:
    builder = RecordingBuilder(error=MechanicalGenerationError("build() raised"))

    with TestClient(_app_with(builder)) as client:
        response = client.post("/api/instances/hand-v3/build")

    assert response.status_code == 502


def test_the_catalog_lists_exactly_the_registered_instances() -> None:
    with TestClient(_app_with(RecordingBuilder())) as client:
        response = client.get("/api/instances")

    assert response.status_code == 200
    listed = {entry["slug"] for entry in response.json()["instances"]}
    assert listed == set(HAND_INSTANCES)
