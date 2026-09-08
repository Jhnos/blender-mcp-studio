"""The registry is the only place a hand instance is named.

Everything downstream — the contract builder, the differential, the instance
table guard — reads instances from here. A test that built its own instance
would drift from the one that ships; the guard in `test_docs_hand_framework_figures`
reads this registry for the same reason.
"""

import pytest

from src.core.domain.hand_instances import HAND_INSTANCES, HandInstance
from src.core.domain.palm_v3 import AnthropomorphicPalmSpec


def test_hand_v3_is_registered_under_the_names_its_package_and_contracts_use() -> None:
    v3 = HAND_INSTANCES["hand-v3"]

    assert isinstance(v3, HandInstance)
    assert v3.palm == AnthropomorphicPalmSpec()
    assert (v3.namespace, v3.family) == ("HJ_", "V3")
    assert v3.generator_script == "scripts/model_finger_v3.py"
    assert v3.blend_file == "finger_v3.blend"
    assert v3.stl_files == ("phalanx_mm.stl", "palm_mm.stl", "finger_v3_mm.stl", "hand_v3_mm.stl")
    assert v3.render_files == (
        "finger_v3_assembly.png",
        "finger_v3_joint_detail.png",
        "finger_v3_print_layout.png",
    )
    assert v3.output_dir == "tmp/hand-v3"
    assert v3.contract_name == "hand_v3"


def test_every_registered_instance_has_its_own_namespace() -> None:
    prefixes = [f"{i.namespace}{i.family}_" for i in HAND_INSTANCES.values()]

    assert len(prefixes) == len(set(prefixes))
    for one in prefixes:
        for other in prefixes:
            assert one == other or not one.startswith(other)


def test_the_registry_is_not_empty() -> None:
    """A conformance suite over an empty registry passes for nothing."""
    assert HAND_INSTANCES


def test_an_instance_ships_one_phalanx_mesh_per_part_number() -> None:
    """A gradient finger is two prints; a package with one phalanx file hides the second."""
    from dataclasses import replace

    v3 = HAND_INSTANCES["hand-v3"]
    steeper = replace(v3.palm.finger, moment_arms_mm=(7.1, 6.1))

    with pytest.raises(ValueError, match="part number"):
        replace(v3, slug="hand-v3-gradient", palm=replace(v3.palm, finger=steeper))

    two = replace(
        v3,
        slug="hand-v3-gradient",
        palm=replace(v3.palm, finger=steeper),
        phalanx_stls=("phalanx_1_mm.stl", "phalanx_2_mm.stl"),
    )
    assert two.stl_files[:2] == ("phalanx_1_mm.stl", "phalanx_2_mm.stl")
    assert v3.phalanx_stls == ("phalanx_mm.stl",)
