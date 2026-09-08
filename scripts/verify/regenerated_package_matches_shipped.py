#!/usr/bin/env python3
"""Does the generator still produce the package that shipped?

Reads the shipped manifest under models/<slug>/ as the only expectation source
and the freshly exported STLs under tmp/<slug>/ (what the contract run just
generated). Triangle count must match exactly, dimensions within 0.1 mm; hashes
are never compared because STL export is not byte-reproducible. Exit 1 on any
mismatch, on any missing mesh, and on an empty population.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.publish_print_package import PACKAGES  # noqa: E402
from src.infrastructure.narrowing import as_str_keyed_exact  # noqa: E402
from src.verification.package_reproduction import (  # noqa: E402
    expected_from_manifest,
    reproduction_report,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, choices=sorted(PACKAGES))
    parser.add_argument(
        "--source", type=Path, default=None, help="regenerated STLs (default tmp/<slug>)"
    )
    parser.add_argument(
        "--shipped", type=Path, default=None, help="shipped package (default models/<slug>)"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    package = PACKAGES[args.package]
    source: Path = args.source or PROJECT_ROOT / "tmp" / package.slug
    shipped: Path = args.shipped or PROJECT_ROOT / "models" / package.slug

    manifest_path = shipped / "manifest.json"
    manifest = as_str_keyed_exact(json.loads(manifest_path.read_text()))
    if manifest is None:
        print(f"FAIL {manifest_path} is not a JSON object")
        return 1
    expected = expected_from_manifest(manifest, package.stl_files)
    payloads = {path.name: path.read_bytes() for path in sorted(source.glob("*.stl"))}
    report = reproduction_report(expected, payloads)

    print(f"shipped:     {shipped}")
    print(f"regenerated: {source}")
    for verdict in report.verdicts:
        if verdict.passed:
            print(
                f"  PASS {verdict.name}: {verdict.measured_triangles} triangles,"
                f" {verdict.measured_dimensions_mm}"
            )
        else:
            print(f"  FAIL {verdict.reason}")
    print(("PASS " if report.passed else "FAIL ") + report.summary)
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
