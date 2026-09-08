"""A hand package is its registered instance's files, typed once.

`PACKAGES["hand-v3"]` used to list every file name a second time beside the
generator that wrote them. With two hand instances that is two places to
drift; the package is now derived from the registry and this holds it there.
"""

from scripts.publish_print_package import PACKAGES
from src.core.domain.hand_instances import HAND_INSTANCES


def test_hand_packages_are_their_registered_instances() -> None:
    for slug in ("hand-v3", "hand-compact"):
        package = PACKAGES[slug]
        instance = HAND_INSTANCES[slug]

        assert package.generator == instance.generator_script
        assert package.stl_files == instance.stl_files
        assert package.blend_file == instance.blend_file
        assert package.render_files == instance.render_files
        assert package.contracts == (
            f"scripts/verify/contracts/{instance.contract_name}.json",
            f"scripts/verify/contracts/{instance.contract_name}_finger.json",
        )


def test_the_shipped_v3_package_keeps_its_names() -> None:
    """The manifest under models/hand-v3 pins these; the factory may not move them."""
    package = PACKAGES["hand-v3"]

    assert package.revision == "hand-V3"
    assert package.generator == "scripts/model_finger_v3.py"
    assert package.stl_files == (
        "phalanx_mm.stl",
        "palm_mm.stl",
        "finger_v3_mm.stl",
        "hand_v3_mm.stl",
    )
