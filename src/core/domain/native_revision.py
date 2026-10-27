"""Immutable identity receipts for native revision inputs; no geometry qualification."""

from collections.abc import Mapping
from dataclasses import dataclass

from src.core.domain.exceptions import DomainError
from src.core.domain.lab_station_joints import ScreenFoldSpec
from src.core.domain.model_spec import ModelSpec
from src.core.domain.screen_clamp import ScreenClampSpec


class NativeRevisionError(DomainError):
    """A registered native revision cannot meet its declared contract."""


class NativeSourceError(NativeRevisionError):
    """The selected native input lacks coherent, complete provenance."""


SCREEN_CLAMP_RECIPE = "screen-clamp"


@dataclass(frozen=True, slots=True)
class NativeRevisionRequest:
    recipe_id: str
    target_angle_deg: float = 0.0

    def __post_init__(self) -> None:
        if self.recipe_id != SCREEN_CLAMP_RECIPE:
            raise NativeRevisionError("unknown native revision recipe")
        if type(self.target_angle_deg) not in (int, float):
            raise NativeRevisionError("target angle must be a finite indexed angle")
        try:
            _ = self.clamp
        except (ValueError, OverflowError) as exc:
            raise NativeRevisionError(
                "target angle must be a finite indexed angle from 0 to 60"
            ) from exc

    @property
    def clamp(self) -> ScreenClampSpec:
        return ScreenClampSpec(
            sequence=ScreenFoldSpec(
                release_mm=2.2, screw_mm=2.4, target_angle_deg=float(self.target_angle_deg)
            )
        )


def parse_native_revision(payload: Mapping[str, object]) -> NativeRevisionRequest:
    if set(payload) - {"recipe_id", "target_angle_deg"}:
        raise NativeRevisionError(
            "unknown native revision fields; only recipe and angle are allowed"
        )
    recipe, angle = payload.get("recipe_id"), payload.get("target_angle_deg", 0.0)
    if (
        not isinstance(recipe, str)
        or not isinstance(angle, (int, float))
        or isinstance(angle, bool)
    ):
        raise NativeRevisionError("native revision requires a registered recipe and numeric angle")
    return NativeRevisionRequest(recipe, angle)


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


@dataclass(frozen=True, slots=True)
class CapturedNativeRevision:
    spec: ModelSpec
    request: NativeRevisionRequest
    source: NativeModelSource


@dataclass(frozen=True, slots=True)
class PreparedNativeRevision:
    spec: ModelSpec
    request: NativeRevisionRequest
    staged: StagedNativeSource


@dataclass(frozen=True, slots=True)
class NativeStlSet:
    source: NativeModelSource
    native: SourceArtifact
    parts: tuple[SourceArtifact, ...]
    changed_paths: tuple[str, ...]


class NativeSceneError(NativeRevisionError):
    """A verified native input cannot be isolated or saved safely."""


class NativeSceneRestorationError(NativeSceneError):
    """Original data or context did not survive a native operation unchanged."""


@dataclass(frozen=True, slots=True)
class NativeRevisionResult:
    prepared: PreparedNativeRevision
    directory: str
    native: SourceArtifact
    surfaces: SourceArtifact


@dataclass(frozen=True, slots=True)
class NativePrintProduct:
    directory: str  # relative to the configured job root
    stls: NativeStlSet
    project: SourceArtifact  # relative to directory
