"""A release must bind its verification evidence to exact source and image bytes."""

import hashlib
import json

import pytest

from scripts import package_living_feedback as publisher


def verified_fixture(path):
    (path / "source.blend").write_bytes(b"editable source")
    (path / "frame.png").write_bytes(b"verified pixel bytes")

    def sha(name):
        return hashlib.sha256((path / name).read_bytes()).hexdigest()

    report = {
        "passed": True,
        "source_sha256": sha("source.blend"),
        "images": [{"file": "frame.png", "sha256": sha("frame.png"), "rerender_equal": True}],
    }
    (path / "verification.json").write_text(json.dumps(report))
    return report


def test_verified_bytes_are_accepted(tmp_path):
    verified_fixture(tmp_path)
    publisher.verify_source(tmp_path, "source.blend", "images", ["frame.png"])


@pytest.mark.parametrize(
    "defect", ["image", "blend", "missing", "duplicate", "failure", "rerender"]
)
def test_stale_or_incomplete_evidence_blocks_publish(tmp_path, defect):
    report = verified_fixture(tmp_path)
    if defect == "image":
        (tmp_path / "frame.png").write_bytes(b"changed")
    elif defect == "blend":
        (tmp_path / "source.blend").write_bytes(b"changed")
    elif defect == "missing":
        report["images"] = []
    elif defect == "duplicate":
        report["images"].append(report["images"][0])
    elif defect == "failure":
        report["passed"] = False
    else:
        report["images"][0]["rerender_equal"] = False
    (tmp_path / "verification.json").write_text(json.dumps(report))
    with pytest.raises(ValueError):
        publisher.verify_source(tmp_path, "source.blend", "images", ["frame.png"])
