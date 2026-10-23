"""Candidate deliverable directories under the artifact roots (what ``source.root_dir`` can be).

A candidate is a directory one or two levels below a root that directly holds ``.stl`` files or
a ``.3mf``; directories below a candidate belong to it. Hidden (``.``-prefixed) and symlinked
directories are never entered, so nothing outside a root is listed. Each entry carries only
root-relative text: ``root_dir`` (relative to the first root that holds it, the one
``parse_model_spec`` resolves against), the STL count per subdirectory (``.`` = the candidate
itself, counted at most ``max_stl_files`` per candidate) and the 3MF file names. At most
``MAX_ENTRIES`` entries are returned.
"""

from __future__ import annotations

import copy
import itertools
import os
from collections.abc import Iterator
from pathlib import Path

from src.core.domain.model_spec import is_hidden_path
from src.core.domain.model_spec_schema import V1_EXAMPLE
from src.infrastructure.narrowing import as_mapping, as_sequence

MAX_ENTRIES = 200
CANDIDATE_DEPTH = 2
#: How far below a candidate STLs are counted (v78 keeps them at STL/<group>/*.stl).
STL_SCAN_DEPTH = 3


def _entries(directory: Path) -> tuple[list[Path], list[Path]]:
    """(subdirectories, files) directly in ``directory``; hidden names and symlinks skipped."""
    dirs: list[Path] = []
    found: list[Path] = []
    try:
        children = sorted(os.scandir(directory), key=lambda e: e.name)
    except OSError:
        return [], []
    for child in children:
        if child.name.startswith(".") or child.is_symlink():
            continue
        if child.is_dir(follow_symlinks=False):
            dirs.append(Path(child.path))
        elif child.is_file(follow_symlinks=False):
            found.append(Path(child.path))
    return dirs, found


def _is_candidate(files: list[Path]) -> bool:
    return any(f.suffix.lower() in (".stl", ".3mf") for f in files)


def _stl_dirs(candidate: Path, cap: int) -> tuple[dict[str, int], bool]:
    counts: dict[str, int] = {}
    total = 0
    level = [candidate]
    for _ in range(STL_SCAN_DEPTH + 1):
        nxt: list[Path] = []
        for directory in level:
            dirs, found = _entries(directory)
            stls = sum(1 for f in found if f.suffix.lower() == ".stl")
            if stls:
                take = min(stls, cap - total)
                counts[directory.relative_to(candidate).as_posix()] = take
                total += take
                if total >= cap:
                    return counts, True
            nxt.extend(dirs)
        level = nxt
    return counts, False


def _candidates(anchors: list[Path]) -> Iterator[tuple[Path, Path, list[Path]]]:
    """(directory, its anchor, its files) breadth-first; a candidate's subtree is not re-entered."""
    seen: set[Path] = set()
    for anchor in anchors:
        level = [anchor]
        for _ in range(CANDIDATE_DEPTH):
            nxt: list[Path] = []
            for directory in level:
                for sub in _entries(directory)[0]:
                    resolved = sub.resolve()
                    files = _entries(sub)[1]
                    if not _is_candidate(files):
                        nxt.append(sub)
                    elif resolved not in seen:
                        seen.add(resolved)
                        base = next(a for a in anchors if resolved.is_relative_to(a))
                        if not is_hidden_path(resolved.relative_to(base).parts):
                            yield sub, base, files
            level = nxt


def list_artifacts(roots: tuple[Path, ...], *, max_stl_files: int) -> dict[str, object]:
    """Blocking directory scan; see the module docstring for what is listed."""
    anchors = [root.resolve() for root in roots]
    rows: list[dict[str, object]] = []
    found = _candidates(anchors)
    for sub, base, files in itertools.islice(found, MAX_ENTRIES):
        stl_dirs, capped = _stl_dirs(sub, max_stl_files)
        rows.append(
            {
                "root_dir": sub.resolve().relative_to(base).as_posix(),
                "stl_dirs": stl_dirs,
                "stl_count_capped": capped,
                "project_3mf": [f.name for f in files if f.suffix.lower() == ".3mf"],
            }
        )
    truncated = next(found, None) is not None
    default_spec = copy.deepcopy(V1_EXAMPLE)
    selected_source = as_mapping(default_spec["source"])
    assert selected_source is not None
    selected = next((r for r in rows if r["root_dir"] == selected_source["root_dir"]), None)
    available = bool(
        selected
        and selected["stl_dirs"]
        and selected_source["project_3mf"] in (as_sequence(selected["project_3mf"]) or ())
    )
    rows.sort(key=lambda r: r["root_dir"] != selected_source["root_dir"])
    return {
        "artifacts": rows,
        "truncated": truncated,
        "default_spec": default_spec,
        "default_available": available,
    }
