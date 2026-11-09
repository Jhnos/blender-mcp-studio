"""Native revision orchestration, using the same catalog policy as the import pipeline."""

from collections.abc import Mapping

from src.core.domain.exceptions import BlenderExecutionUncertainError
from src.core.domain.model_spec import ModelSpec
from src.core.domain.native_revision import (
    CapturedNativeRevision,
    NativeModelSource,
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
        return await self._execute(prepared)

    async def prepare_source(self, run_id: str) -> StagedNativeSource:
        """Prepare an existing job's captured current source; no Blender mutation yet."""
        _, staged = await self._prepare(run_id)
        return staged

    async def prepare_revision(
        self, run_id: str, request: NativeRevisionRequest
    ) -> PreparedNativeRevision:
        """Keep the same captured spec/print target, intent and source through execution."""
        captured = await self.capture_revision(self._artifacts.current(), request)
        return await self.prepare_captured(run_id, captured)

    async def capture_revision(
        self, selected: Mapping[str, object], request: NativeRevisionRequest
    ) -> CapturedNativeRevision:
        """Fingerprint one already selected input before queueing, without copying or Blender."""
        spec, source = await self._artifacts.native_source_for(selected)
        return CapturedNativeRevision(spec, request, source)

    async def prepare_captured(
        self, run_id: str, captured: CapturedNativeRevision
    ) -> PreparedNativeRevision:
        staged = await self._stage(run_id, captured.spec, captured.source)
        return PreparedNativeRevision(captured.spec, captured.request, staged)

    async def execute_captured(
        self, run_id: str, captured: CapturedNativeRevision
    ) -> NativeRevisionResult:
        if self._runner is None:
            raise NativeRevisionError("native execution is not configured")
        return await self._execute(await self.prepare_captured(run_id, captured))

    async def _prepare(self, run_id: str) -> tuple[ModelSpec, StagedNativeSource]:
        selected = self._artifacts.current()
        spec, source = await self._artifacts.native_source_for(selected)
        return spec, await self._stage(run_id, spec, source)

    async def _stage(
        self, run_id: str, spec: ModelSpec, source: NativeModelSource
    ) -> StagedNativeSource:
        staged = await self._staging.stage(spec, source, run_id)
        if staged.source != source:
            raise NativeRevisionError("staged source disagrees with the captured selection")
        return staged

    async def _execute(self, prepared: PreparedNativeRevision) -> NativeRevisionResult:
        if self._runner is None:
            raise NativeRevisionError("native execution is not configured")
        try:
            return await self._runner.execute(prepared)
        except Exception as exc:
            if prepared.staged.directory.split("/")[0] in self._runner.unresolved_run_ids:
                raise BlenderExecutionUncertainError(
                    "native execution completion unconfirmed; verified recovery is required"
                ) from exc
            raise

    async def reconcile_execution(self, run_id: str) -> bool:
        """After the job worker ends, recheck late terminal receipts without replaying it."""
        if self._runner is None:
            return False
        await self._runner.recover_unfinished()
        return run_id not in self._runner.unresolved_run_ids
