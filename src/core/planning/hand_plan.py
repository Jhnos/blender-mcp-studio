"""Everything the execution layer and the contract builder need, in one object."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.domain.hand_instances import HandInstance
from src.core.planning.expected_counts import ExpectedCounts, expected_counts
from src.core.planning.layout_plan import LayoutPlan, pack, part_footprints
from src.core.planning.naming import NamingPolicy
from src.core.planning.probe_plan import ProbePlan, probe_plan
from src.core.planning.station_plan import Station, station_plan


@dataclass(frozen=True, slots=True)
class HandPlan:
    instance: HandInstance
    naming: NamingPolicy
    counts: ExpectedCounts
    stations: tuple[Station, ...]
    probes: ProbePlan
    layout: LayoutPlan


def hand_plan(instance: HandInstance) -> HandPlan:
    naming = NamingPolicy(instance.namespace, instance.family)
    palm = instance.palm
    stations = station_plan(palm, naming)
    return HandPlan(
        instance=instance,
        naming=naming,
        counts=expected_counts(palm, naming),
        stations=stations,
        probes=probe_plan(palm, naming, stations),
        layout=pack(part_footprints(palm, naming)),
    )
