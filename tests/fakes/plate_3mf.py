"""Write tiny core-spec 3MF files: unit cubes scaled and placed by build-item transforms."""

from __future__ import annotations

import zipfile
from pathlib import Path

_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"


def _cube(object_id: int, size: float) -> str:
    corners = [(x, y, z) for x in (0, size) for y in (0, size) for z in (0, size)]
    vertices = "".join(f'<vertex x="{x}" y="{y}" z="{z}"/>' for x, y, z in corners)
    triangle = '<triangle v1="0" v2="1" v3="2"/>'
    return (
        f'<object id="{object_id}" type="model"><mesh><vertices>{vertices}</vertices>'
        f"<triangles>{triangle}</triangles></mesh></object>"
    )


def write_3mf(path: Path, items: list[tuple[float, str | None]]) -> Path:
    """One cube object per item: ``(edge mm, transform or None)``."""
    objects = "".join(_cube(i + 1, size) for i, (size, _) in enumerate(items))
    build = "".join(
        f'<item objectid="{i + 1}"' + (f' transform="{t}"' if t else "") + "/>"
        for i, (_, t) in enumerate(items)
    )
    model = (
        f'<?xml version="1.0" encoding="UTF-8"?><model xmlns="{_NS}" unit="millimeter">'
        f"<resources>{objects}</resources><build>{build}</build></model>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("3D/3dmodel.model", model)
    return path


def translate(x: float, y: float) -> str:
    return f"1 0 0 0 1 0 0 0 1 {x} {y} 0"
