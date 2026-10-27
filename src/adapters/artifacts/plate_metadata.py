"""Bounded-format XML and slice-instance names, independent of geometry and delivery engines."""

from xml.etree import ElementTree as ET


def require_one(elements: list[ET.Element]) -> ET.Element:
    if len(elements) != 1:
        raise ValueError("plate requires one unique object, component and mesh")
    return elements[0]


def object_name(element: ET.Element) -> str:
    meta = require_one([m for m in element.findall("metadata") if m.get("key") == "name"])
    name = meta.get("value", "")
    if not name:
        raise ValueError("plate owner must have a name")
    return name


def plate_object_labels(settings: ET.Element, plate_id: int) -> dict[int, str]:
    """Bind fresh slicer identify_id labels to names; source archive object IDs are different."""

    def metadata(element: ET.Element, key: str) -> str:
        value = require_one([m for m in element.findall("metadata") if m.get("key") == key]).get(
            "value"
        )
        if value is None or not value:
            raise ValueError("plate instance metadata is missing")
        return value

    objects = settings.findall("object")
    names = {obj.get("id"): object_name(obj) for obj in objects}
    if len(names) != len(objects) or None in names:
        raise ValueError("plate requires unique named source object IDs")
    plate = require_one(
        [p for p in settings.findall("plate") if metadata(p, "plater_id") == str(plate_id)]
    )
    labels: dict[int, str] = {}
    instances: set[tuple[str, int]] = set()
    for instance in plate.findall("model_instance"):
        source = metadata(instance, "object_id")
        values = [metadata(instance, key) for key in ("instance_id", "identify_id")]
        if any(not value.isascii() or not value.isdecimal() or len(value) > 20 for value in values):
            raise ValueError("plate instance labels must be bounded integers")
        index, label = (int(value) for value in values)
        if (
            index < 0
            or label < 0
            or label in labels
            or (source, index) in instances
            or source not in names
        ):
            raise ValueError("plate has missing, duplicate or incoherent instance labels")
        labels[label] = names[source]
        instances.add((source, index))
    if not labels:
        raise ValueError("plate has no named slice instances")
    return labels


def parse_plate_xml(payload: bytes) -> ET.Element:
    if b"<!DOCTYPE" in payload or b"<!ENTITY" in payload:
        raise ValueError("plate XML entity declarations are unsupported")
    return ET.fromstring(payload)
