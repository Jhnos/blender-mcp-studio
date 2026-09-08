"""Where each chain hangs on the palm, computed once.

`palm_v3_geometry.py` built the thumb's basis matrix twice from the same spec,
in `build_palm` and again in `assemble_hand`. Both were right, and nothing said
they had to stay that way. The palm cuts and the assembly now read one tuple,
and it is checkable without Blender because it is three vectors, not a Matrix.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.domain.finger_v3 import SingleTendonFingerSpec
from src.core.domain.palm_v3 import AnthropomorphicPalmSpec
from src.core.domain.rotation import Axis3
from src.core.planning.naming import NamingPolicy

#: Columns of a rotation: where the chain's local x, y and z point in the world.
Basis = tuple[Axis3, Axis3, Axis3]

IDENTITY: Basis = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


@dataclass(frozen=True, slots=True)
class Station:
    label: str
    origin_mm: Axis3
    basis: Basis
    chain: SingleTendonFingerSpec
    #: How far above the root's origin the chain's base unit sits: the root's
    #: joint offset plus the chain's own, so the knuckle is an ordinary joint.
    lift_mm: float


def _cross(a: Axis3, b: Axis3) -> Axis3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def thumb_basis(palm: AnthropomorphicPalmSpec) -> Basis:
    """(across, pad, axis): the spec's frame completed to a right-handed triad."""
    axis, pad = palm.thumb_frame
    return (_cross(axis, pad), pad, axis)


def station_plan(palm: AnthropomorphicPalmSpec, naming: NamingPolicy) -> tuple[Station, ...]:
    root_offset = palm.finger.link.joint_center_offset_mm
    stations = [
        Station(
            label=naming.station_label(index),
            origin_mm=(x_mm, 0.0, 0.0),
            basis=IDENTITY,
            chain=palm.finger,
            lift_mm=root_offset + palm.finger.link.joint_center_offset_mm,
        )
        for index, x_mm in enumerate(palm.row_finger_x_mm, start=1)
    ]
    stations.append(
        Station(
            label=naming.station_label(None),
            origin_mm=palm.thumb_root_mm,
            basis=thumb_basis(palm),
            chain=palm.thumb,
            lift_mm=root_offset + palm.thumb.link.joint_center_offset_mm,
        )
    )
    return tuple(stations)
