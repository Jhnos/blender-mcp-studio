"""Placed XY extent of a 3MF plate and the printer's printable area (no slicer)."""

from pathlib import Path

import pytest

from src.adapters.slicing.plate_extent import (
    MAX_ARCHIVE_ENTRIES,
    MAX_LAYOUT_WORK,
    MAX_MODEL_BYTES,
    PlateExtentError,
    bed_size,
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


# ---- review round: encodings, broken zips, lying sizes, the real catalog ----

_NS = 'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"'


def _model(prefix: str = "") -> str:
    return (
        prefix + f'<model {_NS}><resources><object id="1"><mesh><vertices>'
        '<vertex x="0" y="0" z="0"/><vertex x="10" y="10" z="0"/></vertices></mesh></object>'
        '</resources><build><item objectid="1"/></build></model>'
    )


def _raw_3mf(path: Path, data: bytes, method: int = 8) -> Path:
    import zipfile

    with zipfile.ZipFile(path, "w", method) as archive:
        archive.writestr("3D/3dmodel.model", data)
    return path


def _patch(path: Path, local_offset: int, central_offset: int, fmt: str, value: int) -> None:
    import struct

    raw = bytearray(path.read_bytes())
    struct.pack_into(fmt, raw, raw.rfind(b"PK\x01\x02") + central_offset, value)
    struct.pack_into(fmt, raw, raw.find(b"PK\x03\x04") + local_offset, value)
    path.write_bytes(bytes(raw))


def test_plate_extent_rejects_non_utf8(tmp_path: Path) -> None:
    # the reviewer's case: a UTF-16 entity declaration slips past a byte-level DTD regex
    u16 = '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE model [<!ENTITY a "aaaa">]>'
    with pytest.raises(PlateExtentError, match="u16.3mf.*not UTF-8"):
        plate_extent(_raw_3mf(tmp_path / "u16.3mf", (u16 + _model()).encode("utf-16")))
    with pytest.raises(PlateExtentError, match="not UTF-8"):  # BOM, no DTD at all
        plate_extent(_raw_3mf(tmp_path / "bom.3mf", b"\xff\xfe" + _model().encode("utf-16-le")))
    with pytest.raises(PlateExtentError, match="not UTF-8"):
        plate_extent(_raw_3mf(tmp_path / "u32.3mf", _model().encode("utf-32")))
    latin = _model('<?xml version="1.0" encoding="ISO-8859-1"?>').encode("latin-1")
    with pytest.raises(PlateExtentError, match="not UTF-8"):
        plate_extent(_raw_3mf(tmp_path / "latin.3mf", latin))
    ok = _model("<?xml version='1.0' encoding='utf-8'?>").encode("utf-8")
    assert plate_extent(_raw_3mf(tmp_path / "ok.3mf", ok)) == pytest.approx((0, 0, 10, 10))
    bom8 = b"\xef\xbb\xbf" + _model('<?xml version="1.0" encoding="UTF-8"?>').encode()
    assert plate_extent(_raw_3mf(tmp_path / "bom8.3mf", bom8)) == pytest.approx((0, 0, 10, 10))


def test_encrypted_member_is_refused(tmp_path: Path) -> None:
    path = _raw_3mf(tmp_path / "enc.3mf", _model().encode())
    raw = bytearray(path.read_bytes())
    raw[raw.rfind(b"PK\x01\x02") + 8] |= 1
    raw[raw.find(b"PK\x03\x04") + 6] |= 1
    path.write_bytes(bytes(raw))
    with pytest.raises(PlateExtentError, match="enc.3mf"):
        plate_extent(path)


def test_unsupported_compression_is_refused(tmp_path: Path) -> None:
    path = _raw_3mf(tmp_path / "meth.3mf", _model().encode())
    _patch(path, 8, 10, "<H", 99)
    with pytest.raises(PlateExtentError, match="meth.3mf"):
        plate_extent(path)


def test_corrupt_deflate_is_refused(tmp_path: Path) -> None:
    import struct

    path = _raw_3mf(tmp_path / "corrupt.3mf", (_model() * 20).encode())
    raw = bytearray(path.read_bytes())
    local = raw.find(b"PK\x03\x04")
    start = local + 30 + struct.unpack_from("<H", raw, local + 26)[0]
    raw[start + 2 : start + 40] = b"\xff" * 38
    path.write_bytes(bytes(raw))
    with pytest.raises(PlateExtentError, match="corrupt.3mf"):
        plate_extent(path)


def test_lying_declared_size_is_refused(tmp_path: Path) -> None:
    path = _raw_3mf(tmp_path / "lie.3mf", _model().encode() + b" " * 5000, method=0)
    _patch(path, 22, 24, "<I", 500)  # declares 500 B; really 5k
    with pytest.raises(PlateExtentError, match="lie.3mf"):
        plate_extent(path, max_model_bytes=1000)


def test_model_read_is_bounded_whatever_the_member_yields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An endless member (a size the zip reader would not stop at) is cut at cap + 1 bytes."""
    import io
    import zipfile

    class Endless(io.RawIOBase):
        def read(self, size: int = -1) -> bytes:
            if size is None or size < 0:
                raise AssertionError("unbounded read of the model part")
            return b" " * size

    path = write_3mf(tmp_path / "e.3mf", [(10, None)])
    monkeypatch.setattr(zipfile.ZipFile, "open", lambda self, name, *a, **k: Endless())
    with pytest.raises(PlateExtentError, match="e.3mf.*exceeds 1000 B"):
        plate_extent(path, max_model_bytes=1000)


def test_every_catalog_printer_resolves_a_printable_area() -> None:
    from src.adapters.slicing.bundle_profiles import app_bundle, resolve_printer_profiles
    from src.infrastructure.printer_catalog_loader import load_printer_catalog
    from src.infrastructure.tools_config import load_tools_config

    catalog, tools = load_printer_catalog(), load_tools_config()
    checked = []
    for printer in catalog.printers:
        slicer = catalog.slicer(printer.slicer)
        bundle = app_bundle(getattr(tools, slicer.binary_key))
        if bundle is None or not (bundle / slicer.profiles_subdir).is_dir():
            continue
        machine = resolve_printer_profiles(bundle / slicer.profiles_subdir, printer, "0.20", "PLA")
        area = printable_area(machine["machine"])
        assert area is not None and area[2] > area[0] and area[3] > area[1], printer.id
        checked.append(printer.id)
    if not checked:
        pytest.skip("no slicer app bundle installed on this host")


def test_bed_size_reads_area_and_height() -> None:
    machine = {"printable_area": ["0x0", "256x0", "256x250", "0x250"], "printable_height": "240"}
    assert bed_size(machine) == (256.0, 250.0, 240.0)


def test_bed_size_is_none_when_height_or_area_is_missing_or_unreadable() -> None:
    area = ["0x0", "10x0", "10x10", "0x10"]
    assert bed_size({"printable_area": area}) is None
    assert bed_size({"printable_area": area, "printable_height": "tall"}) is None
    assert bed_size({"printable_height": "100"}) is None


# --- production extension: components that point at another model part (Bambu layout) ---

_CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
_PROD_NS = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"


def _part(object_id: int, size: float, body: str = "") -> str:
    return (
        f'<model xmlns="{_CORE_NS}"><resources><object id="{object_id}"><mesh><vertices>'
        f'<vertex x="0" y="0" z="0"/><vertex x="{size}" y="{size}" z="1"/></vertices></mesh>'
        f"</object></resources>{body}</model>"
    )


def _root(*components: str) -> str:
    return (
        f'<model xmlns="{_CORE_NS}" xmlns:p="{_PROD_NS}"><resources>'
        f'<object id="9"><components>{"".join(components)}</components></object></resources>'
        '<build><item objectid="9"/></build></model>'
    )


def _production_3mf(path: Path, root: str, parts: dict[str, str]) -> Path:
    import zipfile

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("3D/3dmodel.model", root)
        for name, text in parts.items():
            archive.writestr(name, text)
    return path


def test_production_components_resolve_in_other_parts(tmp_path: Path) -> None:
    root = _root(
        '<component p:path="/3D/Objects/object_1.model" objectid="1"/>',
        '<component p:path="/3D/Objects/object_2.model" objectid="2"'
        ' transform="1 0 0 0 1 0 0 0 1 100 50 0"/>',
    )
    path = _production_3mf(
        tmp_path / "prod.3mf",
        root,
        {"3D/Objects/object_1.model": _part(1, 4), "3D/Objects/object_2.model": _part(2, 6)},
    )
    assert plate_extent(path) == pytest.approx((0, 0, 106, 56))


@pytest.mark.parametrize(
    "bad",
    ["/3D/../secret.model", "/3D" + chr(92) + "o.model", "/3D/Objects/o.xml"],
)
def test_production_path_escape_or_bad_suffix_is_refused(tmp_path: Path, bad: str) -> None:
    root = _root(f'<component p:path="{bad}" objectid="1"/>')
    path = _production_3mf(tmp_path / "esc.3mf", root, {"3D/Objects/o.xml": _part(1, 4)})
    with pytest.raises(PlateExtentError, match="esc.3mf"):
        plate_extent(path)


def test_production_missing_part_is_refused(tmp_path: Path) -> None:
    root = _root('<component p:path="/3D/Objects/nope.model" objectid="1"/>')
    with pytest.raises(PlateExtentError, match="gone.3mf"):
        plate_extent(_production_3mf(tmp_path / "gone.3mf", root, {}))


def test_production_part_with_dtd_is_refused(tmp_path: Path) -> None:
    root = _root('<component p:path="/3D/Objects/o.model" objectid="1"/>')
    path = _production_3mf(
        tmp_path / "dtd.3mf", root, {"3D/Objects/o.model": "<!DOCTYPE x>" + _part(1, 4)}
    )
    with pytest.raises(PlateExtentError, match="dtd.3mf.*DTD"):
        plate_extent(path)


def test_production_cumulative_budget_is_refused(tmp_path: Path) -> None:
    root = _root(
        '<component p:path="/3D/Objects/a.model" objectid="1"/>',
        '<component p:path="/3D/Objects/b.model" objectid="2"/>',
    )
    parts = {"3D/Objects/a.model": _part(1, 4), "3D/Objects/b.model": _part(2, 4)}
    path = _production_3mf(tmp_path / "sum.3mf", root, parts)
    each = max(len(text.encode()) for text in parts.values())
    cap = len(root.encode()) + each + each // 2  # each part alone fits; the sum does not
    with pytest.raises(PlateExtentError, match="sum.3mf.*exceeds"):
        plate_extent(path, max_model_bytes=cap)
    assert plate_extent(path) == pytest.approx((0, 0, 4, 4))


def test_production_part_is_parsed_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import zipfile

    root = _root(
        '<component p:path="/3D/Objects/a.model" objectid="1"/>',
        '<component p:path="/3D/Objects/a.model" objectid="1"'
        ' transform="1 0 0 0 1 0 0 0 1 10 0 0"/>',
    )
    path = _production_3mf(tmp_path / "once.3mf", root, {"3D/Objects/a.model": _part(1, 4)})
    opened: list[str] = []
    real_open = zipfile.ZipFile.open

    def spy(self: zipfile.ZipFile, name: str, *a: object, **k: object) -> object:
        opened.append(str(name))
        return real_open(self, name, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(zipfile.ZipFile, "open", spy)
    assert plate_extent(path) == pytest.approx((0, 0, 14, 4))
    assert opened.count("3D/Objects/a.model") == 1


def test_production_cross_part_cycle_is_refused(tmp_path: Path) -> None:
    root = _root('<component p:path="/3D/Objects/a.model" objectid="1"/>')
    loop = (
        f'<model xmlns="{_CORE_NS}" xmlns:p="{_PROD_NS}"><resources><object id="1"><components>'
        '<component p:path="/3D/Objects/a.model" objectid="1"/></components></object>'
        "</resources></model>"
    )
    path = _production_3mf(tmp_path / "loop.3mf", root, {"3D/Objects/a.model": loop})
    with pytest.raises(PlateExtentError, match="loop.3mf"):
        plate_extent(path)


def _fan_out_part(levels: int, fan: int) -> str:
    """Object k holds ``fan`` components to object k+1; the last object is a 2-vertex mesh."""
    objects = [
        f'<object id="{k}"><components>'
        + f'<component objectid="{k + 1}"/>' * fan
        + "</components></object>"
        for k in range(1, levels)
    ]
    leaf = (
        f'<object id="{levels}"><mesh><vertices><vertex x="0" y="0" z="0"/>'
        '<vertex x="1" y="1" z="1"/></vertices></mesh></object>'
    )
    return f'<model xmlns="{_CORE_NS}"><resources>{"".join(objects)}{leaf}</resources></model>'


def test_component_fan_out_is_refused_by_the_work_cap(tmp_path: Path) -> None:
    """A few hundred bytes that expand to 10**6 visits must stop at the default work cap."""
    root = _root('<component p:path="/3D/Objects/fan.model" objectid="1"/>')
    parts = {"3D/Objects/fan.model": _fan_out_part(levels=7, fan=10)}
    path = _production_3mf(tmp_path / "fan.3mf", root, parts)
    assert MAX_LAYOUT_WORK < 10**6
    with pytest.raises(PlateExtentError, match="fan.3mf.*exceeds .* units of layout work"):
        plate_extent(path)


def test_too_many_archive_entries_are_refused(tmp_path: Path) -> None:
    root = _root('<component p:path="/3D/Objects/o.model" objectid="1"/>')
    parts = {"3D/Objects/o.model": _part(1, 4)}
    parts.update({f"Metadata/x{i}.png": "" for i in range(MAX_ARCHIVE_ENTRIES)})
    path = _production_3mf(tmp_path / "many.3mf", root, parts)
    with pytest.raises(PlateExtentError, match="many.3mf.*entries"):
        plate_extent(path)


_V92_NAME = Path("models") / "lab-station-v92" / "P2S-PLA-76件單盤-已切片-v92.3mf"
_V92 = next(
    (p / _V92_NAME for p in Path(__file__).resolve().parents if (p / _V92_NAME).is_file()), None
)


@pytest.mark.skipif(_V92 is None, reason="v92 deliverable absent on this host")
def test_plate_extent_real_v92_production_layout_fits_p2s() -> None:
    assert _V92 is not None
    extent = plate_extent(_V92)
    print(f"v92 extent: {extent}")
    min_x, min_y, max_x, max_y = extent
    assert 0 <= min_x < max_x <= 256 and 0 <= min_y < max_y <= 256
