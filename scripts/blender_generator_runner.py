"""Shared entry-point wrapper for the local mechanical generators.

Every generator does the same three things around its own `build()`: remove what
a previous run left behind, hide everything it did not create so renders and
exports see only the new geometry, and put the scene's visibility back exactly as
it was — even when the build raises.

That wrapper was copied into each generator. Two of the copies were byte
identical; the third differed only in having factored out its own prefix filter.
"""

from __future__ import annotations

from collections.abc import Callable

import bpy

#: Every generator in this repo namespaces its output with this prefix.
DEFAULT_PREFIX = "HH_"


def clear_previous(prefix: str = DEFAULT_PREFIX) -> None:
    """Remove objects and collections left by an earlier run of this generator."""
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefix):
            bpy.data.objects.remove(obj, do_unlink=True)
    for group in list(bpy.data.collections):
        if group.name.startswith(prefix):
            bpy.data.collections.remove(group)


def run_generator(build: Callable[[], None], prefix: str = DEFAULT_PREFIX) -> None:
    """Clear prior output, hide unrelated objects, build, then restore visibility.

    The prefix filter on the visibility snapshot is deliberate. Two of the three
    copies omitted it and relied on `clear_previous` having already deleted
    everything under the prefix — true on the happy path, but it left them with
    nothing to fall back on if a delete had failed. Filtering costs nothing and
    covers that case.

    Restoration happens in `finally`: a generator that raises half-way must not
    leave the operator's scene with everything hidden.
    """
    clear_previous(prefix)
    external = [
        (obj, obj.hide_render, obj.hide_viewport)
        for obj in bpy.context.scene.objects
        if not obj.name.startswith(prefix)
    ]
    try:
        for obj, _, _ in external:
            obj.hide_render = True
            obj.hide_viewport = True
        build()
    finally:
        for obj, hide_render, hide_viewport in external:
            obj.hide_render = hide_render
            obj.hide_viewport = hide_viewport
