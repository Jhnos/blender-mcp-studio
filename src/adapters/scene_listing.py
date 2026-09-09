"""The scene's object list, read without the addon's ten-object cap.

`get_scene_info` in the upstream addon carries the comment "limit to first 10
objects". Its `object_count` is the true total, so the summary it returns is
internally inconsistent for any real scene: 209 objects, ten of them named. The
Web UI shows that list, so a user working in a scene of any size sees the first
ten and nothing else.

ADR-001 keeps the addon as the execution boundary but allows the internal
adapter to use `execute_code` behind a curated operation — which is what this
is. The cap here is ours, far above any scene this studio has produced, and
reaching it is reported rather than hidden: replacing a silent cap of ten with
a silent cap of five hundred would fix the number and keep the defect.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from src.adapters.blender_scene_decoding import decode_vector
from src.core.domain.exceptions import SceneOperationError
from src.core.domain.scene_operations import SceneObjectSummary
from src.infrastructure.narrowing import as_nonempty_str, as_sequence, as_str

#: Above any scene this project has built; the largest observed is ~210 objects
#: with four hand instances and two octopus hands loaded at once.
SCENE_OBJECT_CAP = 500

#: Reads one past the cap so truncation is observed, not assumed from a count
#: that another code path produced.
_LIST_CODE = """\
import bpy, json
rows = []
for obj in bpy.context.scene.objects:
    if len(rows) > {cap}:
        break
    rows.append([obj.name, obj.type, [round(v, 6) for v in obj.location]])
print(json.dumps(rows))
"""


def listing_code(cap: int = SCENE_OBJECT_CAP) -> str:
    return _LIST_CODE.format(cap=cap)


async def list_scene_objects(
    run: Callable[[str], Awaitable[object]],
    cap: int = SCENE_OBJECT_CAP,
) -> tuple[tuple[SceneObjectSummary, ...], bool]:
    """Return the scene's objects and whether the cap cut the list short."""
    payload = as_str(await run(listing_code(cap)))
    if payload is None:
        raise SceneOperationError("the scene listing did not come back as text")
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SceneOperationError(f"the scene listing was not JSON: {exc}") from exc

    rows = as_sequence(decoded)
    if rows is None:
        raise SceneOperationError("the scene listing was not a list")

    truncated = len(rows) > cap
    objects: list[SceneObjectSummary] = []
    for row in rows[:cap]:
        fields = as_sequence(row)
        if fields is None or len(fields) != 3:
            raise SceneOperationError(f"a scene listing row is malformed: {row!r}")
        name = as_nonempty_str(fields[0])
        object_type = as_nonempty_str(fields[1])
        if name is None or object_type is None:
            raise SceneOperationError(f"a scene listing row is malformed: {row!r}")
        objects.append(
            SceneObjectSummary(
                name=name,
                object_type=object_type,
                # The same decoder the addon reply uses. A second copy here is
                # how the two paths end up disagreeing about what a location is.
                location=decode_vector(fields[2], f"{name} location"),
            )
        )
    return tuple(objects), truncated
