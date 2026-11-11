"""Render the selected EC78 link review or compose the verified USB comparison."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from hashlib import file_digest
from io import BytesIO
from pathlib import Path

# Blender runs --python scripts by file path rather than as Python modules.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.verify.lab_station_render_preflight import (  # noqa: E402
    read_review_input,
    require_review_source,
    selected_review_native,
)
from src.infrastructure.narrowing import as_finite_number, as_mapping  # noqa: E402

LINK_CASE = "EC78-r4-三探頭-15度回座-四線"
POSE_RECEIPT = "驗證/review-test-poses.json"
# Engineering USB fixed-end receipts: 1345, screen 60°, lid 90°, top view.
# Ordered by route, independent of the caller's filenames or directories.
USB_VIEW_SHA256 = (
    "8a5ef05d72bd137a6a84d763f6b033dcdb10e6a7e44c6773105452e952697bf2",  # 625 mm
    "6657c9ffb4bc388604514e3646e2b31cd08dc4a28226e37e6fa02776e34daf14",  # 542 mm
)


def render_link_review(
    root: Path, loaded_source: Path, evaluated_frame: float, render: Callable[[], None]
) -> None:
    source, expected_native = selected_review_native(root)
    manifest = as_mapping(json.loads((source.parent / "SHA256.json").read_bytes()))
    if manifest is None:
        raise ValueError("review preflight requires a selected source manifest")
    poses = as_mapping(
        json.loads(
            read_review_input(
                source.parent / POSE_RECEIPT, manifest.get(POSE_RECEIPT), "motion receipt"
            )
        )
    )
    if poses is None or poses.get("native_sha256") != expected_native:
        raise ValueError("review preflight motion receipt disagrees with selected native")
    cases = as_mapping(poses.get("cases"))
    case = as_mapping(cases.get(LINK_CASE)) if cases is not None else None
    if case is None:
        raise ValueError("review preflight link pose is missing")
    with loaded_source.open("rb") as stream:
        observed_native = file_digest(stream, "sha256").hexdigest()
    require_review_source(
        observed_native,
        evaluated_frame,
        expected_native=expected_native,
        expected_frame=case.get("frame"),
    )
    render()


def compose_usb_review(
    original: Path,
    shortened: Path,
    expected: tuple[str, str],
    compose: Callable[[bytes, bytes], None],
) -> None:
    left = read_review_input(original, expected[0], "625 mm original top view")
    right = read_review_input(shortened, expected[1], "542 mm shortened top view")
    compose(left, right)


def _render_link_images(output: Path) -> None:
    import bpy
    from mathutils import Vector

    scene = bpy.context.scene
    mesh = bpy.data.meshes.get("V89_LINK150_shared")
    links = [obj for obj in scene.objects if obj.type == "MESH" and obj.data == mesh]
    if len(links) != 8 or any(obj.hide_render or not obj.visible_get() for obj in links):
        raise ValueError("link review requires eight visible instances of the selected shared mesh")
    camera = scene.camera
    if camera is None:
        raise ValueError("link review requires the selected scene camera")
    output.mkdir()
    for obj in scene.objects:
        if obj.type in {"MESH", "CURVE"}:
            obj.color = (0.32, 0.36, 0.40, 1)
    for link in links:
        link.color = (1, 0.45, 0.06, 1)

    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = 1300
    scene.render.resolution_y = 960
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.53
    center = Vector((-0.045, -0.072, 0.163))
    for label, offset in (("正面", (-0.53, -0.63, 0.38)), ("背面", (0.39, 0.60, 0.36))):
        camera.location = center + Vector(offset)
        camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(output / f"EC78-r4-共用連桿-{label}.png")
        if bpy.ops.render.render(write_still=True) != {"FINISHED"}:
            raise ValueError(f"link review render failed for {label}")


def _write_usb_comparison(left: bytes, right: bytes, output: Path) -> None:
    from PIL import Image, ImageDraw

    result = Image.new("RGB", (1260, 605), "#f7f8fb")
    draw = ImageDraw.Draw(result)
    for x, title, data in ((20, "625 mm original", left), (640, "542 mm shortened", right)):
        with Image.open(BytesIO(data)) as image:
            view = image.convert("RGB").crop((140, 54, 1060, 890))
            result.paste(view.resize((600, 545), Image.Resampling.LANCZOS), (x, 42))
        draw.text((x, 17), title, fill="#223247")
    with output.open("xb") as stream:
        result.save(stream, format="PNG")


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    links = modes.add_parser("links", help="render the formal link review in background Blender")
    links.add_argument("--frame", type=float, required=True)
    links.add_argument("--output", type=Path, required=True)
    usb = modes.add_parser("usb", help="compose the 625 mm and 542 mm USB top views")
    usb.add_argument("--original", type=Path, required=True)
    usb.add_argument("--shortened", type=Path, required=True)
    usb.add_argument("--output", type=Path, required=True)
    for mode in (links, usb):
        mode.add_argument(
            "--check-only", action="store_true", help="validate inputs without writing"
        )
    args = parser.parse_args(argv)
    if args.mode == "links":
        import bpy

        if not bpy.app.background or not bpy.data.filepath or bpy.data.is_dirty:
            raise ValueError("link review requires a saved file in background Blender")
        frame = as_finite_number(args.frame)
        if frame is None or frame < 1:
            raise ValueError("link review requires a finite positive frame")
        scene = bpy.context.scene
        scene.frame_set(int(frame), subframe=frame - int(frame))
        render_link_review(
            Path(__file__).resolve().parents[1],
            Path(bpy.data.filepath),
            scene.frame_current_final,
            lambda: None if args.check_only else _render_link_images(args.output),
        )
    else:
        compose_usb_review(
            args.original,
            args.shortened,
            USB_VIEW_SHA256,
            lambda left, right: (
                None if args.check_only else _write_usb_comparison(left, right, args.output)
            ),
        )
    print("EC78 review inputs verified")
    return 0


if __name__ == "__main__":
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    sys.exit(main(arguments))
