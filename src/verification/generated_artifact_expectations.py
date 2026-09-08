"""What a generated-artifact contract *is*: the shapes, with no parsing.

Split out of `generated_artifact_contract` at its hard line cap. The seam is
the usual one and it held: these are frozen value objects that describe what a
model must satisfy, while the module they came from turns untrusted JSON into
them. Reading one never requires reading the other.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
    closure_trajectory: ClosureTrajectory | None = None


@dataclass(frozen=True, slots=True)
class ClosureTrajectory:
    """One coordinated closing motion, not one joint's arc.

    The per-joint sweep proves each arc is clear on its own. A finger closes
    every joint at once, and two joints each half-flexed reach places neither
    visits alone, so the trajectory is swept as a whole and the shares say how
    the motion is distributed.
    """

    chain_prefix: str
    pivot_offset_mm: float
    axis: str
    travel_shares: tuple[float, ...]
    full_travel_deg: float
    steps: int


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
