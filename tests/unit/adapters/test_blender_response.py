"""Tests for the shared Blender response decoding.

`decode_marked_json` was extracted from two adapters that carried the same
marker-scanning prologue, differing only in the marker, the exception type and
two messages. Those three stay with the caller, so the tests check both that the
shared mechanics are right and that the caller's wording survives.
"""

from __future__ import annotations

import pytest

from src.adapters.blender_response import decode_marked_json
from src.core.domain.exceptions import BatchTransformError, PrintReadinessError

MARKER = "RESULT_JSON:"


def _decode(output: str, error: type[Exception] = BatchTransformError) -> object:
    return decode_marked_json(
        output,
        MARKER,
        missing="no structured payload",
        invalid="invalid JSON",
        error=error,
    )


def test_reads_the_payload_after_the_marker() -> None:
    assert _decode(f'{MARKER}{{"affected": 2}}') == {"affected": 2}


def test_ignores_output_printed_before_the_marker() -> None:
    assert _decode(f'Blender warning: something\n{MARKER}{{"ok": true}}') == {"ok": True}


def test_ignores_output_printed_after_the_payload_line() -> None:
    assert _decode(f'{MARKER}{{"ok": true}}\ntrailing log line') == {"ok": True}


def test_the_last_marker_wins() -> None:
    """A script that logs before printing its result emits the marker twice.

    Taking the first would return a stale payload, so the scan is anchored at the
    end. This is the behaviour `rfind` was chosen for; asserting it keeps a later
    switch to `find` from passing silently.
    """
    assert _decode(f'{MARKER}{{"stale": true}}\n{MARKER}{{"fresh": true}}') == {"fresh": True}


def test_missing_marker_raises_the_callers_error_and_message() -> None:
    with pytest.raises(BatchTransformError, match="no structured payload"):
        _decode("Blender printed nothing structured")


def test_invalid_json_raises_the_callers_error_and_message() -> None:
    with pytest.raises(BatchTransformError, match="invalid JSON"):
        _decode(f"{MARKER}not json at all")


def test_each_caller_keeps_its_own_exception_type() -> None:
    """The whole reason the error factory is injected rather than shared."""
    with pytest.raises(PrintReadinessError):
        _decode("nothing here", PrintReadinessError)
