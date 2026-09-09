"""The three-station gripper: two fingers and a thumb. An entry point, nothing else.

Same generator as V3 and the compact hand, a different registered instance under
its own namespace, so building this never clears either of them. What makes it a
different hand — a two-finger row instead of four — is entirely in
`HAND_INSTANCES["hand-gripper"]`.

`row_finger_count` is the field this instance exists to exercise. Its own comment
in `AnthropomorphicPalmSpec` records that the count used to be typed in four
places and agreed by luck; until now it had only ever been built at 4.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.blender_generator_runner import run_generator  # noqa: E402
from scripts.hand_generator import build_hand  # noqa: E402


def build() -> None:
    build_hand("hand-gripper", cleared_prefix="HR_")


def main() -> None:
    run_generator(build, prefix="HR_")


if __name__ == "__main__":
    main()
