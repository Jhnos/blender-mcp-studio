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
