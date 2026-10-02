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


def test_feedback_catalog_covers_requested_effects_and_items():
    from scripts.living_asset_contract import feedback_catalog, validate_feedback_catalog

    catalog = feedback_catalog()
    validate_feedback_catalog(catalog)
    assert {x["id"] for x in catalog["effects"]} == {
        "pickup",
        "unlock",
        "complete",
        "footsteps",
        "teleport",
        "blocked",
    }
    assert {x["id"] for x in catalog["items"]} == {
        "key",
        "letter",
        "potion",
        "purse",
        "tool",
        "parcel",
    }
    assert sum(len(x["frames"]) for x in catalog["effects"]) == 48
    assert all(not x["loop"] for x in catalog["effects"])


@pytest.mark.parametrize(
    "defect",
    [
        "missing",
        "duplicate",
        "frames",
        "timing",
        "nan",
        "path",
        "anchor",
        "icon",
        "loop",
        "schema-bool",
        "frame-bool",
    ],
)
def test_feedback_catalog_rejects_unpublishable_metadata(defect):
    from scripts.living_asset_contract import feedback_catalog, validate_feedback_catalog

    catalog = feedback_catalog()
    effect = catalog["effects"][0]
    if defect == "missing":
        catalog["effects"].pop()
    elif defect == "duplicate":
        catalog["items"][-1] = deepcopy(catalog["items"][0])
    elif defect == "frames":
        effect["frames"][-1] = 0
    elif defect == "timing":
        effect["duration_ms"] = 0
    elif defect == "nan":
        effect["scale"] = float("nan")
    elif defect == "path":
        effect["atlas"] = "../secret"
    elif defect == "anchor":
        catalog["items"][0]["ground"]["anchor"] = [0, 0]
    elif defect == "icon":
        catalog["items"][0]["inventory"]["size"] = [128, 192]
    elif defect == "schema-bool":
        catalog["schema_version"] = True
    elif defect == "frame-bool":
        effect["frames"][0] = False
    else:
        effect["loop"] = True
    with pytest.raises(ValueError):
        validate_feedback_catalog(catalog)
