"""Cable test inputs and expectations; importing this registry never requires Blender."""

from dataclasses import dataclass
from typing import Literal

from src.core.domain.cable_paths import CubicPath
from src.core.domain.lab_station import Point
from src.core.domain.verification import VerificationSuite
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
class PairProbe:
    first: CubicPath
    second: CubicPath
    first_radius_mm: float = 3
    second_radius_mm: float = 3
    step_mm: float = 0.15


PAIR_CASES = (
    Scenario(
        "pair_unequal_radius_clear",
        PairProbe(straight((0, 0, 0), (30, 0, 0)), straight((0, 7, 0), (30, 7, 0)), 1, 5),
        "clear",
    ),
    Scenario(
        "pair_parallel_clear",
        PairProbe(straight((0, 0, 0), (30, 0, 0)), straight((0, 8, 0), (30, 8, 0))),
        "clear",
    ),
    Scenario(
        "pair_tangent_rejected",
        PairProbe(straight((0, 0, 0), (30, 0, 0)), straight((0, 6, 0), (30, 6, 0))),
        "wire_contact",
    ),
    Scenario(
        "pair_crossing_between_samples",
        PairProbe(straight((-5, 0, 0), (5, 0, 0)), straight((0, -5, 0), (0, 5, 0)), 0.1, 0.1, 20),
        "wire_contact",
    ),
    Scenario(
        "pair_spatial_clear",
        PairProbe(straight((0, 0, 0), (30, 0, 0)), straight((15, -15, 8), (15, 15, 8))),
        "clear",
    ),
    Scenario(
        "pair_unequal_radius_rejected",
        PairProbe(straight((0, 0, 0), (30, 0, 0)), straight((0, 6, 0), (30, 6, 0)), 1, 5),
        "wire_contact",
    ),
    Scenario(
        "pair_negative_coordinates",
        PairProbe(straight((-30, 0, 0), (-1, 0, 0)), straight((-30, -8, 0), (-1, -8, 0))),
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


BUNDLE_ROUTES = (
    RoutePose("capillary", 0, 220),
    RoutePose("pH_temp", 0, 170),
    RoutePose("pH_temp", 1, 170),
)


@dataclass(frozen=True, slots=True)
class BundlePose:
    capillary_lift_mm: float = 0
    ph_temp_lift_mm: float = 0
    obstruction_radius_mm: float | None = None
    preview_stem: str | None = None


BUNDLE_CASES = (
    Scenario("bundle_working", BundlePose(preview_stem="bundle-working"), "found"),
    Scenario(
        "bundle_capillary_raised",
        BundlePose(capillary_lift_mm=100, preview_stem="bundle-capillary-raised"),
        "found",
    ),
    Scenario(
        "bundle_ph_temp_raised",
        BundlePose(ph_temp_lift_mm=100, preview_stem="bundle-ph-temp-raised"),
        "found",
    ),
    Scenario("bundle_obstruction_rejected", BundlePose(obstruction_radius_mm=500), "not_found"),
)


def registered_suites() -> tuple["VerificationSuite", ...]:
    """Catalog coverage is derived from the exact cases the Blender runner consumes."""
    return (
        VerificationSuite(
            "electrode-head-bundle",
            "Electrode head bundle",
            "Three head segments checked together in working and independent raised poses, "
            "plus an obstruction control. No cross-segment, continuous motion or material qualification.",
            tuple((case.name, case.expected) for case in BUNDLE_CASES),
        ),
        VerificationSuite(
            "cable-contact-controls",
            "Cable contact controls",
            "Synthetic clearance/contact checks; no material or load qualification.",
            tuple((case.name, case.expected) for case in (*CONTACT_CASES, *PAIR_CASES)),
        ),
        VerificationSuite(
            "electrode-head-routes",
            "Electrode head routes",
            "Four independent routes on the current electrode assembly; poses are restored. "
            "Requires the lab-station electrode model. No bundle, continuous motion or material qualification.",
            tuple((case.name, case.expected) for case in ROUTE_CASES),
        ),
    )
