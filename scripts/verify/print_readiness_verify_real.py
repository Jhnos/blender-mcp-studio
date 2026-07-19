#!/usr/bin/env python3
"""Discriminating real-Blender fixtures for print-readiness inspection.

Fixtures are created and read back through the addon socket (independent
oracle). Reports are requested through the public REST and MCP boundaries.
Every object carries a nonce prefix and is removed in a finally block.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import socket
import ssl
import urllib.request
from dataclasses import dataclass
from typing import cast

from fastmcp import Client

DEFAULT_BASE_URL = "https://bearmacminimac-mini.tail56c751.ts.net/blender"
ORACLE_ADDRESS = ("127.0.0.1", 9876)


@dataclass(frozen=True, slots=True)
class Evidence:
    hypothesis: str
    passed: bool
    detail: str


def _oracle_response(code: str, timeout: float = 20.0) -> dict[str, object]:
    payload = json.dumps({"type": "execute_code", "params": {"code": code}}).encode()
    with socket.create_connection(ORACLE_ADDRESS, timeout=timeout) as connection:
        connection.settimeout(timeout)
        connection.sendall(payload)
        raw = b""
        while True:
            chunk = connection.recv(65536)
            if not chunk:
                break
            raw += chunk
            try:
                decoded = json.loads(raw.decode())
            except json.JSONDecodeError:
                continue
            if not isinstance(decoded, dict):
                raise RuntimeError("Oracle returned non-object JSON")
            return cast(dict[str, object], decoded)
    raise RuntimeError("Oracle closed without a complete response")


def _oracle_stdout(code: str) -> str:
    response = _oracle_response(code)
    if response.get("status") != "success":
        raise RuntimeError(f"Oracle execute_code failed: {response!r}")
    result = response.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("result"), str):
        raise RuntimeError(f"Unexpected oracle result: {response!r}")
    return result["result"].strip()


def _cleanup(prefix: str) -> int:
    quoted = json.dumps(prefix)
    output = _oracle_stdout(
        "import bpy, json\n"
        f"objects = [obj for obj in bpy.data.objects if obj.name.startswith({quoted})]\n"
        "for obj in objects:\n"
        "    bpy.data.objects.remove(obj, do_unlink=True)\n"
        "print(json.dumps({'removed': len(objects)}))"
    )
    result = json.loads(output)
    if not isinstance(result, dict) or not isinstance(result.get("removed"), int):
        raise RuntimeError(f"Unexpected cleanup result: {result!r}")
    return result["removed"]


def _seed(prefix: str, body: str) -> None:
    quoted = json.dumps(prefix)
    _oracle_stdout(
        "import bpy, json\n"
        "for obj in bpy.context.scene.objects:\n"
        "    obj.select_set(False)\n"
        f"prefix = {quoted}\n"
        f"{body}\n"
        "selected = []\n"
        "for obj in bpy.context.scene.objects:\n"
        "    if obj.name.startswith(prefix):\n"
        "        obj.hide_set(False)\n"
        "        obj.hide_viewport = False\n"
        "        obj.select_set(True)\n"
        "        selected.append(obj.name)\n"
        "print(json.dumps(selected))"
    )


def _rest_report(base_url: str, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "selection_only": True,
        "apply_modifiers": True,
        "min_wall_thickness_mm": 0.8,
        "overhang_angle_deg": 45.0,
    }
    body.update(overrides)
    request = urllib.request.Request(
        f"{base_url}/api/print-readiness",
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(
        request, timeout=40, context=ssl.create_default_context()
    ) as response:
        result = json.loads(response.read())
    if not isinstance(result, dict):
        raise RuntimeError(f"REST returned a non-object report: {result!r}")
    return cast(dict[str, object], result)


def _issue_codes(report: dict[str, object]) -> set[str]:
    issues = report.get("issues")
    if not isinstance(issues, list):
        raise RuntimeError(f"Report issues are invalid: {report!r}")
    return {
        item["code"]
        for item in issues
        if isinstance(item, dict) and isinstance(item.get("code"), str)
    }


def _metrics(report: dict[str, object]) -> dict[str, object]:
    metrics = report.get("metrics")
    if not isinstance(metrics, dict):
        raise RuntimeError(f"Report metrics are invalid: {report!r}")
    return cast(dict[str, object], metrics)


def _record(evidence: list[Evidence], hypothesis: str, passed: bool, detail: str) -> None:
    evidence.append(Evidence(hypothesis, passed, detail))
    print(f"[{'PASS' if passed else 'FAIL'}] {hypothesis}: {detail}")


async def _mcp_report(endpoint: str) -> dict[str, object]:
    async with Client(endpoint) as client:
        result = await client.call_tool(
            "check_print_readiness",
            {
                "selection_only": True,
                "apply_modifiers": True,
                "min_wall_thickness_mm": 0.8,
                "overhang_angle_deg": 45.0,
            },
            raise_on_error=False,
        )
    if result.is_error or not isinstance(result.structured_content, dict):
        raise RuntimeError(f"MCP readiness failed: {result.content!r}")
    return cast(dict[str, object], result.structured_content)


async def _verify() -> int:
    base_url = os.environ.get("BLENDER_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    endpoint = os.environ.get("BLENDER_MCP_URL", f"{base_url}/mcp")
    prefix = f"verify_print_{secrets.token_hex(4)}_"
    evidence: list[Evidence] = []

    try:
        _cleanup(prefix)

        _seed(
            prefix,
            "bpy.ops.mesh.primitive_cube_add(size=0.02, location=(0, 0, 0.01))\n"
            "bpy.context.object.name = prefix + 'cube'",
        )
        cube = _rest_report(base_url)
        cube_metrics = _metrics(cube)
        cube_dimensions = cube_metrics.get("dimensions_mm")
        cube_volume = cube_metrics.get("estimated_volume_mm3")
        cube_ok = (
            cube.get("status") == "ready"
            and isinstance(cube_dimensions, list)
            and all(abs(float(value) - 20.0) < 0.05 for value in cube_dimensions)
            and isinstance(cube_volume, (int, float))
            and abs(float(cube_volume) - 8000.0) < 1.0
        )
        _record(
            evidence,
            "Watertight cube",
            cube_ok,
            f"status={cube.get('status')}, dimensions={cube_dimensions}, volume={cube_volume}",
        )

        mcp_cube = await _mcp_report(endpoint)
        _record(
            evidence,
            "REST equals MCP",
            mcp_cube == cube,
            f"same structured report={mcp_cube == cube}",
        )

        _cleanup(prefix)
        _seed(
            prefix,
            "verts = [(-.01,-.01,0),(.01,-.01,0),(.01,.01,0),(-.01,.01,0),"
            "(-.01,-.01,.02),(.01,-.01,.02),(.01,.01,.02),(-.01,.01,.02)]\n"
            "faces = [(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]\n"
            "mesh = bpy.data.meshes.new(prefix + 'open_mesh')\n"
            "mesh.from_pydata(verts, [], faces)\n"
            "obj = bpy.data.objects.new(prefix + 'open_cube', mesh)\n"
            "bpy.context.collection.objects.link(obj)",
        )
        open_cube = _rest_report(base_url)
        _record(
            evidence,
            "Open cube",
            "non_manifold_edges" in _issue_codes(open_cube),
            f"status={open_cube.get('status')}, issues={sorted(_issue_codes(open_cube))}",
        )

        _cleanup(prefix)
        _seed(
            prefix,
            "mesh = bpy.data.meshes.new(prefix + 'flat_mesh')\n"
            "mesh.from_pydata([(0,0,0),(.02,0,0),(0,.02,0)], [], [(0,1,2)])\n"
            "obj = bpy.data.objects.new(prefix + 'flat', mesh)\n"
            "bpy.context.collection.objects.link(obj)",
        )
        flat = _rest_report(base_url)
        flat_codes = _issue_codes(flat)
        _record(
            evidence,
            "Zero-volume geometry",
            {"non_manifold_edges", "zero_volume"}.issubset(flat_codes),
            f"issues={sorted(flat_codes)}",
        )

        _cleanup(prefix)
        _seed(
            prefix,
            "bpy.ops.mesh.primitive_cube_add(size=.02, location=(-.003,0,.01))\n"
            "bpy.context.object.name = prefix + 'intersect_a'\n"
            "bpy.ops.mesh.primitive_cube_add(size=.02, location=(.003,0,.01))\n"
            "bpy.context.object.name = prefix + 'intersect_b'",
        )
        intersecting = _rest_report(base_url)
        _record(
            evidence,
            "Intersecting cubes",
            intersecting.get("status") == "review"
            and "intersections" in _issue_codes(intersecting),
            f"status={intersecting.get('status')}, issues={sorted(_issue_codes(intersecting))}",
        )

        _cleanup(prefix)
        _seed(
            prefix,
            "bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,.0002))\n"
            "obj = bpy.context.object\n"
            "obj.name = prefix + 'thin_plate'\n"
            "obj.dimensions = (.02, .02, .0004)\n"
            "bpy.context.view_layer.update()",
        )
        thin = _rest_report(base_url)
        _record(
            evidence,
            "0.4 mm thin plate",
            "thin_walls" in _issue_codes(thin),
            f"issues={sorted(_issue_codes(thin))}",
        )

        _cleanup(prefix)
        _seed(
            prefix,
            "bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,.001))\n"
            "base = bpy.context.object\n"
            "base.name = prefix + 'overhang_base'\n"
            "base.dimensions = (.02,.02,.002)\n"
            "bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,.012))\n"
            "shelf = bpy.context.object\n"
            "shelf.name = prefix + 'overhang_shelf'\n"
            "shelf.dimensions = (.02,.02,.002)\n"
            "bpy.context.view_layer.update()",
        )
        overhang_45 = _rest_report(base_url, overhang_angle_deg=45.0)
        overhang_90 = _rest_report(base_url, overhang_angle_deg=90.0)
        _record(
            evidence,
            "Overhang threshold",
            "overhangs" in _issue_codes(overhang_45)
            and "overhangs" not in _issue_codes(overhang_90),
            f"45°={sorted(_issue_codes(overhang_45))}, 90°={sorted(_issue_codes(overhang_90))}",
        )

        _cleanup(prefix)
        _seed(
            prefix,
            "size = 102\n"
            "verts = [(x*.0001,y*.0001,0) for y in range(size) for x in range(size)]\n"
            "faces = []\n"
            "for y in range(size-1):\n"
            "    for x in range(size-1):\n"
            "        a = y*size+x; b=a+1; c=a+size; d=c+1\n"
            "        faces.extend([(a,b,d),(a,d,c)])\n"
            "mesh = bpy.data.meshes.new(prefix + 'large_mesh')\n"
            "mesh.from_pydata(verts, [], faces)\n"
            "obj = bpy.data.objects.new(prefix + 'large', mesh)\n"
            "bpy.context.collection.objects.link(obj)",
        )
        large = _rest_report(base_url)
        _record(
            evidence,
            "Analysis cap",
            large.get("analysis_truncated") is True and "analysis_truncated" in _issue_codes(large),
            f"triangles={_metrics(large).get('triangle_count')}, truncated={large.get('analysis_truncated')}",
        )
    except Exception as exc:
        _record(evidence, "Verification runtime", False, f"{type(exc).__name__}: {exc}")
    finally:
        try:
            removed = _cleanup(prefix)
            _record(evidence, "Teardown", True, f"removed={removed}")
        except Exception as exc:
            _record(evidence, "Teardown", False, f"{type(exc).__name__}: {exc}")

    print("\n=== PRINT READINESS REAL EVIDENCE ===")
    for item in evidence:
        print(f"{item.hypothesis:24} {'PASS' if item.passed else 'FAIL'}")
    passed = sum(item.passed for item in evidence)
    print(f"{passed}/{len(evidence)} passed; prefix={prefix}")
    return 0 if evidence and all(item.passed for item in evidence) else 1


def main() -> None:
    raise SystemExit(asyncio.run(_verify()))


if __name__ == "__main__":
    main()
