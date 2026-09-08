"""The framework's first claim: it reproduces the shipped V3 package, face for face.

STL export is not byte-reproducible (the same generator run twice gave three
different hashes out of four files), so the differential does not compare
hashes. It compares what the package test already pins: triangle count exactly,
bounding dimensions within 0.1 mm. The manifest is the expectation source, so
the differential does not introduce a second table of numbers.

Every should-pass case here has a should-fire twin. A differential that only
has passing fixtures is indistinguishable from one that always passes.
"""

import struct

import pytest

from src.verification.package_reproduction import (
    ExpectedMesh,
    ReproductionReport,
    compare_mesh,
    expected_from_manifest,
    reproduction_report,
)


def _stl(triangle_count: int, dimensions: tuple[float, float, float]) -> bytes:
    """A binary STL whose bounding box and triangle count are exactly as asked."""
    assert triangle_count >= 1
    x, y, z = dimensions
    header = b"\0" * 80 + struct.pack("<I", triangle_count)
    span = struct.pack("<12fH", 0, 0, 0, 0, 0, 0, x, y, z, 0, 0, 0, 0)
    filler = struct.pack("<12fH", 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0)
    return header + span + filler * (triangle_count - 1)


MANIFEST = {
    "files": {
        "phalanx_mm.stl": {"triangle_count": 3434, "dimensions_mm": [24.0, 22.0, 67.0], "sha256": "x"},
        "palm_mm.stl": {"triangle_count": 2686, "dimensions_mm": [140.0, 44.0, 103.5], "sha256": "y"},
        "finger_v3.blend": {"sha256": "z"},
    }
}


def test_the_manifest_is_the_only_expectation_source() -> None:
    expected = expected_from_manifest(MANIFEST, ("phalanx_mm.stl", "palm_mm.stl"))

    assert expected == {
        "phalanx_mm.stl": ExpectedMesh("phalanx_mm.stl", 3434, (24.0, 22.0, 67.0)),
        "palm_mm.stl": ExpectedMesh("palm_mm.stl", 2686, (140.0, 44.0, 103.5)),
    }


def test_a_listed_stl_the_manifest_never_measured_is_refused() -> None:
    with pytest.raises(ValueError, match="finger_v3.blend"):
        expected_from_manifest(MANIFEST, ("finger_v3.blend",))


def test_an_stl_the_manifest_does_not_mention_is_refused() -> None:
    with pytest.raises(ValueError, match="hand_v3_mm.stl"):
        expected_from_manifest(MANIFEST, ("hand_v3_mm.stl",))


def test_the_same_faces_and_size_pass() -> None:
    verdict = compare_mesh(
        ExpectedMesh("phalanx_mm.stl", 3434, (24.0, 22.0, 67.0)),
        _stl(3434, (24.0000105, 22.0000038, 67.0)),
    )

    assert verdict.passed
    assert verdict.measured_triangles == 3434


def test_one_triangle_more_fires() -> None:
    verdict = compare_mesh(
        ExpectedMesh("phalanx_mm.stl", 3434, (24.0, 22.0, 67.0)),
        _stl(3435, (24.0, 22.0, 67.0)),
    )

    assert not verdict.passed
    assert "3435" in verdict.reason and "3434" in verdict.reason


def test_a_dimension_off_by_two_tenths_fires_and_one_tenth_does_not() -> None:
    expected = ExpectedMesh("palm_mm.stl", 2686, (140.0, 44.0, 103.5))

    assert compare_mesh(expected, _stl(2686, (140.0, 44.0, 103.58))).passed
    assert not compare_mesh(expected, _stl(2686, (140.0, 44.0, 103.72))).passed


def test_a_missing_regenerated_file_is_a_failure_that_names_it() -> None:
    expected = ExpectedMesh("palm_mm.stl", 2686, (140.0, 44.0, 103.5))

    verdict = compare_mesh(expected, None)

    assert not verdict.passed
    assert "palm_mm.stl" in verdict.reason and "missing" in verdict.reason


def test_a_corrupt_payload_is_a_failure_not_an_exception() -> None:
    expected = ExpectedMesh("palm_mm.stl", 2686, (140.0, 44.0, 103.5))

    verdict = compare_mesh(expected, b"not an stl")

    assert not verdict.passed
    assert "palm_mm.stl" in verdict.reason


def test_the_report_fails_closed_on_an_empty_population() -> None:
    report = reproduction_report({}, {})

    assert isinstance(report, ReproductionReport)
    assert not report.passed
    assert "vacuous" in report.summary


def test_the_report_passes_only_when_every_file_does() -> None:
    expected = expected_from_manifest(MANIFEST, ("phalanx_mm.stl", "palm_mm.stl"))
    good = {
        "phalanx_mm.stl": _stl(3434, (24.0, 22.0, 67.0)),
        "palm_mm.stl": _stl(2686, (140.0, 44.0, 103.5)),
    }

    assert reproduction_report(expected, good).passed
    one_bad = good | {"palm_mm.stl": _stl(2687, (140.0, 44.0, 103.5))}
    report = reproduction_report(expected, one_bad)
    assert not report.passed
    assert [v.name for v in report.verdicts if not v.passed] == ["palm_mm.stl"]


def test_a_regenerated_file_nobody_expected_is_reported_not_ignored() -> None:
    expected = expected_from_manifest(MANIFEST, ("phalanx_mm.stl",))
    payloads = {
        "phalanx_mm.stl": _stl(3434, (24.0, 22.0, 67.0)),
        "extra_mm.stl": _stl(10, (1.0, 1.0, 1.0)),
    }

    report = reproduction_report(expected, payloads)

    assert report.passed
    assert "extra_mm.stl" in report.summary
