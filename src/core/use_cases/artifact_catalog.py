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

import asyncio
import copy
import itertools
import os
from collections.abc import Callable, Iterator, Mapping
from dataclasses import asdict
from pathlib import Path

from src.core.domain.model_spec import (
    ImportedArtifact,
    ModelSpec,
    ModelSpecError,
    is_hidden_path,
    parse_model_spec,
)
from src.core.domain.model_spec_schema import describe_model_spec
from src.core.domain.native_revision import NativeModelSource, NativeSourceError
from src.core.ports.native_source_port import NativeSourcePort
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


def _is_selected_file(path: Path, root: Path) -> bool:
    return (
        path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root.resolve())
    )


def list_artifacts(
    roots: tuple[Path, ...], *, max_stl_files: int, selected_spec: Mapping[str, object]
) -> dict[str, object]:
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
    default_spec = copy.deepcopy(dict(selected_spec))
    selected_source = as_mapping(default_spec["source"])
    assert selected_source is not None
    selected = next((r for r in rows if r["root_dir"] == selected_source["root_dir"]), None)
    target = anchors[0] / str(selected_source["root_dir"])
    project = target / str(selected_source["project_3mf"])
    stl_glob = str(selected_source.get("stl_glob", ImportedArtifact(root_dir="").stl_glob))
    if selected is None:
        _, files = _entries(target)
        if (
            target.is_dir()
            and not target.is_symlink()
            and (
                any(_is_selected_file(path, target) for path in target.glob(stl_glob))
                or _is_selected_file(project, target)
            )
        ):
            counts, capped = _stl_dirs(target, max_stl_files)
            selected = {
                "root_dir": selected_source["root_dir"],
                "stl_dirs": counts,
                "stl_count_capped": capped,
                "project_3mf": [f.name for f in files if f.suffix.lower() == ".3mf"],
            }
            rows.insert(0, selected)
            truncated = truncated or len(rows) > MAX_ENTRIES
            rows = rows[:MAX_ENTRIES]
    if selected is not None and _is_selected_file(project, target):
        projects = list(as_sequence(selected["project_3mf"]) or ())
        if selected_source["project_3mf"] not in projects:
            projects.append(selected_source["project_3mf"])
        selected["project_3mf"] = projects
    available = bool(
        selected
        and _is_selected_file(project, target)
        and any(_is_selected_file(path, target) for path in target.glob(stl_glob))
    )
    rows.sort(key=lambda r: r["root_dir"] != selected_source["root_dir"])
    return {
        "artifacts": rows,
        "truncated": truncated,
        "default_spec": default_spec,
        "default_available": available,
    }


class ArtifactCatalog:
    """One injected current-selection policy, shared by all delivery paths."""

    def __init__(
        self,
        roots: tuple[Path, ...],
        max_stl_files: int,
        selected_spec: Callable[[], Mapping[str, object]],
        *,
        native_sources: NativeSourcePort | None = None,
    ) -> None:
        self._roots = roots
        self._cap = max_stl_files
        self._selected_spec = selected_spec
        self._native_sources = native_sources

    def _parse_selection(self, selected: Mapping[str, object]) -> ModelSpec:
        parsed = parse_model_spec(selected, artifact_roots=self._roots)
        source = as_mapping(selected["source"])
        assert source is not None
        if Path(str(source["root_dir"])).is_absolute():
            raise ModelSpecError("selected model root_dir must be relative")
        if not parsed.source.project_3mf:
            raise ModelSpecError("selected model must declare project_3mf")
        return parsed

    def current(self) -> dict[str, object]:
        selected = copy.deepcopy(dict(self._selected_spec()))
        self._parse_selection(selected)
        return selected

    async def native_description_for(
        self, selected: Mapping[str, object]
    ) -> dict[str, object] | None:
        """Identity for the exact discovery snapshot; never consult the provider twice."""
        if self._native_sources is None:
            return None
        description: dict[str, object] = {"scope": "file_identity_only"}
        try:
            _, source = await self.native_source_for(selected)
        except NativeSourceError as exc:
            description.update(available=False, reason=str(exc))
        else:
            description.update(asdict(source))
            description["available"] = True
        return description

    async def native_source_for(
        self, selected: Mapping[str, object]
    ) -> tuple[ModelSpec, NativeModelSource]:
        """Resolve typed provenance from the captured selection, never query it again."""
        if self._native_sources is None:
            raise NativeSourceError("native source resolution is not configured")
        spec = await asyncio.to_thread(self._parse_selection, selected)
        source = await self._native_sources.resolve(spec)
        if source.model_name != spec.name:
            raise NativeSourceError("native provenance disagrees with selected model")
        return spec, source

    async def discover(self) -> dict[str, object]:
        catalog = await asyncio.to_thread(self.list)
        selected = as_mapping(catalog["default_spec"])
        assert selected is not None
        native = await self.native_description_for(selected)
        if native is not None:
            catalog["default_native"] = native
        return catalog

    def describe(self, printers: tuple[str, ...], materials: tuple[str, ...]) -> dict[str, object]:
        return describe_model_spec(printers, materials, self.current())

    def list(self) -> dict[str, object]:
        return list_artifacts(self._roots, max_stl_files=self._cap, selected_spec=self.current())
