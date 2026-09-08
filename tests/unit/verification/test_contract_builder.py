"""The committed contracts are generated artifacts, and this is the proof.

Every value in `hand_v3.json` and `hand_v3_finger.json` used to be typed from
the spec by hand, and one of them drifted to describe a four-phalanx hand. Now
the builder produces them from the plan and this test holds the committed
files to the builder's output, so editing either one alone goes red.
"""

import json
from pathlib import Path

import pytest

from src.core.domain.hand_instances import HAND_INSTANCES
from src.core.planning.hand_plan import hand_plan
from src.verification.contract_builder import contract_mappings, render_contract
from src.verification.generated_artifact_contract import contract_from_mapping

ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "scripts" / "verify" / "contracts"


def _committed(name: str) -> dict[str, object]:
    loaded = json.loads((CONTRACTS / name).read_text())
    assert isinstance(loaded, dict)
    return loaded


@pytest.mark.parametrize("slug", sorted(HAND_INSTANCES))
def test_the_builder_reproduces_the_committed_hand_v3_contracts(slug: str) -> None:
    plan = hand_plan(HAND_INSTANCES[slug])

    generated = contract_mappings(plan, ROOT)

    assert set(generated) == {
        f"{plan.instance.contract_name}.json",
        f"{plan.instance.contract_name}_finger.json",
    }
    for name, mapping in generated.items():
        assert mapping == _committed(name), name
        # And what the verifier parses from each is the same object.
        assert contract_from_mapping(mapping, ROOT) == contract_from_mapping(_committed(name), ROOT)


def test_rendering_is_stable_and_round_trips() -> None:
    plan = hand_plan(HAND_INSTANCES["hand-v3"])

    for name, mapping in contract_mappings(plan, ROOT).items():
        text = render_contract(mapping)
        assert text.endswith("\n") and json.loads(text) == mapping
        assert (CONTRACTS / name).read_text() == text, f"{name} is not the rendered output"


def test_the_hand_contract_carries_the_assembly_claims_and_the_finger_the_kinematics() -> None:
    plan = hand_plan(HAND_INSTANCES["hand-v3"])
    generated = contract_mappings(plan, ROOT)
    hand = generated["hand_v3.json"]["oracle"]
    finger = generated["hand_v3_finger.json"]["oracle"]
    assert isinstance(hand, dict) and isinstance(finger, dict)

    assert "disjoint_groups" in hand and "channel_probes" in hand
    assert "joint_sweep" not in hand and "closure_trajectory" not in hand
    assert "joint_sweep" in finger and "closure_trajectory" in finger
    assert "disjoint_groups" not in finger and "channel_probes" not in finger
    assert hand["expected_shells_per_object"] == 1 == finger["expected_shells_per_object"]


def test_a_spec_change_moves_the_contract() -> None:
    """The whole point: a contract that cannot drift from the spec."""
    from dataclasses import replace

    from src.core.domain.hand_instances import HandInstance

    v3 = HAND_INSTANCES["hand-v3"]
    shifted = replace(v3, palm=replace(v3.palm, finger_gap_mm=8.0))

    hand = contract_mappings(hand_plan(shifted), ROOT)["hand_v3.json"]["oracle"]
    assert isinstance(hand, dict)
    probes = hand["channel_probes"]
    assert isinstance(probes, list) and isinstance(probes[0], dict)
    assert probes[0]["open_points_mm"][0] == [-48.0, -6.6]
    assert isinstance(v3, HandInstance)
