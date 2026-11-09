"""One-pass declared bead-envelope inspection; no files, firmware or physical adhesion claims."""

from collections.abc import Iterable
from math import inf, isfinite

from src.core.domain.extrusion import (
    BuildVolume,
    ExtrusionInspection,
    ExtrusionObjectStats,
    ExtrusionPath,
    ExtrusionRoleStats,
)

_BOUND_EPSILON_MM = 1e-9  # Floating arithmetic only; not a manufacturing tolerance.
_MAX_FEATURE_ROLES = 64
_MAX_OBJECT_LABELS = 1024


def inspect_extrusions(
    paths: Iterable[ExtrusionPath],
    volume: BuildVolume,
    *,
    require_support: bool = False,
    require_brim: bool = False,
    allow_support: bool = True,
    allow_brim: bool = True,
    expected_object_ids: frozenset[int] | None = None,
) -> ExtrusionInspection:
    if expected_object_ids is not None and (
        not expected_object_ids
        or len(expected_object_ids) > _MAX_OBJECT_LABELS
        or any(type(i) is not int or i < 0 for i in expected_object_ids)
    ):
        raise ValueError("expected object inventory must contain bounded nonnegative labels")
    object_totals: dict[int, tuple[int, int]] = {}
    unassigned = 0
    minimum, maximum = [inf, inf, inf], [-inf, -inf, -inf]
    count, outside, contacts, radius_error = 0, 0, 0, 0.0
    totals: dict[str, tuple[int, float, int]] = {}
    for count, path in enumerate(paths, 1):
        try:
            metrics = path.measure()
        except ValueError as exc:
            raise ValueError(f"deposition path {count}: {exc}") from exc
        if path.role not in totals and len(totals) >= _MAX_FEATURE_ROLES:
            raise ValueError("too many extrusion feature roles for bounded inspection")
        inside = all(
            low >= bed_low - _BOUND_EPSILON_MM and high <= bed_high + _BOUND_EPSILON_MM
            for low, high, bed_low, bed_high in zip(
                metrics.minimum_mm,
                metrics.maximum_mm,
                volume.minimum_mm,
                volume.maximum_mm,
                strict=True,
            )
        )
        bed_contact = (
            inside
            and abs(metrics.minimum_mm[2] - volume.minimum_mm[2]) <= _BOUND_EPSILON_MM
            and metrics.maximum_mm[2] > volume.minimum_mm[2] + _BOUND_EPSILON_MM
        )
        contacts += int(bed_contact)
        previous = totals.get(path.role, (0, 0.0, 0))
        accumulated_length = previous[1] + metrics.xy_length_mm
        if not isfinite(accumulated_length):
            raise ValueError("accumulated extrusion length exceeds finite numerical range")
        totals[path.role] = (
            previous[0] + 1,
            accumulated_length,
            previous[2] + int(bed_contact),
        )
        outside += int(not inside)
        if path.object_id is None:
            unassigned += 1
        else:
            if path.object_id not in object_totals and len(object_totals) >= _MAX_OBJECT_LABELS:
                raise ValueError("too many object labels for bounded inspection")
            previous_object = object_totals.get(path.object_id, (0, 0))
            object_totals[path.object_id] = (
                previous_object[0] + 1,
                previous_object[1] + int(bed_contact),
            )
        for axis in range(3):
            minimum[axis] = min(minimum[axis], metrics.minimum_mm[axis])
            maximum[axis] = max(maximum[axis], metrics.maximum_mm[axis])
        radius_error = max(radius_error, metrics.arc_radius_disagreement_mm)
    roles = tuple(ExtrusionRoleStats(name, *values) for name, values in sorted(totals.items()))
    violations = []
    if not count:
        violations.append("no declared model deposition paths")
    if outside:
        violations.append(f"{outside} deposition paths leave the build envelope")
    if not contacts:
        violations.append("no deposition path has declared bed contact")
    if require_support and not any(
        role.role.startswith("Support") and role.bed_contact_paths for role in roles
    ):
        violations.append("required support has no declared bed-contact paths")
    if require_brim and not any(role.role == "Brim" and role.bed_contact_paths for role in roles):
        violations.append("required brim has no declared bed-contact paths")
    if not allow_support and any(role.role.startswith("Support") and role.paths for role in roles):
        violations.append("support is disabled but support deposition was emitted")
    if not allow_brim and any(role.role == "Brim" and role.paths for role in roles):
        violations.append("brim is disabled but brim deposition was emitted")
    objects = tuple(
        ExtrusionObjectStats(label, *values) for label, values in sorted(object_totals.items())
    )
    if expected_object_ids is not None:
        if set(object_totals) != expected_object_ids:
            violations.append("deposition object labels differ from the expected sliced inventory")
        if unassigned:
            violations.append(f"{unassigned} deposition paths have no object label")
        missing_contact = [o.object_id for o in objects if not o.bed_contact_paths]
        if missing_contact:
            violations.append(
                f"{len(missing_contact)} objects lack declared bed contact: {missing_contact[:8]}"
            )
    return ExtrusionInspection(
        count,
        outside,
        (minimum[0], minimum[1], minimum[2]) if count else None,
        (maximum[0], maximum[1], maximum[2]) if count else None,
        contacts,
        roles,
        radius_error,
        tuple(violations),
        objects,
        unassigned,
    )
