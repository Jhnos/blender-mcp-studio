"""A printer whose bundle profiles cannot be read is unavailable, not usable with null facts."""

from __future__ import annotations

from tests.fakes.design_ports import FakeSlicing
from tests.unit.core.test_design_pipeline import _rig

P2S, K1C = "bambu-p2s-0.4", "creality-k1c-0.4"


def _unreadable(tmp_path):
    rig = _rig(tmp_path)
    rig.slicing = FakeSlicing(rig.lease, printer_ids=(P2S, K1C))
    rig.pipeline._slicing = rig.slicing
    reason = f"process profile 'Bad @K1C' not found under {rig.runs}/bundle"
    rig.slicing.unreadable = {K1C: reason}
    return rig


async def test_unreadable_bundle_lists_the_printer_as_unavailable(tmp_path):
    rig = _unreadable(tmp_path)
    listing = await rig.pipeline.list_printers()
    assert [e.printer.id for e in listing.printers] == [P2S]
    (gone,) = [u for u in listing.unavailable if u.printer_id == K1C]
    assert "'Bad @K1C'" in gone.reason
    assert str(tmp_path) not in gone.reason  # scrubbed like every other exit


def test_unreadable_bundle_is_left_out_of_the_schema(tmp_path):
    rig = _unreadable(tmp_path)
    target = rig.pipeline.describe_spec()["schema"]["properties"]["print_target"]
    assert target["properties"]["printer"]["enum"] == [P2S]
    assert [r["if"]["properties"]["printer"]["const"] for r in target["allOf"]] == [P2S]
