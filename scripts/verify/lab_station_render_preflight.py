"""Check workstation render inputs inside Blender or during offline composition."""

import json
from hashlib import file_digest, sha256
from pathlib import Path

from src.infrastructure.config_loader import load_selected_model_spec
from src.infrastructure.narrowing import as_finite_number, as_mapping


def review_source_differences(
    native: object, frame: object, expected_native: object, expected_frame: float
) -> list[str]:
    return [
        field
        for field, observed, expected in (
            ("native_sha256", native, expected_native),
            ("frame", as_finite_number(frame), expected_frame),
        )
        if observed != expected
    ]


def require_review_source(
    native: str, frame: float, *, expected_native: object, expected_frame: object
) -> None:
    """Compare the loaded source and evaluated frame to the selected review case."""
    verified_frame = as_finite_number(expected_frame)
    if verified_frame is None or verified_frame < 1:
        raise ValueError("review preflight has an invalid expected frame")
    differences = review_source_differences(native, frame, expected_native, verified_frame)
    if differences:
        raise ValueError(f"review preflight differs in {', '.join(differences)}")


def read_review_input(path: Path, expected_sha256: object, label: str) -> bytes:
    """Return the exact bytes checked against an independently selected receipt."""
    data = path.read_bytes()
    if sha256(data).hexdigest() != expected_sha256:
        raise ValueError(f"review preflight {label} SHA-256 differs from selected receipt")
    return data


def selected_review_native_sha256(root: Path) -> str:
    """Resolve the expected formal source independently of the open Blender file."""
    return selected_review_native(root)[1]


def selected_review_native(root: Path) -> tuple[Path, str]:
    """Return the verified native path and SHA-256 from the current selection."""
    spec = load_selected_model_spec(root)
    source = as_mapping(spec.get("source"))
    if source is None or not isinstance(root_dir := source.get("root_dir"), str):
        raise ValueError("review preflight requires a selected source directory")
    selected = root / root_dir
    manifest = as_mapping(json.loads((selected / "SHA256.json").read_bytes()))
    if manifest is None:
        raise ValueError("review preflight requires a selected source manifest")
    entries = [(name, digest) for name, digest in manifest.items() if name.endswith(".blend")]
    if len(entries) != 1:
        raise ValueError("review preflight requires one selected native source")
    name, digest = entries[0]
    if not isinstance(digest, str):
        raise ValueError("review preflight has no selected native SHA-256")
    with (selected / name).open("rb") as stream:
        if file_digest(stream, "sha256").hexdigest() != digest:
            raise ValueError("review preflight selected native SHA-256 differs from manifest")
    return selected / name, digest
