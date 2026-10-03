"""Cable test inputs and expectations; importing this registry never requires Blender."""

from dataclasses import dataclass
from typing import Literal

from src.core.domain.cable_paths import CubicPath
from src.core.domain.lab_station import Point
from src.core.planning.cable_path_plan import RouteBoundary, straight
from src.verification.scenario_runner import Scenario


@dataclass(frozen=True, slots=True)
class ContactProbe:
    boundary: RouteBoundary
    curve: CubicPath
    check: Literal["surface", "self"] = "surface"
    terminal: bool = False


def surface(
    start: Point,
    end: Point,
    *,
    radius: float = 3,
    direction: Point = (1, 0, 0),
    terminal: bool = False,
) -> ContactProbe:
    return ContactProbe(
        RouteBoundary("fixture", start, end, direction, direction, 60, radius),
        straight(start, end),
        terminal=terminal,
    )


CONTACT_CASES = (
    Scenario("clear_path", surface((1980, 2000, 2020), (2020, 2000, 2020)), "clear"),
    Scenario(
        "crossing_rejected", surface((1980, 2000, 2000), (2020, 2000, 2000)), "envelope_contact"
    ),
    Scenario("embedded_rejected", surface((2000, 2000, 2000), (2005, 2000, 2000)), "start_inside"),
    Scenario(
        "outward_face_allowed",
        surface((2000, 2000, 2040), (2000, 2000, 2010), direction=(0, 0, -1), terminal=True),
        "clear",
    ),
    Scenario(
        "penetrating_terminal_rejected",
        surface((2000, 2000, 2040), (2000, 2000, 2009), direction=(0, 0, -1), terminal=True),
        "terminal_not_on_outward_face",
    ),
    Scenario(
        "radius_inflation_rejected",
        surface((1980, 2000, 2020), (2020, 2000, 2020), radius=11),
        "envelope_contact",
    ),
    Scenario(
        "self_contact_rejected",
        ContactProbe(
            RouteBoundary("loop", (0, 0, 0), (0, 0, 0), (1, 1, 0), (1, -1, 0), 60),
            CubicPath(((0, 0, 0), (20, 20, 0), (-20, 20, 0), (0, 0, 0))),
            "self",
        ),
        "nonlocal_self_contact",
    ),
    Scenario(
        "self_clear_path",
        ContactProbe(
            RouteBoundary("line", (0, 0, 0), (30, 0, 0), (1, 0, 0), (1, 0, 0), 60),
            straight((0, 0, 0), (30, 0, 0)),
            "self",
        ),
        "clear",
    ),
)


@dataclass(frozen=True, slots=True)
class RoutePose:
    head: Literal["capillary", "pH_temp"]
    channel: int
    length_mm: float
    lift_mm: float = 0
    preview_stem: str | None = None


ROUTE_CASES = (
    Scenario(
        "capillary_working", RoutePose("capillary", 0, 220, preview_stem="capillary-0"), "found"
    ),
    Scenario("capillary_raised", RoutePose("capillary", 0, 220, 100, "capillary-100"), "found"),
    Scenario("ph_working", RoutePose("pH_temp", 0, 150), "found"),
    Scenario("temperature_working", RoutePose("pH_temp", 1, 150), "found"),
)
