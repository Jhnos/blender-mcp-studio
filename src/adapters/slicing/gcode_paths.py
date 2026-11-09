"""Stream the declared Bambu deposition dialect into framework-free path geometry.

Machine custom G-code updates modal state but is not a model footprint. Unknown geometry,
unknown absolute positions, missing bead metadata and unsupported arc planes fail closed.
No repair, guessed bead width, printer connection or material/adhesion inference occurs here.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from math import isfinite

from src.core.domain.extrusion import ExtrusionPath

_COMMAND = re.compile(r"^([GM])([0-9]+(?:\.[0-9]+)?)(?=\s|[A-Z]|$)", re.I)
_WORD = re.compile(r"([A-Z])\s*([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))", re.I)
_UNSUPPORTED_GEOMETRY = frozenset(
    {
        "G5",
        "G6",
        "G10",
        "G11",
        "G51",
        "G52",
        "G53",
        "G54",
        "G55",
        "G56",
        "G57",
        "G58",
        "G59",
        "G68",
        "G69",
    }
)


def _words(text: str) -> dict[str, float]:
    values: dict[str, float] = {}
    cursor = 0
    for match in _WORD.finditer(text):
        if text[cursor : match.start()].strip():
            raise ValueError("unsupported numeric words")
        key, number = match.group(1).upper(), float(match.group(2))
        if key in values or not isfinite(number):
            raise ValueError("duplicate or non-finite numeric words")
        values[key] = number
        cursor = match.end()
    if text[cursor:].strip():
        raise ValueError("unsupported numeric words")
    return values


def _metadata_number(value: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError("invalid numeric deposition metadata") from exc


@dataclass(slots=True)
class _State:
    position: list[float | None] = field(default_factory=lambda: [None, None, None])
    origin: list[float | None] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    e: float | None = None
    xyz_absolute: bool = True
    e_absolute: bool = True
    xy_plane: bool = True
    relative_center: bool = True
    role: str | None = None
    width: float | None = None
    height: float | None = None
    layer: int = -1
    object_id: int | None = None

    def annotation(self, text: str) -> None:
        text = text.strip()
        if text == "CHANGE_LAYER":
            self.layer += 1
        elif text.startswith("FEATURE:"):
            self.role = text.split(":", 1)[1].strip()
        elif text.startswith("OBJECT_ID:"):
            value = text.split(":", 1)[1].strip()
            if re.fullmatch(r"(?:-1|[0-9]{1,20})", value) is None:
                raise ValueError("object label must be a bounded integer")
            label = int(value)
            if not -1 <= label < 2**64:
                raise ValueError("object label outside the supported range")
            self.object_id = label if label >= 0 else None
        elif text.startswith("LINE_WIDTH:"):
            self.width = _metadata_number(text.split(":", 1)[1])
        elif text.startswith("LAYER_HEIGHT:"):
            self.height = _metadata_number(text.split(":", 1)[1])

    @property
    def model(self) -> bool:
        return self.role is not None and self.role != "Custom"

    def reset_origin(self, values: dict[str, float]) -> None:
        if not values:
            raise ValueError("origin reset requires explicit coordinates")
        for axis, key in enumerate("XYZ"):
            if key in values:
                position = self.position[axis]
                self.origin[axis] = position - values[key] if position is not None else None
        if "E" in values:
            self.e = values["E"]

    def motion(self, command: str, values: dict[str, float]) -> ExtrusionPath | None:
        if set(values) - set("XYZEFIJRP"):
            raise ValueError("unsupported motion words or multiple commands in one block")
        if "P" in values and command not in ("G2", "G3"):
            raise ValueError("unsupported motion parameter")
        start = tuple(self.position)
        for axis, key in enumerate("XYZ"):
            if key not in values:
                continue
            reference = self.origin[axis] if self.xyz_absolute else self.position[axis]
            self.position[axis] = values[key] + reference if reference is not None else None
        e_relative = not self.xyz_absolute or not self.e_absolute
        delta_e: float | None = 0.0
        if "E" in values:
            delta_e = (
                values["E"]
                if e_relative
                else (values["E"] - self.e if self.e is not None else None)
            )
            self.e = (
                (self.e + values["E"] if self.e is not None else None)
                if e_relative
                else values["E"]
            )
        moved = start != tuple(self.position) or command in ("G2", "G3")
        if not self.model or not moved or "E" not in values:
            return None
        if delta_e is None:
            raise ValueError("absolute extrusion requires a known previous counter")
        if delta_e <= 0:
            return None
        if any(v is None for v in (*start, *self.position)):
            raise ValueError("deposition requires known physical XYZ endpoints")
        if self.width is None or self.height is None or self.role is None:
            raise ValueError("deposition requires explicit width, height and feature metadata")
        # None has been rejected; constructing exact triples keeps narrowing local.
        sx, sy, sz = start
        ex, ey, ez = self.position
        assert sx is not None and sy is not None and sz is not None
        assert ex is not None and ey is not None and ez is not None
        center = None
        if command in ("G2", "G3"):
            if (
                not self.xy_plane
                or not self.relative_center
                or "R" in values
                or "P" in values
                or not ({"I", "J"} & values.keys())
            ):
                raise ValueError("only XY arcs with relative I/J centers are supported")
            center = (sx + values.get("I", 0.0), sy + values.get("J", 0.0))
        return ExtrusionPath(
            (sx, sy, sz),
            (ex, ey, ez),
            self.width,
            self.height,
            self.role,
            self.layer,
            center,
            command == "G2",
            object_id=self.object_id,
        )

    def command(self, command: str, rest: str) -> ExtrusionPath | None:
        if command == "G20" or command in _UNSUPPORTED_GEOMETRY:
            raise ValueError("unsupported units or coordinate geometry")
        if command in ("G90", "G91"):
            self.xyz_absolute = command == "G90"
        elif command in ("M82", "M83"):
            self.e_absolute = command == "M82"
        elif command in ("G17", "G18", "G19"):
            self.xy_plane = command == "G17"
        elif command in ("G90.1", "G91.1"):
            self.relative_center = command == "G91.1"
        elif command == "G28":
            axes = {key for key in "XYZ" if key in rest.upper()} or set("XYZ")
            for axis, key in enumerate("XYZ"):
                if key in axes:
                    self.position[axis], self.origin[axis] = None, 0.0
        elif command == "G92":
            self.reset_origin(_words(rest))
        elif command in ("G0", "G1", "G2", "G3"):
            return self.motion(command, _words(rest))
        elif command.startswith("G") and command not in ("G4", "G21"):
            if self.model:
                raise ValueError("unsupported print coordinate command")
            # An opaque machine operation cannot establish a known model start position.
            self.position = [None, None, None]
        return None


def iter_extrusions(lines: Iterable[str]) -> Iterator[ExtrusionPath]:
    """Consume once, retain only modal state, and yield positive model deposition moves."""
    state = _State()
    for number, raw in enumerate(lines, 1):
        try:
            code, _, comment = raw.partition(";")
            if not code.strip():
                state.annotation(comment)
                continue
            code = code.strip()
            match = _COMMAND.match(code)
            if match is None:
                if state.model and not re.fullmatch(r"T[0-9]+", code):
                    raise ValueError("unsupported print command text")
                continue
            command = match.group(1).upper() + format(float(match.group(2)), "g")
            path = state.command(command, code[match.end() :])
            if path is not None:
                yield path
        except (ValueError, OverflowError) as exc:
            raise ValueError(f"G-code line {number}: {exc}") from exc
