"""Verify the selected workstation's published render, motion and slice lineage."""

import json
from collections.abc import Mapping
from pathlib import Path

from scripts.verify.native_pipeline_checks import object_value, rows


def check_delivery(root: Path, receipt: object) -> list[str]:
    """Cross-check receipts only after the independent source-byte check succeeds."""
    try:
        source = object_value(receipt)
        selected = root / str(source["root_dir"])
        native_sha = object_value(source["native"])["sha256"]
        project_sha = object_value(source["project_3mf"])["sha256"]
        parts = {Path(str(row["path"])).stem: row["sha256"] for row in rows(source["parts"])}
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
        changed_sha = parts[str(native["modified"])]
        comparisons = (
            ("native source", native["native_sha256"], native_sha),
            ("render native source", synchronized["render_native_sha256"], native_sha),
            ("motion native source", document("motion-dense")["native_sha256"], native_sha),
            ("render inventory", renders, rendered_files),
            ("reopened revised STL", native["reopened_stl_sha256"], changed_sha),
            ("exported revised STL", native["stl_sha256"], changed_sha),
            ("sliced revised STL", sliced["revised_surface_sha256"], changed_sha),
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
        failures = [
            f"selected delivery evidence disagrees with {field}"
            for field, observed, expected in comparisons
            if observed != expected
        ]
        if not rendered_files:
            failures.append("selected delivery has no verified renders")
        return failures
    except (OSError, ValueError, KeyError) as error:
        return [f"selected delivery evidence unavailable: {error}"]
