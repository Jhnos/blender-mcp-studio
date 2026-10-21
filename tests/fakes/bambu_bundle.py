"""A tiny fake BambuStudio.app tree with vendor profiles (2-level ``inherits`` plus an include)."""

from __future__ import annotations

import json
from pathlib import Path

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
            bbl / kind / f"{kind}_base.json", {"type": kind, "base_key": "base", "shared": "base"}
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
    }
