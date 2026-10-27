"""A tiny fake BambuStudio.app tree with vendor profiles (2-level ``inherits`` plus an include)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

MACHINE_GEOMETRY = {
    "printable_area": ["0x0", "256x0", "256x256", "0x256"],
    "printable_height": "256",
    "bed_exclude_area": [],
    "extruder_offset": ["0X0"],
    "nozzle_diameter": ["0.4"],
}

LEAVES = {
    "machine": "Bambu Lab P2S 0.4 nozzle",
    "process": "0.20mm Standard @BBL P2S",
    "filament": "Generic PLA @BBL P2S",
}


def _write(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def make_bundle(tmp_path: Path, *, profiles: bool = True) -> Path:
    """Create ``Fake.app`` and return its ``Contents/MacOS/BambuStudio`` binary path."""
    app = tmp_path / "Fake.app"
    binary = app / "Contents" / "MacOS" / "BambuStudio"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    if not profiles:
        return binary
    bbl = app / "Contents" / "Resources" / "profiles" / "BBL"
    for kind, leaf in LEAVES.items():
        _write(
            bbl / kind / f"{kind}_base.json",
            {
                "type": kind,
                "base_key": "base",
                "shared": "base",
                **(MACHINE_GEOMETRY if kind == "machine" else {}),
            },
        )
        _write(bbl / kind / f"{kind}_extra.json", {"extra_key": "extra", "shared": "extra"})
        _write(
            bbl / kind / f"{kind}_mid.json",
            {"inherits": f"{kind}_base", "include": [f"{kind}_extra"], "mid_key": "mid"},
        )
        _write(
            bbl / kind / f"{leaf}.json",
            {
                "type": kind,
                "name": leaf,
                "inherits": f"{kind}_mid",
                "instantiation": "true",
                "shared": "leaf",
                "leaf_key": "leaf",
            },
        )
    return binary


def flattened(kind: str) -> dict[str, object]:
    """What the adapter must produce for ``kind`` from ``make_bundle`` (v80 semantics)."""
    return {
        "type": kind,
        "base_key": "base",
        "extra_key": "extra",
        "mid_key": "mid",
        "shared": "leaf",
        "leaf_key": "leaf",
        "name": LEAVES[kind],
        "instantiation": "true",
        "inherits": "",
        "from": "system",
        **(MACHINE_GEOMETRY if kind == "machine" else {}),
    }


def write_sliced_output(path: Path) -> None:
    """Minimal named Bambu output for command-adapter tests; real geometry is tested separately."""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "Metadata/model_settings.config",
            '<config><object id="2"><metadata key="name" value="lid"/></object><plate><metadata key="plater_id" value="1"/><model_instance><metadata key="object_id" value="2"/><metadata key="instance_id" value="0"/><metadata key="identify_id" value="8"/></model_instance></plate></config>',
        )
        archive.writestr(
            "Metadata/plate_1.gcode",
            "\n".join(
                (
                    "G90",
                    "M83",
                    "G92 E0",
                    "G0 X1 Y1 Z.2",
                    "; CHANGE_LAYER",
                    "; LAYER_HEIGHT: .2",
                    "; LINE_WIDTH: .5",
                    "; OBJECT_ID: 8",
                    "; FEATURE: Outer wall",
                    "G1 X2 E.1",
                )
            )
            + "\n",
        )
