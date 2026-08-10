#!/usr/bin/env python3
"""Prove one REST batch transform is one real Blender Undo transaction."""

from __future__ import annotations

import json
import math
import os
import secrets
import socket
import ssl
import urllib.request
from dataclasses import dataclass
from typing import cast

DEFAULT_BASE_URL = "https://bearmacminimac-mini.tail56c751.ts.net/blender"
ORACLE_ADDRESS = ("127.0.0.1", 9876)
TOLERANCE = 1e-6


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
    output = _oracle_stdout(
        "import bpy, json\n"
        f"prefix = {json.dumps(prefix)}\n"
        "objects = [obj for obj in bpy.data.objects if obj.name.startswith(prefix)]\n"
        "for obj in objects:\n"
        "    bpy.data.objects.remove(obj, do_unlink=True)\n"
        "print(json.dumps({'removed': len(objects)}))"
    )
    result = json.loads(output)
    if not isinstance(result, dict) or not isinstance(result.get("removed"), int):
        raise RuntimeError(f"Unexpected cleanup result: {result!r}")
    return result["removed"]


def _seed(prefix: str) -> tuple[str, str]:
    left = prefix + "left"
    right = prefix + "right"
    _oracle_stdout(
        "import bpy, json\n"
        f"left_name = {json.dumps(left)}\n"
        f"right_name = {json.dumps(right)}\n"
        "verts = [(-.01,-.01,-.01),(.01,-.01,-.01),(.01,.01,-.01),"
        "(-.01,.01,-.01),(-.01,-.01,.01),(.01,-.01,.01),(.01,.01,.01),"
        "(-.01,.01,.01)]\n"
        "faces = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),"
        "(2,3,7,6),(3,0,4,7)]\n"
        "class BLENDER_MCP_OT_seed_batch_fixture(bpy.types.Operator):\n"
        "    bl_idname = 'blender_mcp.seed_batch_fixture'\n"
        "    bl_label = 'Seed Batch Fixture'\n"
        "    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}\n"
        "    def execute(self, context):\n"
        "        def add(name, location, rotation, scale):\n"
        "            mesh = bpy.data.meshes.new(name + '_mesh')\n"
        "            mesh.from_pydata(verts, [], faces)\n"
        "            obj = bpy.data.objects.new(name, mesh)\n"
        "            context.collection.objects.link(obj)\n"
        "            obj.location = location\n"
        "            obj.rotation_euler = rotation\n"
        "            obj.scale = scale\n"
        "        add(left_name, (-.03, 0, .01), (.1, .2, .3), (1.0, 1.2, .8))\n"
        "        add(right_name, (.03, 0, .01), (-.2, .1, -.1), (.9, 1.1, 1.3))\n"
        "        return {'FINISHED'}\n"
        "bpy.utils.register_class(BLENDER_MCP_OT_seed_batch_fixture)\n"
        "try:\n"
        "    result = bpy.ops.blender_mcp.seed_batch_fixture('EXEC_DEFAULT', True)\n"
        "    if 'FINISHED' not in result:\n"
        "        raise RuntimeError('Fixture seed was cancelled')\n"
        "finally:\n"
        "    bpy.utils.unregister_class(BLENDER_MCP_OT_seed_batch_fixture)\n"
        "print(json.dumps([left_name, right_name]))"
    )
    return left, right


def _transforms(names: tuple[str, ...]) -> dict[str, dict[str, list[float]]]:
    output = _oracle_stdout(
        "import bpy, json\n"
        f"names = {json.dumps(list(names))}\n"
        "state = {}\n"
        "for name in names:\n"
        "    obj = bpy.data.objects.get(name)\n"
        "    if obj is not None:\n"
        "        state[name] = {\n"
        "            'location': list(obj.location),\n"
        "            'rotation': list(obj.rotation_euler),\n"
        "            'scale': list(obj.scale),\n"
        "        }\n"
        "print(json.dumps(state, sort_keys=True))"
    )
    raw = json.loads(output)
    if not isinstance(raw, dict):
        raise RuntimeError(f"Unexpected transform result: {raw!r}")
    result: dict[str, dict[str, list[float]]] = {}
    for name, value in raw.items():
        if not isinstance(name, str) or not isinstance(value, dict):
            raise RuntimeError(f"Unexpected object transform: {name!r}={value!r}")
        channels: dict[str, list[float]] = {}
        for channel in ("location", "rotation", "scale"):
            vector = value.get(channel)
            if not isinstance(vector, list) or len(vector) != 3:
                raise RuntimeError(f"Unexpected {channel}: {vector!r}")
            channels[channel] = [float(component) for component in vector]
        result[name] = channels
    return result


def _rest_json(
    base_url: str,
    path: str,
    body: dict[str, object] | None = None,
) -> dict[str, object]:
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=None if body is None else json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    with urllib.request.urlopen(
        request,
        timeout=30,
        context=ssl.create_default_context(),
    ) as response:
        result = json.loads(response.read())
    if not isinstance(result, dict):
        raise RuntimeError(f"REST returned non-object JSON: {result!r}")
    return cast(dict[str, object], result)


def _close(left: float, right: float) -> bool:
    return abs(left - right) <= TOLERANCE


def _expected_after(
    before: dict[str, dict[str, list[float]]],
) -> dict[str, dict[str, list[float]]]:
    expected: dict[str, dict[str, list[float]]] = {}
    for name, channels in before.items():
        expected[name] = {
            "location": [
                channels["location"][0] + 0.01,
                channels["location"][1] - 0.02,
                channels["location"][2] + 0.03,
            ],
            "rotation": [
                channels["rotation"][0],
                channels["rotation"][1] + math.radians(15.0),
                channels["rotation"][2] - math.radians(30.0),
            ],
            "scale": [
                channels["scale"][0] * 1.1,
                channels["scale"][1] * 0.9,
                channels["scale"][2] * 1.05,
            ],
        }
    return expected


def _states_equal(
    actual: dict[str, dict[str, list[float]]],
    expected: dict[str, dict[str, list[float]]],
) -> bool:
    if actual.keys() != expected.keys():
        return False
    return all(
        _close(actual[name][channel][axis], expected[name][channel][axis])
        for name in expected
        for channel in ("location", "rotation", "scale")
        for axis in range(3)
    )


def _record(
    evidence: list[Evidence],
    hypothesis: str,
    passed: bool,
    detail: str,
) -> None:
    evidence.append(Evidence(hypothesis, passed, detail))
    print(f"[{'PASS' if passed else 'FAIL'}] {hypothesis}: {detail}")


def main() -> int:
    base_url = os.environ.get("BLENDER_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    prefix = f"verify_batch_{secrets.token_hex(4)}_"
    evidence: list[Evidence] = []
    try:
        _cleanup(prefix)
        names = _seed(prefix)
        before = _transforms(names)
        receipt = _rest_json(
            base_url,
            "/api/scene/batch-transform",
            {
                "object_names": list(names),
                "translation_mm": [10.0, -20.0, 30.0],
                "rotation_deg": [0.0, 15.0, -30.0],
                "scale_percent": [10.0, -10.0, 5.0],
            },
        )
        after = _transforms(names)
        expected = _expected_after(before)
        _record(
            evidence,
            "One REST request updates both objects",
            receipt.get("affected_count") == 2 and _states_equal(after, expected),
            f"receipt={receipt}, state_matches={_states_equal(after, expected)}",
        )

        undo = _rest_json(base_url, "/api/undo")
        restored = _transforms(names)
        _record(
            evidence,
            "One Undo restores both objects",
            undo.get("success") is True and _states_equal(restored, before),
            f"undo={undo}, restored={_states_equal(restored, before)}",
        )
    finally:
        removed = _cleanup(prefix)
        print(f"[CLEANUP] removed={removed}, prefix={prefix}")

    failures = [item for item in evidence if not item.passed]
    print(f"Evidence: {len(evidence) - len(failures)}/{len(evidence)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
