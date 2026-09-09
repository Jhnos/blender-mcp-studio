"""Pure core of the shipped-versus-regenerated package differential.

The framework's first claim is that it reproduces the package that shipped.
STL export is not byte-reproducible (the same generator run twice gave three
different hashes out of four files), so this never compares hashes. It compares
what the package test already pins: triangle count within a sliver budget,
bounding dimensions within a tenth of a millimetre. The shipped manifest is the
only expectation source, so no second table of numbers exists to drift.

The sliver budget exists because Blender's exact boolean solver does not order
its output deterministically: the same compact phalanx built eight times in one
session came back with six distinct vertex orderings from the first union on,
and the cleanup thresholds then dissolved one sliver quad or not — 2976 or 2978
triangles — from run to run. V3 reproduced exactly only because its slivers sit
clear of the thresholds. The budget is two triangles per booleaned part and is
derived from the plan, never typed in; zero stays the default so a mesh whose
budget nobody derived is still held exact.

Fail-closed throughout: a listed mesh the manifest never measured, a mesh that
was not regenerated, a payload that is not an STL, and an empty population are
all failures with a reason, never passes and never exceptions at the call site.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from src.core.domain.hand_instances import HandInstance
from src.core.planning.hand_plan import hand_plan
from src.infrastructure.narrowing import (
    as_finite_number,
    as_positive_int,
    as_sequence,
    as_str_keyed_exact,
)
from src.verification.artifact_files import binary_stl_metrics

#: Same tolerance the package tests use; float32 export noise sits far below it.
DIMENSION_TOLERANCE_MM = 0.1
#: One sliver quad per booleaned part: what the solver's ordering noise can add
#: or remove once the cleanup thresholds have had their say (observed, 2026-09-09).
SLIVER_TRIANGLES_PER_PART = 2


@dataclass(frozen=True, slots=True)
class ExpectedMesh:
    name: str
    triangle_count: int
    dimensions_mm: tuple[float, float, float]
    #: Triangles the regenerated count may differ by, either way. Zero = exact.
    sliver_budget: int = 0


@dataclass(frozen=True, slots=True)
class MeshVerdict:
    name: str
    passed: bool
    reason: str
    measured_triangles: int | None = None
    measured_dimensions_mm: tuple[float, float, float] | None = None


@dataclass(frozen=True, slots=True)
class ReproductionReport:
    verdicts: tuple[MeshVerdict, ...]
    #: Regenerated files the manifest does not list. Reported, never counted.
    unexpected: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return bool(self.verdicts) and all(verdict.passed for verdict in self.verdicts)

    @property
    def summary(self) -> str:
        if not self.verdicts:
            return "vacuous: the manifest lists no meshes, so nothing was compared"
        passed = sum(1 for verdict in self.verdicts if verdict.passed)
        text = f"{passed}/{len(self.verdicts)} meshes reproduce the shipped package"
        if self.unexpected:
            text += "; regenerated but not in the manifest: " + ", ".join(self.unexpected)
        return text


def _dimensions(value: object, name: str) -> tuple[float, float, float]:
    axes = as_sequence(value)
    if axes is None or len(axes) != 3:
        raise ValueError(f"manifest never measured {name}: dimensions_mm must be three numbers")
    x, y, z = (as_finite_number(axis) for axis in axes)
    if x is None or y is None or z is None:
        raise ValueError(f"manifest never measured {name}: dimensions_mm must be three numbers")
    return (x, y, z)


def sliver_budgets(instance: HandInstance) -> dict[str, int]:
    """Two triangles per booleaned part, per shipped STL, from the plan's counts."""
    counts = hand_plan(instance).counts
    per_part = SLIVER_TRIANGLES_PER_PART
    budgets = {name: per_part for name in instance.phalanx_stls}
    budgets[instance.palm_stl] = per_part
    budgets[instance.finger_stl] = per_part * counts.units_per_finger
    budgets[instance.hand_stl] = per_part * (counts.hand_unit_count + 1)
    return budgets


def expected_from_manifest(
    manifest: Mapping[str, object],
    stl_files: Sequence[str],
    sliver_budgets: Mapping[str, int] | None = None,
) -> dict[str, ExpectedMesh]:
    """The meshes a package promises, read from its shipped manifest and nothing else.

    `sliver_budgets` is the one thing not read from the manifest: it comes from
    the plan, and a file it does not name is held exact.
    """
    budgets = sliver_budgets or {}
    files = as_str_keyed_exact(manifest.get("files"))
    if files is None:
        raise ValueError("manifest has no 'files' mapping")
    expected: dict[str, ExpectedMesh] = {}
    for name in stl_files:
        entry = as_str_keyed_exact(files.get(name))
        if entry is None:
            raise ValueError(f"manifest does not list {name}")
        triangles = as_positive_int(entry.get("triangle_count"))
        if triangles is None:
            raise ValueError(f"manifest never measured {name}: triangle_count is missing")
        expected[name] = ExpectedMesh(
            name,
            triangles,
            _dimensions(entry.get("dimensions_mm"), name),
            budgets.get(name, 0),
        )
    return expected


def compare_mesh(expected: ExpectedMesh, payload: bytes | None) -> MeshVerdict:
    """One regenerated mesh against what shipped. `None` means it was not regenerated."""
    name = expected.name
    if payload is None:
        return MeshVerdict(name, False, f"{name}: missing — the generator did not export it")
    try:
        measured = binary_stl_metrics(payload)
    except ValueError as error:
        return MeshVerdict(name, False, f"{name}: unreadable STL ({error})")
    if abs(measured.triangle_count - expected.triangle_count) > expected.sliver_budget:
        return MeshVerdict(
            name,
            False,
            f"{name}: {measured.triangle_count} triangles, manifest says"
            f" {expected.triangle_count} (sliver budget ±{expected.sliver_budget})",
            measured.triangle_count,
            measured.dimensions_mm,
        )
    drift = max(
        abs(got - want)
        for got, want in zip(measured.dimensions_mm, expected.dimensions_mm, strict=True)
    )
    if drift > DIMENSION_TOLERANCE_MM:
        return MeshVerdict(
            name,
            False,
            f"{name}: dimensions {measured.dimensions_mm} vs manifest {expected.dimensions_mm}"
            f" (drift {drift:.3f} mm > {DIMENSION_TOLERANCE_MM})",
            measured.triangle_count,
            measured.dimensions_mm,
        )
    return MeshVerdict(name, True, "", measured.triangle_count, measured.dimensions_mm)


def reproduction_report(
    expected: Mapping[str, ExpectedMesh], payloads: Mapping[str, bytes]
) -> ReproductionReport:
    verdicts = tuple(compare_mesh(mesh, payloads.get(name)) for name, mesh in expected.items())
    unexpected = tuple(sorted(set(payloads) - set(expected)))
    return ReproductionReport(verdicts, unexpected)
