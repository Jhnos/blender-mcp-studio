"""Native provenance is resolved by storage, never by a delivery client's filenames."""

from typing import Protocol

from src.core.domain.model_spec import ModelSpec
from src.core.domain.native_revision import NativeModelSource


class NativeSourcePort(Protocol):
    async def resolve(self, spec: ModelSpec) -> NativeModelSource:
        """Read-time identity receipt; execution must stage/recheck before mutation."""
        ...
