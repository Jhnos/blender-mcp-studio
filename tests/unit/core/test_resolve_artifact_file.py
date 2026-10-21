"""The one path gate for caller-supplied files (shared by the ModelSpec parser and MCP tools)."""

from __future__ import annotations

import pytest

from src.core.domain.model_spec import ModelSpecError, resolve_artifact_file


def _tree(tmp_path):
    root = tmp_path / "root"
    (root / "STL").mkdir(parents=True)
    (root / "STL" / "a.stl").write_bytes(b"x")
    (root / "p.3mf").write_bytes(b"x")
    (root / ".hid").mkdir()
    (root / ".hid" / "h.stl").write_bytes(b"x")
    return root


def test_resolves_inside_root(tmp_path):
    root = _tree(tmp_path)
    got = resolve_artifact_file("STL/a.stl", suffix=".stl", roots=(root,))
    assert got == (root / "STL" / "a.stl").resolve()


def test_second_root_is_searched(tmp_path):
    root = _tree(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    got = resolve_artifact_file("p.3mf", suffix=".3mf", roots=(other, root))
    assert got == (root / "p.3mf").resolve()


@pytest.mark.parametrize(
    ("value", "suffix", "needle"),
    [
        ("../root/STL/a.stl", ".stl", "relative"),
        ("/etc/passwd.stl", ".stl", "relative"),
        ("", ".stl", "relative"),
        (".hid/h.stl", ".stl", "hidden"),
        ("STL/a.stl", ".3mf", "must end in .3mf"),
        ("STL/missing.stl", ".stl", "not found"),
    ],
)
def test_rejects_bad_paths_without_host_path(tmp_path, value, suffix, needle):
    root = _tree(tmp_path)
    with pytest.raises(ModelSpecError, match=needle) as err:
        resolve_artifact_file(value, suffix=suffix, roots=(root,))
    assert str(tmp_path) not in str(err.value)


def test_rejects_symlink_escape(tmp_path):
    root = _tree(tmp_path)
    secret = tmp_path / "secret.stl"
    secret.write_bytes(b"x")
    (root / "STL" / "link.stl").symlink_to(secret)
    with pytest.raises(ModelSpecError, match="outside") as err:
        resolve_artifact_file("STL/link.stl", suffix=".stl", roots=(root,))
    assert str(tmp_path) not in str(err.value)


def test_rejects_symlink_into_hidden_part(tmp_path):
    root = _tree(tmp_path)
    (root / "STL" / "viahidden.stl").symlink_to(root / ".hid" / "h.stl")
    with pytest.raises(ModelSpecError, match="hidden"):
        resolve_artifact_file("STL/viahidden.stl", suffix=".stl", roots=(root,))
