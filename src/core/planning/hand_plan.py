"""Everything the execution layer and the contract builder need, in one object.

The executor reads this and nothing else: no spec, no arithmetic, no literal.
Every tolerance a gate applies and every key the scene is stamped with is a
field here, so the scan that keeps literals out of `scripts/hand_*.py` has
nothing to forgive.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.domain.hand_instances import HandInstance
from src.core.planning.expected_counts import ExpectedCounts, expected_counts
from src.core.planning.layout_plan import Footprint, LayoutPlan, pack, part_footprints
from src.core.planning.naming import NamingPolicy
from src.core.planning.palm_plan import PalmPlan, palm_plan
from src.core.planning.phalanx_plan import FingerPlan, finger_plan
from src.core.planning.presentation_plan import PresentationPlan, presentation_plan
from src.core.planning.probe_plan import ProbePlan, probe_plan
from src.core.planning.station_plan import Station, station_plan


@dataclass(frozen=True, slots=True)
class Tolerances:
    #: A palm root that misses the fork's height by more than this cannot be
    #: coaxial with anything; the hand cannot be assembled.
    knuckle_mm: float = 0.5
    #: A built part whose laid-flat footprint differs from the planned one by
    #: more than this means the plan and the geometry have parted.
    footprint_mm: float = 0.5


@dataclass(frozen=True, slots=True)
class SceneKeys:
    stations: str
    phalanx_names: str
    design_note: str


@dataclass(frozen=True, slots=True)
class HandPlan:
    instance: HandInstance
    naming: NamingPolicy
    counts: ExpectedCounts
    stations: tuple[Station, ...]
    #: One finger plan per station, aligned with `stations`.
    chains: tuple[FingerPlan, ...]
    palm: PalmPlan
    probes: ProbePlan
    #: What each printed part measures laid flat, from the spec; the executor
    #: checks the built parts against these before laying anything out.
    footprints: tuple[Footprint, ...]
    layout: LayoutPlan
    presentation: PresentationPlan
    scene_keys: SceneKeys
    tolerances: Tolerances
    #: Height the palm's roots must reach: the fork bore plus the lug's radius.
    knuckle_reach_mm: float

    @property
    def loose_finger(self) -> FingerPlan:
        """The finger exported on its own: the first station's chain."""
        return self.chains[0]


def hand_plan(instance: HandInstance) -> HandPlan:
    naming = NamingPolicy(instance.namespace, instance.family)
    palm = instance.palm
    link = palm.finger.link
    stations = station_plan(palm, naming)
    footprints = part_footprints(palm, naming)
    return HandPlan(
        instance=instance,
        naming=naming,
        counts=expected_counts(palm, naming),
        stations=stations,
        chains=tuple(finger_plan(station.chain, naming) for station in stations),
        palm=palm_plan(palm, naming, stations),
        probes=probe_plan(palm, naming, stations),
        footprints=footprints,
        layout=pack(footprints),
        presentation=presentation_plan(instance, palm),
        scene_keys=SceneKeys(
            stations=naming.scene_key("HAND_STATIONS"),
            phalanx_names=naming.scene_key("PHALANX_NAMES"),
            design_note=naming.scene_key("DESIGN_NOTE"),
        ),
        tolerances=Tolerances(),
        knuckle_reach_mm=link.joint_center_offset_mm + link.lug_outer_diameter_mm / 2,
    )
