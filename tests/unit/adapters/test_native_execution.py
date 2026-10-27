"""Durable native completion is independent of socket observation."""

import hashlib
import json
from dataclasses import asdict

import pytest

from src.adapters.artifacts.native_execution import NativeExecutionJournal
from src.core.domain.native_revision import NativeSceneError, SourceArtifact


def fixture(tmp_path):
    journal = NativeExecutionJournal(tmp_path / "execution")
    identity = journal.reserve("a" * 32, "closed body", "b" * 64)
    native = journal.directory / "candidate.blend"
    native.write_bytes(b"saved native")
    surfaces = journal.directory / "changed-surfaces.json"
    surfaces.write_bytes(b"{}")

    def receipt(path):
        return asdict(
            SourceArtifact(
                path.name, hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size
            )
        )

    terminal = {
        **identity,
        "status": "completed",
        "restored": True,
        "output": receipt(native),
        "surfaces": receipt(surfaces),
        "error": None,
    }
    return journal, terminal


def test_terminal_is_durable_and_requires_ack_after_matching_original_identity(tmp_path):
    journal, terminal = fixture(tmp_path)
    assert journal.read_terminal() is None and journal.unfinished()
    journal.publish_terminal(terminal)
    reopened = NativeExecutionJournal(journal.directory)
    assert reopened.read_terminal() == terminal and reopened.unfinished()
    reopened.acknowledge()
    assert not NativeExecutionJournal(journal.directory).unfinished()
    assert json.loads((journal.directory / "pending.json").read_text())["nonce"] == "a" * 32


@pytest.mark.parametrize(
    "fault", ["nonce", "program_sha256", "source_sha256", "restored", "output", "extra", "ack"]
)
def test_wrong_or_unrestored_receipt_never_unlocks_the_engine(tmp_path, fault):
    journal, terminal = fixture(tmp_path)
    if fault in ("nonce", "program_sha256", "source_sha256"):
        terminal[fault] = "c" * len(terminal[fault])
    elif fault == "restored":
        terminal[fault] = False
    elif fault == "extra":
        terminal["unexpected"] = True
    journal.publish_terminal(terminal)
    if fault == "output":
        (journal.directory / "candidate.blend").write_bytes(b"tampered")
    if fault == "ack":
        (journal.directory / "acknowledged.json").write_text("{}")
    with pytest.raises(NativeSceneError):
        journal.acknowledge()
    assert not (journal.directory / "acknowledged.json").exists() or fault == "ack"


def test_completed_failure_can_be_acknowledged_only_after_restoration(tmp_path):
    journal, terminal = fixture(tmp_path)
    terminal.update(status="failed", output=None, surfaces=None, error="operation rejected")
    journal.publish_terminal(terminal)
    assert journal.acknowledge()["status"] == "failed"
    assert not journal.unfinished()


def test_reservation_terminal_and_ack_are_exclusive_and_pending_json_is_bounded(tmp_path):
    journal, terminal = fixture(tmp_path)
    original = (journal.directory / "pending.json").read_bytes()
    with pytest.raises(NativeSceneError):
        journal.reserve("d" * 32, "another body", "e" * 64)
    assert (journal.directory / "pending.json").read_bytes() == original
    journal.publish_terminal(terminal)
    with pytest.raises(NativeSceneError):
        journal.publish_terminal(terminal)
    (journal.directory / "pending.json").write_bytes(b"x" * 65537)
    with pytest.raises(NativeSceneError):
        journal.read_terminal()


def test_symlinked_execution_directory_is_never_accepted(tmp_path):
    actual = tmp_path / "actual"
    actual.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    journal = NativeExecutionJournal(alias)
    with pytest.raises(NativeSceneError):
        journal.reserve("a" * 32, "closed body", "b" * 64)
    assert not list(actual.iterdir())


def test_terminal_cannot_replace_integer_protocol_with_boolean(tmp_path):
    journal, terminal = fixture(tmp_path)
    terminal["protocol"] = True
    journal.publish_terminal(terminal)
    with pytest.raises(NativeSceneError):
        journal.acknowledge()


def test_missing_pending_cannot_hide_a_started_or_terminal_callback(tmp_path):
    journal, terminal = fixture(tmp_path)
    journal.publish_terminal(terminal)
    (journal.directory / "pending.json").unlink()
    with pytest.raises(NativeSceneError):
        journal.unfinished()
