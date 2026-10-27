"""The two existing-part changes from the measured screen-clamp study.

No source/version/path choice or Boolean implementation lives here. Coordinates
are mm in the source's axis-aligned X hinge frame. The stop's top offset is the
measured datum of the original fixed lug, not a claim of manufacturing tolerance.
"""

from dataclasses import dataclass
from math import isfinite, pi

from src.core.domain.lab_station import Point
from src.core.domain.native_revision import NativeRevisionError
from src.core.planning.csg import Cylinder


@dataclass(frozen=True, slots=True)
class ScreenRevisionPlan:
    pivot_mm: Point
    bore: Cylinder
    bore_phase_rad: float
    stop_rings_mm: tuple[tuple[Point, ...], ...]
    modified_owners: tuple[str, str] = ("LS_FIT_lcd_back", "LS_FIT_lid")
    triangulate_owners: tuple[str, ...] = (
        "RH_-101_M3_screw",
        "RH_101_M3_screw",
        "S_capillary_yaw_bolt",
    )
    wrist_owner: str = "TE_pH_temp_three_point_wrist"


def plan_screen_revision(pivot_mm: Point) -> ScreenRevisionPlan:
    try:
        valid = len(pivot_mm) == 3 and all(
            type(v) in (int, float) and isfinite(v) for v in pivot_mm
        )
    except OverflowError:
        valid = False
    if not valid or abs(pivot_mm[0]) > 0.001:
        raise NativeRevisionError("screen recipe requires a finite pivot on the X=0 hinge plane")
    x, y, z = pivot_mm
    top = z + 7.62916512459884
    rings = tuple(
        (
            (x + 82.0, plane_y, top),
            (x + 83.5, plane_y, top),
            (x + 83.5, plane_y, top - 4.0),
            (x + 83.0, plane_y, top - 4.0),
            (x + 82.0, plane_y, top - 3.0),
        )
        for plane_y in (y - 5.25, y - 1.25)
    )
    return ScreenRevisionPlan(
        pivot_mm,
        Cylinder("NATIVE_CLAMP_clearance", 3.0, 5.5, (x - 68.75, y, z), "X", 96),
        pi / 192,
        rings,
    )
