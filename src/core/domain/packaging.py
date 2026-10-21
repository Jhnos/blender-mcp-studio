"""Immutable description of a run's delivered files."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PackagedFile:
    # POSIX path relative to the run directory, so the package is portable across hosts.
    path: str
    sha256: str
    bytes: int
    # Face count for STL files; None for every other file type.
    triangles: int | None


@dataclass(frozen=True, slots=True)
class ToolUse:
    """An external tool the run used, with the licence under which it was used."""

    name: str
    version: str | None
    license: str
    # How it was run, e.g. "subprocess" (black box) or "library".
    invocation: str


@dataclass(frozen=True, slots=True)
class PackageManifest:
    run_id: str
    spec_name: str
    files: tuple[PackagedFile, ...]
    # Absolute path of the written manifest.json (a return value, not file content).
    manifest_path: str
    tools: tuple[ToolUse, ...] = ()
