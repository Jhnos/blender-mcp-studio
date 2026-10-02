"""Renderer-neutral publishing contracts for actors, feedback and items."""

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


EFFECT_KINDS = ("pickup", "unlock", "complete", "footsteps", "teleport", "blocked")
ITEM_KINDS = ("key", "letter", "potion", "purse", "tool", "parcel")


def feedback_catalog() -> dict[str, Any]:
    """Publishing geometry; gameplay decides when a one-shot is emitted."""
    return {
        "schema_version": 1,
        "effects": [
            {
                "id": kind,
                "atlas": kind + "-atlas",
                "frame_size": [128, 128],
                "atlas_size": [1024, 128],
                "frames": list(range(8)),
                "fps": 12,
                "duration_ms": 8 * 1000 / 12,
                "loop": False,
                "blend": "NORMAL",
                "scale": 1.0,
                "origin": [0.5, 0.5],
                "reduced_frame": 4,
            }
            for kind in EFFECT_KINDS
        ],
        "items": [
            {
                "id": kind,
                "ground": {"image": kind + "-ground", "size": [128, 192], "anchor": [0.5, 0.75]},
                "inventory": {"image": kind + "-inventory", "size": [64, 64], "anchor": [0.5, 0.5]},
            }
            for kind in ITEM_KINDS
        ],
    }


def validate_feedback_catalog(catalog: dict[str, Any]) -> None:
    """Reject incomplete batches and unsafe playback metadata before rendering/publishing."""
    import math

    def asset_name(value: Any) -> bool:
        return isinstance(value, str) and bool(re.fullmatch(r"[a-z0-9-]+", value))

    try:
        if type(catalog["schema_version"]) is not int or catalog["schema_version"] != 1:
            raise ValueError("unsupported feedback schema")
        for key, expected in (("effects", EFFECT_KINDS), ("items", ITEM_KINDS)):
            entries = catalog[key]
            if len(entries) != len(expected) or {x["id"] for x in entries} != set(expected):
                raise ValueError("feedback batch coverage mismatch")
        for effect in catalog["effects"]:
            if (
                not asset_name(effect["atlas"])
                or effect["frame_size"] != [128, 128]
                or effect["atlas_size"] != [1024, 128]
                or effect["frames"] != list(range(8))
                or any(type(frame) is not int for frame in effect["frames"])
            ):
                raise ValueError("invalid effect frame geometry")
            fps, duration, scale = effect["fps"], effect["duration_ms"], effect["scale"]
            if (
                any(
                    isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
                    for x in (fps, duration, scale)
                )
                or fps != 12
                or not math.isclose(duration, 8000 / fps)
                or not 0 < scale <= 1
                or effect["loop"] is not False
            ):
                raise ValueError("invalid one-shot timing or scale")
            if (
                effect["origin"] != [0.5, 0.5]
                or effect["blend"] != "NORMAL"
                or type(effect["reduced_frame"]) is not int
                or effect["reduced_frame"] not in effect["frames"]
            ):
                raise ValueError("invalid effect presentation")
        for item in catalog["items"]:
            for key, size, anchor in (
                ("ground", [128, 192], [0.5, 0.75]),
                ("inventory", [64, 64], [0.5, 0.5]),
            ):
                image = item[key]
                if (
                    not asset_name(image["image"])
                    or image["size"] != size
                    or image["anchor"] != anchor
                ):
                    raise ValueError("invalid item image geometry")
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("malformed feedback catalog") from error
