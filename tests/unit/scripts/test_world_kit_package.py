"""Checks the actual new deliverables, independently of the generator list."""

import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "models/world-kit"


def test_world_kit_has_all_facets_and_alternate_states():
    manifest = json.loads((PACKAGE / "manifest.json").read_text())
    expected = {
        "window",
        "column",
        "stairs",
        "arch",
        "fence",
        "gate_closed",
        "gate_open",
        "tree",
        "bush",
        "rock",
        "path",
        "planter",
        "well",
        "barrel",
        "bench",
        "bed",
        "lever_off",
        "lever_on",
        "plate_up",
        "plate_down",
        "crystal_off",
        "crystal_on",
    }
    assert manifest["tile_pixels"] == 64
    assert manifest["anchor"] == [0.5, 0.75]
    for palette in ("wood-stone", "metal"):
        entries = [a for a in manifest["assets"] if a["palette"] == palette]
        assert {a["id"] for a in entries} == expected
        for asset in entries:
            data = (PACKAGE / palette / (asset["id"] + ".png")).read_bytes()
            assert struct.unpack(">II", data[16:24]) == (128, 192)
            assert data[25] == 6
            assert 0 < asset["frame"] < 15
        for category in ("architecture", "outdoors", "props"):
            assert (PACKAGE / f"{palette}-{category}.png").stat().st_size > 10000
    assert (PACKAGE / "world-kit.blend").stat().st_size > 100000


def test_real_gate_reopens_world_kit_with_fail_closed_blender_exit():
    ci = (ROOT / "scripts/ci.sh").read_text()
    assert "scripts/verify_world_kit.py" in ci
    assert "--python-exit-code 1" in ci
