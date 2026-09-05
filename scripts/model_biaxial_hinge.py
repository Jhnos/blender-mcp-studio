"""V6 composition: shared body builder, four-way roots, and both pin workflows."""

import sys
from pathlib import Path

import bpy

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.biaxial_hinge_presentation import present_biaxial  # noqa: E402
from scripts.blender_artifact_export import export_stl_mm  # noqa: E402
from scripts.blender_generator_runner import run_generator  # noqa: E402
from scripts.blender_mesh_primitives import collection, material  # noqa: E402
from scripts.hinge_retention import (  # noqa: E402
    create_captive_pin,
    create_grooved_pin,
    create_retaining_clip,
    cut_retainer_seats,
)
from scripts.hollow_hinge_render import create_bent_preview, duplicate_print_layout  # noqa: E402
from scripts.model_inset_hinge import create_body, place_pins, repeat_body  # noqa: E402
from src.core.domain.biaxial_hinge import BiaxialHingeSpec  # noqa: E402

SPEC = BiaxialHingeSpec()
OUTPUT = PROJECT_ROOT / "tmp" / "biaxial-hinge-v6"


def build() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 1.0
    gold = material("HH_V6_BODY", (0.82, 0.48, 0.12, 1))
    light = material("HH_V6_ALT", (1.0, 0.7, 0.24, 1))
    cyan = material("HH_V6_PIN", (0.03, 0.7, 0.9, 1))
    red = material("HH_V6_CLIP", (0.95, 0.2, 0.12, 1))
    magenta = material("HH_V6_CABLE", (0.85, 0.05, 0.6, 1))
    assembly, hardware, layout, bent = [
        collection("HH_" + name) for name in ("ASSEMBLY", "HARDWARE", "LAYOUT", "BENT")
    ]
    master = create_body(assembly, gold, SPEC)
    cut_retainer_seats(master, SPEC)
    captive = create_captive_pin(hardware, cyan, SPEC)
    removable = create_grooved_pin(hardware, cyan, SPEC)
    clip = create_retaining_clip(hardware, red, SPEC)
    parts = repeat_body(master, assembly, light, SPEC)
    pins = place_pins(captive, hardware, SPEC)
    layout_objects = duplicate_print_layout(master, layout)
    bent_objects, cable, target = create_bent_preview(master, bent, SPEC, gold, light, magenta)
    export_stl_mm([master], OUTPUT / "body_mm.stl")
    export_stl_mm([removable], OUTPUT / "assembly_pin_mm.stl")
    export_stl_mm([clip], OUTPUT / "retaining_clip_mm.stl")
    scene["HH_AXIS_NAMES"] = list(SPEC.axis_names)
    scene["HH_RETENTION_STYLES"] = list(SPEC.retention_styles)
    scene["HH_DESIGN_NOTE"] = (
        "V6: biaxial roots; PIP double heads or removable grooved pin + C clip. Unqualified fit prototype; test release, retention and strength before loading."
    )
    present_biaxial(
        OUTPUT,
        SPEC,
        parts,
        pins,
        hardware,
        (captive, removable, clip),
        layout_objects,
        bent_objects,
        cable,
        target,
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "biaxial_hinge_v6.blend"))
    print("BIAXIAL_HINGE_READY", str(OUTPUT))


def main() -> None:
    run_generator(build)


if __name__ == "__main__":
    main()
