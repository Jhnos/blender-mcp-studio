"""Placed XY extent of a 3MF plate and the printer's printable area (no slicer)."""

from pathlib import Path

import pytest

from src.adapters.slicing.plate_extent import (
    MAX_MODEL_BYTES,
    PlateExtentError,
    plate_extent,
    printable_area,
)
from tests.fakes.plate_3mf import translate, write_3mf


def test_plate_extent_uses_build_transforms(tmp_path: Path) -> None:
    path = write_3mf(tmp_path / "p.3mf", [(10, translate(5, 7)), (20, translate(100, 200))])
    assert plate_extent(path) == pytest.approx((5, 7, 120, 220))


def test_plate_extent_applies_rotation_to_vertices(tmp_path: Path) -> None:
    # 90 degrees about z: (x, y) -> (-y, x), then moved by (50, 0)
    path = write_3mf(tmp_path / "p.3mf", [(10, "0 1 0 -1 0 0 0 0 1 50 0 0")])
    assert plate_extent(path) == pytest.approx((40, 0, 50, 10))


def test_plate_extent_without_transform_is_identity(tmp_path: Path) -> None:
    assert plate_extent(write_3mf(tmp_path / "p.3mf", [(30, None)])) == pytest.approx(
        (0, 0, 30, 30)
    )


def test_plate_extent_follows_components(tmp_path: Path) -> None:
    import zipfile

    ns = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    model = (
        f'<model xmlns="{ns}"><resources>'
        '<object id="1"><mesh><vertices><vertex x="0" y="0" z="0"/>'
        '<vertex x="4" y="4" z="1"/></vertices></mesh></object>'
        '<object id="2"><components><component objectid="1" transform="1 0 0 0 1 0 0 0 1 10 0 0"/>'
        "</components></object></resources>"
        '<build><item objectid="2" transform="1 0 0 0 1 0 0 0 1 0 20 0"/></build></model>'
    )
    path = tmp_path / "c.3mf"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("3D/3dmodel.model", model)
    assert plate_extent(path) == pytest.approx((10, 20, 14, 24))


def test_unreadable_plate_raises_named_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.3mf"
    bad.write_bytes(b"not a zip")
    with pytest.raises(PlateExtentError, match="bad.3mf"):
        plate_extent(bad)
    with pytest.raises(PlateExtentError):
        plate_extent(tmp_path / "missing.3mf")


def _model_3mf(path: Path, model: str) -> Path:
    import zipfile

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("3D/3dmodel.model", model)
    return path


_BOMB = (
    '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
    '<!ENTITY lol2 "&lol;&lol;&lol;&lol;">]><model>&lol2;</model>'
)


def test_plate_extent_rejects_doctype(tmp_path: Path) -> None:
    path = _model_3mf(tmp_path / "d.3mf", '<?xml version="1.0"?><!doctype model><model/>')
    with pytest.raises(PlateExtentError, match="d.3mf.*DTD"):
        plate_extent(path)


def test_plate_extent_rejects_entity(tmp_path: Path) -> None:
    with pytest.raises(PlateExtentError, match="b.3mf.*DTD"):
        plate_extent(_model_3mf(tmp_path / "b.3mf", _BOMB))
    # an ENTITY after harmless text, in any case, is still refused
    late = "<model>" + "x" * 5000 + "<!EnTiTy y 'z'></model>"
    with pytest.raises(PlateExtentError, match="DTD"):
        plate_extent(_model_3mf(tmp_path / "late.3mf", late))


def test_plate_extent_rejects_oversized_model(tmp_path: Path) -> None:
    path = write_3mf(tmp_path / "big.3mf", [(10, None)] * 20)
    with pytest.raises(PlateExtentError, match="big.3mf.*exceeds 100 B"):
        plate_extent(path, max_model_bytes=100)


_V78_NAME = Path("雙上臂四點梯形-v78") / "整機69件-單盤排版-v78.3mf"
# The deliverable sits at the main checkout root; a worktree is nested below it.
_V78 = next(
    (p / _V78_NAME for p in Path(__file__).resolve().parents if (p / _V78_NAME).is_file()), None
)


@pytest.mark.skipif(_V78 is None, reason="v78 deliverable absent on this host")
def test_plate_extent_real_v78_within_cap() -> None:
    import zipfile

    assert _V78 is not None
    with zipfile.ZipFile(_V78) as archive:
        assert archive.getinfo("3D/3dmodel.model").file_size <= MAX_MODEL_BYTES
    min_x, min_y, max_x, max_y = plate_extent(_V78)
    assert (round(max_x - min_x), round(max_y - min_y)) == (241, 241)


def test_printable_area_is_the_bounding_box_of_its_points() -> None:
    assert printable_area({"printable_area": ["0x0", "220x0", "220x220", "0x220"]}) == (
        0.0,
        0.0,
        220.0,
        220.0,
    )
    assert printable_area({}) is None
    assert printable_area({"printable_area": ["junk"]}) is None
