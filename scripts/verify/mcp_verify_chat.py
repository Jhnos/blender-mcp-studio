#!/usr/bin/env python3
"""MCP→Blender 鑑別性驗證 harness (H0/H2/H4/H6/H7).

- Interact: 真使用者網路路徑 = Tailscale URL (硬規則 #1) 的 WS chat + REST.
- Oracle:   獨立 ground-truth = 直連 socket 9876 execute_code print() (繞過 api).
每輪 nonce 隔離 (verify_ 前綴) + teardown.
"""

import json
import random
import socket
import ssl
import time
import urllib.request

from src.infrastructure.narrowing import (
    as_sequence,
    as_str,
    as_str_keyed_exact,
    dig,
)

TS = "bearmacminimac-mini.tail56c751.ts.net"
BASE = f"https://{TS}/blender"
WS_URL = f"wss://{TS}/blender/ws/chat"
ORACLE = ("127.0.0.1", 9876)


def oracle(code: str, timeout: float = 10) -> dict[str, object] | None:
    s = socket.create_connection(ORACLE, timeout=timeout)
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


def o_stdout(code: str) -> str:
    r = oracle(code)
    output = as_str(dig(r, "result", "result")) if r else None
    if r is not None and output is not None and r.get("status") == "success":
        return output.strip()
    return f"<oracle-error: {json.dumps(r)[:200]}>"


def o_names() -> list[str]:
    raw = json.loads(
        o_stdout("import bpy,json\nprint(json.dumps([o.name for o in bpy.data.objects]))")
    )
    return [name for name in raw if isinstance(name, str)]


def o_count() -> int:
    return int(o_stdout("import bpy\nprint(len(bpy.data.objects))"))


def rest(method: str, path: str, body: dict[str, object] | None = None) -> tuple[int, object]:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"} if data else {}
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
        ct = resp.headers.get("Content-Type", "")
        raw = resp.read()
        return (resp.status, json.loads(raw) if "json" in ct else raw)


def ws_chat(text: str, timeout: float = 90) -> tuple[str, str | None, str | None]:
    """Drive the real WS chat path; return (final_content, blender_output, session_id)."""
    import websocket  # websocket-client

    ws = websocket.create_connection(WS_URL, timeout=timeout, sslopt={"cert_reqs": ssl.CERT_NONE})
    ws.send(json.dumps({"type": "chat", "content": text, "session_id": None}))
    final, bout, sid = "", None, None
    t0 = time.time()
    try:
        while time.time() - t0 < timeout:
            msg = json.loads(ws.recv())
            if msg.get("session_id"):
                sid = msg["session_id"]
            st = msg.get("status")
            if st == "streaming":
                continue
            if st in ("done", "error"):
                final = msg.get("content", "")
                bout = msg.get("blender_output")
                break
    finally:
        ws.close()
    return final, bout, sid


def teardown() -> None:
    o_stdout(
        "import bpy\n"
        "d=[o for o in bpy.data.objects if o.name.startswith('verify_')]\n"
        "[bpy.data.objects.remove(o, do_unlink=True) for o in d]\n"
        "print('removed', len(d))"
    )


def main() -> None:
    results: list[tuple[str, bool, object]] = []

    def rec(hid: str, ok: bool, detail: object) -> None:
        results.append((hid, ok, detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {hid}: {detail}")

    print("=== PRECHECK ===")
    base_names = o_names()
    base_n = len(base_names)
    print(f"baseline oracle: {base_n} objects {base_names}")
    teardown()  # clean any residue first

    nonce = f"verify_{random.randint(10000, 99999)}"
    print(f"\n=== H0: chat NL -> real Blender mutation (nonce={nonce}) ===")
    cmd = f"用 Blender Python 建立一個名為 {nonce} 的立方體（cube）"
    print(f"sending via Tailscale WS: {cmd!r}")
    try:
        content, bout, _sid = ws_chat(cmd)
        print(f"  reply: {content[:160]!r}")
        print(f"  blender_output: {str(bout)[:160]!r}")
    except Exception as e:
        rec("H0", False, f"WS chat failed: {e}")
        content, bout = "", None

    time.sleep(1.5)
    after_names = o_names()
    exists = nonce in after_names
    rec(
        "H0", exists, f"oracle sees {nonce}? {exists}. objects now={len(after_names)} {after_names}"
    )

    if exists:
        print("\n=== H4: differential count ===")
        rec(
            "H4",
            len(after_names) == base_n + 1,
            f"baseline {base_n} -> after create {len(after_names)} (expect +1)",
        )

        print(f"\n=== H2: real geometry read-back ({nonce}) ===")
        verts = o_stdout(f"import bpy\nprint(len(bpy.data.objects['{nonce}'].data.vertices))")
        rec("H2", verts == "8", f"{nonce} vertex count = {verts} (a real cube has 8)")

        print("\n=== H6: frontend /api/scene reflects real state ===")
        try:
            st, scene = rest("GET", "/api/scene")
            scene_body = as_str_keyed_exact(scene) or {}
            scene_objects = scene_body.get("objects")
            fe_names = [
                name
                for item in (as_sequence(scene_objects) or [])
                for name in [as_str((as_str_keyed_exact(item) or {}).get("name"))]
                if name is not None
            ]
            rec(
                "H6",
                nonce in fe_names,
                f"frontend /api/scene names={fe_names}; contains {nonce}? {nonce in fe_names}",
            )
        except Exception as e:
            rec("H6", False, f"/api/scene failed: {e}")

        print("\n=== H7: delete via frontend REST -> oracle confirms gone ===")
        try:
            st, _ = rest("DELETE", f"/api/object/{nonce}")
            time.sleep(1.0)
            gone = nonce not in o_names()
            rec("H7", gone, f"after REST delete, oracle sees {nonce}? {not gone} (expect gone)")
        except Exception as e:
            rec("H7", False, f"delete failed: {e}")

    print("\n=== TEARDOWN ===")
    teardown()
    print(f"final oracle: {o_names()}")

    print("\n=== EVIDENCE MATRIX ===")
    for hid, ok, detail in results:
        print(f"  {hid:4} {'PASS' if ok else 'FAIL'}  {detail}")
    npass = sum(1 for _, ok, _ in results if ok)
    print(f"\n{npass}/{len(results)} assertions passed")


if __name__ == "__main__":
    main()
