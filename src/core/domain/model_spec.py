"""Machine-readable model specification for the design pipeline (spec versions 1 and 2).

Spec v2 names its printer and material explicitly. Spec v1 predates the printer catalog: a
missing printer/material is filled from the one legacy machine v1 always meant, and the parse
records that so the run report can say so. Nothing else in the domain chooses a machine.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from src.core.domain.exceptions import DomainError

SUPPORTED_SPEC_VERSIONS = ("1", "2")
#: What a spec v1 without ``print_target.printer`` / ``.material`` always meant.
LEGACY_V1_PRINTER = "bambu-p2s-0.4"
LEGACY_V1_MATERIAL = "PLA"
#: Spec v1 printer names -> catalog ids (v1 vocabulary translation; v2 names catalog ids only).
V1_PRINTER_IDS: dict[str, str] = {"bambu-p2s": LEGACY_V1_PRINTER}
SPEC_KEYS = ("spec_version", "name", "source", "print_target", "mechanism")
SOURCE_KEYS = ("root_dir", "stl_glob", "project_3mf")
PRINT_TARGET_KEYS = ("printer", "material", "layer_height_mm", "support", "brim_mm")
MECHANISM_KEYS = ("suites",)
MECHANISM_V1_UNSUPPORTED = (
    "mechanism suites are not supported in spec v1: Phase 1 verifies imported artifacts "
    "only; suites run against the open Blender scene, not this model"
)


class ModelSpecError(DomainError):
    """A model spec payload is malformed, unsupported or points outside allowed roots."""


@dataclass(frozen=True, slots=True)
class PrintTarget:
    printer: str
    material: str
    layer_height_mm: float = 0.2
    support: bool = True
    brim_mm: float = 3.0


#: Job parameters only (layer height, support, brim); printer and material are never defaulted.
JOB_DEFAULTS = PrintTarget(printer="", material="")


@dataclass(frozen=True, slots=True)
class ImportedArtifact:
    root_dir: str
    stl_glob: str = "STL/*.stl"
    project_3mf: str | None = None


@dataclass(frozen=True, slots=True)
class MechanismChecks:
    suites: tuple[str, ...] = ()  # registered suite ids; () = declared not applicable


@dataclass(frozen=True, slots=True)
class ModelSpec:
    spec_version: str
    name: str
    source: ImportedArtifact
    print_target: PrintTarget
    mechanism: MechanismChecks = field(default_factory=MechanismChecks)
    #: ``(field, value)`` pairs a spec v1 left out and the legacy defaults filled in.
    legacy_defaults: tuple[tuple[str, str], ...] = ()

    @property
    def legacy_default(self) -> bool:
        return bool(self.legacy_defaults)


def _section(payload: Mapping[str, object], key: str, *, required: bool) -> Mapping[str, object]:
    value = payload.get(key)
    if value is None:
        if required:
            raise ModelSpecError(f"missing required section: {key}")
        return {}
    if not isinstance(
        value, Mapping
    ):  # narrow-ok: values are re-checked per field; keys by _reject_unknown
        raise ModelSpecError(f"{key} must be an object")
    return value


def _reject_unknown(section: Mapping[str, object], allowed: tuple[str, ...], where: str) -> None:
    unknown = sorted((k for k in section if k not in allowed), key=str)
    if unknown:
        raise ModelSpecError(
            f"unknown keys in {where}: {', '.join(map(str, unknown))} "
            f"(allowed: {', '.join(allowed)})"
        )


def _str(section: Mapping[str, object], key: str, default: str) -> str:
    value = section.get(key, default)
    if not isinstance(value, str):
        raise ModelSpecError(f"{key} must be str")
    return value


def _bool(section: Mapping[str, object], key: str, default: bool) -> bool:
    value = section.get(key, default)
    if not isinstance(value, bool):
        raise ModelSpecError(f"{key} must be bool")
    return value


def _float(section: Mapping[str, object], key: str, default: float) -> float:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ModelSpecError(f"{key} must be a number")
    return float(value)


def _physical(section: Mapping[str, object], key: str, default: float, *, positive: bool) -> float:
    value = _float(section, key, default)
    if not math.isfinite(value) or (value <= 0 if positive else value < 0):
        bound = "> 0" if positive else ">= 0"
        raise ModelSpecError(f"{key} must be finite and {bound}")
    return value


def is_hidden_path(parts: tuple[str, ...]) -> bool:
    """A part starting with ``.`` (.env, .git, .venv, .claude); the bare ``.`` is not hidden."""
    return any(part.startswith(".") and part != "." for part in parts)


def _check_relative(value: str, label: str, suffix: str) -> None:
    """The syntactic half of the path gate: relative, no ``..``, not hidden, right suffix."""
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ModelSpecError(f"{label} must be a relative path inside the artifact")
    if is_hidden_path(path.parts):
        raise ModelSpecError(f"{label} must not contain hidden path parts")
    if not value.lower().endswith(suffix):
        raise ModelSpecError(f"{label} must end in {suffix}")


def _contained_relative(
    value: str, field_name: str, base: Path | None = None, *, suffix: str
) -> str:
    """Reject empty, absolute, ``..``, hidden, wrong-suffix and symlink-escaping paths.

    Only print inputs are readable: ``suffix`` is a literal, case-insensitive end of the value.
    """
    label = f"source.{field_name}"
    _check_relative(value, label, suffix)
    if base is not None and not (base / value).resolve().is_relative_to(base):
        raise ModelSpecError(f"{label} resolves outside the artifact root")
    return value


def resolve_artifact_file(path: str, *, suffix: str, roots: tuple[Path, ...]) -> Path:
    """Resolve a caller-supplied ``path`` to an existing file inside one of ``roots``.

    The one gate for paths a remote host hands us (MCP tools): the same syntactic rules as the
    ModelSpec parser, then ``resolve().is_relative_to(root)`` (symlinks) and no hidden part in
    the resolved path. Messages never contain a host path.
    """
    _check_relative(path, "path", suffix)
    escaped = False
    for root in roots:
        base = root.resolve()
        candidate = (base / path).resolve()
        if not candidate.is_relative_to(base):
            escaped = True
            continue
        if is_hidden_path(candidate.relative_to(base).parts):
            raise ModelSpecError("path must not contain hidden path parts")
        if candidate.is_file():
            return candidate
    if escaped:
        raise ModelSpecError("path resolves outside the artifact root")
    raise ModelSpecError("path not found in the allowed artifact roots")


def _resolve_root(root_dir: str, artifact_roots: tuple[Path, ...]) -> str:
    if not root_dir:
        raise ModelSpecError("source.root_dir must not be empty")
    for root in artifact_roots:
        base = root.resolve()
        candidate = (base / root_dir).resolve()
        if candidate.is_relative_to(base):
            if is_hidden_path(candidate.relative_to(base).parts):
                raise ModelSpecError("source.root_dir must not contain hidden path parts")
            return str(candidate)
    raise ModelSpecError("source.root_dir is outside the allowed artifact roots")


def _parse_source(payload: Mapping[str, object], roots: tuple[Path, ...]) -> ImportedArtifact:
    src = _section(payload, "source", required=True)
    _reject_unknown(src, SOURCE_KEYS, "source")
    root_dir = src.get("root_dir")
    if not isinstance(root_dir, str):
        raise ModelSpecError("source.root_dir must be str")
    project = src.get("project_3mf")
    if project is not None and not isinstance(project, str):
        raise ModelSpecError("source.project_3mf must be str")
    resolved = _resolve_root(root_dir, roots)
    return ImportedArtifact(
        root_dir=resolved,
        stl_glob=_contained_relative(_str(src, "stl_glob", "STL/*.stl"), "stl_glob", suffix=".stl"),
        project_3mf=(
            None
            if project is None
            else _contained_relative(project, "project_3mf", Path(resolved), suffix=".3mf")
        ),
    )


def _parse_print_target(
    payload: Mapping[str, object], version: str
) -> tuple[PrintTarget, tuple[tuple[str, str], ...]]:
    v2 = version == "2"
    sec = _section(payload, "print_target", required=False)  # v2: its keys are required below
    _reject_unknown(sec, PRINT_TARGET_KEYS, "print_target")
    legacy: list[tuple[str, str]] = []
    chosen: dict[str, str] = {}
    for key, fallback in (("printer", LEGACY_V1_PRINTER), ("material", LEGACY_V1_MATERIAL)):
        if key in sec:
            chosen[key] = _str(sec, key, "")
        elif v2:
            raise ModelSpecError(f"print_target.{key} is required in spec v2")
        else:
            chosen[key] = fallback
            legacy.append((key, fallback))
    printer = chosen["printer"] if v2 else V1_PRINTER_IDS.get(chosen["printer"], chosen["printer"])
    d = JOB_DEFAULTS
    target = PrintTarget(
        printer=printer,
        material=chosen["material"],
        layer_height_mm=_physical(sec, "layer_height_mm", d.layer_height_mm, positive=True),
        support=_bool(sec, "support", d.support),
        brim_mm=_physical(sec, "brim_mm", d.brim_mm, positive=False),
    )
    return target, tuple(legacy)


def _parse_mechanism(payload: Mapping[str, object]) -> MechanismChecks:
    sec = _section(payload, "mechanism", required=False)
    _reject_unknown(sec, MECHANISM_KEYS, "mechanism")
    suites = sec.get("suites", ())
    if isinstance(suites, str) or not isinstance(
        suites, (list, tuple)
    ):  # narrow-ok: elements checked below
        raise ModelSpecError("mechanism.suites must be a list of strings")
    checked = tuple(s for s in suites if isinstance(s, str) and s)
    if len(checked) != len(suites):
        raise ModelSpecError("mechanism.suites must be a list of strings")
    if checked:
        raise ModelSpecError(MECHANISM_V1_UNSUPPORTED)
    return MechanismChecks(suites=checked)


def parse_print_target(payload: Mapping[str, object]) -> PrintTarget:
    """Only the spec's ``print_target``, read exactly as ``parse_model_spec`` reads it."""
    version = payload.get("spec_version")
    if not isinstance(version, str) or version not in SUPPORTED_SPEC_VERSIONS:
        raise ModelSpecError(f"unsupported spec_version: {version!r}")
    return _parse_print_target(payload, version)[0]


def parse_model_spec(
    payload: Mapping[str, object], *, artifact_roots: tuple[Path, ...]
) -> ModelSpec:
    """Validate ``payload`` and resolve its artifact root inside ``artifact_roots``."""
    _reject_unknown(payload, SPEC_KEYS, "spec")
    if "spec_version" not in payload:
        raise ModelSpecError("missing spec_version")
    version = payload.get("spec_version")
    if not isinstance(version, str) or version not in SUPPORTED_SPEC_VERSIONS:
        raise ModelSpecError(
            f"unsupported spec_version: {version!r} (supported: "
            f"{', '.join(map(repr, SUPPORTED_SPEC_VERSIONS))})"
        )
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ModelSpecError("name must be a non-empty string")
    target, legacy = _parse_print_target(payload, version)
    return ModelSpec(
        spec_version=version,
        name=name,
        source=_parse_source(payload, artifact_roots),
        print_target=target,
        mechanism=_parse_mechanism(payload),
        legacy_defaults=legacy,
    )
