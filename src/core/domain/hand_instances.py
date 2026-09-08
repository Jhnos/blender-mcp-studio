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
    phalanx_stl: str
    palm_stl: str
    finger_stl: str
    hand_stl: str
    assembly_render: str
    joint_render: str
    layout_render: str
    #: Written into the .blend so the file says what it is and what it does not claim.
    design_note: str

    def __post_init__(self) -> None:
        if not _SLUG.match(self.slug):
            raise ValueError(
                f"an instance slug is lowercase words joined by hyphens, not {self.slug!r}"
            )
        if len(set(self.stl_files)) != len(self.stl_files):
            raise ValueError("two meshes cannot ship under one file name")

    @property
    def stl_files(self) -> tuple[str, ...]:
        return (self.phalanx_stl, self.palm_stl, self.finger_stl, self.hand_stl)

    @property
    def render_files(self) -> tuple[str, ...]:
        return (self.assembly_render, self.joint_render, self.layout_render)

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
        phalanx_stl="phalanx_mm.stl",
        palm_stl="palm_mm.stl",
        finger_stl="finger_v3_mm.stl",
        hand_stl="hand_v3_mm.stl",
        assembly_render="finger_v3_assembly.png",
        joint_render="finger_v3_joint_detail.png",
        layout_render="finger_v3_print_layout.png",
        design_note=(
            "V3 finger: three planar units, both hinge ends on one axis so the stack "
            "goes together unrotated, and one tendon bore per unit at that joint's own "
            "moment arm. Unqualified fit prototype; no grip force, retention or "
            "strength claim. Never printed."
        ),
    ),
}
