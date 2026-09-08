"""The palm as named solids: plate, boss, roots, routes, port and clamp.

Every root is a male tongue placed by its station, because a finger's own base
end is a female fork: the knuckle is the same joint as every other joint in
the finger. The boss comes before the roots so the thumb's root has something
to land on — without it the root unions as a second shell and every
watertightness check still passes.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.domain.palm_v3 import AnthropomorphicPalmSpec
from src.core.domain.rotation import Axis3
from src.core.planning.csg import Box, Cylinder, HollowBox, Operation, difference, union
from src.core.planning.naming import NamingPolicy
from src.core.planning.phalanx_plan import BORE_SEGMENTS, PIN_BORE_OVERRUN_MM
from src.core.planning.route_plan import PLATE_OVERRUN_MM, Route, route_plan
from src.core.planning.station_plan import Basis, Station

#: The clamp groove's cutter is a band; its inner box overshoots the band's
#: depth so the two faces never coincide.
CLAMP_DEPTH_OVERRUN_MM = 4.0


@dataclass(frozen=True, slots=True)
class RootPlan:
    """One knuckle root, built at the origin pointing up, then placed by its station."""

    name: str
    origin_mm: Axis3
    basis: Basis
    stem: Box
    lug: Cylinder
    bore: Cylinder


@dataclass(frozen=True, slots=True)
class PalmPlan:
    name: str
    plate: Box
    thenar: Box
    roots: tuple[RootPlan, ...]
    routes: tuple[Route, ...]
    air_port: Cylinder
    clamp: tuple[Box, Box]
    #: Applied to the plate before the roots are unioned on, and after.
    before_roots: tuple[Operation, ...]
    after_roots: tuple[Operation, ...]

    @property
    def operations(self) -> tuple[Operation, ...]:
        return (*self.before_roots, *self.after_roots)


def _root(palm: AnthropomorphicPalmSpec, naming: NamingPolicy, station: Station) -> RootPlan:
    link = palm.finger.link
    name = naming.root(station.label)
    axis = palm.finger.male_hinge_axis
    offset = link.joint_center_offset_mm
    return RootPlan(
        name=name,
        origin_mm=station.origin_mm,
        basis=station.basis,
        stem=Box(
            f"{name}_STEM",
            (link.male_tongue_thickness_mm, link.lug_outer_diameter_mm, offset),
            (0.0, 0.0, offset / 2.0),
        ),
        lug=Cylinder(
            f"{name}_LUG",
            link.lug_outer_diameter_mm / 2.0,
            link.male_tongue_thickness_mm,
            (0.0, 0.0, offset),
            axis,
        ),
        bore=Cylinder(
            f"{name}_BORE",
            link.printed_pin_bore_mm / 2.0,
            link.male_tongue_thickness_mm + PIN_BORE_OVERRUN_MM,
            (0.0, 0.0, offset),
            axis,
            BORE_SEGMENTS,
        ),
    )


def palm_plan(
    palm: AnthropomorphicPalmSpec, naming: NamingPolicy, stations: tuple[Station, ...]
) -> PalmPlan:
    link = palm.finger.link
    plate_height = palm.plate_height_mm
    plate = Box(
        naming.palm(),
        (palm.palm_width_mm, link.body_depth_mm, plate_height),
        (0.0, 0.0, -plate_height / 2.0),
    )
    centre, size = palm.thenar_bridge_mm
    thenar = Box(naming.thenar(), size, centre)
    routes = route_plan(palm, naming, stations)

    port_x, port_z = palm.air_port_center_mm
    air_port = Cylinder(
        naming.cutter("AIR_PORT"),
        palm.air_port_diameter_mm / 2.0,
        link.body_depth_mm + PLATE_OVERRUN_MM,
        (port_x, 0.0, port_z),
        "Y",
        BORE_SEGMENTS,
    )

    wall = palm.cuff_clamp_wall_mm
    z = palm.cuff_clamp_center_z_mm
    outer = Box(
        naming.cutter("CLAMP_OUTER"),
        (palm.palm_width_mm + PLATE_OVERRUN_MM, link.body_depth_mm + PLATE_OVERRUN_MM, wall),
        (0.0, 0.0, z),
    )
    inner = Box(
        naming.cutter("CLAMP_INNER"),
        (
            palm.palm_width_mm - 2.0 * wall,
            link.body_depth_mm - 2.0 * wall,
            wall + CLAMP_DEPTH_OVERRUN_MM,
        ),
        (0.0, 0.0, z),
    )

    return PalmPlan(
        name=naming.palm(),
        plate=plate,
        thenar=thenar,
        roots=tuple(_root(palm, naming, station) for station in stations),
        routes=routes,
        air_port=air_port,
        clamp=(outer, inner),
        before_roots=(union(thenar),),
        after_roots=(
            *(difference(route.bore) for route in routes),
            difference(air_port),
            difference(HollowBox(outer.name, outer, inner)),
        ),
    )
