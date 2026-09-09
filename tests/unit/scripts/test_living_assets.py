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
