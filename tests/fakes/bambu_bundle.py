"""Tiny fake slicer .app trees with vendor profiles (2-level ``inherits`` plus an include).

``make_bundle`` is a BambuStudio-shaped app with the P2S leaves; ``make_orca_bundle`` is an
OrcaSlicer-shaped app with the Creality K1C leaves named in ``config/printers/creality``.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from src.core.domain.import_limits import ImportLimits

#: Import caps for adapter tests (the fake 3MFs are a few kB).
TEST_LIMITS = ImportLimits(10, 100000, 100000, 100000)

MACHINE_GEOMETRY = {
    "printer_model": "Bambu Lab P2S",
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

K1C_LEAVES = {
    "machine": "Creality K1C 0.4 nozzle",
    "process": "0.20mm Standard @Creality K1C",
    "filament": "Generic PLA @K1C-all",
}


def _write(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def make_bundle(tmp_path: Path, *, profiles: bool = True) -> Path:
    """Create ``Fake.app`` and return its ``Contents/MacOS/BambuStudio`` binary path."""
    return _make_app(tmp_path / "Fake.app", "BambuStudio", "BBL", LEAVES if profiles else None)


def make_orca_bundle(tmp_path: Path) -> Path:
    """Create ``Orca.app`` and return its ``Contents/MacOS/OrcaSlicer`` binary path."""
    return _make_app(tmp_path / "Orca.app", "OrcaSlicer", "Creality", K1C_LEAVES)


def _make_app(app: Path, exe: str, vendor: str, leaves: dict[str, str] | None) -> Path:
    binary = app / "Contents" / "MacOS" / exe
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    if leaves is None:
        return binary
    vendor_dir = app / "Contents" / "Resources" / "profiles" / vendor
    for kind, leaf in leaves.items():
        _write(
            vendor_dir / kind / f"{kind}_base.json",
            {
                "name": f"{kind}_base",
                "type": kind,
                "base_key": "base",
                "shared": "base",
                **(MACHINE_GEOMETRY if kind == "machine" else {}),
            },
        )
        _write(
            vendor_dir / kind / f"{kind}_extra.json",
            {"name": f"{kind}_extra", "extra_key": "extra", "shared": "extra"},
        )
        _write(
            vendor_dir / kind / f"{kind}_mid.json",
            {
                "name": f"{kind}_mid",
                "inherits": f"{kind}_base",
                "include": [f"{kind}_extra"],
                "mid_key": "mid",
            },
        )
        _write(
            vendor_dir / kind / f"{leaf}.json",
            {
                "type": kind,
                "name": leaf,
                "inherits": f"{kind}_mid",
                "instantiation": "true",
                "shared": "leaf",
                "leaf_key": "leaf",
                **_bed(kind),
            },
        )
    return binary


#: Every fake machine has a 220 x 220 printable area (the plate-fit precheck needs one).
FAKE_BED = ["0x0", "220x0", "220x220", "0x220"]


def _bed(kind: str) -> dict[str, object]:
    return {"printable_area": list(FAKE_BED)} if kind == "machine" else {}


def flattened(kind: str, leaves: dict[str, str] = LEAVES) -> dict[str, object]:
    """What the adapter must produce for ``kind`` from a fake bundle (v80 semantics)."""
    return {
        **(MACHINE_GEOMETRY if kind == "machine" else {}),  # the base; the leaf's bed wins
        "type": kind,
        "base_key": "base",
        "extra_key": "extra",
        "mid_key": "mid",
        "shared": "leaf",
        "leaf_key": "leaf",
        **_bed(kind),
        "name": leaves[kind],
        "instantiation": "true",
        "inherits": "",
        "from": "system",
    }


def make_named_bundle(root: Path) -> Path:
    """A ``profiles`` root whose file names differ from the JSON ``name`` (Creality style)."""
    vendor = root / "Acme"
    _write(vendor / "machine" / "m_file.json", {"name": "Acme Z 0.4 nozzle", "bed": "220x220"})
    _write(vendor / "process" / "base_file.json", {"name": "fdm base", "wall_loops": "2"})
    _write(
        vendor / "process" / "p_file.json",
        {
            "name": "0.20mm Standard @Acme",
            "inherits": "fdm base",
            "compatible_printers": ["Acme Z 0.4 nozzle"],
        },
    )
    _write(vendor / "filament" / "f_ok.json", {"name": "Acme PLA", "compatible_printers": []})
    _write(
        vendor / "filament" / "f_other.json",
        {"name": "Acme PETG", "compatible_printers": ["Acme Y 0.4 nozzle"]},
    )
    return root


def write_sliced_output(path: Path) -> None:
    """Minimal named Bambu output for command-adapter tests; real geometry is tested separately."""
    settings: dict[str, object] = {
        "printer_model": "Bambu Lab P2S",
        "nozzle_diameter": ["0.4"],
        "filament_type": ["PLA"],
        "layer_height": "0.2",
        "enable_support": "1",
        "brim_width": "3",
    }
    for kind in ("machine", "process", "filament"):
        profile = path.parent / (kind + ".json")
        if profile.exists():
            values = json.loads(profile.read_text())
            settings.update({key: values[key] for key in settings if key in values})
    header = (
        "; CONFIG_BLOCK_START\n"
        + "\n".join(
            "; " + key + " = " + str(value[0] if isinstance(value, list) else value)
            for key, value in settings.items()
        )
        + "\n; CONFIG_BLOCK_END\n"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Metadata/project_settings.config", json.dumps(settings))
        archive.writestr(
            "Metadata/model_settings.config",
            '<config><object id="2"><metadata key="name" value="lid"/></object><plate><metadata key="plater_id" value="1"/><model_instance><metadata key="object_id" value="2"/><metadata key="instance_id" value="0"/><metadata key="identify_id" value="8"/></model_instance></plate></config>',
        )
        archive.writestr(
            "Metadata/plate_1.gcode",
            header
            + "\n".join(
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
