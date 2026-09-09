"""What a build of one registered mechanical instance produces.

Deliberately not a hash. The generators are not byte-reproducible — the same
source run twice gives different STL bytes for three of four parts
(`docs/LESSONS_LEARNED.md`, "產生器不是位元組可重現的"). Face count and
dimensions are what survive a re-run, so they are what this DTO carries and
what any regression check compares.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BuiltPart:
    """One exported mesh, named by the file the instance declares for it."""

    name: str
    face_count: int
    dimensions_mm: tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class InstanceBuild:
    """The result of running one instance's generator to completion."""

    slug: str
    output_dir: str
    parts: tuple[BuiltPart, ...]

    @property
    def part_names(self) -> tuple[str, ...]:
        return tuple(part.name for part in self.parts)


@dataclass(frozen=True, slots=True)
class InstanceSummary:
    """A registered instance as the catalog endpoint reports it.

    The declared file list is part of the summary because it is the claim a
    build is checked against; a catalog that only gave slugs would leave the
    caller with no way to know what a build should have produced.
    """

    slug: str
    family: str
    declared_parts: tuple[str, ...]
    output_dir: str
