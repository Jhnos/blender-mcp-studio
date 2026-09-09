#!/usr/bin/env python3
"""Does the same part build to the same mesh N times in the live Blender?

The lesson behind this (FF-18): a gate that demands an exact triangle count was
calibrated on one instance that happened to reproduce. Before trusting any
exact-count rule, build the part several times and look at the distribution.
This drives the generator's own ``realise``/``boolean``/``cleanup_mesh`` inside
the running Blender, records the triangle count and a vertex hash after every
operation, and prints every step whose result differs across runs.

Exit 0 when every run agrees, 1 when any step differs. A differing hash with an
equal count is still reported: that is the solver's ordering noise, the thing
the cleanup thresholds later turn into a sliver.

The Blender-side code imports this repository the way the contract bootstrap
does — module names as data, reloaded from the generator's import closure — so
the resident Blender runs the code that is on disk, not what it loaded last.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle  # noqa: E402
from src.core.domain.hand_instances import HAND_INSTANCES  # noqa: E402
from src.infrastructure.narrowing import (  # noqa: E402
    as_int,
    as_sequence,
    as_str,
    as_str_keyed_exact,
)
from src.verification.generator_imports import reload_modules_for  # noqa: E402

GEOMETRY = "scripts.hand_geometry"
PRIMITIVES = "scripts.blender_mesh_primitives"
INSTANCES = "src.core.domain.hand_instances"
PLAN = "src.core.planning.hand_plan"

PROBE = """
import bpy, hashlib, importlib, json, sys
root = {root}
if root not in sys.path:
    sys.path.insert(0, root)
modules = {{}}
for name in {modules}:
    modules[name] = importlib.reload(importlib.import_module(name))
hand_plan = modules[{plan}].hand_plan
instances = modules[{instances}].HAND_INSTANCES
cleanup_mesh = modules[{primitives}].cleanup_mesh
boolean, realise = modules[{geometry}].boolean, modules[{geometry}].realise
build_palm = modules[{geometry}].build_palm

def signature(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    digest = hashlib.sha1()
    for vertex in mesh.vertices:
        digest.update(("%.5f,%.5f,%.5f;" % tuple(vertex.co)).encode())
    return [len(mesh.loop_triangles), digest.hexdigest()[:8]]

plan = hand_plan(instances[{slug}])

# Every station's chain, not only the first. The palm and the outer stations were
# never measured while this probe read `loose_finger` alone, and an unmeasured
# part is exactly where a budget calibrated on luck goes wrong.
parts = []
seen = set()
for chain in plan.chains:
    for part in chain.parts:
        if part.name not in seen:
            seen.add(part.name)
            parts.append(part)

report = {{}}
for part in parts:
    runs = []
    for _ in range({runs}):
        body = realise(part.body)
        trail = [["body", *signature(body)]]
        for operation in part.operations:
            boolean(body, realise(operation.solid), operation.mode)
            trail.append([operation.solid.name + ":" + operation.mode, *signature(body)])
        cleanup_mesh(body)
        trail.append(["cleanup", *signature(body)])
        runs.append(trail)
        bpy.data.objects.remove(body, do_unlink=True)
    report[part.name] = runs

# The palm is built by its own generator function, not by the loop above: the
# roots are unioned on between two operation groups. Driving `build_palm` keeps
# this probe from carrying a second copy of that sequence, which would be one
# more thing able to stop tracking the generator.
palm_runs = []
for _ in range({runs}):
    palm = build_palm(plan.palm)
    palm_runs.append([["build_palm", *signature(palm)]])
    bpy.data.objects.remove(palm, do_unlink=True)
report[plan.palm.name] = palm_runs
print(json.dumps(report))
"""

Step = tuple[str, int, str]


def probe_code(slug: str, runs: int) -> str:
    closure = reload_modules_for(PROJECT_ROOT, PROJECT_ROOT / (GEOMETRY.replace(".", "/") + ".py"))
    modules = [*closure, INSTANCES, PLAN, PRIMITIVES, GEOMETRY]
    ordered = list(dict.fromkeys(modules))
    return PROBE.format(
        root=json.dumps(str(PROJECT_ROOT)),
        modules=json.dumps(ordered),
        plan=json.dumps(PLAN),
        instances=json.dumps(INSTANCES),
        primitives=json.dumps(PRIMITIVES),
        geometry=json.dumps(GEOMETRY),
        slug=json.dumps(slug),
        runs=runs,
    )


def _steps(value: object, part: str) -> list[list[Step]]:
    """Blender's JSON is untyped; refuse anything that is not the shape asked for."""
    runs = as_sequence(value)
    if runs is None:
        raise ValueError(f"{part}: runs are not a list")
    result: list[list[Step]] = []
    for run in runs:
        steps = as_sequence(run)
        if steps is None:
            raise ValueError(f"{part}: a run is not a list of steps")
        parsed: list[Step] = []
        for step in steps:
            fields = as_sequence(step)
            label = as_str(fields[0]) if fields and len(fields) == 3 else None
            count = as_int(fields[1]) if fields and len(fields) == 3 else None
            digest = as_str(fields[2]) if fields and len(fields) == 3 else None
            if label is None or count is None or digest is None:
                raise ValueError(f"{part}: malformed step {step!r}")
            parsed.append((label, count, digest))
        result.append(parsed)
    return result


def unstable_steps(runs: Sequence[Sequence[Step]]) -> list[tuple[str, list[int], str]]:
    """One row per step: label, counts across runs, and why it differs (or '')."""
    rows: list[tuple[str, list[int], str]] = []
    for index in range(len(runs[0])):
        label = runs[0][index][0]
        counts = [run[index][1] for run in runs]
        hashes = {run[index][2] for run in runs}
        if len(set(counts)) > 1:
            rows.append((label, counts, "triangle count differs"))
        elif len(hashes) > 1:
            rows.append((label, counts, f"{len(hashes)} distinct vertex orderings"))
        else:
            rows.append((label, counts, ""))
    return rows


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", default="hand-compact", choices=sorted(HAND_INSTANCES))
    parser.add_argument("--runs", type=int, default=4)
    parser.add_argument("--blender-host", default="127.0.0.1")
    parser.add_argument("--blender-port", type=int, default=9876)
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="write the measured per-part spread here (default: print only)",
    )
    return parser.parse_args(argv)


def final_spread(runs: Sequence[Sequence[Step]]) -> int:
    """How far the finished part's triangle count moved across the runs.

    The last step of each run is the part as it would be exported, so this is the
    number the sliver budget has to cover. The intermediate steps are diagnosis:
    they say *where* the noise entered, not how much of it survives.
    """
    finals = [run[-1][1] for run in runs]
    return max(finals) - min(finals)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    oracle = BlenderSocketOracle(args.blender_host, args.blender_port, timeout=900)
    report = oracle.execute_json(probe_code(args.instance, args.runs))
    unstable = 0
    spreads: dict[str, int] = {}
    for part, value in report.items():
        runs = _steps(value, part)
        spreads[part] = final_spread(runs)
        print(f"== {part} ({len(runs)} runs, final spread {spreads[part]})")
        for label, counts, why in unstable_steps(runs):
            note = f"   <-- {why}" if why else ""
            unstable += 1 if why else 0
            print(f"  {label:40s} {counts}{note}")

    if args.json is not None:
        merged = _merged_record(args.json, args.instance, args.runs, spreads)
        args.json.write_text(json.dumps(merged, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {args.json}")

    if unstable == 0:
        print("PASS every run agrees")
        return 0
    print(f"FAIL {unstable} step(s) differ across runs")
    return 1


def _merged_record(
    path: Path, slug: str, runs: int, spreads: dict[str, int]
) -> dict[str, object]:
    """Replace this instance's entry, keep the others.

    Measuring one instance must not silently drop the numbers taken for another;
    a record that shrank every time someone probed a single hand would report a
    coverage gap as if it were a measurement.
    """
    existing: dict[str, object] = {}
    if path.is_file():
        loaded = as_str_keyed_exact(json.loads(path.read_text(encoding="utf-8")))
        existing = loaded or {}
    instances = as_str_keyed_exact(existing.get("instances")) or {}
    instances[slug] = {"parts": spreads}
    return {
        "measured_on": date.today().isoformat(),
        "runs": runs,
        "instances": instances,
    }


if __name__ == "__main__":
    raise SystemExit(main())
