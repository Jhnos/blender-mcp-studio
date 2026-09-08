"""Render furniture as data, so a second model line does not need a second fork.

`scripts/archive/README.md` records why this module exists. Two archived render
modules differ by 77 lines with the same function names in the same order —
they were forked from each other — and the README names the correct way to
revive that line: define a profile carrying prefix, resolution, camera mode,
lights and floor, then let each fork become a constant. Moving the fork back
would put a third near-copy in the live tree, and every future attempt to remove
duplication would have to start by untangling it.

Deliberately free of ``bpy``. A profile is numbers and names; only the render
module turns it into a scene, and keeping the split means these values can be
unit-tested on a machine with no Blender at all.

The prefix is the load-bearing field. It is what keeps one model's camera,
lights and floor out of another model's collision groups and STL exports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

#: ``(suffix, energy, size_mm, location_mm)`` for one area light.
Light = tuple[str, float, float, tuple[float, float, float]]


@runtime_checkable
class StackedAssembly(Protocol):
    """What the render setup actually needs from a specification: how tall it is.

    It was typed as a union of two named specs, which is a list of the callers
    that happened to exist rather than a statement of the requirement — and the
    third caller failed to type-check for no reason anyone could act on. The
    camera and lights aim at the middle of the stack; the middle of the stack is
    the unit count and the pitch. Nothing else is read.
    """

    @property
    def assembly_unit_count(self) -> int: ...

    @property
    def unit_pitch_mm(self) -> float: ...


@dataclass(frozen=True, slots=True)
class PresentationProfile:
    """One model line's look: what it is called, how it is lit, where it is seen from."""

    prefix: str
    resolution: tuple[int, int]
    background_color: tuple[float, float, float]
    curvature_ridge: float
    curvature_valley: float
    floor_size_mm: float
    floor_z_mm: float
    camera_location_mm: tuple[float, float, float]
    ortho_scale_mm: float
    lights: tuple[Light, ...]

    def __post_init__(self) -> None:
        if not self.prefix or not self.prefix.endswith("_"):
            raise ValueError(
                "prefix must be non-empty and end in an underscore, so scene furniture "
                f"cannot collide with another model's: {self.prefix!r}"
            )
        if len(self.resolution) != 2 or any(side <= 0 for side in self.resolution):
            raise ValueError(f"render resolution must be two positive sides: {self.resolution}")
        if self.ortho_scale_mm <= 0:
            raise ValueError("an orthographic camera with no scale sees nothing")
        if self.floor_size_mm <= 0:
            raise ValueError("floor must have a positive size")
        if self.curvature_ridge <= 0 or self.curvature_valley <= 0:
            raise ValueError("cavity factors must be positive")
        if not self.lights:
            raise ValueError("a scene with no lights renders a black frame")
        for name, energy, size_mm, _ in self.lights:
            if not name:
                raise ValueError("every light needs a name suffix")
            if energy <= 0 or size_mm <= 0:
                raise ValueError(f"light {name!r} must have positive energy and size")

    def object_name(self, role: str) -> str:
        """Scene-object name for one role, e.g. ``FLOOR`` -> ``HH_FLOOR``."""
        return f"{self.prefix}{role}"

    @property
    def light_names(self) -> tuple[str, ...]:
        return tuple(self.object_name(name) for name, *_ in self.lights)


#: The live look, driving V5, V6 and both octopus hands. Transcribed from
#: ``hollow_hinge_render.setup_render`` as it stood at V01.08.001. Changing a
#: number here re-renders four delivered models, and no contract would notice:
#: they assert that a PNG exists, not what is inside it.
MECHANICAL_PROFILE = PresentationProfile(
    prefix="HH_",
    resolution=(1200, 1500),
    background_color=(0.008, 0.014, 0.026),
    curvature_ridge=2.0,
    curvature_valley=1.6,
    floor_size_mm=300.0,
    floor_z_mm=-25.0,
    camera_location_mm=(145.0, -270.0, 145.0),
    ortho_scale_mm=226.0,
    lights=(
        ("KEY", 30.0, 80.0, (90.0, -100.0, 190.0)),
        ("FILL", 16.0, 70.0, (-90.0, -35.0, 100.0)),
        ("RIM", 24.0, 60.0, (35.0, 95.0, 175.0)),
    ),
)

#: The hinge-chain line's look, transcribed from
#: ``scripts/archive/hinge_chain_render.setup_render``. Kept as the fork actually
#: was rather than re-invented, so the archived evidence still describes it: a
#: taller, wider frame for a longer assembly, and a camera pulled further back.
FINGER_PROFILE = PresentationProfile(
    prefix="HJ_",
    resolution=(1100, 1300),
    background_color=(0.012, 0.018, 0.032),
    curvature_ridge=1.8,
    curvature_valley=1.4,
    floor_size_mm=360.0,
    floor_z_mm=-32.0,
    camera_location_mm=(190.0, -335.0, 205.0),
    ortho_scale_mm=285.0,
    lights=(
        ("KEY", 28.0, 90.0, (85.0, -110.0, 230.0)),
        ("FILL", 14.0, 75.0, (-105.0, -30.0, 130.0)),
        ("RIM", 22.0, 65.0, (45.0, 105.0, 205.0)),
    ),
)
