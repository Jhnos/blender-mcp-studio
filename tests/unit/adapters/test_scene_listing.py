"""The scene list is the scene, not the addon's first ten objects.

The upstream addon's `get_scene_info` carries the comment "limit to first 10
objects" while reporting the true total, so the summary contradicted itself for
every real scene — 209 objects, ten of them named, and the Web UI showing the
ten. These tests pin the replacement and the one property that makes it an
improvement rather than a bigger version of the same defect: reaching the cap
is reported, not hidden.
"""

from __future__ import annotations

import json

import pytest

from src.adapters.scene_listing import SCENE_OBJECT_CAP, list_scene_objects, listing_code
from src.core.domain.exceptions import SceneOperationError


def _rows(count: int) -> str:
    return json.dumps([[f"obj_{index}", "MESH", [0.0, 1.0, 2.0]] for index in range(count)])


def _runner(payload: str):
    async def run(code: str) -> object:
        assert "bpy" in code
        return payload

    return run


@pytest.mark.asyncio
async def test_a_scene_larger_than_the_addons_cap_comes_back_whole() -> None:
    """209 is the real scene on the machine this was found on."""
    objects, truncated = await list_scene_objects(_runner(_rows(209)))

    assert len(objects) == 209
    assert not truncated
    assert objects[0].name == "obj_0"
    assert objects[-1].location == (0.0, 1.0, 2.0)


@pytest.mark.asyncio
async def test_reaching_the_cap_is_reported_not_hidden() -> None:
    """Should-fire on the defect being fixed. A silent cap of five hundred is
    the same defect as a silent cap of ten, one order of magnitude later."""
    objects, truncated = await list_scene_objects(_runner(_rows(12)), cap=10)

    assert len(objects) == 10
    assert truncated


@pytest.mark.asyncio
async def test_exactly_the_cap_is_not_truncated() -> None:
    objects, truncated = await list_scene_objects(_runner(_rows(10)), cap=10)

    assert len(objects) == 10
    assert not truncated


@pytest.mark.asyncio
async def test_a_malformed_row_is_refused_rather_than_dropped() -> None:
    """Dropping it would shorten the list without saying so — the same silence
    this whole module exists to remove."""
    payload = json.dumps([["only_a_name"]])

    with pytest.raises(SceneOperationError, match="malformed"):
        await list_scene_objects(_runner(payload))


@pytest.mark.asyncio
async def test_a_non_json_reply_is_refused() -> None:
    with pytest.raises(SceneOperationError, match="not JSON"):
        await list_scene_objects(_runner("Traceback (most recent call last):"))


def test_the_generated_code_reads_one_past_the_cap() -> None:
    """Truncation is observed from the rows themselves, not inferred from a
    count some other code path produced."""
    assert f"len(rows) > {SCENE_OBJECT_CAP}" in listing_code()
    assert "import bpy" in listing_code()
