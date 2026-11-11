import sys
from hashlib import sha256
from pathlib import Path
from shutil import copyfile
from types import SimpleNamespace

import pytest

from scripts.verify.lab_station_render_preflight import read_review_input, require_review_source


def test_render_preflight_binds_native_and_exact_frame() -> None:
    r2 = sha256(b"r2 assembly").hexdigest()
    r4 = sha256(b"r4 assembly").hexdigest()
    require_review_source(r2, 1453, expected_native=r2, expected_frame=1453)
    require_review_source(r4, 2025, expected_native=r4, expected_frame=2025)

    with pytest.raises(ValueError, match="native_sha256"):
        require_review_source(r2, 2025, expected_native=r4, expected_frame=2025)
    with pytest.raises(ValueError, match="frame"):
        require_review_source(r4, 2497, expected_native=r4, expected_frame=2025)


def test_composite_preflight_rejects_same_name_image_swap(tmp_path: Path) -> None:
    before, after = (tmp_path / key / "USB-top.png" for key in ("625", "542"))
    for path, data in ((before, b"625 mm route"), (after, b"542 mm route")):
        path.parent.mkdir()
        path.write_bytes(data)
    before_sha, after_sha = (sha256(path.read_bytes()).hexdigest() for path in (before, after))
    assert read_review_input(before, before_sha, "625 mm") == b"625 mm route"
    assert read_review_input(after, after_sha, "542 mm") == b"542 mm route"
    with pytest.raises(ValueError, match="625 mm"):
        read_review_input(after, before_sha, "625 mm")
    with pytest.raises(ValueError, match="542 mm"):
        read_review_input(before, after_sha, "542 mm")


def test_tracked_render_entry_rejects_wrong_native_and_frame(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import ec78_review_render as entry

    root = Path(__file__).resolve().parents[3]
    (r4,) = (root / "models/lab-station-ec78-r4").glob("*.blend")
    historical = tmp_path / "EC78-同源操作總成-r2候選.blend"
    historical.write_bytes(b"historical r2 source stand-in")
    calls: list[Path] = []
    scene = SimpleNamespace(frame_current_final=1.0)

    def set_frame(frame: int, *, subframe: float) -> None:
        scene.frame_current_final = frame + subframe

    scene.frame_set = set_frame
    data = SimpleNamespace(filepath=str(r4), is_dirty=False)
    monkeypatch.setitem(
        sys.modules,
        "bpy",
        SimpleNamespace(
            app=SimpleNamespace(background=True), context=SimpleNamespace(scene=scene), data=data
        ),
    )
    monkeypatch.setattr(entry, "_render_link_images", calls.append)
    output = tmp_path / "links"

    def run(source: Path, frame: int) -> int:
        data.filepath = str(source)
        return entry.main(["links", "--frame", str(frame), "--output", str(output)])

    assert run(r4, 2025) == 0
    assert calls == [output]
    calls.clear()
    with pytest.raises(ValueError, match="native_sha256"):
        run(historical, 2025)
    with pytest.raises(ValueError, match="frame"):
        run(r4, 2497)
    assert calls == []
    assert not output.exists()


def test_tracked_composition_entry_rejects_swapped_same_name_pngs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import ec78_review_render as entry

    root = Path(__file__).resolve().parents[3]
    selected = root / "models/lab-station-ec78-r4"
    name = "HMI-USB低位固定-60度-後蓋90度-俯視.png"
    original, shortened = (tmp_path / slot / name for slot in ("625", "542"))
    # Use two distinct, checked-in PNGs as stand-ins for the unpublished USB views.
    for path, image in zip((original, shortened), sorted(selected.glob("*.png"))[:2], strict=True):
        path.parent.mkdir()
        copyfile(image, path)
    expected = tuple(sha256(p.read_bytes()).hexdigest() for p in (original, shortened))
    monkeypatch.setattr(entry, "USB_VIEW_SHA256", expected)
    calls: list[tuple[bytes, bytes, Path]] = []
    output = tmp_path / "comparison.png"

    def compose(left: bytes, right: bytes, path: Path) -> None:
        calls.append((left, right, path))

    monkeypatch.setattr(entry, "_write_usb_comparison", compose)

    def run(left: Path, right: Path) -> int:
        return entry.main(
            ["usb", "--original", str(left), "--shortened", str(right), "--output", str(output)]
        )

    assert run(original, shortened) == 0
    assert calls == [(original.read_bytes(), shortened.read_bytes(), output)]
    calls.clear()
    with pytest.raises(ValueError, match="625 mm"):
        run(shortened, original)
    with pytest.raises(ValueError, match="542 mm"):
        run(original, original)
    assert calls == []
    assert not output.exists()
