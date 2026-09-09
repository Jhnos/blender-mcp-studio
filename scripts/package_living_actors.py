"""Validate RGBA frames and publish a bounded editable source archive plus atlases."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.living_asset_contract import validate_actor  # noqa: E402


def publish(destination: Path) -> None:
    source = ROOT / "models/living-actors"
    manifest = json.loads((source / "manifest.json").read_text())
    assert json.loads((source / "verification.json").read_text())["passed"]
    destination.mkdir(parents=True, exist_ok=True)
    for actor in manifest["actors"]:
        validate_actor(actor)
        atlas = Image.new("RGBA", (1536, 768))
        images = []
        for i in range(48):
            image = Image.open(source / actor["id"] / f"{i:02d}.png").convert("RGBA")
            bounds = image.getchannel("A").getbbox()
            assert (
                image.size == (128, 192)
                and bounds
                and min(bounds[:2]) > 0
                and bounds[2] < 128
                and bounds[3] < 192
            ), (actor["id"], i, bounds)
            atlas.paste(image, ((i % 12) * 128, (i // 12) * 192))
            images.append(image)
        assert all(
            len({images[i].tobytes() for i in clip["frames"]}) > 1
            for clip in actor["clips"].values()
        )
        assert len({images[d * 12].tobytes() for d in range(4)}) == 4
        reopened = Image.open(
            ROOT / "tmp/living-actors-verify" / (actor["id"] + "-00.png")
        ).convert("RGBA")
        difference = ImageStat.Stat(ImageChops.difference(images[0], reopened))
        assert max(difference.mean) < 1, difference.mean
        atlas.save(destination / (actor["atlas"] + ".png"))
        shutil.copyfile(
            source / (actor["portrait"] + ".png"), destination / (actor["portrait"] + ".png")
        )
    marker_count = len(manifest["marker_kinds"]) * 3
    atlas = Image.new("RGBA", (192, len(manifest["marker_kinds"]) * 64))
    for i in range(marker_count):
        image = Image.open(source / "markers" / f"{i:02d}.png").convert("RGBA")
        assert image.size == (64, 64) and image.getchannel("A").getbbox()
        atlas.paste(image, ((i % 3) * 64, (i // 3) * 64))
    atlas.save(destination / "markers-atlas.png")
    for name in ("actors-preview.png", "markers-preview.png"):
        preview = Image.open(source / name).convert("RGBA")
        bounds = preview.getchannel("A").getbbox()
        assert (
            bounds
            and min(bounds[:2]) > 0
            and bounds[2] < preview.width
            and bounds[3] < preview.height
        ), (name, bounds)
        shutil.copyfile(source / name, destination / name)
    manifest["source_sha256"] = {
        name: hashlib.sha256((source / name).read_bytes()).hexdigest()
        for name in ("living-actors.blend", "living-markers.blend")
    }
    names = [a[k] + ".png" for a in manifest["actors"] for k in ("atlas", "portrait")] + [
        "markers-atlas.png",
        "actors-preview.png",
        "markers-preview.png",
    ]
    manifest["files"] = {
        name: hashlib.sha256((destination / name).read_bytes()).hexdigest() for name in names
    }
    manifest["source_generators"] = [
        "scripts/model_living_actors.py",
        "scripts/living_actor_geometry.py",
        "scripts/model_living_markers.py",
    ]
    (destination / "actors.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    with zipfile.ZipFile(
        destination / "living-actors-source.zip", "w", zipfile.ZIP_DEFLATED
    ) as archive:
        for name in (
            "living-actors.blend",
            "living-markers.blend",
            "manifest.json",
            "verification.json",
            "README.md",
        ):
            archive.write(source / name, "living-actors/" + name)
        for name in [
            "scripts/model_living_actors.py",
            "scripts/living_actor_geometry.py",
            "scripts/model_living_markers.py",
            "scripts/living_asset_contract.py",
            "scripts/package_living_actors.py",
            "scripts/verify_living_actors.py",
        ]:
            archive.write(ROOT / name, name)
    print(
        "LIVING_ASSETS_PUBLISHED",
        len(manifest["actors"]),
        sum((destination / name).stat().st_size for name in names),
    )


if __name__ == "__main__":
    publish(Path(sys.argv[1]))
