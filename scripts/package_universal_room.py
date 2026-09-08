"""Publish only validated game sprites; retain editable source in this project."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


def package(source: Path, destination: Path) -> None:
    manifest = json.loads((source / "manifest.json").read_text())
    destination.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for palette in ("wood-stone", "metal"):
        atlas = Image.new("RGBA", (512, 768))
        assets = [a for a in manifest["assets"] if a["palette"] == palette]
        if len(assets) != 15:
            raise ValueError(
                "expected 12 models, two alternate states and one wall orientation per palette"
            )
        for asset in assets:
            sprite = Image.open(source / palette / (asset["id"] + ".png")).convert("RGBA")
            expected = (64, 64) if asset["id"] == "floor" else (128, 192)
            if sprite.size != expected or sprite.getbbox() is None:
                raise ValueError("empty or incorrectly sized sprite: " + asset["id"])
            if asset["id"] != "floor":
                x0, y0, x1, y1 = sprite.getbbox()
                if x0 == 0 or y0 == 0 or x1 == 128 or y1 == 192:
                    raise ValueError("cropped sprite: " + asset["id"])
            index = asset["frame"]
            atlas.paste(sprite, ((index % 4) * 128, (index // 4) * 192))
        atlas.save(destination / (palette + "-atlas.png"))
        Image.open(source / palette / "floor.png").save(destination / (palette + "-floor.png"))
    for path in destination.glob("*.png"):
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest["sha256"] = hashes
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    package(Path(__file__).resolve().parents[1] / "models/universal-room", args.destination)
