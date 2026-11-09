"""Independent host geometry and material-witness checks for native source steps."""

from __future__ import annotations

import json
from pathlib import Path

from src.core.domain.native_revision import NativeModelSource, NativeSourceError, SourceArtifact


def check(payload: Path) -> None:
    from src.infrastructure.narrowing import (
        as_finite_number,
        as_sequence,
        as_str_keyed_exact,
        required,
    )
    from src.verification.mesh_integrity import require_triangle_surface

    document = required(
        json.loads(payload.read_text()),
        as_str_keyed_exact,
        message="invalid stage",
        error=ValueError,
    )
    surfaces = required(
        document.get("surfaces"), as_str_keyed_exact, message="missing surfaces", error=ValueError
    )
    if not surfaces:
        raise ValueError("empty stage cannot qualify")
    for name, raw in surfaces.items():
        mesh = required(raw, as_str_keyed_exact, message="invalid surface", error=ValueError)
        try:
            require_triangle_surface(mesh)
        except ValueError as exc:
            raise ValueError(f"{name}: {exc}") from exc
    material = None
    if document["stage"] in ("operation-0", "operation-1"):
        import numpy as np

        from src.verification.mesh_integrity import bounded_sides

        original_files = list(payload.parent.glob("*-prepared-all.json"))
        assert len(original_files) == 1
        original = required(
            json.loads(original_files[0].read_text()),
            as_str_keyed_exact,
            message="invalid prepared snapshot",
            error=ValueError,
        )
        prepared = required(
            original.get("surfaces"),
            as_str_keyed_exact,
            message="missing prepared surfaces",
            error=ValueError,
        )
        pivot = required(
            document.get("pivot_mm"), as_sequence, message="missing pivot", error=ValueError
        )
        if len(pivot) != 3:
            raise ValueError("invalid pivot")
        x, y, z = (
            required(v, as_finite_number, message="invalid pivot", error=ValueError) for v in pivot
        )
        cut = document["stage"] == "operation-0"
        owner = "LS_FIT_lcd_back" if cut else "LS_FIT_lid"
        queries = (
            ((x - 69, y + 2.85, z), (x - 69, y + 3.5, z))
            if cut
            else ((x + 82.25, y - 3.25, z + 6.5), (x + 83.25, y - 3.25, z + 6.5))
        )
        observed = []
        for raw_surface in (prepared[owner], surfaces[owner]):
            mesh = required(
                raw_surface, as_str_keyed_exact, message="invalid witness surface", error=ValueError
            )
            matrix_rows = required(
                mesh.get("matrix_world"), as_sequence, message="invalid frame", error=ValueError
            )
            matrix = [
                [
                    required(
                        v, as_finite_number, message="invalid frame component", error=ValueError
                    )
                    for v in required(
                        row, as_sequence, message="invalid frame row", error=ValueError
                    )
                ]
                for row in matrix_rows
            ]
            if len(matrix) != 4 or any(len(row) != 4 for row in matrix):
                raise ValueError("invalid witness frame")
            inverse = np.linalg.inv(matrix)
            points = [
                (inverse @ np.asarray([q[0] / 1000, q[1] / 1000, q[2] / 1000, 1]))[:3].tolist()
                for q in queries
            ]
            observed.append(bounded_sides(mesh, points))
        expected = [(1, 1), (-1, 1)] if cut else [(-1, 1), (1, 1)]
        material = {"before": observed[0], "after": observed[1], "retained_control": True}
        if observed != expected:
            reason = (
                "source-witness-incompatible"
                if observed[0] != expected[0]
                else "material-change-missing"
            )
            payload.with_suffix(".rejected.json").write_text(
                json.dumps(
                    {
                        "stage": document["stage"],
                        "reason": reason,
                        "observed": observed,
                        "expected": expected,
                    }
                )
            )
            raise ValueError(reason)
    proof = {
        "stage": document["stage"],
        "owners": sorted(surfaces),
        "passed": True,
        "material_witness": material,
    }
    payload.with_suffix(".checked.json").write_text(json.dumps(proof))
    print(json.dumps({"stage": document["stage"], "checked": len(surfaces), "passed": True}))


def check_plate_bindings(
    source: NativeModelSource, snapshot: Path, owners: tuple[str, ...]
) -> dict[str, object]:
    """Prove original STL/template frames before a revised 3MF may reuse placement."""
    from src.adapters.artifacts.native_source import read_source_asset
    from src.adapters.artifacts.plate_project import PlateProject
    from src.verification.artifact_files import binary_stl_surface

    def read(receipt: SourceArtifact) -> bytes:
        try:
            return read_source_asset(snapshot, receipt, receipt.size_bytes)
        except NativeSourceError as exc:
            raise ValueError(str(exc)) from exc

    if not owners or len(set(owners)) != len(owners):
        raise ValueError("plate binding requires unique nonempty owners")
    if source.project_3mf is None:
        raise ValueError("plate binding requires the captured source project")
    by_owner = {Path(p.path).stem: p for p in source.parts}
    if len(by_owner) != len(source.parts) or set(owners) - set(by_owner):
        raise ValueError("plate binding owner is missing or ambiguous")
    project = PlateProject(
        read(source.project_3mf), tuple(by_owner), max_bytes=source.project_3mf.size_bytes
    )
    return project.bind_originals(
        {owner: binary_stl_surface(read(by_owner[owner])) for owner in owners}
    )
