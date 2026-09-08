"""The published library is a complete, metre-scale editable deliverable."""

import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "models/universal-room"


def test_all_module_states_and_palettes_are_shipped() -> None:
    manifest = json.loads((PACKAGE / "manifest.json").read_text())
    required = {
        "floor",
        "wall",
        "corner",
        "doorframe",
        "door_closed",
        "door_open",
        "table",
        "chair",
        "chest_closed",
        "chest_open",
        "cabinet",
        "shelf",
        "lamp",
        "noticeboard",
        "wall_side",
    }
    assert manifest["units"] == "metres" and manifest["tile_pixels"] == 64
    for palette in ("wood-stone", "metal"):
        assets = [a for a in manifest["assets"] if a["palette"] == palette]
        assert {a["id"] for a in assets} == required
        assert len({a["frame"] for a in assets}) == len(required)
        floor = next(a for a in assets if a["id"] == "floor")
        assert floor["dimensions_m"][:2] == [1, 1]
        for asset in assets:
            data = (PACKAGE / palette / (asset["id"] + ".png")).read_bytes()
            assert data[:8] == b"\x89PNG\r\n\x1a\n"
            expected = (64, 64) if asset["id"] == "floor" else (128, 192)
            assert struct.unpack(">II", data[16:24]) == expected
            assert data[25] == 6  # RGBA; the game needs transparent object backgrounds.
    assert (PACKAGE / "universal-room.blend").stat().st_size > 100000
    assert (PACKAGE / "warehouse.blend").stat().st_size > 100000
    assert (PACKAGE / "warehouse-preview.png").stat().st_size > 10000
