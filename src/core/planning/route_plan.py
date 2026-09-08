"""The channels through the palm: one per route per station.

`palm_v3_geometry.py` wrote the two routes as a literal pair and the stations
under a second spelling. Here a route is the finger's own bore offset, a
station is the station plan's, and the bore is named by the policy.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.domain.finger_v3 import SingleTendonFingerSpec
from src.core.domain.palm_v3 import AnthropomorphicPalmSpec
from src.core.planning.csg import Cylinder
from src.core.planning.naming import NamingPolicy
from src.core.planning.phalanx_plan import BORE_SEGMENTS
from src.core.planning.station_plan import Station

#: How far a through-cut in the plate overshoots both faces.
PLATE_OVERRUN_MM = 8.0


@dataclass(frozen=True, slots=True)
class Route:
    route: str
    station: str
    y_mm: float
    bore: Cylinder


def routes_for(finger: SingleTendonFingerSpec) -> tuple[tuple[str, float], ...]:
    """Palmar tendon, dorsal wiring: where each runs across the plate's depth."""
    return (("TENDON", finger.tendon_bore_offset_mm), ("WIRING", finger.wiring_bore_offset_mm))


def route_plan(
    palm: AnthropomorphicPalmSpec, naming: NamingPolicy, stations: tuple[Station, ...]
) -> tuple[Route, ...]:
    link = palm.finger.link
    plate_height = palm.plate_height_mm
    routes: list[Route] = []
    for station in stations:
        for route, y_mm in routes_for(palm.finger):
            routes.append(
                Route(
                    route,
                    station.label,
                    y_mm,
                    Cylinder(
                        naming.cut(route, station.label),
                        link.tendon_hole_diameter_mm / 2.0,
                        plate_height + PLATE_OVERRUN_MM,
                        (station.origin_mm[0], y_mm, -plate_height / 2.0),
                        "Z",
                        BORE_SEGMENTS,
                    ),
                )
            )
    return tuple(routes)
