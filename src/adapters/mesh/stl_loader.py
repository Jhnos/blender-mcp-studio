"""The one place that decides whether an STL file is a readable, non-empty triangle mesh."""

from __future__ import annotations

import struct
from pathlib import Path

import trimesh

# trimesh 5.1.1 defines no load-specific exception type; STL parsing surfaces these.
_LOAD_ERRORS = (OSError, ValueError, EOFError, struct.error)


def load_stl(path: Path | str) -> trimesh.Trimesh:
    """Load an STL or raise ValueError with a reason that carries no path prefix."""
    try:
        # An open handle makes a missing file a clean OSError (a path string plus
        # file_type= is treated as a file object and fails with AttributeError).
        with open(path, "rb") as handle:
            mesh = trimesh.load(handle, file_type="stl", force="mesh")
    except _LOAD_ERRORS as exc:
        raise ValueError(f"cannot read STL: {exc}") from exc
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f"loaded {type(mesh).__name__}, expected a triangle mesh")
    if len(mesh.faces) == 0:
        raise ValueError("STL has no triangles")
    return mesh
