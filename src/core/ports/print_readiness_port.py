"""Outgoing port for inspecting a scene's 3D-print readiness."""

from __future__ import annotations

from typing import Protocol

from src.core.domain.print_readiness import (
    PrintInspection,
    PrintReadinessReport,
    PrintReadinessSpec,
)


class PrintReadinessPort(Protocol):
    async def inspect(self, spec: PrintReadinessSpec) -> PrintInspection: ...


class PrintReadinessQueryPort(Protocol):
    """Incoming application boundary shared by REST and MCP delivery."""

    async def check(self, spec: PrintReadinessSpec) -> PrintReadinessReport: ...
