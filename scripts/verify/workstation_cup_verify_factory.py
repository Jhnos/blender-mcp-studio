"""Verify a nominal cup's extraction against the currently selected native assembly."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import shutil
import subprocess
import sys
import uuid
from collections.abc import Mapping
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify.native_session_verify_factory import (  # noqa: E402
    current_source,
    installed_blender,
    sha256,
)
from src.infrastructure.narrowing import as_mapping, as_nonempty_sequence, required  # noqa: E402

DISH = "LS_FIT_spill_dish"
TRAY = "LS_FIT_sample_tray"
REFERENCE_CUP = "LS_REF_vessel_250ml_ENVELOPE"
CAPILLARY = "S_capillary_probe_0"
SCREEN_STEPS = 240
CUP_OUTER_RADIUS_MM = 37.25
CUP_INNER_RADIUS_MM = 35.25
CUP_HEIGHT_MM = 81.0
CUP_FLOOR_MM = 3.0
DISH_SHIFT_MM = (1.8826358461505448, -11.950695846520576)
LIFT_RANGE_MM = (6.5, 9.5)
NOMINAL_LIFT_MM = 7.0
MINIMUM_ASSEMBLY_GAP_MM = 1.0
PARKED_ARMS_DEG = ((15.0, 15.0), (0.0, 30.0))


def document(value: object) -> Mapping[str, object]:
    return required(value, as_mapping, message="expected evidence object", error=ValueError)


def array(value: object) -> list[object]:
    return list(
        required(value, as_nonempty_sequence, message="missing evidence rows", error=ValueError)
    )


def assess(evidence: Mapping[str, object], expected_sha: str) -> dict[str, object]:
    """Bound the upright cup's swept volumes and reject three incorrect operations."""
    import numpy as np

    from src.verification.mesh_integrity import convex_envelope, solid_overlap_volume

    if evidence.get("native_sha256") != expected_sha:
        raise ValueError("cup evidence comes from a different native model")
    raw_meshes = document(evidence.get("parked"))
    frames = [document(row) for row in array(evidence.get("screen_frames"))]
    display = set(frames[0])
    if len(frames) != SCREEN_STEPS + 1 or any(set(row) != display for row in frames):
        raise ValueError("display sweep is incomplete")
    if not {"LS_FIT_lcd_front", "LS_FIT_lcd_back"} <= display <= raw_meshes.keys():
        raise ValueError("display geometry is missing")

    def world(owner: str, override: object = None) -> tuple[np.ndarray, np.ndarray]:
        data = document(raw_meshes[owner])
        matrix = np.array(
            array(data["matrix_world"] if override is None else override), dtype=float
        )
        points = np.array(array(data["vertices"]), dtype=float)
        faces = np.array(array(data["faces"]))
        if matrix.shape != (4, 4) or points.ndim != 2 or points.shape[1] != 3:
            raise ValueError(f"invalid mesh frame for {owner}")
        if not np.isfinite(matrix).all() or not np.isfinite(points).all():
            raise ValueError(f"nonfinite mesh frame for {owner}")
        determinant = np.linalg.det(matrix[:3, :3])
        if determinant == 0:
            raise ValueError(f"singular mesh frame for {owner}")
        if determinant < 0:
            faces = faces[:, ::-1]
        return (points @ matrix[:3, :3].T + matrix[:3, 3]) * 1000, faces

    def soup(points: np.ndarray, faces: np.ndarray) -> dict[str, object]:
        return {"vertices": points.tolist(), "faces": faces.tolist()}

    parked = {name: world(name) for name in raw_meshes}
    dish, dish_faces = parked[DISH]
    tray = parked[TRAY][0]
    dish_lo, dish_hi = dish.min(axis=0), dish.max(axis=0)
    tray_lo, tray_hi = tray.min(axis=0), tray.max(axis=0)
    heights = np.unique(dish[:, 2].round(4))
    if len(heights) != 3 or not math.isclose(dish_lo[2], tray_hi[2], abs_tol=0.0001):
        raise ValueError("unsupported spill dish seating or rim")
    floor = float(dish[np.isclose(dish[:, 2], heights[1], atol=0.0001), 2].max())
    rim = float(dish_hi[2])
    lip = floor + CUP_HEIGHT_MM
    center = (dish_lo[:2] + dish_hi[:2]) / 2 + DISH_SHIFT_MM
    shifted_dish = soup(dish + (*DISH_SHIFT_MM, 0), dish_faces)
    tray_margin = float(
        np.min(
            np.minimum(
                dish_lo[:2] + DISH_SHIFT_MM - tray_lo[:2], tray_hi[:2] - dish_hi[:2] - DISH_SHIFT_MM
            )
        )
    )
    end = np.array((center[0], tray_lo[1] - CUP_OUTER_RADIUS_MM - 1.0))
    low_lift, high_lift = LIFT_RANGE_MM
    if tray_margin <= 0 or floor + low_lift <= rim:
        raise ValueError("candidate cup or shifted dish does not clear its tray")

    pivot = np.array(array(evidence["pivot_mm"]))
    display_envelopes = {}
    for name in sorted(display):
        base = parked[name][0] - pivot
        radius = float(np.linalg.norm(base[:, 1:], axis=1).max())
        locations = []
        for index, frame in enumerate(frames):
            theta = math.radians(index * 60.0 / SCREEN_STEPS - 60.0)
            c, s = math.cos(theta), math.sin(theta)
            rotation = np.array(((1, 0, 0), (0, c, -s), (0, s, c)))
            actual = world(name, frame[name])[0]
            if float(np.linalg.norm(base @ rotation.T + pivot - actual, axis=1).max()) > 0.001:
                raise ValueError(f"display hinge is not rigid for {name}")
            locations.append(actual)
        positions = np.vstack(locations)
        between_samples = 2 * radius * math.sin(math.radians(30 / SCREEN_STEPS) / 2) + 0.002
        display_envelopes[name] = (
            positions.min(axis=0) - between_samples,
            positions.max(axis=0) + between_samples,
        )

    count = 96
    circle = np.array(
        [(math.cos(i * math.tau / count), math.sin(i * math.tau / count)) for i in range(count)]
    )

    def sweep(a: np.ndarray, b: np.ndarray, z0: float, z1: float) -> np.ndarray:
        radius = CUP_OUTER_RADIUS_MM / math.cos(math.pi / count)
        return np.array(
            [(*point, z) for xy, z in product((a, b), (z0, z1)) for point in xy + radius * circle]
        )

    def cup_wall(xy: np.ndarray, lift: float) -> dict[str, object]:
        rings = (
            (CUP_OUTER_RADIUS_MM, floor),
            (CUP_OUTER_RADIUS_MM, lip),
            (CUP_INNER_RADIUS_MM, lip),
            (CUP_INNER_RADIUS_MM, floor + CUP_FLOOR_MM),
        )
        vertices = [(*point, z + lift) for radius, z in rings for point in xy + radius * circle]
        vertices.extend(((*xy, floor + lift), (*xy, floor + lift + CUP_FLOOR_MM)))
        faces: list[tuple[int, int, int]] = []
        for index in range(count):
            next_index = (index + 1) % count
            for ring in range(3):
                a, b = ring * count, (ring + 1) * count
                faces.extend(
                    (
                        (a + index, a + next_index, b + next_index),
                        (a + index, b + next_index, b + index),
                    )
                )
            faces.extend(
                (
                    (4 * count, next_index, index),
                    (4 * count + 1, 3 * count + index, 3 * count + next_index),
                )
            )
        return {"vertices": vertices, "faces": faces}

    def check(points: np.ndarray) -> dict[str, object]:
        lo, hi = points.min(axis=0), points.max(axis=0)
        nearest: dict[str, float] = {}
        hull = convex_envelope(points.tolist())
        for name, (pts, faces) in parked.items():
            if name in display | {DISH, REFERENCE_CUP}:
                continue
            gap = float(
                np.linalg.norm(
                    np.maximum(np.maximum(pts.min(axis=0) - hi, lo - pts.max(axis=0)), 0)
                )
            )
            if gap == 0 and solid_overlap_volume(hull, soup(pts, faces)) > 0:
                raise ValueError(f"cup sweep overlaps {name}")
            nearest[name] = gap
        for name, (a, b) in display_envelopes.items():
            gap = float(np.linalg.norm(np.maximum(np.maximum(a - hi, lo - b), 0)))
            if gap <= 0:
                raise ValueError(f"cup sweep is not separated from the moving display: {name}")
            nearest[name] = gap
        if solid_overlap_volume(hull, shifted_dish) > 0:
            raise ValueError("cup sweep overlaps shifted spill dish")
        name = min(nearest, key=nearest.__getitem__)
        if nearest[name] < MINIMUM_ASSEMBLY_GAP_MM:
            raise ValueError(f"cup sweep cannot establish clearance from {name}")
        return {"nearest": name, "gap_lower_mm": nearest[name], "checked_meshes": len(parked) - 1}

    segments = {
        "lift": check(sweep(center, center, floor, lip + high_lift)),
        "forward": check(sweep(center, end, floor + low_lift, lip + high_lift)),
        "nominal_forward": check(
            sweep(center, end, floor + NOMINAL_LIFT_MM, lip + NOMINAL_LIFT_MM)
        ),
    }
    controls = {
        "saved_dish": (cup_wall(center, 0), soup(dish, dish_faces)),
        "slide_16_mm_without_lift": (cup_wall(center + (0, -16), 0), shifted_dish),
        "lift_12_mm": (cup_wall(center, 12), soup(*parked[CAPILLARY])),
    }
    volumes = {name: solid_overlap_volume(cup, target) for name, (cup, target) in controls.items()}
    if not all(value > 0 for value in volumes.values()):
        raise ValueError("a cup extraction negative control failed to detect overlap")
    return {
        "native_sha256": expected_sha,
        "screen_range_deg": [0, 60],
        "cup_outer_diameter_mm": 2 * CUP_OUTER_RADIUS_MM,
        "cup_inner_diameter_mm": 2 * CUP_INNER_RADIUS_MM,
        "cup_height_mm": CUP_HEIGHT_MM,
        "dish_shift_xy_mm": DISH_SHIFT_MM,
        "dish_tray_edge_margin_mm": tray_margin,
        "lift_range_mm": LIFT_RANGE_MM,
        "forward_mm": float(center[1] - end[1]),
        "segments": segments,
        "negative_overlap_cubic_mm": volumes,
        "scope": "Nominal outer cup envelopes after arms park, with hollow cup wall collision controls. Actual hardware, wiring and handling are separate.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", type=Path)
    parser.add_argument("--work", type=Path)
    parser.add_argument("--capture", nargs=2, type=Path, help=argparse.SUPPRESS)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    if args.capture:
        from scripts.verify.workstation_cup_capture import capture

        capture(
            *args.capture,
            screen_steps=SCREEN_STEPS,
            parked_arms=PARKED_ARMS_DEG,
            required_meshes={
                DISH,
                TRAY,
                CAPILLARY,
                REFERENCE_CUP,
                "LS_FIT_lcd_front",
                "LS_FIT_lcd_back",
            },
        )
        return 0
    blender = args.blender or installed_blender(
        Path.home() / "Library/LaunchAgents/com.blender-mcp.blender.plist"
    )
    work = (args.work or ROOT / "tmp" / f"workstation-cup-{uuid.uuid4().hex}").resolve()
    native, expected, model = asyncio.run(current_source())
    native = ROOT / native
    work.mkdir(parents=True, exist_ok=False)
    snapshot = work / "source.blend"
    shutil.copyfile(native, snapshot)
    if sha256(snapshot) != expected:
        raise ValueError("selected native changed during snapshot")
    captured = work / "capture.json"
    log = work / "blender.log"
    with log.open("w") as handle:
        done = subprocess.run(
            [
                str(blender),
                "--background",
                "--factory-startup",
                "--disable-autoexec",
                "--threads",
                "2",
                str(snapshot),
                "--python-exit-code",
                "1",
                "--python",
                str(Path(__file__).resolve()),
                "--",
                "--capture",
                str(snapshot),
                str(captured),
            ],
            cwd=ROOT,
            stdout=handle,
            stderr=subprocess.STDOUT,
            timeout=120,
            check=False,
        )
    if done.returncode:
        raise RuntimeError(f"Blender cup capture failed; see {log}")
    result = assess(document(json.loads(captured.read_bytes())), expected)
    if sha256(snapshot) != expected or sha256(native) != expected:
        raise ValueError("native source changed during verification")
    (work / "cup-extraction.json").write_text(
        json.dumps(
            {
                **result,
                "model": model,
                "capture_sha256": sha256(captured),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    print(work / "cup-extraction.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
