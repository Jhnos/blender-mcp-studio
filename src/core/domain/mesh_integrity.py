"""Immutable verdicts for host-side mesh integrity checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MeshVerdict:
    path: str
    vertices: int
    triangles: int
    watertight: bool
    # None means "not evaluated" (the CGAL conversion failed); that never passes.
    self_intersecting: bool | None
    # The path-prefixed reason for any failure other than self-intersection (unreadable,
    # open, nonmanifold, zero-area ...). None means exactly "nothing failed".
    error: str | None

    @property
    def passed(self) -> bool:
        return (
            self.error is None
            and self.watertight
            and self.self_intersecting is False
            and self.triangles > 0
        )


@dataclass(frozen=True, slots=True)
class MeshIntegrityReport:
    verdicts: tuple[MeshVerdict, ...]

    @property
    def passed(self) -> bool:
        return all(verdict.passed for verdict in self.verdicts)
