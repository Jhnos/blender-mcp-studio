"""V3 hand: the entry point, and nothing else.

The contracts, the shipped manifest and the package tests all name this file
and the `run_generator(build, prefix="HJ_")` line below, so the file stays.
Everything it used to do is now `scripts/hand_generator.py` reading a plan;
the prefix here is checked against the instance's namespace at build time, so
the two literals in this file cannot drift apart from the registry unnoticed.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.blender_generator_runner import run_generator  # noqa: E402
from scripts.hand_generator import build_hand  # noqa: E402


def build() -> None:
    build_hand("hand-v3", cleared_prefix="HJ_")


def main() -> None:
    # The prefix is not decoration: `run_generator` defaults to "HH_", which every
    # earlier generator uses. Left at the default, each run in a live Blender
    # stacked another whole hand on the last.
    run_generator(build, prefix="HJ_")


if __name__ == "__main__":
    main()
