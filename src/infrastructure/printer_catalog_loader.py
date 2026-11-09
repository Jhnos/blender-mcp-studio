"""Load ``config/slicers.yaml`` and ``config/printers/<vendor>/*.yaml`` into a PrinterCatalog."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import fields
from pathlib import Path

import yaml

from src.core.domain.printer_catalog import ExitCode, PrinterCatalog, PrinterProfile, SlicerSpec
from src.infrastructure.config_loader import default_config_dir as _builtin_dir
from src.infrastructure.narrowing import as_int, as_mapping, as_sequence
from src.infrastructure.tools_config import ToolsConfig

#: A slicer's ``binary_key`` must name one of these (the runtime reads it with getattr).
_TOOLS_FIELDS = frozenset(f.name for f in fields(ToolsConfig))
#: Printer ``overrides`` files live here, relative to the config dir.
OVERRIDES_SUBDIR = "slicer-profiles"

_SLICER_KEYS = frozenset(
    ("id", "name", "binary_key", "profiles_subdir", "license", "error_codes", "install_hint")
)
_EXIT_CODE_KEYS = frozenset(("code", "meaning", "name", "hint"))
_PRINTER_KEYS = frozenset(
    (
        "id",
        "vendor",
        "model",
        "nozzle_mm",
        "slicer",
        "profile_vendor_dir",
        "machine",
        "processes",
        "filaments",
        "bed_type",
        "overrides",
    )
)


def _read(path: Path, base: Path) -> tuple[str, Mapping[str, object]]:
    """Parse one catalog file; every error names the path relative to the config dir."""
    where = path.relative_to(base).as_posix()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        problem = str(getattr(exc, "problem", None) or "parse error")
        raise ValueError(f"{where}: invalid YAML: {problem}") from exc
    mapping = as_mapping(raw)
    if mapping is None:
        raise ValueError(f"{where}: top level must be a mapping")
    return where, mapping


def _known_keys(raw: Mapping[str, object], allowed: frozenset[str], where: str) -> None:
    extra = sorted(str(key) for key in raw if key not in allowed)
    if extra:
        raise ValueError(f"{where}: unknown key(s) {', '.join(extra)}; allowed: {sorted(allowed)}")


def _require(raw: Mapping[str, object], key: str, where: str) -> object:
    if raw.get(key) is None:
        raise ValueError(f"{where}: missing key {key}")
    return raw[key]


def _text(raw: Mapping[str, object], key: str, where: str) -> str:
    value = _require(raw, key, where)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{where}: {key} must be a non-empty string")
    return value


def _pairs(raw: Mapping[str, object], key: str, where: str) -> tuple[tuple[str, str], ...]:
    mapping = as_mapping(_require(raw, key, where))
    if not mapping:
        raise ValueError(f"{where}: {key} must be a non-empty mapping")
    for name in mapping:
        if not isinstance(name, str):
            raise ValueError(
                f"{where}: {key} key {name} must be a string; quote it in YAML, e.g. '0.20'"
            )
    return tuple((str(k), str(v)) for k, v in mapping.items())


def _heights(pairs: tuple[tuple[str, str], ...], where: str) -> tuple[tuple[str, str], ...]:
    """``processes`` keys are layer heights: each must parse as a positive, finite float."""
    for key, _ in pairs:
        try:
            height = float(key)
        except ValueError:
            height = math.nan
        if not math.isfinite(height) or height <= 0:
            raise ValueError(
                f"{where}: processes key '{key}' must be a positive layer height in mm, "
                "e.g. '0.20'"
            )
    return pairs


def _slicer(raw: Mapping[str, object], where: str) -> SlicerSpec:
    _known_keys(raw, _SLICER_KEYS, where)
    codes = as_sequence(raw.get("error_codes", []))
    if codes is None:
        raise ValueError(f"{where}: error_codes must be a list")
    pairs: list[ExitCode] = []
    for item in codes:
        entry = as_mapping(item)
        code = as_int(entry.get("code")) if entry is not None else None
        if entry is None or code is None:
            raise ValueError(f"{where}: error_codes entries need an integer code and a meaning")
        _known_keys(entry, _EXIT_CODE_KEYS, where)
        pairs.append(
            ExitCode(
                code,
                str(entry.get("meaning", "")),
                str(entry.get("name", "")),
                str(entry.get("hint", "")),
            )
        )
    binary_key = _text(raw, "binary_key", where)
    if binary_key not in _TOOLS_FIELDS:
        raise ValueError(
            f"{where}: binary_key '{binary_key}' is not a tools.yaml setting; "
            f"known: {sorted(_TOOLS_FIELDS)}"
        )
    return SlicerSpec(
        id=_text(raw, "id", where),
        name=_text(raw, "name", where),
        binary_key=binary_key,
        profiles_subdir=_text(raw, "profiles_subdir", where),
        license=_text(raw, "license", where),
        error_codes=tuple(pairs),
        install_hint=_text(raw, "install_hint", where),
    )


def _printer(raw: Mapping[str, object], where: str) -> PrinterProfile:
    _known_keys(raw, _PRINTER_KEYS, where)
    nozzle = _require(raw, "nozzle_mm", where)
    if isinstance(nozzle, bool) or not isinstance(nozzle, int | float) or nozzle <= 0:
        raise ValueError(f"{where}: nozzle_mm must be a positive number")
    overrides = raw.get("overrides")
    return PrinterProfile(
        id=_text(raw, "id", where),
        vendor=_text(raw, "vendor", where),
        model=_text(raw, "model", where),
        nozzle_mm=float(nozzle),
        slicer=_text(raw, "slicer", where),
        profile_vendor_dir=_text(raw, "profile_vendor_dir", where),
        machine=_text(raw, "machine", where),
        processes=_heights(_pairs(raw, "processes", where), where),
        filaments=_pairs(raw, "filaments", where),
        bed_type=_text(raw, "bed_type", where),
        overrides=str(overrides) if overrides is not None else None,
    )


def _slicer_entry(item: object, where: str) -> Mapping[str, object]:
    entry = as_mapping(item)
    if entry is None:
        raise ValueError(f"{where}: every slicers entry must be a mapping")
    return entry


def _printer_files(base: Path) -> list[Path]:
    """Every ``printers/<vendor>/<id>.yaml``; anything else under printers/ is an error."""
    root = base / "printers"
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir() or path.name == ".DS_Store":
            continue
        rel = path.relative_to(base).as_posix()
        if path.suffix != ".yaml":
            raise ValueError(f"{rel}: stray file; printer files must be named <id>.yaml")
        if path.parent == root:
            raise ValueError(f"{rel}: misplaced; put it in a vendor folder printers/<vendor>/")
        files.append(path)
    return files


def load_printer_catalog(config_dir: Path | None = None) -> PrinterCatalog:
    """Read every slicer and printer file; fail loudly, naming the file, on any inconsistency."""
    base = config_dir or _builtin_dir()
    where, top = _read(base / "slicers.yaml", base)
    _known_keys(top, frozenset(("slicers",)), where)
    slicers_raw = as_sequence(top.get("slicers"))
    if not slicers_raw:
        raise ValueError(f"{where}: slicers must be a non-empty list")
    slicers = tuple(_slicer(_slicer_entry(item, where), where) for item in slicers_raw)
    slicer_ids: set[str] = set()
    for slicer in slicers:
        if slicer.id in slicer_ids:
            raise ValueError(f"{where}: duplicate slicer id '{slicer.id}'")
        slicer_ids.add(slicer.id)
    printers: list[PrinterProfile] = []
    seen: dict[str, str] = {}
    for path in _printer_files(base):
        where, raw = _read(path, base)
        printer = _printer(raw, where)
        if printer.id in seen:
            raise ValueError(
                f"duplicate printer id '{printer.id}' in {where}, "
                f"already defined in {seen[printer.id]}"
            )
        if printer.slicer not in slicer_ids:
            raise ValueError(
                f"{where}: unknown slicer '{printer.slicer}'; known: {sorted(slicer_ids)}"
            )
        if printer.overrides is not None and not (
            base / OVERRIDES_SUBDIR / printer.overrides
        ).is_file():
            raise ValueError(
                f"{where}: overrides '{printer.overrides}' is not a file in {OVERRIDES_SUBDIR}/"
            )
        seen[printer.id] = where
        printers.append(printer)
    if not printers:
        raise ValueError("printers/: no printers found; add printers/<vendor>/<id>.yaml files")
    return PrinterCatalog(printers=tuple(printers), slicers=slicers)
