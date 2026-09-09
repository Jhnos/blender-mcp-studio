"""Versioned, renderer-neutral contract for the first editable actor delivery."""

from __future__ import annotations

import re
from typing import Any, TypedDict

DIRECTIONS = ("down", "left", "right", "up")
CLIPS = {"idle": (2, 2), "walk": (6, 8), "interact": (4, 8)}
MARKER_KINDS = ("talk", "quest", "deliver", "investigate", "locked", "exit")


class RoleStyle(TypedDict):
    label: str
    coat: tuple[float, float, float, float]
    skin: tuple[float, float, float, float]


ROLES: dict[str, RoleStyle] = {
    "traveler": {"label": "旅人", "coat": (0.035, 0.27, 0.30, 1), "skin": (0.64, 0.37, 0.21, 1)},
    "guide": {"label": "嚮導", "coat": (0.46, 0.14, 0.045, 1), "skin": (0.80, 0.59, 0.38, 1)},
    "guard": {"label": "守衛", "coat": (0.12, 0.20, 0.40, 1), "skin": (0.48, 0.25, 0.14, 1)},
    "artisan": {"label": "工匠", "coat": (0.32, 0.09, 0.34, 1), "skin": (0.72, 0.45, 0.28, 1)},
}


def actor_spec(asset_id: str, label: str) -> dict[str, Any]:
    clips = {}
    for direction_index, direction in enumerate(DIRECTIONS):
        offset = direction_index * 12
        for name, (count, fps) in CLIPS.items():
            clips[name + "-" + direction] = {
                "frames": list(range(offset, offset + count)),
                "fps": fps,
                "loop": name == "idle",
            }
            offset += count
    return {
        "id": asset_id,
        "label": label,
        "atlas": asset_id + "-atlas",
        "portrait": asset_id + "-portrait",
        "frame_size": [128, 192],
        "atlas_size": [1536, 768],
        "anchor": [0.5, 0.75],
        "clips": clips,
    }


def validate_actor(spec: dict[str, Any]) -> None:
    if not re.fullmatch(r"[a-z0-9-]+", str(spec.get("atlas", ""))):
        raise ValueError("invalid atlas")
    if spec.get("frame_size") != [128, 192] or spec.get("anchor") != [0.5, 0.75]:
        raise ValueError("invalid frame geometry")
    expected = {f"{clip}-{direction}" for direction in DIRECTIONS for clip in CLIPS}
    clips = spec.get("clips", {})
    if set(clips) != expected:
        raise ValueError("missing direction or clip")
    frames = []
    for key, clip in clips.items():
        if len(clip["frames"]) != CLIPS[key.split("-")[0]][0] or not 0 < clip["fps"] <= 24:
            raise ValueError("invalid clip timing")
        frames.extend(clip["frames"])
    if sorted(frames) != list(range(48)):
        raise ValueError("frame coverage mismatch")
