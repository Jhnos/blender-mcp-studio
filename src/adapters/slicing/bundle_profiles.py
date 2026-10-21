"""Vendor slicer profiles read from the installed BambuStudio.app (never vendored in the repo).

``config/slicer-profiles/p2s-pla-profiles.json`` names the three leaf profiles inside
``<App>.app/Contents/Resources/profiles/``; ``<App>.app`` is the bundle enclosing the configured
binary. Flattening reproduces ``tmp/lab-station-slicing-v80/prepare_profiles.py``: the
``inherits`` parent first, then each ``include`` in order, then the profile's own keys (child
wins); ``include`` is dropped and ``inherits`` is blanked. The leaf then gets ``type``, ``name``
and ``from: system``. ``instantiation`` is kept, as v80 kept it.
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

from src.core.domain.slicing import ToolUnavailableError
from src.infrastructure.narrowing import as_sequence, as_str_keyed

LEAVES_FILE = "p2s-pla-profiles.json"
KINDS = ("machine", "process", "filament")


def app_bundle(binary: Path) -> Path | None:
    """The ``.app`` directory enclosing ``binary``, or None."""
    return next((parent for parent in binary.parents if parent.suffix == ".app"), None)


def profiles_root(binary: Path) -> Path | None:
    bundle = app_bundle(binary)
    return None if bundle is None else bundle / "Contents" / "Resources" / "profiles"


def _load(path: Path) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ToolUnavailableError(
            f"Bambu Studio profile {path.name} is unreadable: {type(exc).__name__}"
        ) from exc
    data = as_str_keyed(raw, context=path.name)
    if data is None:
        raise ToolUnavailableError(f"Bambu Studio profile {path.name} is not an object")
    return data


def _resolve(kind_dir: Path, name: str, stack: tuple[str, ...]) -> dict[str, object]:
    if name in stack:
        raise ToolUnavailableError(f"profile inheritance cycle: {' -> '.join((*stack, name))}")
    data = _load(kind_dir / f"{name}.json")
    result: dict[str, object] = {}
    parent = data.get("inherits")
    if isinstance(parent, str) and parent:
        result.update(_resolve(kind_dir, parent, (*stack, name)))
    includes = data.get("include")
    for included in as_sequence(includes) or ():
        result.update(_resolve(kind_dir, str(included), (*stack, name)))
    result.update(data)
    result.pop("include", None)
    result["inherits"] = ""
    return result


def flatten_leaf(root: Path, leaf: str) -> dict[str, object]:
    """Flatten ``<vendor>/<kind>/<name>.json`` under ``root`` into one full profile."""
    parts = PurePosixPath(leaf).parts
    if len(parts) != 3 or parts[1] not in KINDS or not parts[2].endswith(".json"):
        raise ToolUnavailableError(f"bad leaf profile name in {LEAVES_FILE}: {leaf}")
    vendor, kind, file_name = parts
    name = file_name.removesuffix(".json")
    data = _resolve(root / vendor / kind, name, ())
    data.update(type=kind, name=name, **{"from": "system"})
    return data


def leaf_names(config_dir: Path) -> dict[str, str]:
    """``{kind: "<vendor>/<kind>/<name>.json"}`` from the repository's own data file."""
    data = _load(config_dir / LEAVES_FILE)
    names = {kind: data.get(kind) for kind in KINDS}
    missing = [kind for kind, value in names.items() if not isinstance(value, str)]
    if missing:
        raise ToolUnavailableError(f"{LEAVES_FILE} names no {', '.join(missing)} profile")
    return {kind: str(value) for kind, value in names.items()}


def bundle_profiles(binary: Path, config_dir: Path) -> dict[str, dict[str, object]]:
    """The three flattened profiles for ``binary``'s bundle; ToolUnavailableError if absent."""
    root = profiles_root(binary)
    if root is None or not root.is_dir():
        raise ToolUnavailableError(
            "Bambu Studio is installed but its app bundle has no profiles directory "
            "(Contents/Resources/profiles); reinstall BambuStudio.app."
        )
    return {kind: flatten_leaf(root, leaf) for kind, leaf in leaf_names(config_dir).items()}
