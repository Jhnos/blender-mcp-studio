"""REST verification must preserve other jobs' fixtures, including on failure."""

import sys
from types import SimpleNamespace

import pytest

from scripts.verify import mcp_verify_rest as verifier


def test_teardown_deletes_only_owned_names(monkeypatch):
    own = "verify_rest_0123abcd"
    names = [own, own + "_r", own + "_extra", "verify_other", "user-model"]
    objects = [SimpleNamespace(name=n) for n in names]

    class Objects:
        def __iter__(self):
            return iter(objects)

        def remove(self, obj, do_unlink):
            assert do_unlink
            objects.remove(obj)

    monkeypatch.setitem(
        sys.modules, "bpy", SimpleNamespace(data=SimpleNamespace(objects=Objects()))
    )

    def execute(code):
        exec(code, {})
        return "removed 2"

    monkeypatch.setattr(verifier, "o_out", execute)
    verifier.teardown(own)
    assert [o.name for o in objects] == [own + "_extra", "verify_other", "user-model"]


def test_failure_still_cleans_only_its_nonce(monkeypatch):
    attempted = []
    cleaned = []

    def failing(name):
        attempted.append(name)
        raise RuntimeError("scene unavailable")

    monkeypatch.setattr(verifier, "_verify", failing)
    monkeypatch.setattr(verifier, "teardown", cleaned.append)
    with pytest.raises(RuntimeError, match="scene unavailable"):
        verifier.main()
    assert len(attempted) == 1 and cleaned == attempted
    assert attempted[0].startswith("verify_rest_")


def test_teardown_rejects_unowned_prefix(monkeypatch):
    monkeypatch.setattr(verifier, "o_out", lambda code: pytest.fail("must not execute"))
    with pytest.raises(ValueError):
        verifier.teardown("verify_")


def test_failed_observation_is_not_successful_process(monkeypatch):
    name = "verify_rest_0123abcd"
    observations = iter([[], [name], [name + "_r"], [], [], [], []])
    monkeypatch.setattr(verifier, "o_names", lambda: next(observations))
    monkeypatch.setattr(verifier, "o_out", lambda code: "8")
    monkeypatch.setattr(verifier, "rest", lambda *args: (200, {"objects": []}))
    monkeypatch.setattr(verifier.time, "sleep", lambda seconds: None)
    with pytest.raises(AssertionError, match="H6-frontend-reflects"):
        verifier._verify(name)


def test_cleanup_failure_is_visible(monkeypatch):
    monkeypatch.setattr(verifier, "o_out", lambda code: "<err:timeout>")
    with pytest.raises(RuntimeError, match="cleanup"):
        verifier.teardown("verify_rest_0123abcd")
