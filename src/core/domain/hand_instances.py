"""The registry: the only place a hand instance is named.

An instance is one palm spec, one namespace to build it under, and the files it
ships as. The contract builder, the reproduction differential and the instance
table guard all read from here, so there is one answer to "what is hand-v3".

Only V3 is registered. The compact instance's spec exists (`CompactHingeLinkSpec`)
but its palm placement has not been swept, and registering a palm that fails
its own invariants is not registering an instance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.core.domain.palm_v3 import AnthropomorphicPalmSpec

_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


@dataclass(frozen=True, slots=True)
class HandInstance:
    slug: str
    palm: AnthropomorphicPalmSpec
    #: What `run_generator` clears by, and the family inside it — see `NamingPolicy`.
    namespace: str
    family: str
    #: The entry point a contract runs. Kept by name because contracts, the
    #: manifest and the package tests all pin it.
    generator_script: str
    blend_file: str
    stl_files: tuple[str, ...]
    render_files: tuple[str, ...]

    def __post_init__(self) -> None:
        if not _SLUG.match(self.slug):
            raise ValueError(
                f"an instance slug is lowercase words joined by hyphens, not {self.slug!r}"
            )
        if not self.stl_files:
            raise ValueError("an instance ships at least one mesh")

    @property
    def output_dir(self) -> str:
        return f"tmp/{self.slug}"

    @property
    def contract_name(self) -> str:
        return self.slug.replace("-", "_")


HAND_INSTANCES: dict[str, HandInstance] = {
    "hand-v3": HandInstance(
        slug="hand-v3",
        palm=AnthropomorphicPalmSpec(),
        namespace="HJ_",
        family="V3",
        generator_script="scripts/model_finger_v3.py",
        blend_file="finger_v3.blend",
        stl_files=("phalanx_mm.stl", "palm_mm.stl", "finger_v3_mm.stl", "hand_v3_mm.stl"),
        render_files=(
            "finger_v3_assembly.png",
            "finger_v3_joint_detail.png",
            "finger_v3_print_layout.png",
        ),
    ),
}
