"""Inspect fresh Bambu output bytes against its actual machine profile; never print or repair."""

from __future__ import annotations

import hashlib
import re
import time
import zipfile
import zlib
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import asdict
from math import isfinite
from pathlib import Path
from xml.etree import ElementTree as ET

from src.adapters.artifacts.native_source import fingerprint_source_asset
from src.adapters.artifacts.plate_metadata import parse_plate_xml, plate_object_labels
from src.adapters.slicing.gcode_paths import iter_extrusions
from src.core.domain.extrusion import BuildVolume, ExtrusionInspection
from src.core.domain.import_limits import ImportLimits
from src.core.domain.native_revision import NativeSourceError
from src.core.domain.slicing import SliceRequest
from src.core.use_cases.toolpath_inspection import inspect_extrusions
from src.infrastructure.narrowing import as_sequence

# Measured full 69-object inspection: 26.51 s, 2026-10-27; five times rounded seconds.
SLOWEST_INSPECTION_MEASURED_S = 27
TOOLPATH_INSPECTION_TIMEOUT_S = 5 * SLOWEST_INSPECTION_MEASURED_S

_GCODE = re.compile(r"Metadata/plate_([1-9][0-9]*)\.gcode")
_MAX_METADATA_BYTES = 4 * 1024 * 1024
_SCOPE = "commanded bead envelopes and named bed-contact paths; not measured adhesion, assembly or load acceptance"


def _xy(value: object) -> tuple[float, float]:
    try:
        x, y = str(value).lower().split("x")
        return float(x), float(y)
    except (ValueError, TypeError) as exc:
        raise ValueError("machine must declare finite XY coordinates") from exc


def machine_volume(machine: Mapping[str, object]) -> BuildVolume:
    points = as_sequence(machine.get("printable_area"))
    exclusions = as_sequence(machine.get("bed_exclude_area"))
    offsets = as_sequence(machine.get("extruder_offset"))
    if (
        points is None
        or exclusions is None
        or exclusions
        or offsets is None
        or len(offsets) != 1
        or _xy(offsets[0]) != (0.0, 0.0)
    ):
        raise ValueError("unsupported or undeclared machine exclusions or extruder offsets")
    corners = [_xy(p) for p in points]
    if len(corners) == 5 and corners[-1] == corners[0]:
        corners.pop()
    xs, ys = {p[0] for p in corners}, {p[1] for p in corners}
    if (
        len(corners) != 4
        or len(xs) != 2
        or len(ys) != 2
        or set(corners) != {(x, y) for x in xs for y in ys}
    ):
        raise ValueError("inspection requires an explicit rectangular build plate")
    if any(
        a[0] != b[0] and a[1] != b[1]
        for a, b in zip(corners, corners[1:] + corners[:1], strict=True)
    ):
        raise ValueError("machine printable polygon is not a rectangle perimeter")
    try:
        height = float(str(machine["printable_height"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("machine must declare a finite positive printable height") from exc
    return BuildVolume((min(xs), min(ys), 0.0), (max(xs), max(ys), height))


def _document(result: ExtrusionInspection, labels: dict[int, str]) -> dict[str, object]:
    doc = asdict(result)
    doc.update(
        passed=result.passed,
        support_paths=result.support_paths,
        brim_paths=result.brim_paths,
        bed_support_paths=result.bed_support_paths,
        bed_brim_paths=result.bed_brim_paths,
    )
    objects = {obj.object_id: obj for obj in result.objects}
    doc["objects"] = [
        {
            "object_id": label,
            "name": name,
            "paths": objects[label].paths if label in objects else 0,
            "bed_contact_paths": objects[label].bed_contact_paths if label in objects else 0,
        }
        for label, name in sorted(labels.items())
    ]
    doc["unknown_object_ids"] = sorted(set(objects) - labels.keys())
    return doc


def _hashed_lines(
    raw: Iterable[bytes],
    update: Callable[[bytes], None],
    deadline: float,
    clock: Callable[[], float],
) -> Iterator[str]:
    for index, line in enumerate(raw):
        if index % 1024 == 0 and clock() >= deadline:
            raise ValueError("toolpath inspection exceeded its cooperative time budget")
        update(line)
        yield line.decode("utf-8")


def inspect_sliced_project(
    project: Path,
    machine: Mapping[str, object],
    limits: ImportLimits,
    *,
    request: SliceRequest | None = None,
    timeout_s: float = TOOLPATH_INSPECTION_TIMEOUT_S,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, object]:
    if type(timeout_s) not in (int, float) or not isfinite(timeout_s) or timeout_s <= 0:
        raise ValueError("inspection budget must be finite and positive")
    deadline = clock() + timeout_s
    plates: list[dict[str, object]] = []
    report: dict[str, object] = {"passed": False, "scope": _SCOPE, "plates": plates}
    try:
        volume = machine_volume(machine)
        report["build_volume"] = asdict(volume)
        if project.is_symlink():
            raise ValueError("sliced output must not be a symlink")
        receipt = fingerprint_source_asset(project, project.name, limits.max_3mf_bytes)
        report["source"] = asdict(receipt)
        with zipfile.ZipFile(project) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if (
                len(set(names)) != len(names)
                or sum(info.file_size for info in infos) > limits.max_3mf_bytes * 16
            ):
                raise ValueError("sliced archive is duplicated or exceeds its expanded byte budget")
            metadata = archive.getinfo("Metadata/model_settings.config")
            if metadata.file_size > min(limits.max_3mf_bytes, _MAX_METADATA_BYTES):
                raise ValueError("slice instance metadata exceeds its byte budget")
            settings = parse_plate_xml(archive.read(metadata))
            members = sorted(name for name in names if _GCODE.fullmatch(name))
            if not members:
                raise ValueError("sliced archive has no plate G-code")
            for member in members:
                matched = _GCODE.fullmatch(member)
                assert matched is not None
                labels = plate_object_labels(settings, int(matched.group(1)))
                digest = hashlib.sha256()
                with archive.open(member) as raw:
                    result = inspect_extrusions(
                        iter_extrusions(_hashed_lines(raw, digest.update, deadline, clock)),
                        volume,
                        expected_object_ids=frozenset(labels),
                        allow_support=request.support if request is not None else True,
                        allow_brim=request.brim_mm > 0 if request is not None else True,
                    )
                plate = _document(result, labels)
                plate.update(gcode=member, gcode_sha256=digest.hexdigest())
                plates.append(plate)
        if clock() >= deadline:
            raise ValueError("toolpath inspection exceeded its cooperative time budget")
        if fingerprint_source_asset(project, project.name, limits.max_3mf_bytes) != receipt:
            raise ValueError("sliced output changed during inspection")
        report["passed"] = bool(plates) and all(p["passed"] is True for p in plates)
    except OSError:
        report["error"] = "sliced output evidence could not be read"
    except (
        ValueError,
        KeyError,
        zipfile.BadZipFile,
        zlib.error,
        NativeSourceError,
        ET.ParseError,
    ) as exc:
        report["error"] = str(exc)
    return report
