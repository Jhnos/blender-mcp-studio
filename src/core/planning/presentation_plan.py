"""What the renders show and how they are framed, decided before Blender opens.

Camera positions, framing margins, colours and captions were literals inside
the bpy presentation module. They are composition, not geometry, but they are
still numbers an executor is not allowed to invent, so they live here with the
V3 values as defaults and the executor reads them.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.domain.hand_instances import HandInstance
from src.core.domain.palm_v3 import AnthropomorphicPalmSpec
from src.core.domain.rotation import Axis3

#: The floor sits this far under a view's lowest point, so parts never float.
FLOOR_CLEARANCE_MM = 2.0
#: Parts are printed on their side: a quarter turn about this axis.
LAY_FLAT_AXIS = "X"

Rgba = tuple[float, float, float, float]

_NUMBER_WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


@dataclass(frozen=True, slots=True)
class Palette:
    body: Rgba
    alt: Rgba
    floor: Rgba
    label: Rgba


@dataclass(frozen=True, slots=True)
class Framing:
    """Frame a subject from its measured extent: margin × the larger of width and
    height-scaled-to-aspect, with the eye placed at these multiples of the frame."""

    margin: float
    aspect: float
    eye: Axis3


@dataclass(frozen=True, slots=True)
class ViewPlan:
    file_name: str
    #: `hand`, `finger` or `layout`: which object set the executor shows.
    subject: str
    title: str
    location_mm: Axis3 | None = None
    target_mm: Axis3 | None = None
    scale_mm: float | None = None
    framing: Framing | None = None
    label_offset: float = 0.0


@dataclass(frozen=True, slots=True)
class PresentationPlan:
    views: tuple[ViewPlan, ...]
    palette: Palette
    floor_clearance_mm: float
    lay_flat_axis: str


V3_PALETTE = Palette(
    body=(0.86, 0.80, 0.68, 1.0),
    alt=(0.72, 0.66, 0.55, 1.0),
    floor=(0.05, 0.06, 0.08, 1.0),
    label=(0.95, 0.95, 0.95, 1.0),
)


def presentation_plan(instance: HandInstance, palm: AnthropomorphicPalmSpec) -> PresentationPlan:
    link = palm.finger.link
    row = len(palm.row_finger_x_mm)
    units = link.assembly_unit_count
    return PresentationPlan(
        views=(
            ViewPlan(
                file_name=instance.assembly_render,
                subject="hand",
                title=(
                    f"{instance.family} hand: {_NUMBER_WORDS[row]} fingers, "
                    "an opposed thumb, one tendon each"
                ),
                # Framed from the measured extent: at a fixed 260 the vertical
                # field was 204 mm against a 229 mm finger and the tips were out
                # of frame in every render taken.
                framing=Framing(margin=1.25, aspect=1400 / 1100, eye=(0.9, -1.6, 0.25)),
            ),
            ViewPlan(
                file_name=instance.joint_render,
                subject="finger",
                title="Both hinge ends on one axis",
                location_mm=(110.0, -150.0, 55.0),
                target_mm=(0.0, 0.0, link.unit_pitch_mm),
                scale_mm=110.0,
                # A vertical stack up the middle of frame; a centred caption
                # sits behind it, and the empty space is to the side.
                label_offset=-0.30,
            ),
            ViewPlan(
                file_name=instance.layout_render,
                subject="layout",
                title=f"Print layout: one plate, {_NUMBER_WORDS[units]} phalanges and the palm",
                # Straight down. Seen from an angle one row projects onto the
                # next and parts 11 mm apart read as overlapping.
                location_mm=(0.0, 0.0, 420.0),
                target_mm=(0.0, 0.0, 0.0),
                scale_mm=320.0,
            ),
        ),
        palette=V3_PALETTE,
        floor_clearance_mm=FLOOR_CLEARANCE_MM,
        lay_flat_axis=LAY_FLAT_AXIS,
    )
