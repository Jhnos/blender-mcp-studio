"""Promote verified V6 manufacturing files from ignored output to a tracked package."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.verification.artifact_files import binary_stl_metrics  # noqa: E402


@dataclass(frozen=True, slots=True)
class Package:
    """One model's promotion contract: what moves, and what the manifest claims."""

    slug: str
    revision: str
    generator: str
    stl_files: tuple[str, ...]
    blend_file: str
    contracts: tuple[str, ...]


PACKAGES: dict[str, Package] = {
    "biaxial-hinge-v6": Package(
        slug="biaxial-hinge-v6",
        revision="V6",
        generator="scripts/model_biaxial_hinge.py",
        stl_files=(
            "body_mm.stl",
            "assembly_pin_mm.stl",
            "retaining_clip_mm.stl",
            "print_in_place_2body_double_head_mm.stl",
            "separate_parts_2body_2pin_2clip_mm.stl",
        ),
        blend_file="biaxial_hinge_v6.blend",
        contracts=(
            "scripts/verify/contracts/biaxial_hinge.json",
            "scripts/verify/contracts/biaxial_hinge_pip.json",
            "scripts/verify/contracts/biaxial_hinge_split.json",
            "scripts/verify/contracts/biaxial_hinge_probe.json",
            "scripts/verify/contracts/biaxial_hinge_split_probe.json",
        ),
    ),
    "octopus-hand-v1": Package(
        slug="octopus-hand-v1",
        revision="octopus-hand-V1",
        generator="scripts/model_octopus_hand.py",
        stl_files=(
            "test_coupon_mm.stl",
            "octopus_hand_v1_mm.stl",
            "palm_mm.stl",
            "arm_body_mm.stl",
            "arm_tip_mm.stl",
        ),
        blend_file="octopus_hand_v1.blend",
        contracts=(
            "scripts/verify/contracts/octopus_hand.json",
            "scripts/verify/contracts/octopus_hand_tips.json",
        ),
    ),
}

DEFAULT_PACKAGE = "biaxial-hinge-v6"
SOURCE = PROJECT_ROOT / "tmp" / DEFAULT_PACKAGE
DESTINATION = PROJECT_ROOT / "models" / DEFAULT_PACKAGE


def publish(
    source: Path = SOURCE,
    destination: Path = DESTINATION,
    package: Package = PACKAGES[DEFAULT_PACKAGE],
) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    entries: dict[str, dict[str, object]] = {}
    for name in (*package.stl_files, package.blend_file):
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
        "model_revision": package.revision,
        "units": "mm",
        "source_generator": package.generator,
        "verification_contracts": list(package.contracts),
        "files": entries,
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Promote verified manufacturing files into a controlled print package."
    )
    parser.add_argument("--package", choices=sorted(PACKAGES), default=DEFAULT_PACKAGE)
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--destination", type=Path, default=None)
    args = parser.parse_args()
    package = PACKAGES[args.package]
    source = args.source or PROJECT_ROOT / "tmp" / package.slug
    destination = args.destination or PROJECT_ROOT / "models" / package.slug
    publish(source, destination, package)


if __name__ == "__main__":
    main()
