"""Every registered instance is a hand by the same rules, or it is not registered.

PS-1: any link that satisfies `FingerLinkSpec` composes into a hand and yields
contracts. Parametrised over the registry so a new instance is held to every
rule the day it is added, and refused if the registry is empty, because a
suite over nothing passes for nothing.
"""

from dataclasses import replace

import pytest

from src.core.domain.hand_instances import HAND_INSTANCES
from src.core.planning.hand_plan import hand_plan
from src.core.planning.probe_plan import probe_soundness

SLUGS = sorted(HAND_INSTANCES)


def test_the_registry_holds_the_human_scale_instance() -> None:
    """VOC-4: the compact hand is an instance of the same programme, not a fork."""
    assert "hand-compact" in HAND_INSTANCES


@pytest.mark.parametrize("slug", SLUGS)
def test_every_registered_instance_conforms(slug: str) -> None:
    instance = HAND_INSTANCES[slug]

    # The palm survives its own strict invariants: proportions of a hand,
    # and a thumb that can reach the index fingertip.
    strict = replace(instance.palm, strict=True)
    assert strict.thumb_index_tip_gap_mm < strict.pinch_contact_mm
    assert 0.7 <= strict.finger_to_palm_ratio <= 1.4

    plan = hand_plan(instance)
    assert probe_soundness(instance.palm, plan.probes) == []
    assert plan.layout.fits_bed, plan.layout.footprint_mm
    assert plan.counts.phalanx_part_count == len(instance.phalanx_stls)
    assert len(plan.chains) == len(plan.stations) == plan.counts.row_finger_count + 1


def test_registered_namespaces_never_overlap() -> None:
    prefixes = [hand_plan(instance).naming.prefix for instance in HAND_INSTANCES.values()]

    for one in prefixes:
        for other in prefixes:
            assert one == other or not (one.startswith(other) or other.startswith(one))
