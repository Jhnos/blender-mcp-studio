"""Vendor slicer profiles read from an installed slicer app bundle (never vendored in the repo).

Profiles live in ``<App>.app/Contents/Resources/profiles/<VendorDir>/{machine,process,filament}/``.
They are located by the JSON ``name`` field, not by file name: Creality's bundle, for one, has
files whose names differ from their ``name``. A per-(vendor dir, kind) index is built once per
``resolve_printer_profiles`` call by reading every ``*.json`` (unreadable files are skipped;
two files declaring one ``name`` is an error naming both).

Flattening reproduces ``tmp/lab-station-slicing-v80/prepare_profiles.py``: the ``inherits``
parent first (also resolved by name), then each ``include`` in order, then the profile's own keys
(child wins); ``include`` is dropped and ``inherits`` is blanked. The leaf then gets ``type``,
``name`` and ``from: system``. ``instantiation`` is kept, as v80 kept it.

Compatibility (measured 2026-10-22 on BambuStudio 02.08.02.61 BBL and OrcaSlicer 2.4.2 Creality):
profiles express it as a ``compatible_printers`` list of machine ``name`` strings (BBL 2162
files, Creality 885); empty or absent means any machine. ``compatible_printers_condition`` is
a string that is empty in every profile either bundle resolves to; a non-empty one is not
evaluated here: it is accepted and ``check_compatible`` returns a note for it.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.core.domain.exceptions import DomainError
from src.core.domain.printer_catalog import PrinterProfile
from src.core.domain.slicing import ToolUnavailableError
from src.infrastructure.narrowing import as_sequence, as_str_keyed

KINDS = ("machine", "process", "filament")

Profile = dict[str, object]
_Index = dict[str, list[Path]]


class UnknownProfileError(DomainError):
    """A profile name resolves to no file in the bundle, or to more than one."""


class IncompatibleProfileError(DomainError):
    """A process or filament profile does not declare the chosen machine compatible."""


def app_bundle(binary: Path) -> Path | None:
    """The ``.app`` directory enclosing ``binary``, or None."""
    return next((parent for parent in binary.parents if parent.suffix == ".app"), None)


def profiles_root(binary: Path) -> Path | None:
    bundle = app_bundle(binary)
    return None if bundle is None else bundle / "Contents" / "Resources" / "profiles"


def _read(path: Path) -> dict[str, object] | None:
    try:
        return as_str_keyed(json.loads(path.read_text(encoding="utf-8")), context=path.name)
    except (OSError, ValueError):
        return None


def _build_index(kind_dir: Path) -> tuple[_Index, list[Path]]:
    """``name -> files declaring it`` plus the files whose JSON could not be read.

    Never raises: ambiguity matters only for a name that is actually requested.
    """
    index: _Index = {}
    unreadable: list[Path] = []
    for path in sorted(kind_dir.glob("*.json")):
        data = _read(path)
        if data is None:
            unreadable.append(path)
            continue
        name = data.get("name")
        if isinstance(name, str) and name:
            index.setdefault(name, []).append(path)
    return index, unreadable


class _Bundle:
    """Name index per kind for one vendor directory, built on first use."""

    def __init__(self, vendor_dir: Path) -> None:
        self._vendor_dir = vendor_dir
        self._indexes: dict[str, tuple[_Index, list[Path]]] = {}

    def _index(self, kind: str) -> tuple[_Index, list[Path]]:
        if kind not in self._indexes:
            self._indexes[kind] = _build_index(self._vendor_dir / kind)
        return self._indexes[kind]

    def _locate(self, kind: str, name: str) -> Path:
        index, unreadable = self._index(kind)
        paths = index.get(name, [])
        if len(paths) > 1:
            raise UnknownProfileError(
                f"ambiguous {kind} profile name '{name}': declared by both "
                f"{paths[0].name} and {paths[1].name}"
            )
        if paths:
            return paths[0]
        if unreadable:
            files = ", ".join(p.name for p in unreadable)
            raise ToolUnavailableError(
                f"{kind} profile '{name}' not found, and these files are unreadable and "
                f"may hold it: {files}"
            )
        raise UnknownProfileError(
            f"{kind} profile '{name}' not found in the slicer bundle "
            f"(vendor dir {self._vendor_dir.name}); the app may have renamed it"
        )

    def flatten(self, kind: str, name: str, stack: tuple[str, ...] = ()) -> Profile:
        if name in stack:
            raise ToolUnavailableError(f"profile inheritance cycle: {' -> '.join((*stack, name))}")
        path = self._locate(kind, name)
        data = _read(path)
        if data is None:
            raise ToolUnavailableError(f"{kind} profile '{name}' is unreadable: {path.name}")
        result: Profile = {}
        parent = data.get("inherits")
        if isinstance(parent, str) and parent:
            result.update(self.flatten(kind, parent, (*stack, name)))
        for included in as_sequence(data.get("include")) or ():
            result.update(self.flatten(kind, str(included), (*stack, name)))
        result.update(data)
        result.pop("include", None)
        result["inherits"] = ""
        return result


def _leaf(bundle: _Bundle, kind: str, name: str) -> Profile:
    data = bundle.flatten(kind, name)
    data.update(type=kind, name=name, **{"from": "system"})
    return data


def _lookup(pairs: tuple[tuple[str, str], ...], key: str, what: str, printer_id: str) -> str:
    for candidate, name in pairs:
        if candidate == key:
            return name
    known = ", ".join(candidate for candidate, _ in pairs)
    raise UnknownProfileError(f"printer '{printer_id}' has no {what} '{key}'; it has: {known}")


def resolve_printer_profiles(
    bundle_profiles_root: Path, printer: PrinterProfile, layer_height: str, material: str
) -> dict[str, Profile]:
    """Flattened ``machine``, ``process`` and ``filament`` profiles for ``printer``."""
    bundle = _Bundle(bundle_profiles_root / printer.profile_vendor_dir)
    process = _lookup(printer.processes, layer_height, "layer height", printer.id)
    filament = _lookup(printer.filaments, material, "material", printer.id)
    return {
        "machine": _leaf(bundle, "machine", printer.machine),
        "process": _leaf(bundle, "process", process),
        "filament": _leaf(bundle, "filament", filament),
    }


def _names(value: object) -> list[str]:
    return [str(item) for item in as_sequence(value) or ()]


def _unevaluated(profiles: dict[str, Profile]) -> tuple[str, ...]:
    notes: list[str] = []
    for kind in ("process", "filament"):
        profile = profiles.get(kind)
        for key in ("compatible_printers_condition", "compatible_prints_condition"):
            if profile is not None and profile.get(key):
                notes.append(f"{kind} profile '{profile.get('name')}': {key} not evaluated")
    return tuple(notes)


def check_compatible(profiles: dict[str, Profile], machine_name: str) -> tuple[str, ...]:
    """Refuse a process or filament profile that does not declare ``machine_name`` compatible.

    Returns notes for every non-empty ``*_condition`` string accepted without evaluation.
    """
    for kind in ("process", "filament"):
        profile = profiles.get(kind)
        if profile is None:
            continue
        allowed = _names(profile.get("compatible_printers"))
        if allowed and machine_name not in allowed:
            raise IncompatibleProfileError(
                f"{kind} profile '{profile.get('name')}' does not declare machine "
                f"'{machine_name}' compatible"
            )
    process = profiles.get("process")
    filament = profiles.get("filament")
    if process is not None and filament is not None:
        prints = _names(filament.get("compatible_prints"))
        if prints and process.get("name") not in prints:
            raise IncompatibleProfileError(
                f"filament profile '{filament.get('name')}' does not declare process "
                f"'{process.get('name')}' compatible"
            )
    return _unevaluated(profiles)
