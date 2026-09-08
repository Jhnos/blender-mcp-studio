"""The human-scale hand on the compact link. An entry point, nothing else.

Same generator as V3, a different registered instance under its own namespace,
so building this never clears the V3 hand. What makes it a different hand —
the 2 mm pin, the bearingless lug, the 15 mm body, the moment-arm gradient —
is entirely in `HAND_INSTANCES["hand-compact"]`.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.blender_generator_runner import run_generator  # noqa: E402
from scripts.hand_generator import build_hand  # noqa: E402


def build() -> None:
    build_hand("hand-compact", cleared_prefix="HK_")


def main() -> None:
    run_generator(build, prefix="HK_")


if __name__ == "__main__":
    main()
