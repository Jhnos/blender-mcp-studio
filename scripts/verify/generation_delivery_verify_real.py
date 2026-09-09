#!/usr/bin/env python3
"""Does the product's own path build what the shipped package contains?

Runs the build through the public REST endpoint — the path a user reaches —
and then compares the result against the shipped manifest with the same
plan-derived sliver budgets the script path is held to.

Two properties, both of which a green run has to earn:

* `tmp/<slug>` is emptied first. A differential that reads a directory still
  holding the previous run's output goes green even when nothing was built
  (`docs/LESSONS_LEARNED.md`, "差分閘門讀的目錄裡還躺著上一次的輸出").
* The numbers the API reported are compared against the bytes on disk. An
  endpoint that answered with plausible fiction would otherwise pass.

The URL is the current machine's own Tailscale FQDN, read at run time. A
hard-coded host verifies some other machine, or nothing.
"""

from __future__ import annotations

import argparse
import json
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.publish_print_package import PACKAGES  # noqa: E402
from src.core.domain.hand_instances import HAND_INSTANCES  # noqa: E402
from src.infrastructure.narrowing import (  # noqa: E402
    as_nonempty_sequence,
    as_nonempty_str,
    as_positive_int,
    as_str_keyed_exact,
)
from src.verification.artifact_files import binary_stl_metrics  # noqa: E402
from src.verification.package_reproduction import (  # noqa: E402
    expected_from_manifest,
    reproduction_report,
    sliver_budgets,
)

BUILD_TIMEOUT_S = 900


def self_fqdn() -> str:
    """This machine's Tailscale name, never a literal."""
    raw = subprocess.run(
        ["tailscale", "status", "--self", "--json"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    status = as_str_keyed_exact(json.loads(raw))
    self_node = as_str_keyed_exact((status or {}).get("Self"))
    name = (self_node or {}).get("DNSName")
    if not isinstance(name, str) or not name:
        raise RuntimeError("tailscale status did not report Self.DNSName")
    return name.rstrip(".")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, choices=sorted(PACKAGES))
    parser.add_argument("--base", default=None, help="default https://<self fqdn>/blender")
    return parser.parse_args(argv)


def _empty_output_dir(directory: Path) -> int:
    removed = 0
    for path in sorted(directory.glob("*.stl")):
        path.unlink()
        removed += 1
    return removed


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    package = PACKAGES[args.package]
    instance = HAND_INSTANCES.get(package.slug)
    if instance is None:
        print(f"FAIL {package.slug} is not a registered instance")
        return 1

    base = args.base or f"https://{self_fqdn()}/blender"
    source = PROJECT_ROOT / instance.output_dir
    source.mkdir(parents=True, exist_ok=True)
    print(f"endpoint:  {base}/api/instances/{instance.slug}/build")
    print(f"cleared:   {_empty_output_dir(source)} stale STL(s) from {source}")

    request = urllib.request.Request(
        f"{base}/api/instances/{instance.slug}/build", data=b"", method="POST"
    )
    with urllib.request.urlopen(
        request, timeout=BUILD_TIMEOUT_S, context=ssl.create_default_context()
    ) as response:
        if response.status != 200:
            print(f"FAIL build endpoint answered {response.status}")
            return 1
        reported = as_str_keyed_exact(json.loads(response.read()))
    if reported is None:
        print("FAIL build endpoint did not answer with a JSON object")
        return 1

    payloads = {path.name: path.read_bytes() for path in sorted(source.glob("*.stl"))}

    parts = as_nonempty_sequence(reported.get("parts"))
    if parts is None:
        print("FAIL build endpoint reported no parts")
        return 1

    failures = 0
    for entry in parts:
        part = as_str_keyed_exact(entry)
        name = as_nonempty_str((part or {}).get("name"))
        reported_faces = as_positive_int((part or {}).get("face_count"))
        if name is None or reported_faces is None:
            print(f"  FAIL a reported part is not a named mesh with a face count: {entry!r}")
            failures += 1
            continue
        payload = payloads.get(name)
        if payload is None:
            print(f"  FAIL {name}: the API reported it but nothing was written")
            failures += 1
            continue
        measured = binary_stl_metrics(payload)
        if measured.triangle_count != reported_faces:
            print(
                f"  FAIL {name}: API said {reported_faces} triangles,"
                f" the file has {measured.triangle_count}"
            )
            failures += 1
    print(f"API numbers vs bytes on disk: {'PASS' if failures == 0 else 'FAIL'}")

    manifest = as_str_keyed_exact(
        json.loads((PROJECT_ROOT / "models" / package.slug / "manifest.json").read_text())
    )
    if manifest is None:
        print("FAIL shipped manifest is not a JSON object")
        return 1
    expected = expected_from_manifest(manifest, package.stl_files, sliver_budgets(instance))
    report = reproduction_report(expected, payloads)
    for verdict in report.verdicts:
        print(
            f"  {'PASS' if verdict.passed else 'FAIL'} {verdict.name}:"
            f" {verdict.measured_triangles} triangles, {verdict.measured_dimensions_mm}"
            + ("" if verdict.passed else f" — {verdict.reason}")
        )
    print(("PASS " if report.passed else "FAIL ") + report.summary)
    return 0 if report.passed and failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
