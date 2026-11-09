"""Placed XY extent of a 3MF plate, and a machine profile's printable area (stdlib only).

The slicers run with ``--arrange 0``, so a plate laid out for a larger bed is refused by the
slicer itself (OrcaSlicer 2.4.2 exits -52 with one log line). This module lets the adapter say
why before any slicer starts. The extent is every mesh vertex of every build item, through the
item's transform and any ``components`` transforms, so it is exact for rotated parts too.
The root model part (``3D/3dmodel.model``) is read first. A component carrying the production
extension ``p:path`` (the standard Bambu/Orca project layout: ``/3D/Objects/object_N.model``)
is resolved inside the same archive, its ``objectid`` looked up in that part and its transform
composed as for an in-part component. The path loses one leading ``/``; ``..`` segments,
backslashes, a missing part or a suffix other than ``.model`` raise ``PlateExtentError``.

Hardening (the input can come from a remote MCP caller; stdlib only, no new dependency).
Every part read (root and referenced) gets the checks below, each part is parsed at most once,
and ONE cumulative budget of ``MAX_MODEL_BYTES`` covers the root plus all parts. Each read is a
bounded read of at most the remaining budget + 1 (the declared size is checked first), so a zip
bomb cannot inflate past the cap. A model that is not
UTF-8 (a UTF-16/UTF-32 byte-order mark, or an XML declaration naming another ``encoding``) is
refused first, because the byte-level DTD check below only holds for an ASCII-compatible
encoding: a UTF-16 ``<!ENTITY`` would not match it. Then any ``<!DOCTYPE`` or ``<!ENTITY``
anywhere in the bytes, any case, is refused before parsing, so ``ElementTree`` never sees a DTD
and cannot expand entities (a 3MF core model has no use for one). Encrypted members,
unsupported compression and corrupt deflate data are refused as ``PlateExtentError`` too.
Anything this module cannot measure is refused by ``plate_fit``; no slicer then starts.
``MAX_MODEL_BYTES`` is 5 x the measured uncompressed v78 ``3D/3dmodel.model``: 8168153 B
(1402754 B compressed) in ``雙上臂四點梯形-v78/整機69件-單盤排版-v78.3mf``, 69 parts, measured
with ``zipfile.ZipInfo.file_size`` on 2026-10-22, giving 40840765 B.
"""

from __future__ import annotations

import re
import zipfile
import zlib
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
_WIDE_BOMS = (b"\xff\xfe", b"\xfe\xff", b"\x00\x00\xfe\xff")  # UTF-16 LE/BE, UTF-32 BE (LE ⊃ 16 LE)
_DECLARED = re.compile(rb"""^(?:\xef\xbb\xbf)?\s*<\?xml[^>]*?\bencoding\s*=\s*["']([^"']*)["']""")
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


class _Part:
    """One parsed ``.model`` part: its objects, and (root only) its build items."""

    def __init__(self, root: ElementTree.Element) -> None:
        self.objects = {
            obj.get("id"): obj for obj in root.iter(f"{_CORE}object") if obj.get("id") is not None
        }
        self.items = [
            (item.get("objectid"), _matrix(item.get("transform")))
            for item in root.iter(f"{_CORE}item")
        ]


class _Archive:
    """Reads and parses model parts of one 3MF under ONE cumulative byte budget."""

    def __init__(self, archive: zipfile.ZipFile, name: str, cap: int) -> None:
        self._zip, self._name, self._cap, self._left = archive, name, cap, cap
        self._parts: dict[str, _Part] = {}

    def part(self, member: str) -> _Part:
        if member not in self._parts:
            self._parts[member] = _Part(ElementTree.fromstring(self._read(member)))
        return self._parts[member]

    def resolve(self, production_path: str) -> str:
        """The archive member a ``p:path`` names; refuses escapes, odd suffixes, absent parts."""
        member = production_path[1:] if production_path.startswith("/") else production_path
        if (
            "\\" in member
            or ".." in member.split("/")
            or not member.endswith(".model")
            or member not in self._zip.namelist()
        ):
            raise PlateExtentError(f"{self._name}: component part is not a model in the archive")
        return member

    def _read(self, member: str) -> bytes:
        """One part, bounded by what is left of the budget; refuses non-UTF-8 and any DTD."""
        if self._zip.getinfo(member).file_size > self._left:
            raise PlateExtentError(f"{self._name}: {member} exceeds {self._cap} B uncompressed")
        with self._zip.open(member) as handle:
            data = handle.read(self._left + 1)  # a false declared size cannot exceed it either
        if len(data) > self._left:
            raise PlateExtentError(f"{self._name}: {member} exceeds {self._cap} B uncompressed")
        self._left -= len(data)
        declared = _DECLARED.match(data)
        if (
            data.startswith(_WIDE_BOMS)
            or b"\x00" in data  # UTF-16/32 even without a BOM; never legal in UTF-8 XML
            or (declared is not None and declared.group(1).lower() != b"utf-8")
        ):
            raise PlateExtentError(f"{self._name}: {member} is not UTF-8; refused")
        if _DTD.search(data):
            raise PlateExtentError(
                f"{self._name}: {member} declares a DTD (DOCTYPE/ENTITY); refused"
            )
        return data

    def points(
        self, part: _Part, object_id: str | None, m: Matrix, depth: int = 0
    ) -> Iterator[tuple[float, float]]:
        obj = part.objects.get(object_id)
        if obj is None or depth > 16:
            raise ValueError(f"build references unknown or cyclic object {object_id!r}")
        for vertex in obj.iter(f"{_CORE}vertex"):
            x, y, z = (float(vertex.get(axis, "0")) for axis in ("x", "y", "z"))
            yield (
                x * m[0] + y * m[3] + z * m[6] + m[9],
                x * m[1] + y * m[4] + z * m[7] + m[10],
            )
        for component in obj.iter(f"{_CORE}component"):
            target = part
            for key, value in component.attrib.items():
                if key.endswith("}path"):
                    target = self.part(self.resolve(value))
            inner = _matrix(component.get("transform"))
            yield from self.points(target, component.get("objectid"), _compose(inner, m), depth + 1)


def plate_extent(path: Path, *, max_model_bytes: int = MAX_MODEL_BYTES) -> Extent:
    """XY bounding box of every placed vertex, in millimetres."""
    try:
        with zipfile.ZipFile(path) as archive:
            reader = _Archive(archive, path.name, max_model_bytes)
            root = reader.part(_MODEL)
            xs: list[float] = []
            ys: list[float] = []
            for object_id, matrix in root.items:
                for x, y in reader.points(root, object_id, matrix):
                    xs.append(x)
                    ys.append(y)
    except OSError as exc:  # str(OSError) carries the absolute path; strerror does not
        raise PlateExtentError(
            f"cannot measure the layout of {path.name}: {exc.strerror or type(exc).__name__}"
        ) from exc
    except (
        KeyError,
        ValueError,
        zipfile.BadZipFile,
        ElementTree.ParseError,
        RuntimeError,  # encrypted member
        NotImplementedError,  # unsupported compression method
        zlib.error,  # corrupt deflate stream
    ) as exc:
        reason = str(exc) or type(exc).__name__
        raise PlateExtentError(f"cannot measure the layout of {path.name}: {reason}") from exc
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


def bed_size(machine: Mapping[str, object]) -> tuple[float, float, float] | None:
    """``(width, depth, height)`` mm a flattened machine profile prints, else ``None``."""
    area = printable_area(machine)
    try:
        height = float(str(machine.get("printable_height")))
    except ValueError:
        return None
    if area is None:
        return None
    return area[2] - area[0], area[3] - area[1], height


def fits(layout: Extent, bed: Extent, tolerance_mm: float = 0.01) -> bool:
    return (
        layout[0] >= bed[0] - tolerance_mm
        and layout[1] >= bed[1] - tolerance_mm
        and layout[2] <= bed[2] + tolerance_mm
        and layout[3] <= bed[3] + tolerance_mm
    )


def plate_fit(input_3mf: Path, machine: Mapping[str, object], printer_id: str) -> str | None:
    """The refusal message, or None when the layout fits the printable area.

    A layout or bed that cannot be measured is refused as well: a model this module will not
    parse (DTD, non-UTF-8, oversize, broken zip) must not reach the slicer either.
    """
    bed = printable_area(machine)
    if bed is None:
        return f"plate-fit precheck failed: {printer_id} has no printable_area"
    try:
        layout = plate_extent(input_3mf)
    except PlateExtentError as exc:
        return f"plate-fit precheck failed: {exc}"
    if fits(layout, bed):
        return None
    w, h = layout[2] - layout[0], layout[3] - layout[1]
    big_w, big_h = bed[2] - bed[0], bed[3] - bed[1]
    return (
        f"layout {w:.0f}×{h:.0f} mm does not fit {printer_id} printable area "
        f"{big_w:.0f}×{big_h:.0f} mm; choose a larger printer or re-lay out the plate"
    )
