"""One selection snapshot feeds both public discovery and typed native provenance."""

import pytest

from src.core.domain.model_spec import ModelSpec
from src.core.domain.native_revision import NativeModelSource, NativeSourceError, SourceArtifact
from src.core.use_cases.artifact_catalog import ArtifactCatalog
from tests.unit.core.test_design_pipeline import _rig


class Sources:
    def __init__(self, error=None, wrong_model=False):
        self.seen = []
        self.error = error
        self.wrong_model = wrong_model

    async def resolve(self, spec: ModelSpec) -> NativeModelSource:
        self.seen.append(spec)
        if self.error:
            raise self.error
        part = SourceArtifact("native.blend", "a" * 64, 12)
        return NativeModelSource(
            "wrong" if self.wrong_model else spec.name,
            "artifact",
            part,
            (SourceArtifact("STL/a.stl", "c" * 64, 1), SourceArtifact("STL/b.stl", "d" * 64, 1)),
            SourceArtifact("p.3mf", "e" * 64, 3),
            "b" * 64,
            4,
        )


async def test_discovery_uses_exactly_one_selection_snapshot(tmp_path):
    rig = _rig(tmp_path)
    calls = 0
    source = Sources()

    def current():
        nonlocal calls
        calls += 1
        return {
            "spec_version": "1",
            "name": f"selection-{calls}",
            "source": {"root_dir": "artifact", "stl_glob": "STL/*.stl", "project_3mf": "p.3mf"},
        }

    rig.pipeline._artifacts = ArtifactCatalog((tmp_path,), 565, current, native_sources=source)
    result = await rig.pipeline.list_artifacts()
    assert calls == 1 and source.seen[0].name == result["default_spec"]["name"]
    assert (
        result["default_native"]["available"]
        and result["default_native"]["model_name"] == "selection-1"
    )
    assert result["default_native"]["scope"] == "file_identity_only"
    assert str(tmp_path) not in repr(result) and not rig.jobs.records
    second = await rig.pipeline.list_artifacts()
    assert calls == 2 and second["default_native"]["model_name"] == "selection-2"


@pytest.mark.parametrize(
    "source",
    [
        Sources(error=NativeSourceError("checksum mismatch: native.blend")),
        Sources(wrong_model=True),
    ],
)
async def test_bad_native_is_visible_without_fallback_or_false_import_failure(tmp_path, source):
    rig = _rig(tmp_path)
    selected = {
        "spec_version": "1",
        "name": "current",
        "source": {"root_dir": "artifact", "stl_glob": "STL/*.stl", "project_3mf": "p.3mf"},
    }
    rig.pipeline._artifacts = ArtifactCatalog(
        (tmp_path,), 565, lambda: selected, native_sources=source
    )
    result = await rig.pipeline.list_artifacts()
    assert result["default_available"] is True
    assert result["default_spec"] == selected
    assert result["default_native"]["available"] is False and result["default_native"]["reason"]
    assert not rig.jobs.records
