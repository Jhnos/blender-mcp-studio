"""Native revision orchestration, using the same catalog policy as the import pipeline."""

from src.core.domain.model_spec import ModelSpec
from src.core.domain.native_revision import (
    NativeRevisionError,
    NativeRevisionRequest,
    NativeRevisionResult,
    PreparedNativeRevision,
    StagedNativeSource,
)
from src.core.ports.native_runner_port import NativeRunnerPort
from src.core.ports.native_staging_port import NativeStagingPort
from src.core.use_cases.artifact_catalog import ArtifactCatalog


class NativeRevisionService:
    def __init__(
        self,
        artifacts: ArtifactCatalog,
        staging: NativeStagingPort,
        *,
        runner: NativeRunnerPort | None = None,
    ) -> None:
        self._artifacts = artifacts
        self._staging = staging
        self._runner = runner

    @property
    def unresolved_run_ids(self) -> tuple[str, ...]:
        return self._runner.unresolved_run_ids if self._runner is not None else ()

    async def recover_unfinished(self) -> int:
        return await self._runner.recover_unfinished() if self._runner is not None else 0

    async def execute_revision(
        self, run_id: str, request: NativeRevisionRequest
    ) -> NativeRevisionResult:
        if self._runner is None:
            raise NativeRevisionError("native execution is not configured")
        prepared = await self.prepare_revision(run_id, request)
        return await self._runner.execute(prepared)

    async def prepare_source(self, run_id: str) -> StagedNativeSource:
        """Prepare an existing job's captured current source; no Blender mutation yet."""
        _, staged = await self._prepare(run_id)
        return staged

    async def prepare_revision(
        self, run_id: str, request: NativeRevisionRequest
    ) -> PreparedNativeRevision:
        """Keep the same captured spec/print target, intent and source through execution."""
        spec, staged = await self._prepare(run_id)
        return PreparedNativeRevision(spec, request, staged)

    async def _prepare(self, run_id: str) -> tuple[ModelSpec, StagedNativeSource]:
        selected = self._artifacts.current()
        spec, source = await self._artifacts.native_source_for(selected)
        staged = await self._staging.stage(spec, source, run_id)
        if staged.source != source:
            raise NativeRevisionError("staged source disagrees with the captured selection")
        return spec, staged
