import struct

import pytest

from src.verification.artifact_files import binary_stl_metrics


def test_binary_stl_metrics_read_millimetres_without_blender() -> None:
    record = struct.pack("<12fH", 0, 0, 1, 0, 0, 0, 35, 0, 0, 0, 42.2, 28.6, 0)
    payload = bytes(80) + struct.pack("<I", 1) + record

    metrics = binary_stl_metrics(payload)

    assert metrics.triangle_count == 1
    assert metrics.dimensions_mm == pytest.approx((35.0, 42.2, 28.6))


@pytest.mark.parametrize("payload", [b"", bytes(84), bytes(80) + struct.pack("<I", 2)])
def test_empty_or_truncated_stl_is_not_an_acceptable_artifact(payload: bytes) -> None:
    with pytest.raises(ValueError, match="STL"):
        binary_stl_metrics(payload)


def test_binary_stl_surface_preserves_close_vertices_and_indexes_only_exact_duplicates() -> None:
    from src.verification.artifact_files import binary_stl_surface

    a, b, c, d = (0, 0, 0), (1, 0, 0), (0, 1, 0), (1e-9, 0, 0)
    payload = bytes(80) + struct.pack("<I", 2)
    for triangle in ((a, b, c), (d, c, b)):
        payload += struct.pack("<12fH", 0, 0, 1, *(v for p in triangle for v in p), 0)
    surface = binary_stl_surface(payload)
    assert surface["faces"] == [(0, 1, 2), (3, 2, 1)]
    assert len(surface["vertices"]) == 4
    assert surface["vertices"][3][0] == pytest.approx(1e-9)


@pytest.mark.parametrize("payload", [b"", bytes(84), bytes(80) + struct.pack("<I", 2)])
def test_binary_stl_surface_rejects_empty_or_truncated_payload(payload: bytes) -> None:
    from src.verification.artifact_files import binary_stl_surface

    with pytest.raises(ValueError, match="STL"):
        binary_stl_surface(payload)


def test_binary_stl_surface_rejects_nonfinite_coordinates() -> None:
    from src.verification.artifact_files import binary_stl_surface

    record = struct.pack("<12fH", 0, 0, 1, float("nan"), 0, 0, 1, 0, 0, 0, 1, 0, 0)
    with pytest.raises(ValueError, match="non-finite"):
        binary_stl_surface(bytes(80) + struct.pack("<I", 1) + record)
