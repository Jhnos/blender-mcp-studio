"""Native revision orchestration, using the same catalog policy as the import pipeline."""

from src.core.domain.native_revision import StagedNativeSource
from src.core.ports.native_staging_port import NativeStagingPort
from src.core.use_cases.artifact_catalog import ArtifactCatalog


class NativeRevisionService:
    def __init__(self, artifacts: ArtifactCatalog, staging: NativeStagingPort) -> None:
        self._artifacts = artifacts
        self._staging = staging

    async def prepare_source(self, run_id: str) -> StagedNativeSource:
        """Prepare an existing job's captured current source; no Blender mutation yet."""
        selected = self._artifacts.current()
        spec, source = await self._artifacts.native_source_for(selected)
        return await self._staging.stage(spec, source, run_id)
