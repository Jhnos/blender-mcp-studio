"""Verify a nominal cup's extraction against a catalog-resolved native assembly."""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify.native_session_verify_factory import (  # noqa: E402
    current_source,
    installed_blender,
    sha256,
)
from scripts.verify.workstation_cup_checks import (  # noqa: E402
    CAPILLARY,
    DISH,
    PARKED_ARMS_DEG,
    REFERENCE_CUP,
    SCREEN_STEPS,
    TRAY,
    assess,
    document,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", type=Path)
    parser.add_argument("--work", type=Path)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--spec", type=Path, help="candidate ModelSpec JSON")
    source.add_argument("--capture", nargs=2, type=Path, help=argparse.SUPPRESS)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    if args.capture:
        from scripts.verify.workstation_cup_capture import capture

        capture(
            *args.capture,
            screen_steps=SCREEN_STEPS,
            parked_arms=PARKED_ARMS_DEG,
            cup_name=REFERENCE_CUP,
            required_meshes={
                DISH,
                TRAY,
                CAPILLARY,
                REFERENCE_CUP,
                "LS_FIT_lcd_front",
                "LS_FIT_lcd_back",
            },
        )
        return 0
    blender = args.blender or installed_blender(
        Path.home() / "Library/LaunchAgents/com.blender-mcp.blender.plist"
    )
    work = (args.work or ROOT / "tmp" / f"workstation-cup-{uuid.uuid4().hex}").resolve()
    spec_bytes = args.spec.read_bytes() if args.spec is not None else None
    selection = document(json.loads(spec_bytes)) if spec_bytes is not None else None
    native, expected, model = asyncio.run(current_source(selection))
    native = ROOT / native
    work.mkdir(parents=True, exist_ok=False)
    if spec_bytes is not None:
        (work / "spec.json").write_bytes(spec_bytes)
    snapshot = work / "source.blend"
    shutil.copyfile(native, snapshot)
    if sha256(snapshot) != expected:
        raise ValueError("selected native changed during snapshot")
    captured = work / "capture.json"
    log = work / "blender.log"
    with log.open("w") as handle:
        done = subprocess.run(
            [
                str(blender),
                "--background",
                "--factory-startup",
                "--disable-autoexec",
                "--threads",
                "2",
                str(snapshot),
                "--python-exit-code",
                "1",
                "--python",
                str(Path(__file__).resolve()),
                "--",
                "--capture",
                str(snapshot),
                str(captured),
            ],
            cwd=ROOT,
            stdout=handle,
            stderr=subprocess.STDOUT,
            timeout=120,
            check=False,
        )
    if done.returncode:
        raise RuntimeError(f"Blender cup capture failed; see {log}")
    result = assess(document(json.loads(captured.read_bytes())), expected)
    if sha256(snapshot) != expected or sha256(native) != expected:
        raise ValueError("native source changed during verification")
    (work / "cup-extraction.json").write_text(
        json.dumps(
            {
                **result,
                "model": model,
                "capture_sha256": sha256(captured),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    print(work / "cup-extraction.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
