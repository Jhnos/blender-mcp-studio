"""Pure native-job lineage and downloaded-byte checks; no transport or scene mutation."""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from collections.abc import Mapping
from dataclasses import fields
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET

from src.adapters.artifacts.plate_metadata import parse_plate_xml, plate_object_labels
from src.core.domain.native_revision import NativeModelSource
from src.core.planning.screen_revision_plan import SCREEN_MODIFIED_OWNERS
from src.infrastructure.narrowing import as_mapping, as_sequence


def object_value(value: object) -> Mapping[str, object]:
    result = as_mapping(value)
    if result is None:
        raise ValueError("native evidence must be an object")
    return result


def rows(value: object) -> list[Mapping[str, object]]:
    sequence = as_sequence(value)
    if sequence is None:
        raise ValueError("native parts must be an array")
    return [object_value(item) for item in sequence]


def artifact(value: object) -> Mapping[str, object]:
    item = object_value(value)
    name, sha, size = item.get("path"), item.get("sha256"), item.get("size_bytes")
    if not isinstance(name, str) or not name:
        raise ValueError("native artifact needs a relative path")
    path = PurePosixPath(name)
    if (
        path.is_absolute()
        or path.as_posix() != name
        or any(p.startswith(".") for p in path.parts)
        or "\\" in name
    ):
        raise ValueError("native artifact path must be canonical and relative")
    if not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{64}", sha) is None:
        raise ValueError("native artifact requires a SHA256")
    if type(size) is not int or size <= 0:
        raise ValueError("native artifact requires a positive byte count")
    return item


def artifacts(product: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    stls = object_value(product["stls"])
    output = {}
    for item in [artifact(stls["native"]), *(artifact(p) for p in rows(stls["parts"]))]:
        path = "native-product/parts/" + str(item["path"])
        if path in output:
            raise ValueError("native product has duplicate output paths")
        output[path] = item
    project = artifact(product["project"])
    output["native-product/" + str(project["path"])] = project
    return output


def check_product(
    product: Mapping[str, object], selected: Mapping[str, object], run_id: str
) -> list[str]:
    try:
        if selected.get("available") is not True:
            raise ValueError("selected native receipt is unavailable")
        if product["directory"] != run_id + "/native-product":
            raise ValueError("native product belongs to a different job")
        stls = object_value(product["stls"])
        source = {field.name: selected[field.name] for field in fields(NativeModelSource)}
        if stls["source"] != source:
            raise ValueError("native product disagrees with selected source")
        originals = rows(selected["parts"])
        actual = rows(stls["parts"])
        original = {str(artifact(p)["path"]): p for p in originals}
        revised = {str(artifact(p)["path"]): p for p in actual}
        if (
            len(original) != len(originals)
            or len(revised) != len(actual)
            or set(original) != set(revised)
        ):
            raise ValueError("native product must contain each original part exactly once")
        expected = {p for p in original if PurePosixPath(p).stem in SCREEN_MODIFIED_OWNERS}
        changed = as_sequence(stls["changed_paths"])
        if (
            len(expected) != len(SCREEN_MODIFIED_OWNERS)
            or changed is None
            or len(changed) != len(expected)
            or set(changed) != expected
        ):
            raise ValueError("native changed parts differ from the registered original owners")
        for name, part in revised.items():
            if (part == original[name]) == (name in expected):
                raise ValueError(
                    "native changed or unchanged bytes disagree with original identity"
                )
        candidate = artifact(stls["native"])
        if candidate["sha256"] == artifact(selected["native"])["sha256"] or not str(
            candidate["path"]
        ).endswith(".blend"):
            raise ValueError("native output must be a distinct saved revision")
        if artifact(product["project"])["path"] != "project.3mf":
            raise ValueError("native product must name its same-part plate")
        artifacts(product)
    except (KeyError, TypeError, ValueError) as exc:
        return ["native product receipt rejected: " + str(exc)]
    return []


def check_downloads(product: Mapping[str, object], payloads: Mapping[str, bytes]) -> list[str]:
    try:
        for name, receipt in artifacts(product).items():
            payload = payloads[name]
            if (
                len(payload) != receipt["size_bytes"]
                or hashlib.sha256(payload).hexdigest() != receipt["sha256"]
            ):
                raise ValueError("download fingerprint mismatch: " + name)
    except (KeyError, TypeError, ValueError) as exc:
        return ["native downloaded output rejected: " + str(exc)]
    return []


def check_slice_inventory(payload: bytes, owners: tuple[str, ...]) -> list[str]:
    """An archive containing all meshes can still silently skip an object while slicing."""
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            settings = parse_plate_xml(archive.read("Metadata/model_settings.config"))
            sliced = parse_plate_xml(archive.read("Metadata/slice_info.config"))
        plates, sliced_plates = settings.findall("plate"), sliced.findall("plate")
        if len(plates) != 1 or len(sliced_plates) != 1:
            raise ValueError("native slice must contain one configured and sliced plate")
        names = {}
        for obj in settings.findall("object"):
            metadata = {v.get("key"): v.get("value") for v in obj.findall("metadata")}
            names[obj.get("id")] = metadata.get("name")
        instances = []
        for instance in plates[0].findall("model_instance"):
            metadata = {v.get("key"): v.get("value") for v in instance.findall("metadata")}
            if metadata.get("instance_id") != "0":
                raise ValueError("native slice has an unexpected extra instance")
            instances.append(names[metadata.get("object_id")])
        objects = sliced_plates[0].findall("object")
        actual = [obj.get("name") for obj in objects]
        if (
            len(instances) != len(owners)
            or set(instances) != set(owners)
            or len(actual) != len(owners)
            or set(actual) != set(owners)
        ):
            raise ValueError("native slice does not contain every original part once")
        if any(obj.get("skipped") not in ("false", "0") for obj in objects):
            raise ValueError("native slice skipped an original part")
    except (KeyError, ValueError, zipfile.BadZipFile, ET.ParseError) as exc:
        return ["native sliced inventory rejected: " + str(exc)]
    return []


def check_extrusion_receipt(
    receipt: Mapping[str, object], payload: bytes, owners: tuple[str, ...]
) -> list[str]:
    """Workstation contract: fresh single-plate evidence, every part grounded, support/brim present."""
    try:
        source = artifact(receipt["source"])
        if (
            receipt.get("passed") is not True
            or source["size_bytes"] != len(payload)
            or source["sha256"] != hashlib.sha256(payload).hexdigest()
        ):
            raise ValueError("extrusion evidence is failed or belongs to another sliced archive")
        plates = rows(receipt["plates"])
        if len(plates) != 1:
            raise ValueError("workstation extrusion evidence must contain one plate")
        plate = plates[0]
        if (
            plate.get("passed") is not True
            or plate.get("outside_paths") != 0
            or plate.get("violations") != []
            or plate.get("unknown_object_ids") != []
            or plate.get("unassigned_paths") != 0
        ):
            raise ValueError("workstation extrusion evidence contains invalid deposition")
        for key in ("path_count", "bed_contact_paths", "bed_support_paths", "bed_brim_paths"):
            value = plate.get(key)
            if type(value) is not int or value <= 0:
                raise ValueError("workstation requires deposition, bed contact, support and brim")
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = [
                n
                for n in archive.namelist()
                if re.fullmatch(r"Metadata/plate_[1-9][0-9]*\.gcode", n)
            ]
            if members != ["Metadata/plate_1.gcode"] or plate.get("gcode") != members[0]:
                raise ValueError("extrusion evidence names a different plate")
            digest = hashlib.sha256(archive.read(members[0])).hexdigest()
            labels = plate_object_labels(
                parse_plate_xml(archive.read("Metadata/model_settings.config")), 1
            )
        if plate.get("gcode_sha256") != digest:
            raise ValueError("extrusion evidence does not bind the fresh G-code bytes")
        objects = rows(plate["objects"])
        if len(objects) != len(owners) or set(labels.values()) != set(owners):
            raise ValueError("extrusion evidence is missing original parts")
        actual = {}
        for obj in objects:
            label, name = obj.get("object_id"), obj.get("name")
            if type(label) is not int or label in actual or labels.get(label) != name:
                raise ValueError("extrusion object identity differs from sliced metadata")
            for key in ("paths", "bed_contact_paths"):
                value = obj.get(key)
                if type(value) is not int or value <= 0:
                    raise ValueError("every original part requires deposition and bed contact")
            actual[label] = name
        if actual != labels:
            raise ValueError("extrusion object inventory differs from sliced metadata")
    except (KeyError, ValueError, zipfile.BadZipFile, ET.ParseError) as exc:
        return ["native extrusion evidence rejected: " + str(exc)]
    return []
