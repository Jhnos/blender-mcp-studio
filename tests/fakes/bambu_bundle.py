"""Tiny fake slicer .app trees with vendor profiles (2-level ``inherits`` plus an include).

``make_bundle`` is a BambuStudio-shaped app with the P2S leaves; ``make_orca_bundle`` is an
OrcaSlicer-shaped app with the Creality K1C leaves named in ``config/printers/creality``.
"""

from __future__ import annotations

import json
from pathlib import Path

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
            {"name": f"{kind}_base", "type": kind, "base_key": "base", "shared": "base"},
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
