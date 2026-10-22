"""Load ``config/slicers.yaml`` and ``config/printers/<vendor>/*.yaml`` into a PrinterCatalog."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from src.core.domain.printer_catalog import PrinterCatalog, PrinterProfile, SlicerSpec
from src.infrastructure.config_loader import default_config_dir as _builtin_dir
from src.infrastructure.config_loader import load_yaml
from src.infrastructure.narrowing import as_int, as_mapping, as_sequence


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
    value = _require(raw, key, where)
    mapping = as_mapping(value)
    if not mapping:
        raise ValueError(f"{where}: {key} must be a non-empty mapping")
    return tuple((str(k), str(v)) for k, v in mapping.items())


def _slicer(raw: Mapping[str, object], where: str) -> SlicerSpec:
    codes = as_sequence(raw.get("error_codes", []))
    if codes is None:
        raise ValueError(f"{where}: error_codes must be a list")
    pairs: list[tuple[int, str]] = []
    for item in codes:
        entry = as_mapping(item)
        code = as_int(entry.get("code")) if entry is not None else None
        if entry is None or code is None:
            raise ValueError(f"{where}: error_codes entries need an integer code and a meaning")
        pairs.append((code, str(entry.get("meaning", ""))))
    return SlicerSpec(
        id=_text(raw, "id", where),
        name=_text(raw, "name", where),
        binary_key=_text(raw, "binary_key", where),
        profiles_subdir=_text(raw, "profiles_subdir", where),
        license=_text(raw, "license", where),
        error_codes=tuple(pairs),
        install_hint=_text(raw, "install_hint", where),
    )


def _printer(raw: Mapping[str, object], where: str) -> PrinterProfile:
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
        processes=_pairs(raw, "processes", where),
        filaments=_pairs(raw, "filaments", where),
        bed_type=_text(raw, "bed_type", where),
        overrides=str(overrides) if overrides is not None else None,
    )


def _slicer_entry(item: object) -> Mapping[str, object]:
    entry = as_mapping(item)
    if entry is None:
        raise ValueError("config/slicers.yaml: every slicers entry must be a mapping")
    return entry


def load_printer_catalog(config_dir: Path | None = None) -> PrinterCatalog:
    """Read every slicer and printer file; fail loudly, naming the file, on any inconsistency."""
    base = config_dir or _builtin_dir()
    slicers_raw = as_sequence(load_yaml(base / "slicers.yaml").get("slicers"))
    if not slicers_raw:
        raise ValueError("config/slicers.yaml: slicers must be a non-empty list")
    slicers = tuple(_slicer(_slicer_entry(item), "config/slicers.yaml") for item in slicers_raw)
    slicer_ids = {s.id for s in slicers}
    printers: list[PrinterProfile] = []
    seen: dict[str, str] = {}
    for path in sorted((base / "printers").glob("*/*.yaml")):
        where = f"config/printers/{path.parent.name}/{path.name}"
        printer = _printer(load_yaml(path), where)
        if printer.id in seen:
            raise ValueError(
                f"duplicate printer id '{printer.id}' in {where}, already defined in {seen[printer.id]}"
            )
        if printer.slicer not in slicer_ids:
            raise ValueError(
                f"{where}: unknown slicer '{printer.slicer}'; known: {sorted(slicer_ids)}"
            )
        seen[printer.id] = where
        printers.append(printer)
    return PrinterCatalog(printers=tuple(printers), slicers=slicers)
