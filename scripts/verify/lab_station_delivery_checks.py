"""Verify the selected workstation's published render, motion and slice lineage."""

import json
import math
from collections.abc import Mapping
from pathlib import Path

from scripts.verify.lab_station_render_preflight import review_source_differences
from scripts.verify.native_pipeline_checks import object_value, rows
from src.infrastructure.narrowing import as_finite_number


def check_review_replay(
    tested: Mapping[str, object],
    rendered: Mapping[str, object],
    native_sha: object,
    images: Mapping[str, object],
) -> list[str]:
    """Require an independently read render to replay the actual tested cases."""
    tested_cases = object_value(tested["cases"])
    rendered_cases = object_value(rendered["cases"])
    if not tested_cases or tested_cases.keys() != rendered_cases.keys():
        return ["review replay case inventory disagrees with motion test"]
    failures = [
        f"review replay {stage} native_sha256 differs from selected source"
        for stage, receipt in (("test", tested), ("render", rendered))
        if receipt["native_sha256"] != native_sha
    ]
    for name, raw_case in tested_cases.items():
        case = object_value(raw_case)
        readback = object_value(rendered_cases[name])
        frame = as_finite_number(case.get("frame", tested.get("frame")))
        if frame is None or frame < 1:
            failures.append(f"review replay {name} has an invalid tested frame")
            continue
        failures.extend(
            f"review replay {name} differs in {field}"
            for field in review_source_differences(
                readback["native_sha256"], readback["frame"], native_sha, frame
            )
        )
        comparisons = {
            "screen_deg": tested["screen_deg"],
            "angle_deg": case["angle_deg"],
            "release_mm": case["release_mm"],
            "preview_sha256": images[f"{name}.png"],
        }
        failures.extend(
            f"review replay {name} differs in {field}"
            for field, expected in comparisons.items()
            if readback[field] != expected
        )
        for field in ("matrix_delta_mm", "curve_delta_mm"):
            error = as_finite_number(readback[field])
            if error is None or not 0 <= error < 0.001:
                failures.append(f"review replay {name} exceeds tolerance in {field}")
    return failures


def check_bulkhead_bore(
    bore: Mapping[str, object],
    extrusion: Mapping[str, object],
    native_sha: object,
    project_sha: object,
) -> list[str]:
    """Check the EC78 nominal Ø15 mm bore against the selected one-plate toolpath."""
    (plate,) = rows(extrusion["plates"])
    failures = [
        f"selected delivery evidence disagrees with bulkhead-bore {label}"
        for label, field, expected in (
            ("native source", "native_sha256", native_sha),
            ("sliced project", "source_sha256", project_sha),
            ("G-code", "gcode_sha256", plate["gcode_sha256"]),
        )
        if bore[field] != expected
    ]
    radius = bore["clear_radius_lower_mm"]
    checked = bore["checked_early_depositions"]
    if (
        type(checked) is not int
        or checked <= 0
        or isinstance(radius, bool)
        or not isinstance(radius, (int, float))
        or (isinstance(radius, float) and not math.isfinite(radius))
        or radius < 7.45
    ):
        failures.append("bulkhead-bore clearance does not establish a free Ø14.9 mm cylinder")
    return failures


def _stl_comparisons(
    synchronized: Mapping[str, object],
    native: Mapping[str, object],
    sliced: Mapping[str, object],
    parts: Mapping[str, object],
) -> tuple[tuple[str, object, object], ...]:
    if "format_version" not in synchronized:
        changed_sha = parts[str(native["modified"])]
        return (
            ("reopened revised STL", native["reopened_stl_sha256"], changed_sha),
            ("exported revised STL", native["stl_sha256"], changed_sha),
            ("sliced revised STL", sliced["revised_surface_sha256"], changed_sha),
        )
    version = synchronized["format_version"]
    if type(version) is not int or version != 2:
        raise ValueError("unsupported workstation delivery evidence format")
    return (
        ("reopened STL inventory", object_value(native["reopened_stl_sha256_by_owner"]), parts),
        ("exported STL inventory", object_value(native["stl_sha256_by_owner"]), parts),
        ("sliced STL inventory", object_value(sliced["input_stl_sha256_by_owner"]), parts),
    )


def check_delivery(root: Path, receipt: object) -> list[str]:
    """Cross-check receipts only after the independent source-byte check succeeds."""
    try:
        source = object_value(receipt)
        selected = root / str(source["root_dir"])
        native_sha = object_value(source["native"])["sha256"]
        project_sha = object_value(source["project_3mf"])["sha256"]
        part_rows = rows(source["parts"])
        parts = {Path(str(row["path"])).stem: row["sha256"] for row in part_rows}
        if len(parts) != len(part_rows):
            raise ValueError("duplicate STL owner in selected delivery")
        manifest = object_value(json.loads((selected / "SHA256.json").read_bytes()))

        def document(name: str) -> Mapping[str, object]:
            path = f"驗證/{name}.json"
            if path not in manifest:
                raise ValueError(f"unlisted delivery evidence {path}")
            return object_value(json.loads((selected / path).read_bytes()))

        synchronized = document("synchronized-native-result")
        native = object_value(synchronized["native"])
        sliced = object_value(synchronized["slice"])
        renders = object_value(synchronized["render_sha256"])
        rendered_files = {
            path: sha for path, sha in manifest.items() if Path(path).suffix.lower() == ".png"
        }
        extrusion = document("extrusion")
        fit_toolpath = document("fit-toolpath")
        comparisons = (
            ("native source", native["native_sha256"], native_sha),
            ("render native source", synchronized["render_native_sha256"], native_sha),
            ("motion native source", document("motion-dense")["native_sha256"], native_sha),
            ("render inventory", renders, rendered_files),
            *_stl_comparisons(synchronized, native, sliced, parts),
            ("sliced project", sliced["sliced_sha256"], project_sha),
            ("sliced part count", sliced["parts"], len(parts)),
            ("extrusion project", object_value(extrusion["source"])["sha256"], project_sha),
            ("fit toolpath project", fit_toolpath["source_sha256"], project_sha),
            (
                "fit toolpath part inventory",
                object_value(fit_toolpath["bed_model_paths_by_part"]).keys(),
                parts.keys(),
            ),
        )
        for name, fingerprints in (
            ("rear-service", (("native source", "native_sha256", native_sha),)),
            (
                "rear-support-clearance",
                (
                    ("native source", "native_sha256", native_sha),
                    ("sliced project", "sliced_sha256", project_sha),
                ),
            ),
            ("rear-hinge-support", (("sliced project", "sliced_sha256", project_sha),)),
            ("vent-bridge", (("sliced project", "sliced_sha256", project_sha),)),
        ):
            if f"驗證/{name}.json" in manifest:
                observation = document(name)
                comparisons += tuple(
                    (f"{name} {label}", observation[key], expected)
                    for label, key, expected in fingerprints
                )
        failures = [
            f"selected delivery evidence disagrees with {field}"
            for field, observed, expected in comparisons
            if observed != expected
        ]
        if "驗證/bulkhead-bore.json" in manifest:
            failures.extend(
                check_bulkhead_bore(document("bulkhead-bore"), extrusion, native_sha, project_sha)
            )
        if any(
            f"驗證/{name}.json" in manifest for name in ("review-test-poses", "review-render-poses")
        ):
            render_poses = document("review-render-poses")
            if render_poses["pose_recipe_sha256"] != manifest["驗證/review-test-poses.json"]:
                failures.append("review replay render used a different motion recipe")
            failures.extend(
                check_review_replay(
                    document("review-test-poses"),
                    render_poses,
                    native_sha,
                    rendered_files,
                )
            )
        if not rendered_files:
            failures.append("selected delivery has no verified renders")
        return failures
    except (OSError, ValueError, KeyError) as error:
        return [f"selected delivery evidence unavailable: {error}"]
