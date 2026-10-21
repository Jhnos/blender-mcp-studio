"""Machine-readable model specification for the design pipeline (spec version 1)."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from src.core.domain.exceptions import DomainError

SUPPORTED_SPEC_VERSION = "1"


class ModelSpecError(DomainError):
    """A model spec payload is malformed, unsupported or points outside allowed roots."""


@dataclass(frozen=True, slots=True)
class PrintTarget:
    printer: str = "bambu-p2s"
    material: str = "PLA"
    layer_height_mm: float = 0.2
    support: bool = True
    brim_mm: float = 3.0


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
    print_target: PrintTarget = field(default_factory=PrintTarget)
    mechanism: MechanismChecks = field(default_factory=MechanismChecks)


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


def _reject_unknown(section: Mapping[str, object], allowed: set[str], where: str) -> None:
    unknown = sorted((k for k in section if k not in allowed), key=str)
    if unknown:
        raise ModelSpecError(f"unknown keys in {where}: {', '.join(map(str, unknown))}")


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


def _is_hidden(parts: tuple[str, ...]) -> bool:
    """A part starting with ``.`` (.env, .git, .venv, .claude); the bare ``.`` is not hidden."""
    return any(part.startswith(".") and part != "." for part in parts)


def _contained_relative(
    value: str, field_name: str, base: Path | None = None, *, suffix: str
) -> str:
    """Reject empty, absolute, ``..``, hidden, wrong-suffix and symlink-escaping paths.

    Only print inputs are readable: ``suffix`` is a literal, case-insensitive end of the value.
    """
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ModelSpecError(f"source.{field_name} must be a relative path inside the artifact")
    if _is_hidden(path.parts):
        raise ModelSpecError(f"source.{field_name} must not contain hidden path parts")
    if not value.lower().endswith(suffix):
        raise ModelSpecError(f"source.{field_name} must end in {suffix}")
    if base is not None and not (base / value).resolve().is_relative_to(base):
        raise ModelSpecError(f"source.{field_name} resolves outside the artifact root")
    return value


def _resolve_root(root_dir: str, artifact_roots: tuple[Path, ...]) -> str:
    if not root_dir:
        raise ModelSpecError("source.root_dir must not be empty")
    for root in artifact_roots:
        base = root.resolve()
        candidate = (base / root_dir).resolve()
        if candidate.is_relative_to(base):
            if _is_hidden(candidate.relative_to(base).parts):
                raise ModelSpecError("source.root_dir must not contain hidden path parts")
            return str(candidate)
    raise ModelSpecError("source.root_dir is outside the allowed artifact roots")


def _parse_source(payload: Mapping[str, object], roots: tuple[Path, ...]) -> ImportedArtifact:
    src = _section(payload, "source", required=True)
    _reject_unknown(src, {"root_dir", "stl_glob", "project_3mf"}, "source")
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


def _parse_print_target(payload: Mapping[str, object]) -> PrintTarget:
    sec = _section(payload, "print_target", required=False)
    _reject_unknown(
        sec, {"printer", "material", "layer_height_mm", "support", "brim_mm"}, "print_target"
    )
    d = PrintTarget()
    return PrintTarget(
        printer=_str(sec, "printer", d.printer),
        material=_str(sec, "material", d.material),
        layer_height_mm=_physical(sec, "layer_height_mm", d.layer_height_mm, positive=True),
        support=_bool(sec, "support", d.support),
        brim_mm=_physical(sec, "brim_mm", d.brim_mm, positive=False),
    )


def _parse_mechanism(payload: Mapping[str, object]) -> MechanismChecks:
    sec = _section(payload, "mechanism", required=False)
    _reject_unknown(sec, {"suites"}, "mechanism")
    suites = sec.get("suites", ())
    if isinstance(suites, str) or not isinstance(
        suites, (list, tuple)
    ):  # narrow-ok: elements checked below
        raise ModelSpecError("mechanism.suites must be a list of strings")
    checked = tuple(s for s in suites if isinstance(s, str) and s)
    if len(checked) != len(suites):
        raise ModelSpecError("mechanism.suites must be a list of strings")
    return MechanismChecks(suites=checked)


def parse_model_spec(
    payload: Mapping[str, object], *, artifact_roots: tuple[Path, ...]
) -> ModelSpec:
    """Validate ``payload`` and resolve its artifact root inside ``artifact_roots``."""
    _reject_unknown(
        payload, {"spec_version", "name", "source", "print_target", "mechanism"}, "spec"
    )
    if "spec_version" not in payload:
        raise ModelSpecError("missing spec_version")
    if payload.get("spec_version") != SUPPORTED_SPEC_VERSION:
        raise ModelSpecError(f"unsupported spec_version: {payload.get('spec_version')!r}")
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ModelSpecError("name must be a non-empty string")
    return ModelSpec(
        spec_version=SUPPORTED_SPEC_VERSION,
        name=name,
        source=_parse_source(payload, artifact_roots),
        print_target=_parse_print_target(payload),
        mechanism=_parse_mechanism(payload),
    )
