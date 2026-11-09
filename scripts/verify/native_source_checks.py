"""Independent oracles for the current selection: its native provenance (file identity only)
and the print target it resolves to.

Split from ``design_gate_checks`` (file budget); that module re-exports both checks.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from src.core.domain.model_spec import ModelSpecError, parse_print_target
from src.infrastructure.narrowing import as_mapping, as_sequence


def check_native_source(root: Path, spec: Mapping[str, object], receipt: object) -> list[str]:
    """Independent public-receipt oracle, reading actual selected files, not the adapter.

    This establishes file identity only. No historical names, part counts, hashes or
    manufacturing claims are hard-coded, and no Blender operation is performed.
    """
    native = as_mapping(receipt)
    if native is None or native.get("available") is not True:
        return ["selected native provenance is unavailable; no historical fallback"]
    try:
        source = as_mapping(spec["source"])
        if source is None:
            raise ValueError("missing source")
        relative = Path(str(source["root_dir"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("non-relative selected root")
        selected = root / relative

        def safe_file(name: str) -> Path:
            path = selected / name
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError("non-relative manifest asset")
            for ancestor in (path, *path.parents):
                if ancestor == root:
                    break
                if ancestor.is_symlink():
                    raise ValueError("symlinked source")
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError("source outside artifact root")
            return path

        raw = safe_file("SHA256.json").read_bytes()
        manifest = as_mapping(json.loads(raw))
        if not manifest:
            raise ValueError("empty manifest")
        actual: dict[str, object] = {}
        total_bytes = 0
        for name, expected in manifest.items():
            path = safe_file(name)
            with path.open("rb") as handle:
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
            if not isinstance(expected, str) or digest != expected.lower():
                raise ValueError("local manifest checksum mismatch")
            size = path.stat().st_size
            total_bytes += size
            actual[name] = {"path": name, "sha256": digest, "size_bytes": size}
        natives = [name for name in manifest if Path(name).suffix.lower() == ".blend"]
        if len(natives) != 1:
            raise ValueError("ambiguous native")
        parts = [
            p.relative_to(selected).as_posix()
            for p in sorted(selected.glob(str(source["stl_glob"])))
            if p.is_file()
        ]
        if not parts:
            raise ValueError("empty selected parts")
        project_name = source.get("project_3mf")
        if not isinstance(project_name, str) or project_name not in actual:
            raise ValueError("selected project must be in the source manifest")
        expected_receipt = {
            "scope": "file_identity_only",
            "available": True,
            "model_name": spec["name"],
            "root_dir": relative.as_posix(),
            "native": actual[natives[0]],
            "parts": [actual[name] for name in parts],
            "project_3mf": actual[project_name],
            "manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "verified_files": len(manifest),
            "total_bytes": total_bytes,
        }
        observed = dict(native)
        observed["parts"] = list(as_sequence(native.get("parts")) or ())
        return [
            f"native provenance disagrees with selected files: {field}"
            for field, value in expected_receipt.items()
            if observed.get(field) != value
        ]
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        return ["selected native source cannot be independently verified"]


def check_selected_target(spec: Mapping[str, object], expected: object) -> list[str]:
    """The selection must name its printer and material, and resolve to the contract's.

    A spec-v1 printer name is translated to its catalog id by the parser; a selection that
    leaves either out is a failure (the gate never assumes the legacy machine).
    """
    want = as_mapping(expected) or {}
    named = as_mapping(spec.get("print_target")) or {}
    missing = [key for key in ("printer", "material") if key not in named]
    if missing:
        return [f"selected spec names no print_target {', '.join(missing)}; a gate assumes none"]
    try:
        target = parse_print_target(spec)
    except ModelSpecError as exc:
        return [f"selected spec print_target: {exc}"]
    got = {"printer": target.printer, "material": target.material}
    wanted = {key: want.get(key) for key in got}
    return [] if got == wanted else [f"selected delivery targets {got}; contract expects {wanted}"]
