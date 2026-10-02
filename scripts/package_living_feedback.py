"""Publish verified Blender feedback as bounded, byte-checked sprite atlases."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.living_asset_contract import feedback_catalog, validate_feedback_catalog  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_source(source: Path, blend: str, key: str, expected: list[str]) -> None:
    try:
        report = json.loads((source / "verification.json").read_text())
        if report["passed"] is not True or report["source_sha256"] != digest(source / blend):
            raise ValueError("unverified Blender source")
        records = report[key]
        if len(records) != len(expected) or {r["file"] for r in records} != set(expected):
            raise ValueError("incomplete or duplicate verification coverage")
        for record in records:
            if record["rerender_equal"] is not True or record["sha256"] != digest(
                source / record["file"]
            ):
                raise ValueError("image changed after verification: " + record["file"])
    except (KeyError, TypeError) as error:
        raise ValueError("malformed verification evidence") from error


def atlas(paths: list[Path], size: tuple[int, int], output: Path) -> None:
    from PIL import Image

    sheet = Image.new("RGBA", (size[0] * len(paths), size[1]))
    for index, path in enumerate(paths):
        with Image.open(path) as image:
            if image.mode != "RGBA" or image.size != size:
                raise ValueError("invalid RGBA frame: " + str(path))
            bounds = image.getchannel("A").getbbox()
            if not bounds or not (
                0 < bounds[0] < bounds[2] < size[0] and 0 < bounds[1] < bounds[3] < size[1]
            ):
                raise ValueError("empty or clipped frame: " + str(path))
            sheet.paste(image, (index * size[0], 0))
    sheet.save(output)
    with Image.open(output) as reopened:
        for index, path in enumerate(paths):
            with Image.open(path) as original:
                crop = reopened.crop((index * size[0], 0, (index + 1) * size[0], size[1]))
                if crop.tobytes() != original.tobytes():
                    raise ValueError("atlas pixel mismatch: " + str(path))


def publish(destination: Path) -> None:
    manifest = feedback_catalog()
    items = ROOT / "models/living-items"
    effects = ROOT / "models/living-effects"
    manifest["items"] = json.loads((items / "items.json").read_text())["items"]
    manifest["effects"] = json.loads((effects / "effects.json").read_text())["effects"]
    validate_feedback_catalog(manifest)
    item_paths = [
        f"{s['id']}-{view}.png" for s in manifest["items"] for view in ("ground", "inventory")
    ]
    effect_paths = [f"{s['id']}/{frame:02d}.png" for s in manifest["effects"] for frame in range(8)]
    verify_source(items, "living-items.blend", "images", item_paths)
    verify_source(effects, "living-effects.blend", "frames", effect_paths)
    destination.mkdir(parents=True, exist_ok=True)
    files = []
    for effect in manifest["effects"]:
        paths = [effects / effect["id"] / f"{frame:02d}.png" for frame in range(8)]
        if len({digest(p) for p in paths}) != 8:
            raise ValueError("effect requires eight distinct rendered frames")
        name = effect["atlas"] + ".png"
        atlas(paths, (128, 128), destination / name)
        effect["rects"] = [[i * 128, 0, 128, 128] for i in range(8)]
        files.append(name)
    for view, size in [("ground", (128, 192)), ("inventory", (64, 64))]:
        paths = [items / (item[view]["image"] + ".png") for item in manifest["items"]]
        name = "items-" + view + "-atlas.png"
        atlas(paths, size, destination / name)
        files.append(name)
        for index, item in enumerate(manifest["items"]):
            item[view].update(
                {
                    "atlas": name[:-4],
                    "frame": index,
                    "atlas_size": [size[0] * 6, size[1]],
                    "rect": [index * size[0], 0, *size],
                }
            )
            # Individual inventory images can also be used by accessible HTML inventory lists.
            filename = item[view]["image"] + ".png"
            shutil.copyfile(items / filename, destination / filename)
            files.append(filename)
    for source, name in [(items, "items-preview.png"), (effects, "effects-preview.png")]:
        shutil.copyfile(source / name, destination / name)
        files.append(name)
    manifest["content_version"] = "1.0.0"
    manifest["source_version"] = (ROOT / "VERSION").read_text().strip()
    manifest["files"] = {name: digest(destination / name) for name in files}
    manifest["source_sha256"] = {
        name: digest(source / name)
        for source, name in [(items, "living-items.blend"), (effects, "living-effects.blend")]
    }
    manifest["total_png_bytes"] = sum((destination / name).stat().st_size for name in files)
    if manifest["total_png_bytes"] > 4 * 1024 * 1024:
        raise ValueError("feedback PNG budget exceeded")
    with zipfile.ZipFile(
        destination / "living-feedback-source.zip", "w", zipfile.ZIP_DEFLATED
    ) as archive:
        for source, images, blend, metadata, preview in [
            (items, item_paths, "living-items.blend", "items.json", "items-preview.png"),
            (effects, effect_paths, "living-effects.blend", "effects.json", "effects-preview.png"),
        ]:
            for name in [
                blend,
                metadata,
                preview,
                "README.md",
                "verification.json",
                "visual-review.md",
                *images,
            ]:
                archive.write(source / name, (source / name).relative_to(ROOT))
        for name in [
            "model_living_items.py",
            "model_living_effects.py",
            "verify_living_items.py",
            "verify_living_effects.py",
            "living_asset_contract.py",
            "package_living_feedback.py",
        ]:
            archive.write(ROOT / "scripts" / name, "scripts/" + name)
    manifest["source_archive_sha256"] = digest(destination / "living-feedback-source.zip")
    (destination / "feedback.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    print("LIVING_FEEDBACK_PUBLISHED", len(files), manifest["total_png_bytes"])


if __name__ == "__main__":
    publish(Path(sys.argv[1]))
