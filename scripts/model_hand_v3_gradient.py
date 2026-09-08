"""The gradient fixture: V3's link, two part numbers. An entry point, nothing else.

Same generator as V3, a different registered instance under its own namespace,
so building this never clears the V3 hand and the two contracts can run in one
resident Blender. See `HAND_INSTANCES["hand-v3-gradient"]` for what it is for.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.blender_generator_runner import run_generator  # noqa: E402
from scripts.hand_generator import build_hand  # noqa: E402


def build() -> None:
    build_hand("hand-v3-gradient", cleared_prefix="HG_")


def main() -> None:
    run_generator(build, prefix="HG_")


if __name__ == "__main__":
    main()
