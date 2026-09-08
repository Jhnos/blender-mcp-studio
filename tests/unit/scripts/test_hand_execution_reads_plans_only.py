"""ES-5: the execution layer does no arithmetic and names nothing itself.

Every size and every name in `scripts/hand_*.py` has to come from a plan. The
scan is by reading, because those modules import `bpy` at the top. Two things
are forbidden: a float literal outside the unit conversions, and a string
literal that looks like an object name (an upper-case prefix ending in an
underscore). A literal that slips in is exactly the drift this layer exists
to make impossible — the 6.6 that broke the compact link was one.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
SCRIPTS = PROJECT_ROOT / "scripts"

#: The only floats an executor may write: nothing, one, and millimetres to metres.
ALLOWED_FLOATS = {0.0, 1.0, 0.001}
_NAME_LIKE = re.compile(r"^[A-Z][A-Z0-9]*_[A-Z0-9_]*$")


def literal_offences(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offences: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        value = node.value
        if isinstance(value, float) and value not in ALLOWED_FLOATS:
            offences.append(f"{path.name}:{node.lineno} float {value!r}")
        elif isinstance(value, str) and _NAME_LIKE.match(value) and len(value) > 2:
            offences.append(f"{path.name}:{node.lineno} name-like {value!r}")
    return offences


def test_the_scan_fires_on_a_planted_size_and_a_planted_name(tmp_path: Path) -> None:
    dirty = tmp_path / "hand_dirty.py"
    dirty.write_text('x = 6.6\nname = "HJ_V3_PALM"\nok = 0.001\nmode = "UNION"\naxis = "X"\n')

    assert literal_offences(dirty) == [
        "hand_dirty.py:1 float 6.6",
        "hand_dirty.py:2 name-like 'HJ_V3_PALM'",
    ]


def test_bpy_modules_read_plans_only() -> None:
    executors = sorted(SCRIPTS.glob("hand_*.py"))
    assert executors, "no execution modules under scripts/hand_*.py — the scan is vacuous"
    offences = [line for path in executors for line in literal_offences(path)]
    assert offences == []
