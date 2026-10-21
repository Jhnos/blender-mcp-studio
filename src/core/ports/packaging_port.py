"""Port for writing a reproducible manifest of a design run's output files."""

from __future__ import annotations

from typing import Protocol

from src.core.domain.packaging import PackageManifest


class PackagingPort(Protocol):
    async def package(
        self, run_id: str, spec_name: str, run_dir: str, files: tuple[str, ...]
    ) -> PackageManifest: ...
