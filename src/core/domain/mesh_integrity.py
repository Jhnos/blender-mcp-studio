"""Immutable verdicts for host-side mesh integrity checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MeshVerdict:
    path: str
    vertices: int
    triangles: int
    watertight: bool
    self_intersecting: bool
    error: str | None

    @property
    def passed(self) -> bool:
        return (
            self.error is None
            and self.watertight
            and not self.self_intersecting
            and self.triangles > 0
        )


@dataclass(frozen=True, slots=True)
class MeshIntegrityReport:
    verdicts: tuple[MeshVerdict, ...]

    @property
    def passed(self) -> bool:
        return all(verdict.passed for verdict in self.verdicts)
