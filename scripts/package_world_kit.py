"""Validate and publish a bounded world-kit into Veilroom's existing atlas format."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from PIL import Image, ImageChops


def package(source: Path, destination: Path) -> None:
    manifest = json.loads((source / "manifest.json").read_text())
    gallery = destination / "world-kit"
    gallery.mkdir(parents=True, exist_ok=True)
    for palette in ("wood-stone", "metal"):
        target = gallery / palette
        target.mkdir(exist_ok=True)
        for category, names in manifest["families"].items():
            if not 0 < len(names) < 15:
                raise ValueError("family does not fit legacy atlas")
            atlas = Image.new("RGBA", (512, 768))
            floor = Image.open(source.parent / "universal-room" / palette / "floor.png").convert(
                "RGBA"
            )
            atlas.paste(floor, (0, 0))
            for i, kind in enumerate(names, 1):
                sprite = Image.open(source / palette / (kind + ".png")).convert("RGBA")
                bounds = sprite.getchannel("A").getbbox()
                if (
                    sprite.size != (128, 192)
                    or not bounds
                    or bounds[0] <= 0
                    or bounds[1] <= 0
                    or bounds[2] >= 128
                    or bounds[3] >= 192
                ):
                    raise ValueError("empty or cropped sprite " + palette + "/" + kind)
                atlas.paste(sprite, ((i % 4) * 128, (i // 4) * 192))
                sprite.save(target / (kind + ".png"))
            atlas_id = f"world-{palette}-{category}"
            atlas.save(destination / (atlas_id + "-atlas.png"))
            floor.save(destination / (atlas_id + "-floor.png"))
            shutil.copyfile(
                source / f"{palette}-{category}.png", gallery / f"{palette}-{category}.png"
            )
            # Ready for the existing Tiled reader, with explicit physical blocking rather than guessed image alpha.
            ground = [1] * 300
            blocking = [int(i % 20 in (0, 19) or i // 20 in (0, 14)) for i in range(300)]
            blocking[0] = blocking[1] = blocking[21] = 0
            objects = []
            for i, kind in enumerate(names, 1):
                col = 3 + ((i - 1) % 5) * 3
                row = 4 + ((i - 1) // 5) * 5
                blocking[row * 20 + col] = (
                    0
                    if kind in ("path", "stairs", "arch", "gate_open", "plate_up", "plate_down")
                    else 1
                )
                objects.append(
                    {
                        "id": i,
                        "name": kind,
                        "x": col * 64 + 32,
                        "y": row * 64 + 32,
                        "width": 0,
                        "height": 0,
                        "properties": [{"name": "frame", "type": "int", "value": i}],
                    }
                )
            tiled = {
                "type": "map",
                "version": "1.10",
                "tiledversion": "1.11.0",
                "orientation": "orthogonal",
                "renderorder": "right-down",
                "width": 20,
                "height": 15,
                "tilewidth": 64,
                "tileheight": 64,
                "infinite": False,
                "properties": [{"name": "atlas", "type": "string", "value": atlas_id}],
                "layers": [
                    {
                        "type": "tilelayer",
                        "name": "ground",
                        "width": 20,
                        "height": 15,
                        "data": ground,
                    },
                    {
                        "type": "tilelayer",
                        "name": "blocking",
                        "width": 20,
                        "height": 15,
                        "data": blocking,
                    },
                    {"type": "objectgroup", "name": "decorations", "objects": objects},
                    {"type": "objectgroup", "name": "zones", "objects": []},
                ],
                "tilesets": [],
            }
            (gallery / f"{palette}-{category}.tmj").write_text(
                json.dumps(tiled, ensure_ascii=False, indent=2) + "\n"
            )
        for off, on in manifest["state_pairs"]:
            a = Image.open(target / (off + ".png")).convert("RGBA")
            b = Image.open(target / (on + ".png")).convert("RGBA")
            if ImageChops.difference(a, b).convert("RGB").getbbox() is None:
                raise ValueError("state has no visible outcome: " + off)
    for names in manifest["families"].values():
        for kind in names:
            a = Image.open(gallery / "wood-stone" / (kind + ".png")).convert("RGB")
            b = Image.open(gallery / "metal" / (kind + ".png")).convert("RGB")
            if ImageChops.difference(a, b).getbbox() is None:
                raise ValueError("palette has no visible outcome: " + kind)
    verification = json.loads((source / "verification.json").read_text())
    if verification.get("passed") is not True:
        raise ValueError("source Blender verification has not passed")
    with zipfile.ZipFile(gallery / "world-kit-blender.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name in ["world-kit.blend", "manifest.json", "verification.json", "README.md"]:
            archive.write(source / name, "world-kit/" + name)
        for palette in ("wood-stone", "metal"):
            for family in manifest["families"]:
                name = f"{palette}-{family}.blend"
                archive.write(source / name, "world-kit/" + name)
    files = [p for p in gallery.rglob("*") if p.is_file() and p.suffix in (".png", ".tmj", ".zip")]
    files += list(destination.glob("world-*-atlas.png")) + list(
        destination.glob("world-*-floor.png")
    )
    manifest["sha256"] = {
        str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files
    }
    (gallery / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    print("WORLD_KIT_PUBLISHED", len(manifest["assets"]), len(files))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    package(Path(__file__).resolve().parents[1] / "models/world-kit", args.destination)
