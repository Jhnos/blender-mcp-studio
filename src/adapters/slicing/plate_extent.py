"""Placed XY extent of a 3MF plate, and a machine profile's printable area (stdlib only).

The slicers run with ``--arrange 0``, so a plate laid out for a larger bed is refused by the
slicer itself (OrcaSlicer 2.4.2 exits -52 with one log line). This module lets the adapter say
why before any slicer starts. The extent is every mesh vertex of every build item, through the
item's transform and any ``components`` transforms, so it is exact for rotated parts too.
Only the root model part (``3D/3dmodel.model``) is read; a component that points at another
part (``p:path``, production extension) cannot be measured here and raises ``PlateExtentError``.

Hardening (the input can come from a remote MCP caller; stdlib only, no new dependency):
the model part is read once with a bounded read of at most ``MAX_MODEL_BYTES`` + 1 (and its
declared size is checked first), so a zip bomb cannot inflate past the cap; any ``<!DOCTYPE``
or ``<!ENTITY`` anywhere in it, any case, is refused before parsing, so ``ElementTree`` never
sees a DTD and cannot expand entities (a 3MF core model has no use for one).
``MAX_MODEL_BYTES`` is 5 x the measured uncompressed v78 ``3D/3dmodel.model``: 8168153 B
(1402754 B compressed) in ``雙上臂四點梯形-v78/整機69件-單盤排版-v78.3mf``, 69 parts, measured
with ``zipfile.ZipInfo.file_size`` on 2026-10-22, giving 40840765 B.
"""

from __future__ import annotations

import re
import zipfile
from collections.abc import Iterator, Mapping
from pathlib import Path
from xml.etree import ElementTree

from src.core.domain.exceptions import DomainError
from src.infrastructure.narrowing import as_sequence

_CORE = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"
_MODEL = "3D/3dmodel.model"
#: 5 x the measured uncompressed v78 ``3D/3dmodel.model`` (8168153 B, 69 parts, 2026-10-22).
MAX_MODEL_BYTES = 5 * 8168153
_DTD = re.compile(rb"<!\s*(doctype|entity)", re.IGNORECASE)
_IDENTITY = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)

Matrix = tuple[float, ...]
Extent = tuple[float, float, float, float]  # min x, min y, max x, max y (mm)


class PlateExtentError(DomainError):
    """The 3MF's placed extent cannot be measured; the message names the file, not its path."""


def _matrix(text: str | None) -> Matrix:
    if not text:
        return _IDENTITY
    values = tuple(float(part) for part in text.split())
    if len(values) != 12:
        raise ValueError(f"transform has {len(values)} values, expected 12")
    return values


def _compose(inner: Matrix, outer: Matrix) -> Matrix:
    """``inner`` then ``outer`` (3MF row-vector convention: p' = p * M)."""
    a, b = inner, outer
    rows = [
        tuple(sum(a[r * 3 + k] * b[k * 3 + c] for k in range(3)) for c in range(3))
        for r in range(3)
    ]
    shift = tuple(sum(a[9 + k] * b[k * 3 + c] for k in range(3)) + b[9 + c] for c in range(3))
    return (*rows[0], *rows[1], *rows[2], *shift)


class _Model:
    def __init__(self, root: ElementTree.Element) -> None:
        self._objects = {
            obj.get("id"): obj for obj in root.iter(f"{_CORE}object") if obj.get("id") is not None
        }
        self.items = [
            (item.get("objectid"), _matrix(item.get("transform")))
            for item in root.iter(f"{_CORE}item")
        ]

    def points(
        self, object_id: str | None, m: Matrix, depth: int = 0
    ) -> Iterator[tuple[float, float]]:
        obj = self._objects.get(object_id)
        if obj is None or depth > 16:
            raise ValueError(f"build references unknown or cyclic object {object_id!r}")
        for vertex in obj.iter(f"{_CORE}vertex"):
            x, y, z = (float(vertex.get(axis, "0")) for axis in ("x", "y", "z"))
            yield (
                x * m[0] + y * m[3] + z * m[6] + m[9],
                x * m[1] + y * m[4] + z * m[7] + m[10],
            )
        for component in obj.iter(f"{_CORE}component"):
            if any(key.endswith("}path") for key in component.attrib):
                raise ValueError("component in another model part (production extension)")
            inner = _matrix(component.get("transform"))
            yield from self.points(component.get("objectid"), _compose(inner, m), depth + 1)


def _model_bytes(path: Path, cap: int) -> bytes:
    """The root model part, read once and bounded; refuses oversize and any DTD."""
    with zipfile.ZipFile(path) as archive:
        if archive.getinfo(_MODEL).file_size > cap:
            raise PlateExtentError(f"{path.name}: {_MODEL} exceeds {cap} B uncompressed")
        with archive.open(_MODEL) as member:
            data = member.read(cap + 1)  # a false declared size cannot exceed the cap either
    if len(data) > cap:
        raise PlateExtentError(f"{path.name}: {_MODEL} exceeds {cap} B uncompressed")
    if _DTD.search(data):
        raise PlateExtentError(f"{path.name}: {_MODEL} declares a DTD (DOCTYPE/ENTITY); refused")
    return data


def plate_extent(path: Path, *, max_model_bytes: int = MAX_MODEL_BYTES) -> Extent:
    """XY bounding box of every placed vertex, in millimetres."""
    try:
        root = ElementTree.fromstring(_model_bytes(path, max_model_bytes))
        model = _Model(root)
        xs: list[float] = []
        ys: list[float] = []
        for object_id, matrix in model.items:
            for x, y in model.points(object_id, matrix):
                xs.append(x)
                ys.append(y)
    except OSError as exc:  # str(OSError) carries the absolute path; strerror does not
        raise PlateExtentError(
            f"cannot measure the layout of {path.name}: {exc.strerror or type(exc).__name__}"
        ) from exc
    except (KeyError, ValueError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise PlateExtentError(f"cannot measure the layout of {path.name}: {exc}") from exc
    if not xs:
        raise PlateExtentError(f"cannot measure the layout of {path.name}: no placed vertices")
    return min(xs), min(ys), max(xs), max(ys)


def printable_area(machine: Mapping[str, object]) -> Extent | None:
    """Bounding box of a flattened machine profile's ``printable_area`` ("XxY" points)."""
    raw = as_sequence(machine.get("printable_area"))
    if not raw:
        return None
    try:
        points = [tuple(float(v) for v in str(point).split("x")) for point in raw]
    except ValueError:
        return None
    if any(len(point) != 2 for point in points):
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def fits(layout: Extent, bed: Extent, tolerance_mm: float = 0.01) -> bool:
    return (
        layout[0] >= bed[0] - tolerance_mm
        and layout[1] >= bed[1] - tolerance_mm
        and layout[2] <= bed[2] + tolerance_mm
        and layout[3] <= bed[3] + tolerance_mm
    )


def plate_fit(
    input_3mf: Path, machine: Mapping[str, object], printer_id: str
) -> tuple[str | None, tuple[str, ...]]:
    """(refusal message, notes): refuse a layout outside the printable area before slicing.

    A layout or bed that cannot be measured is not refused: the slicer gives the definitive
    answer, and a note says the precheck was skipped.
    """
    bed = printable_area(machine)
    if bed is None:
        return None, (f"plate-fit precheck skipped: {printer_id} has no printable_area",)
    try:
        layout = plate_extent(input_3mf)
    except PlateExtentError as exc:
        return None, (f"plate-fit precheck skipped: {exc}",)
    if fits(layout, bed):
        return None, ()
    w, h = layout[2] - layout[0], layout[3] - layout[1]
    big_w, big_h = bed[2] - bed[0], bed[3] - bed[1]
    return (
        f"layout {w:.0f}×{h:.0f} mm does not fit {printer_id} printable area "
        f"{big_w:.0f}×{big_h:.0f} mm; choose a larger printer or re-lay out the plate"
    ), ()
