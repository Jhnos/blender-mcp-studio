"""Promote verified V6 manufacturing files from ignored output to a tracked package."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.verification.artifact_files import binary_stl_metrics  # noqa: E402

SOURCE = PROJECT_ROOT / "tmp" / "biaxial-hinge-v6"
DESTINATION = PROJECT_ROOT / "models" / "biaxial-hinge-v6"
STL_FILES = (
    "body_mm.stl",
    "assembly_pin_mm.stl",
    "retaining_clip_mm.stl",
    "print_in_place_2body_double_head_mm.stl",
    "separate_parts_2body_2pin_2clip_mm.stl",
)
BLEND_FILE = "biaxial_hinge_v6.blend"


def publish(source: Path = SOURCE, destination: Path = DESTINATION) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    entries: dict[str, dict[str, object]] = {}
    for name in (*STL_FILES, BLEND_FILE):
        source_file = source / name
        if not source_file.is_file() or source_file.stat().st_size == 0:
            raise FileNotFoundError(f"verified source artifact is missing: {source_file}")
        target = destination / name
        shutil.copyfile(source_file, target)
        payload = target.read_bytes()
        entry: dict[str, object] = {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        if target.suffix == ".stl":
            metrics = binary_stl_metrics(payload)
            entry["triangle_count"] = metrics.triangle_count
            entry["dimensions_mm"] = list(metrics.dimensions_mm)
        entries[name] = entry
    manifest = {
        "model_revision": "V6",
        "units": "mm",
        "source_generator": "scripts/model_biaxial_hinge.py",
        "verification_contracts": [
            "scripts/verify/contracts/biaxial_hinge.json",
            "scripts/verify/contracts/biaxial_hinge_pip.json",
            "scripts/verify/contracts/biaxial_hinge_split.json",
            "scripts/verify/contracts/biaxial_hinge_probe.json",
            "scripts/verify/contracts/biaxial_hinge_split_probe.json",
        ],
        "files": entries,
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Promote verified V6 manufacturing files into a controlled print package."
    )
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--destination", type=Path, default=DESTINATION)
    args = parser.parse_args()
    publish(args.source, args.destination)


if __name__ == "__main__":
    main()
