"""The registry: the only place a hand instance is named.

An instance is one palm spec, one namespace to build it under, and the files it
ships as. The contract builder, the reproduction differential and the instance
table guard all read from here, so there is one answer to "what is hand-v3".

Two instances are registered. `hand-v3` ships. `hand-v3-gradient` is a
verification fixture: V3's own link with the steepest gradient its moment-arm
window allows, so that "a finger can be two part numbers" is proved on the
real machine by a controlled differential — same link, same palm, only the
arms differ — rather than asserted. It has no package and never will.

`hand-compact` is the human-scale hand: the bearingless 2 mm-pin link, a
15 mm-deep body, and a moment-arm gradient that closes the joints in order.
Its thumb placement was swept under `strict=True` for reach and then for
rest clearance, after the reach-only pick brushed a finger on the real
machine; both sweeps are documented in docs/hand-framework/v8-results.md. Registered, contracted, never published
until the user accepts the renders (DEFERRALS D-008).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.core.domain.compact_link import CompactHingeLinkSpec
from src.core.domain.finger_v3 import SingleTendonFingerSpec
from src.core.domain.hinge_chain import HingePhalanxSpec
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
    #: One mesh per part number, base part first. A gradient finger is two
    #: prints; a package with one phalanx file would hide the second.
    phalanx_stls: tuple[str, ...]
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
        parts = self.palm.finger.phalanx_part_count
        if len(self.phalanx_stls) != parts:
            raise ValueError(
                f"{self.slug} is {parts} phalanx part number(s) but ships "
                f"{len(self.phalanx_stls)} phalanx mesh(es); one file per part number"
            )
        if len(set(self.stl_files)) != len(self.stl_files):
            raise ValueError("two meshes cannot ship under one file name")

    @property
    def stl_files(self) -> tuple[str, ...]:
        return (*self.phalanx_stls, self.palm_stl, self.finger_stl, self.hand_stl)

    @property
    def render_files(self) -> tuple[str, ...]:
        return (self.assembly_render, self.joint_render, self.layout_render)

    @property
    def output_dir(self) -> str:
        return f"tmp/{self.slug}"

    @property
    def contract_name(self) -> str:
        return self.slug.replace("-", "_")


_V3_LINK = HingePhalanxSpec(joint_count=2, joint_center_offset_mm=27.0)
#: 5.5 / 3.6 sits inside the compact window of 3.15–5.55 with the base joint on
#: the longest arm, so the moment arms — not only the springs — order the closure.
_COMPACT_FINGER = SingleTendonFingerSpec(
    link=CompactHingeLinkSpec(), moment_arms_mm=(5.5, 3.6), spring_stiffness_ratio=(1.0, 1.6)
)

HAND_INSTANCES: dict[str, HandInstance] = {
    "hand-v3": HandInstance(
        slug="hand-v3",
        palm=AnthropomorphicPalmSpec(),
        namespace="HJ_",
        family="V3",
        generator_script="scripts/model_finger_v3.py",
        blend_file="finger_v3.blend",
        phalanx_stls=("phalanx_mm.stl",),
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
    "hand-v3-gradient": HandInstance(
        slug="hand-v3-gradient",
        # The window on this link is 6.05–7.20 mm; 7.1 and 6.1 are the steepest
        # gradient that clears both ends with a margin the float arithmetic keeps.
        palm=AnthropomorphicPalmSpec(
            finger=SingleTendonFingerSpec(link=_V3_LINK, moment_arms_mm=(7.1, 6.1)),
        ),
        namespace="HG_",
        family="V3G",
        generator_script="scripts/model_hand_v3_gradient.py",
        blend_file="hand_v3_gradient.blend",
        phalanx_stls=("phalanx_base_mm.stl", "phalanx_distal_mm.stl"),
        palm_stl="palm_mm.stl",
        finger_stl="finger_gradient_mm.stl",
        hand_stl="hand_gradient_mm.stl",
        assembly_render="gradient_assembly.png",
        joint_render="gradient_joint_detail.png",
        layout_render="gradient_print_layout.png",
        design_note=(
            "Verification fixture, not a deliverable: V3's link with moment arms 7.1 "
            "and 6.1 mm, so the finger is two part numbers. Exists to prove the "
            "generator and the contracts handle a gradient. Never printed, never published."
        ),
    ),
    "hand-compact": HandInstance(
        slug="hand-compact",
        # Swept twice under strict=True. The first sweep optimised reach alone
        # and its pick brushed the third finger with the straight thumb on the
        # real machine (8 overlapping faces). The second sweep adds the rest
        # clearance: this placement clears every straight finger by 3.48 mm
        # (V3: 2.49), brings the tips within 1.08 mm on the coarse grid, and
        # keeps the finger-to-palm ratio at 1.14. The root sits at the plate's
        # own depth, the derived default, as V3's does.
        palm=AnthropomorphicPalmSpec(
            finger=_COMPACT_FINGER,
            thumb=_COMPACT_FINGER,
            thumb_offset_mm=24.0,
            thumb_base_drop_mm=22.0,
            thumb_opposition_deg=25.0,
            thumb_palmar_tilt_deg=-10.0,
            strict=True,
        ),
        namespace="HK_",
        family="COMPACT",
        generator_script="scripts/model_hand_compact.py",
        blend_file="hand_compact.blend",
        phalanx_stls=("phalanx_base_mm.stl", "phalanx_distal_mm.stl"),
        palm_stl="palm_mm.stl",
        finger_stl="finger_compact_mm.stl",
        hand_stl="hand_compact_mm.stl",
        assembly_render="compact_assembly.png",
        joint_render="compact_joint_detail.png",
        layout_render="compact_print_layout.png",
        design_note=(
            "Human-scale hand on the compact link: 2 mm pin, no bearing, 15 mm-deep "
            "body, moment arms 5.5 / 3.6 mm so the joints close from the base. Two "
            "phalanx part numbers. Fit prototype; no grip force claim. Never printed."
        ),
    ),
}
