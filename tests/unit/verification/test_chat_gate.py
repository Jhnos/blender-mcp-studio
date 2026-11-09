"""The real chat gate must fail the process for false or incomplete evidence."""

import pytest

from scripts.verify import mcp_verify_chat as gate


@pytest.mark.parametrize("created,vertices", [(False, "8"), (True, "7"), (True, "8")])
def test_main_requires_all_five_measured_checks(monkeypatch, created, vertices):
    names = iter([[], ["verify_12345"] if created else [], [], []])
    monkeypatch.setattr(gate, "o_names", lambda: next(names))
    monkeypatch.setattr(gate, "teardown", lambda: None)
    monkeypatch.setattr(gate, "ollama_target", lambda: ("model", "http://ollama"))
    monkeypatch.setattr(gate, "wait_for_ollama", lambda *_, **__: 0.0)
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


# ---------------------------------------------------------------- readiness wait
# Observed 2026-10-20: the chat gate failed as "Ollama unreachable" while the
# shared Ollama on this Mac was alive and queuing our request for 300 s behind
# another tailnet client's multi-minute completions. A bounded wait with a
# heartbeat names the real precondition instead of blaming the chat path.


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def test_wait_returns_on_the_first_answered_probe(capsys):
    clock = _Clock()
    elapsed = gate.wait_for_ollama(
        lambda _timeout: 2.5, budget_s=60, pause_s=15, clock=clock, sleep=clock.sleep
    )
    assert elapsed == 2.5
    assert clock.now == 0.0
    assert capsys.readouterr().out.count("ollama probe attempt") == 1


def test_wait_keeps_probing_with_a_heartbeat_until_an_answer(capsys):
    clock = _Clock()
    answers = iter([None, None, 4.0])
    elapsed = gate.wait_for_ollama(
        lambda _timeout: next(answers), budget_s=600, pause_s=15, clock=clock, sleep=clock.sleep
    )
    assert elapsed == 4.0
    assert clock.now == 30.0
    out = capsys.readouterr().out
    assert out.count("ollama probe attempt") == 3
    assert "no successful response" in out


def test_wait_fails_as_a_precondition_once_the_budget_is_spent(capsys):
    clock = _Clock()
    calls = 0

    def never(_timeout: float) -> None:
        nonlocal calls
        calls += 1
        clock.now += 60.0  # each probe burns its own attempt timeout
        return None

    with pytest.raises(RuntimeError, match="shared Ollama") as caught:
        gate.wait_for_ollama(never, budget_s=120, pause_s=15, clock=clock, sleep=clock.sleep)
    assert "cause undetermined" in str(caught.value)
    assert calls == 2
    assert capsys.readouterr().out.count("ollama probe attempt") == 2


def test_main_runs_the_readiness_wait_before_touching_blender(monkeypatch):
    """Wiring proof: a spent budget must stop the gate before any oracle call,
    so a saturated shared Ollama is reported as the precondition it is."""
    touched: list[str] = []
    monkeypatch.setattr(gate, "ollama_target", lambda: ("model", "http://ollama"))
    monkeypatch.setattr(gate, "teardown", lambda: touched.append("teardown"))
    monkeypatch.setattr(gate, "o_names", lambda: touched.append("oracle") or [])

    def spent(*_args, **_kwargs):
        raise RuntimeError("precondition: shared Ollama did not answer")

    monkeypatch.setattr(gate, "wait_for_ollama", spent)
    with pytest.raises(RuntimeError, match="precondition"):
        gate.main()
    assert touched == []


def test_probe_reports_http_status_instead_of_calling_it_a_timeout(monkeypatch, capsys):
    import io
    import urllib.error

    def rejected(*_args, **_kwargs):
        raise urllib.error.HTTPError(
            "http://ollama/api/generate", 404, "Not Found", {}, io.BytesIO(b"model missing")
        )

    monkeypatch.setattr(gate.urllib.request, "urlopen", rejected)
    assert gate.ollama_probe("http://ollama", "missing", 60) is None
    out = capsys.readouterr().out
    assert "HTTP 404" in out
    assert "model missing" in out
