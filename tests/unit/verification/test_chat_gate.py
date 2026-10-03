"""The real chat gate must fail the process for false or incomplete evidence."""

import pytest

from scripts.verify import mcp_verify_chat as gate


@pytest.mark.parametrize("created,vertices", [(False, "8"), (True, "7"), (True, "8")])
def test_main_requires_all_five_measured_checks(monkeypatch, created, vertices):
    names = iter([[], ["verify_12345"] if created else [], [], []])
    monkeypatch.setattr(gate, "o_names", lambda: next(names))
    monkeypatch.setattr(gate, "teardown", lambda: None)
    monkeypatch.setattr(gate.random, "randint", lambda *_: 12345)
    monkeypatch.setattr(gate.time, "sleep", lambda _: None)
    monkeypatch.setattr(gate, "ws_chat", lambda _: ("done", "cube created", "session"))
    monkeypatch.setattr(gate, "o_stdout", lambda _: vertices)
    monkeypatch.setattr(gate, "rest", lambda *_: (200, {"objects": [{"name": "verify_12345"}]}))
    if created and vertices == "8":
        gate.main()
    else:
        with pytest.raises(ValueError, match="Chat verification"):
            gate.main()
