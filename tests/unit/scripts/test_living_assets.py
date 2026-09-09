"""Malformed animation assets must fail before publishing."""

from copy import deepcopy

import pytest

from scripts.living_asset_contract import actor_spec, validate_actor


def test_complete_four_direction_actor():
    spec = actor_spec("traveler", "旅人")
    validate_actor(spec)
    assert sum(len(c["frames"]) for c in spec["clips"].values()) == 48


@pytest.mark.parametrize("defect", ["direction", "frame", "anchor", "path", "fps"])
def test_actor_contract_rejects(defect):
    spec = deepcopy(actor_spec("traveler", "旅人"))
    if defect == "direction":
        del spec["clips"]["walk-up"]
    elif defect == "frame":
        spec["clips"]["walk-down"]["frames"][0] = 99
    elif defect == "anchor":
        spec["anchor"] = [0, 0]
    elif defect == "path":
        spec["atlas"] = "../private"
    else:
        spec["clips"]["idle-down"]["fps"] = 0
    with pytest.raises(ValueError):
        validate_actor(spec)


def test_full_cast_and_event_vocabulary_are_declared():
    from scripts.living_asset_contract import MARKER_KINDS, ROLES

    assert set(ROLES) == {"traveler", "guide", "guard", "artisan"}
    assert {role["label"] for role in ROLES.values()} == {"旅人", "嚮導", "守衛", "工匠"}
    assert len({role["coat"] for role in ROLES.values()}) == 4
    assert MARKER_KINDS == ("talk", "quest", "deliver", "investigate", "locked", "exit")
    assert len(MARKER_KINDS) * 3 == 18
