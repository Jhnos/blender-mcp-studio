"""Immutable identity receipts for native revision inputs; no geometry qualification."""

from dataclasses import dataclass

from src.core.domain.exceptions import DomainError


class NativeRevisionError(DomainError):
    """A registered native revision cannot meet its declared contract."""


class NativeSourceError(NativeRevisionError):
    """The selected native input lacks coherent, complete provenance."""


@dataclass(frozen=True, slots=True)
class SourceArtifact:
    path: str  # canonical path relative to the selected model root
    sha256: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class NativeModelSource:
    model_name: str
    root_dir: str  # relative to an approved artifact root, never a host path
    native: SourceArtifact
    parts: tuple[SourceArtifact, ...]
    project_3mf: SourceArtifact | None
    manifest_sha256: str
    verified_files: int
    total_bytes: int = 0  # aggregate verified assets, excluding the manifest itself


@dataclass(frozen=True, slots=True)
class StagedNativeSource:
    source: NativeModelSource
    directory: str  # relative to the configured job root; no host path in receipts


class NativeSceneError(NativeRevisionError):
    """A verified native input cannot be isolated or saved safely."""


class NativeSceneRestorationError(NativeSceneError):
    """Original data or context did not survive a native operation unchanged."""
