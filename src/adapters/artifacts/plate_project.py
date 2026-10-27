"""Revise verified original meshes in their existing 3MF placement; no slicing.

The component form is deliberately narrow: unique named objects, one mesh each,
identity component transforms and millimetres. Other forms require a new contract.
"""

from __future__ import annotations

import io
import math
import posixpath
import zipfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from xml.dom import minidom
from xml.etree import ElementTree as ET

from src.adapters.artifacts.plate_metadata import (
    object_name as _name,
)
from src.adapters.artifacts.plate_metadata import (
    parse_plate_xml as parse_plate_xml,
)
from src.adapters.artifacts.plate_metadata import (
    plate_object_labels as plate_object_labels,
)
from src.adapters.artifacts.plate_metadata import (
    require_one as _one,
)
from src.verification.mesh_binding import (
    MeshFrameBinding,
    bind_axis_frame,
    require_same_oriented_surface,
)
from src.verification.mesh_integrity import parse_closed_surface

_NS = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
_PRODUCTION = "{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}"
_IDENTITY = "1 0 0 0 1 0 0 0 1 0 0 0"
Surface = Mapping[str, object]


@dataclass(frozen=True, slots=True)
class _Part:
    member: str
    element: ET.Element
    settings: ET.Element
    build: ET.Element

    def surface(self) -> dict[str, object]:
        return {
            "vertices": [
                [float(v.attrib[a]) for a in "xyz"]
                for v in self.element.findall("m:mesh/m:vertices/m:vertex", _NS)
            ],
            "faces": [
                [int(v.attrib[a]) for a in ("v1", "v2", "v3")]
                for v in self.element.findall("m:mesh/m:triangles/m:triangle", _NS)
            ],
        }

    def world_surface(self) -> dict[str, object]:
        if self.build.get("printable", "1") not in ("1", "true"):
            raise ValueError("plate contains a disabled original part")
        transform = tuple(float(v) for v in self.build.get("transform", _IDENTITY).split())
        if len(transform) != 12 or not all(math.isfinite(v) for v in transform):
            raise ValueError("plate build transform must contain twelve finite numbers")
        points, faces = parse_closed_surface(self.surface())
        return {
            "vertices": [
                tuple(
                    sum(point[j] * transform[j * 3 + axis] for j in range(3)) + transform[9 + axis]
                    for axis in range(3)
                )
                for point in points
            ],
            "faces": faces,
        }


def _stale(name: str) -> bool:
    path = PurePosixPath(name)
    return name.endswith((".gcode", ".gcode.md5", ".png")) or (
        path.parent.as_posix() == "Metadata"
        and (
            path.name in ("slice_info.config", "filament_sequence.json")
            or path.name.startswith(("plate_", "plate_no_light_", "top_", "pick_"))
        )
    )


class PlateProject:
    def __init__(self, payload: bytes, owners: tuple[str, ...], *, max_bytes: int) -> None:
        try:
            self._load(payload, owners, max_bytes=max_bytes)
        except (zipfile.BadZipFile, ET.ParseError, KeyError, UnicodeDecodeError) as exc:
            raise ValueError("plate archive is incomplete or malformed") from exc

    def _load(self, payload: bytes, owners: tuple[str, ...], *, max_bytes: int) -> None:
        if not owners or len(set(owners)) != len(owners) or not 0 < len(payload) <= max_bytes:
            raise ValueError("plate requires unique owners and a bounded source")
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            infos = archive.infolist()
            names = [i.filename for i in infos]
            if len(set(names)) != len(names) or sum(i.file_size for i in infos) > max_bytes * 16:
                raise ValueError("plate archive is duplicated or exceeds expanded byte budget")
            for name in names:
                path = PurePosixPath(name)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or "\\" in name
                    or path.as_posix() != name
                ):
                    raise ValueError("plate archive contains a noncanonical member")
            self._entries = {name: archive.read(name) for name in names}
        self._max_bytes = max_bytes
        self._settings = parse_plate_xml(self._entries["Metadata/model_settings.config"])
        wrapper = parse_plate_xml(self._entries["3D/3dmodel.model"])
        if wrapper.get("unit") != "millimeter":
            raise ValueError("plate must use explicit millimetres")
        configurations = self._settings.findall("object")
        if len(configurations) != len(owners) or {_name(o) for o in configurations} != set(owners):
            raise ValueError("plate object names differ from the complete original part set")
        wrappers = wrapper.findall("m:resources/m:object", _NS)
        if len(wrappers) != len(owners):
            raise ValueError("plate wrapper population differs from the original set")
        ids = [o.get("id", "") for o in wrappers]
        built = [o.get("objectid", "") for o in wrapper.findall("m:build/m:item", _NS)]
        if not all(ids) or len(set(ids)) != len(ids) or sorted(built) != sorted(ids):
            raise ValueError("plate build must contain each original wrapper once")
        self._parts: dict[str, _Part] = {}
        for config in configurations:
            obj = _one([o for o in wrappers if o.get("id") == config.get("id")])
            comp = _one(obj.findall("m:components/m:component", _NS))
            if comp.get("transform") != _IDENTITY:
                raise ValueError("plate requires identity component transforms")
            member = comp.get(_PRODUCTION + "path", "").lstrip("/")
            model = parse_plate_xml(self._entries[member])
            if model.get("unit") != "millimeter":
                raise ValueError("plate mesh must use explicit millimetres")
            obj = _one(model.findall("m:resources/m:object", _NS))
            if obj.get("id") != comp.get("objectid"):
                raise ValueError("plate component mesh id differs")
            _one(obj.findall("m:mesh", _NS))
            part = _one(config.findall("part"))
            if part.get("id") != obj.get("id") or _name(part) != _name(config):
                raise ValueError("plate part identity differs from its owner")
            build = _one(
                [
                    item
                    for item in wrapper.findall("m:build/m:item", _NS)
                    if item.get("objectid") == config.get("id")
                ]
            )
            self._parts[_name(config)] = _Part(member, obj, config, build)
        members = {p.member for p in self._parts.values()}
        if len(members) != len(owners) or {
            n for n in self._entries if n.endswith(".model")
        } != members | {"3D/3dmodel.model"}:
            raise ValueError("plate contains extra or shared mesh resources")

    def _bind(self, owner: str, original: Surface) -> tuple[_Part, MeshFrameBinding]:
        if owner not in self._parts:
            raise ValueError("plate binding requires a known original owner")
        part = self._parts[owner]
        return part, bind_axis_frame(original, part.surface())

    def bind_originals(self, originals: Mapping[str, Surface]) -> dict[str, object]:
        if not originals:
            raise ValueError("plate binding requires nonempty original owners")
        report: dict[str, object] = {}
        for owner, original in originals.items():
            part, binding = self._bind(owner, original)
            report[owner] = {
                "member": part.member,
                "wrapper_id": part.settings.get("id"),
                "binding": asdict(binding),
            }
        return report

    def require_same_layout(self, payload: bytes) -> dict[str, float]:
        """Require every enabled original part at its existing world-frame surface after slicing."""
        other = PlateProject(payload, tuple(self._parts), max_bytes=self._max_bytes)
        return {
            owner: require_same_oriented_surface(
                part.world_surface(), other._parts[owner].world_surface()
            )
            for owner, part in self._parts.items()
        }

    def revise(
        self, changes: Mapping[str, tuple[Surface, Surface]]
    ) -> tuple[bytes, dict[str, object]]:
        if not changes or set(changes) - set(self._parts):
            raise ValueError("plate changes require known nonempty original owners")
        entries = dict(self._entries)
        settings = parse_plate_xml(entries["Metadata/model_settings.config"])
        configurations = {_name(o): o for o in settings.findall("object")}
        bindings: dict[str, object] = {}
        for owner, (original, revised) in changes.items():
            part, binding = self._bind(owner, original)
            points, faces = parse_closed_surface(revised)
            transformed = binding.transform(points)
            vertices = "".join(
                f'<vertex x="{x!r}" y="{y!r}" z="{z!r}"/>' for x, y, z in transformed
            )
            triangles = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in faces)
            mesh = f"<mesh><vertices>{vertices}</vertices><triangles>{triangles}</triangles></mesh>"
            text = entries[part.member].decode("utf-8")
            if text.count("<mesh>") != 1 or text.count("</mesh>") != 1:
                raise ValueError("plate mesh markup requires an explicit unadorned mesh")
            start, end = text.index("<mesh>"), text.index("</mesh>") + len("</mesh>")
            entries[part.member] = (text[:start] + mesh + text[end:]).encode("utf-8")
            for node in configurations[owner].iter():
                if "face_count" in node.attrib:
                    node.set("face_count", str(len(faces)))
            for parent in configurations[owner].iter():
                for child in list(parent):
                    if child.tag == "metadata" and child.get("key", "").startswith("source_"):
                        parent.remove(child)
            bindings[owner] = {"member": part.member, **asdict(binding)}
        removed = {name for name in entries if _stale(name)}
        for name in removed:
            del entries[name]
        for parent in settings.iter():
            for child in list(parent):
                if child.tag == "metadata" and child.get("value", "").lstrip("/") in removed:
                    parent.remove(child)
        entries["Metadata/model_settings.config"] = ET.tostring(
            settings, encoding="utf-8", xml_declaration=True
        )
        for name, data in list(entries.items()):
            if not name.endswith(".rels"):
                continue
            parse_plate_xml(
                data
            )  # Reject entity declarations before using the preserving DOM serializer.
            relationships = minidom.parseString(data)
            base = posixpath.dirname(posixpath.dirname(name))
            changed = False
            for relationship in list(relationships.getElementsByTagNameNS("*", "Relationship")):
                target = relationship.getAttribute("Target")
                if relationship.getAttribute("TargetMode") == "External":
                    continue
                resolved = posixpath.normpath(
                    target.lstrip("/") if target.startswith("/") else posixpath.join(base, target)
                )
                if resolved in removed:
                    dom_parent = relationship.parentNode
                    if dom_parent is None:
                        raise ValueError("plate relationship is detached")
                    dom_parent.removeChild(relationship)
                    changed = True
                elif resolved not in entries:
                    raise ValueError("plate has an unresolved internal relationship")
            if changed:
                entries[name] = relationships.toxml(encoding="utf-8")
            relationships.unlink()
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in entries.items():
                archive.writestr(name, data)
        payload = output.getvalue()
        if len(payload) > self._max_bytes:
            raise ValueError("revised plate exceeds byte budget")
        return payload, bindings
