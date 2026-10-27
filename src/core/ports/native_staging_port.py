"""A verified source snapshot is storage work, independent of Blender execution."""

from typing import Protocol

from src.core.domain.model_spec import ModelSpec
from src.core.domain.native_revision import NativeModelSource, StagedNativeSource


class NativeStagingPort(Protocol):
    async def stage(
        self, spec: ModelSpec, expected: NativeModelSource, run_id: str
    ) -> StagedNativeSource:
        """Copy the exact expected source into a new, job-relative snapshot."""
        ...
