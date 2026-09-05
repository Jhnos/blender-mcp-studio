#!/usr/bin/env python3
"""Discriminating real-machine MCP-to-Blender verification.

Interaction uses the canonical Streamable HTTP MCP endpoint. Ground truth uses
the addon socket directly, so the system does not verify mutations through the
same path that made them.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import socket
import sys
from dataclasses import dataclass
from pathlib import Path

from fastmcp import Client

# ci.sh runs this as a subprocess, not through pytest, so nothing else puts the
# repository root on the path.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.infrastructure.narrowing import (  # noqa: E402
    as_int,
    as_str,
    as_str_keyed_exact,
    dig,
    required,
)

DEFAULT_MCP_URL = "https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp"
ORACLE_ADDRESS = ("127.0.0.1", 9876)


@dataclass(frozen=True, slots=True)
class Evidence:
    hypothesis: str
    passed: bool
    detail: str


def _socket_is_listening(timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection(ORACLE_ADDRESS, timeout=timeout):
            return True
    except OSError:
        return False


def _oracle_response(code: str, timeout: float = 10.0) -> dict[str, object]:
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
            return required(
                decoded,
                as_str_keyed_exact,
                message="Oracle returned a non-object JSON value",
                error=RuntimeError,
            )
    raise RuntimeError("Oracle closed the socket without a complete JSON response")


def _oracle_stdout(code: str) -> str:
    response = _oracle_response(code)
    if response.get("status") != "success":
        raise RuntimeError(f"Oracle execute_code failed: {response!r}")
    text = as_str(dig(response, "result", "result"))
    if text is None:
        raise RuntimeError(f"Oracle returned an unexpected success shape: {response!r}")
    return text.strip()


def _oracle_json(code: str) -> object:
    return json.loads(_oracle_stdout(code))


def _cleanup_verification_objects() -> int:
    code = """\
import bpy, json

objects = [obj for obj in bpy.data.objects if obj.name.startswith('verify_mcp_')]
for obj in objects:
    bpy.data.objects.remove(obj, do_unlink=True)
print(json.dumps({"removed": len(objects)}))
"""
    result = _oracle_json(code)
    removed = as_int(dig(result, "removed"))
    if removed is None:
        raise RuntimeError(f"Cleanup returned an unexpected value: {result!r}")
    return removed


def _record(evidence: list[Evidence], hypothesis: str, passed: bool, detail: str) -> None:
    item = Evidence(hypothesis, passed, detail)
    evidence.append(item)
    print(f"[{'PASS' if passed else 'FAIL'}] {hypothesis}: {detail}")


def _tool_detail(result: object) -> str:
    content = getattr(result, "content", None)
    return str(content)[:240]


async def _verify() -> int:
    if not _socket_is_listening():
        print("SKIP: Blender addon is not listening on 127.0.0.1:9876")
        return 0

    endpoint = os.environ.get("BLENDER_MCP_URL", DEFAULT_MCP_URL)
    nonce = f"verify_mcp_{secrets.token_hex(4)}"
    quoted_name = json.dumps(nonce)
    evidence: list[Evidence] = []

    try:
        removed_before = _cleanup_verification_objects()
        _record(evidence, "Preflight cleanup", True, f"removed={removed_before}")
        async with Client(endpoint) as client:
            created = await client.call_tool(
                "create_object",
                {"object_type": "MESH", "name": nonce},
                raise_on_error=False,
            )
            create_ok = not created.is_error
            _record(evidence, "MCP create", create_ok, _tool_detail(created))

            if create_ok:
                geometry = _oracle_json(
                    "import bpy, json\n"
                    f"obj = bpy.data.objects.get({quoted_name})\n"
                    'print(json.dumps({"exists": obj is not None, '
                    "\"vertices\": len(obj.data.vertices) if obj and obj.type == 'MESH' else None}))"
                )
                geometry_ok = geometry == {"exists": True, "vertices": 8}
                _record(evidence, "Oracle geometry", geometry_ok, repr(geometry))

                modified = await client.call_tool(
                    "modify_object",
                    {"name": nonce, "location": [1.0, 2.0, 3.0]},
                    raise_on_error=False,
                )
                modify_ok = not modified.is_error
                _record(evidence, "MCP modify", modify_ok, _tool_detail(modified))

                if modify_ok:
                    location = _oracle_json(
                        "import bpy, json\n"
                        f"obj = bpy.data.objects.get({quoted_name})\n"
                        "print(json.dumps(list(obj.location) if obj else None))"
                    )
                    location_ok = location == [1.0, 2.0, 3.0]
                    _record(evidence, "Oracle location", location_ok, repr(location))

                deleted = await client.call_tool(
                    "delete_object",
                    {"name": nonce},
                    raise_on_error=False,
                )
                delete_ok = not deleted.is_error
                _record(evidence, "MCP delete", delete_ok, _tool_detail(deleted))

                if delete_ok:
                    exists = _oracle_json(
                        "import bpy, json\n"
                        f"print(json.dumps(bpy.data.objects.get({quoted_name}) is not None))"
                    )
                    _record(evidence, "Oracle deletion", exists is False, repr(exists))
    except Exception as exc:
        _record(evidence, "MCP transport", False, f"{type(exc).__name__}: {exc}")
    finally:
        try:
            removed = _cleanup_verification_objects()
            remaining = _oracle_json(
                "import bpy, json\n"
                "print(json.dumps([o.name for o in bpy.data.objects "
                "if o.name.startswith('verify_mcp_')]))"
            )
            _record(
                evidence, "Teardown", remaining == [], f"removed={removed}, remaining={remaining}"
            )
        except Exception as exc:
            _record(evidence, "Teardown", False, f"{type(exc).__name__}: {exc}")

    print("\n=== MCP REAL EVIDENCE ===")
    for item in evidence:
        print(f"{item.hypothesis:18} {'PASS' if item.passed else 'FAIL'}")
    passed = sum(item.passed for item in evidence)
    print(f"{passed}/{len(evidence)} passed; endpoint={endpoint}; nonce={nonce}")
    return 0 if evidence and all(item.passed for item in evidence) else 1


def main() -> None:
    raise SystemExit(asyncio.run(_verify()))


if __name__ == "__main__":
    main()
