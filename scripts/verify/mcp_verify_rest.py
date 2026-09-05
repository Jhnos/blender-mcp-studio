#!/usr/bin/env python3
"""MCP↔Blender pipeline verification via the FRONTEND REST path (LLM-independent).

Proves the api → socket 9876 → real bpy pipeline is genuine, using an
independent oracle (direct socket execute_code). Does NOT exercise the LLM
chat-authoring path (blocked on model config) — that is declared separately.

- Interact: Tailscale REST (硬規則 #1).
- Oracle:   direct socket 9876 execute_code print() (bypasses api).
- Seed:     oracle creates the test object (no LLM needed).
"""

import json
import random
import socket
import ssl
import sys
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.infrastructure.narrowing import as_str, as_str_keyed_exact, dig  # noqa: E402

TS = "bearmacminimac-mini.tail56c751.ts.net"
BASE = f"https://{TS}/blender"


def oracle(code: str, timeout: float = 10) -> dict[str, object] | None:
    s = socket.create_connection(("127.0.0.1", 9876), timeout=timeout)
    s.settimeout(timeout)
    s.sendall(json.dumps({"type": "execute_code", "params": {"code": code}}).encode())
    buf = b""
    while True:
        try:
            c = s.recv(65536)
        except TimeoutError:
            break
        if not c:
            break
        buf += c
        try:
            decoded = as_str_keyed_exact(json.loads(buf.decode()))
            s.close()
            return decoded
        except json.JSONDecodeError:
            continue
    s.close()
    return as_str_keyed_exact(json.loads(buf.decode())) if buf else None


def o_out(code: str) -> str:
    r = oracle(code)
    output = as_str(dig(r, "result", "result")) if r else None
    if output is None or r is None or r.get("status") != "success":
        return f"<err:{json.dumps(r)[:150]}>"
    return output.strip()


def o_names() -> list[str]:
    raw = json.loads(
        o_out("import bpy,json\nprint(json.dumps([o.name for o in bpy.data.objects]))")
    )
    return [name for name in raw if isinstance(name, str)]


def rest(method: str, path: str, body: dict[str, object] | None = None) -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as r:
        raw = r.read()
        try:
            return r.status, json.loads(raw)
        except Exception:
            return r.status, raw


def teardown() -> None:
    o_out(
        "import bpy\nd=[o for o in bpy.data.objects if o.name.startswith('verify_')]\n"
        "[bpy.data.objects.remove(o,do_unlink=True) for o in d]\nprint('removed',len(d))"
    )


def main() -> None:
    R: list[tuple[str, bool, object]] = []

    def rec(h: str, ok: bool, d: object) -> None:
        R.append((h, ok, d))
        print(f"[{'PASS' if ok else 'FAIL'}] {h}: {d}")

    teardown()
    base = o_names()
    base_n = len(base)
    print(f"baseline oracle: {base_n} {base}\n")

    n = f"verify_{random.randint(10000, 99999)}"
    # SEED via oracle (not LLM): create a real cube named n
    o_out(
        f"import bpy\nbpy.ops.mesh.primitive_cube_add()\nbpy.context.active_object.name='{n}'\nprint('seeded')"
    )
    after = o_names()

    rec("SEED", n in after, f"oracle created {n}; objects now {len(after)} {after}")
    rec("H4-create", len(after) == base_n + 1, f"count {base_n}->{len(after)} (+1)")
    verts = o_out(f"import bpy\nprint(len(bpy.data.objects['{n}'].data.vertices))")
    rec(
        "H2-geometry",
        verts == "8",
        f"{n} real vertex count = {verts} (cube=8; only real bpy yields this)",
    )

    # H6: frontend REST /api/scene reflects real Blender (independent read path)
    st, scene = rest("GET", "/api/scene")
    scene_body = as_str_keyed_exact(scene) or {}
    objects = scene_body.get("objects")
    fe = [
        name
        for item in (objects if isinstance(objects, list) else [])  # narrow-ok: names re-checked
        for name in [as_str((as_str_keyed_exact(item) or {}).get("name"))]
        if name is not None
    ]
    rec("H6-frontend-reflects", n in fe, f"Tailscale /api/scene names={fe}; has {n}? {n in fe}")

    # H-rename: frontend REST mutation -> oracle confirms
    n2 = n + "_r"
    st, _ = rest("PUT", f"/api/object/{n}", {"new_name": n2})
    time.sleep(0.8)
    names = o_names()
    rec(
        "H-rename", (n2 in names and n not in names), f"REST rename {n}->{n2}; oracle names={names}"
    )

    # H7: frontend REST delete -> oracle confirms gone
    st, _ = rest("DELETE", f"/api/object/{n2}")
    time.sleep(0.8)
    gone = n2 not in o_names()
    rec("H7-delete", gone, f"REST delete {n2}; oracle gone? {gone}")
    rec(
        "H4-delete",
        len(o_names()) == base_n,
        f"count back to baseline {base_n}? now {len(o_names())}",
    )

    teardown()
    print(f"\nfinal oracle: {o_names()}")
    print("\n=== EVIDENCE MATRIX ===")
    for h, ok, _detail in R:
        print(f"  {h:22} {'PASS' if ok else 'FAIL'}")
    print(f"\n{sum(1 for _, ok, _ in R if ok)}/{len(R)} passed")


if __name__ == "__main__":
    main()
