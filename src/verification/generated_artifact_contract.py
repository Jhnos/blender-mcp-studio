"""Pure contract parsing and evidence assessment for generated Blender artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from src.infrastructure.narrowing import (
    as_finite_number,
    as_mapping,
    as_nonempty_str,
    as_positive_int,
    as_sequence,
    as_str_keyed_exact,
    required,
)


@dataclass(frozen=True, slots=True)
class CollisionExpectation:
    prefix: str
    expected_count: int


@dataclass(frozen=True, slots=True)
class JointSweepExpectation:
    master_object: str
    pivot_offset_mm: float
    axis: str
    mating_twist_deg: float
    angles_deg: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class OracleExpectation:
    object_prefix: str
    expected_count: int
    expected_rotations_deg: tuple[float, ...]
    scene_list_property: str
    expected_scene_list: tuple[str, ...]
    center_probe_object: str
    collision_groups: tuple[CollisionExpectation, ...]
    #: Whether a ray up the probe object's axis should find a clear channel.
    #: True for every hollow body — V5, V6 and both octopus hands carry a cable
    #: channel down the middle. A finger does not, and cannot: a channel there
    #: would cut through the pin bores. The expectation moves rather than the
    #: check disappearing, because a measurement nobody makes is a failure here,
    #: not a skip, and "solid on the axis" is itself an assertion worth holding.
    center_channel_expected_open: bool = True
    joint_sweep: JointSweepExpectation | None = None
    #: Extra bores to prove open, as (x, y) in the probe object's own coordinates.
    #: The centre probe answers one axis; a palm that carries a bore per arm needs one
    #: ray each, and an empty tuple means the contract makes no claim about them.
    bore_probe_points_mm: tuple[tuple[float, float], ...] = ()
    #: Prefixes whose objects must not touch any object of another listed
    #: prefix. Collision groups only compare adjacent units inside one group,
    #: so the digit that crosses in front of the others was measured against
    #: nobody. Absent means no claim; declared and unmeasured is a FAIL.
    disjoint_groups: tuple[str, ...] = ()
    channel_probes: tuple[ChannelProbe, ...] = ()
    #: How many separate solids each prefixed object is allowed to be. Absent
    #: means no claim. This is the quantity no per-face check can see: two
    #: disconnected pieces are each watertight, each manifold, and together they
    #: are not a part.
    expected_shells_per_object: int | None = None


@dataclass(frozen=True, slots=True)
class ChannelProbe:
    """Rays down one object's bores, with the control that makes them mean something.

    `open_points_mm` must all miss and `solid_points_mm` must all hit. A miss
    alone says nothing — a ray aimed past the part misses too, which is how
    this project once reported five open bores through empty air.
    """

    object_name: str
    axis: str
    open_points_mm: tuple[tuple[float, float], ...]
    solid_points_mm: tuple[tuple[float, float], ...]

    @property
    def key(self) -> str:
        return f"{self.object_name}|{self.axis}"


@dataclass(frozen=True, slots=True)
class ReadinessExpectation:
    selection_prefix: str
    expected_selection_count: int
    forbidden_issue_codes: tuple[str, ...]
    #: Bed the print layout has to fit inside, (x, y) in mm. Absent means the
    #: contract makes no claim about how big the plate is; present means a
    #: missing measurement is a FAIL, because a layout that overruns the bed is
    #: found by a person at the slicer and by nobody before them.
    max_footprint_mm: tuple[float, float] | None = None


@dataclass(frozen=True, slots=True)
class GeneratedArtifactContract:
    name: str
    generator_script: Path
    reload_modules: tuple[str, ...]
    artifacts: tuple[Path, ...]
    oracle: OracleExpectation
    readiness: ReadinessExpectation


def _required_mapping(source: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = mapping_value(source, key)
    if value is None:
        raise ValueError(f"{key} must be an object")
    return value


def _required_string(source: Mapping[str, object], key: str) -> str:
    return required(
        source.get(key),
        as_nonempty_str,
        message=f"{key} must be a non-empty string",
        error=ValueError,
    )


def _required_positive_int(source: Mapping[str, object], key: str) -> int:
    return required(
        source.get(key),
        as_positive_int,
        message=f"{key} must be a positive integer",
        error=ValueError,
    )


def _required_strings(source: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = sequence_value(source, key)
    if not value:
        raise ValueError(f"{key} must be a non-empty string array")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{key} must contain only non-empty strings")
    return tuple(item for item in value if isinstance(item, str))


def _required_numbers(source: Mapping[str, object], key: str) -> tuple[float, ...]:
    value = sequence_value(source, key)
    if not value:
        raise ValueError(f"{key} must be a non-empty number array")
    narrowed = tuple(as_finite_number(item) for item in value)
    if any(item is None for item in narrowed):
        raise ValueError(f"{key} must contain only finite numbers")
    return tuple(item for item in narrowed if item is not None)


def _joint_sweep(source: Mapping[str, object]) -> JointSweepExpectation | None:
    if "joint_sweep" not in source:
        return None
    raw = _required_mapping(source, "joint_sweep")
    axis = _required_string(raw, "axis")
    if axis not in ("X", "Y", "Z"):
        raise ValueError("joint_sweep axis must be X, Y or Z")
    numbers = _required_numbers(
        {"values": [raw.get("pivot_offset_mm"), raw.get("mating_twist_deg")]}, "values"
    )
    if numbers[0] <= 0:
        raise ValueError("joint_sweep pivot_offset_mm must be positive")
    return JointSweepExpectation(
        _required_string(raw, "master_object"),
        numbers[0],
        axis,
        numbers[1],
        _required_numbers(raw, "angles_deg"),
    )


def mapping_value(source: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    """A mapping under `key`, or None — narrowed through the SSOT, never `isinstance`."""
    return as_str_keyed_exact(source.get(key))


def sequence_value(source: Mapping[str, object], key: str) -> list[object] | None:
    """A non-text sequence under `key`, or None. Absent and malformed look the same."""
    narrowed = as_sequence(source.get(key))
    return None if narrowed is None else list(narrowed)


def _resolve_path(project_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else project_root / path


def _optional_flag(source: Mapping[str, object], key: str, *, default: bool) -> bool:
    """Read a boolean the contract may omit, refusing anything that is not one.

    A string "false" or a 0 would quietly become truthy, and the whole point of
    this field is that a contract states what it expects rather than leaving it
    to be inferred.
    """
    if key not in source:
        return default
    value = source[key]
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be true or false when present")
    return value


def _point_pairs(
    source: Mapping[str, object], key: str, *, required: bool
) -> tuple[tuple[float, float], ...]:
    entries = sequence_value(source, key)
    if not entries:
        if required:
            raise ValueError(f"{key} must be a non-empty list of two-number points")
        return ()
    points: list[tuple[float, float]] = []
    for entry in entries:
        pair = as_sequence(entry)
        if pair is None or len(pair) != 2:
            raise ValueError(f"each {key} entry must be a two-number list")
        first, second = (as_finite_number(value) for value in pair)
        if first is None or second is None:
            raise ValueError(f"{key} coordinates must be finite numbers")
        points.append((first, second))
    return tuple(points)


def _channel_probes(source: Mapping[str, object]) -> tuple[ChannelProbe, ...]:
    """Optional bore probes. Both halves are required per probe, by design."""
    if "channel_probes" not in source:
        return ()
    entries = sequence_value(source, "channel_probes")
    if not entries:
        raise ValueError("channel_probes must be a non-empty list when present")
    probes: list[ChannelProbe] = []
    for entry in entries:
        mapping = as_mapping(entry)
        if mapping is None:
            raise ValueError("each channel probe must be a mapping")
        axis = _required_string(mapping, "axis").upper()
        if axis not in ("X", "Y", "Z"):
            raise ValueError("a channel probe's axis must be X, Y or Z")
        probes.append(
            ChannelProbe(
                object_name=_required_string(mapping, "object"),
                axis=axis,
                open_points_mm=_point_pairs(mapping, "open_points_mm", required=True),
                solid_points_mm=_point_pairs(mapping, "solid_points_mm", required=True),
            )
        )
    keys = [probe.key for probe in probes]
    if len(set(keys)) != len(keys):
        raise ValueError("two channel probes share one object and axis")
    return tuple(probes)


def _disjoint_groups(source: Mapping[str, object]) -> tuple[str, ...]:
    """Optional list of object prefixes that must not intersect one another."""
    if "disjoint_groups" not in source:
        return ()
    groups = _required_strings(source, "disjoint_groups")
    if len(groups) < 2:
        raise ValueError("disjoint_groups needs at least two prefixes to compare")
    if len(set(groups)) != len(groups):
        raise ValueError("disjoint_groups must not repeat a prefix")
    return groups


def _max_footprint(source: Mapping[str, object]) -> tuple[float, float] | None:
    """Optional (x, y) bed size in mm. Absent means no claim; malformed raises."""
    if "max_footprint_mm" not in source:
        return None
    pair = as_sequence(source.get("max_footprint_mm"))
    if pair is None or len(pair) != 2:
        raise ValueError("max_footprint_mm must be a two-number list when present")
    x, y = (as_finite_number(value) for value in pair)
    if x is None or y is None or x <= 0 or y <= 0:
        raise ValueError("max_footprint_mm must be two positive finite numbers")
    return (x, y)


def _bore_probe_points(source: Mapping[str, object]) -> tuple[tuple[float, float], ...]:
    """Optional list of (x, y) probe points. Absent means no claim; malformed raises.

    Narrowed through the SSOT rather than `isinstance`, so a JSON list of anything is
    rebuilt element by element instead of arriving as a silent `list[Any]`.
    """
    if "bore_probe_points_mm" not in source:
        return ()
    entries = sequence_value(source, "bore_probe_points_mm")
    if not entries:
        raise ValueError("bore_probe_points_mm must be a non-empty list when present")
    points: list[tuple[float, float]] = []
    for entry in entries:
        pair = as_sequence(entry)
        if pair is None or len(pair) != 2:
            raise ValueError("each bore probe point must be a two-number list")
        first, second = (as_finite_number(value) for value in pair)
        if first is None or second is None:
            raise ValueError("bore probe coordinates must be finite numbers")
        points.append((first, second))
    return tuple(points)


def contract_from_mapping(
    source: Mapping[str, object], project_root: Path
) -> GeneratedArtifactContract:
    name = _required_string(source, "name")
    generator_script = _resolve_path(project_root, _required_string(source, "generator_script"))
    reload_modules = _required_strings(source, "reload_modules")
    artifacts = tuple(
        _resolve_path(project_root, item) for item in _required_strings(source, "artifacts")
    )

    oracle_source = _required_mapping(source, "oracle")
    collision_source = sequence_value(oracle_source, "collision_groups")
    if not collision_source:
        raise ValueError("collision_groups must be a non-empty object array")
    collision_groups: list[CollisionExpectation] = []
    for item in collision_source:
        record = mapping_value({"record": item}, "record")
        if record is None:
            raise ValueError("collision_groups must contain only objects")
        collision_groups.append(
            CollisionExpectation(
                prefix=_required_string(record, "prefix"),
                expected_count=_required_positive_int(record, "expected_count"),
            )
        )
    oracle = OracleExpectation(
        object_prefix=_required_string(oracle_source, "object_prefix"),
        expected_count=_required_positive_int(oracle_source, "expected_count"),
        expected_rotations_deg=_required_numbers(oracle_source, "expected_rotations_deg"),
        scene_list_property=_required_string(oracle_source, "scene_list_property"),
        expected_scene_list=_required_strings(oracle_source, "expected_scene_list"),
        center_probe_object=_required_string(oracle_source, "center_probe_object"),
        center_channel_expected_open=_optional_flag(
            oracle_source, "center_channel_expected_open", default=True
        ),
        collision_groups=tuple(collision_groups),
        joint_sweep=_joint_sweep(oracle_source),
        bore_probe_points_mm=_bore_probe_points(oracle_source),
        disjoint_groups=_disjoint_groups(oracle_source),
        channel_probes=_channel_probes(oracle_source),
        expected_shells_per_object=(
            _required_positive_int(oracle_source, "expected_shells_per_object")
            if "expected_shells_per_object" in oracle_source
            else None
        ),
    )
    if len(oracle.expected_rotations_deg) != oracle.expected_count:
        raise ValueError("expected_rotations_deg length must match expected_count")

    readiness_source = _required_mapping(source, "readiness")
    readiness = ReadinessExpectation(
        selection_prefix=_required_string(readiness_source, "selection_prefix"),
        expected_selection_count=_required_positive_int(
            readiness_source, "expected_selection_count"
        ),
        forbidden_issue_codes=_required_strings(readiness_source, "forbidden_issue_codes"),
        max_footprint_mm=_max_footprint(readiness_source),
    )
    return GeneratedArtifactContract(
        name=name,
        generator_script=generator_script,
        reload_modules=reload_modules,
        artifacts=artifacts,
        oracle=oracle,
        readiness=readiness,
    )
