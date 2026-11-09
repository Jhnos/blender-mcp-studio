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


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "different-state",
        "source",
        "missing-backup",
        "late-change",
        "not-terminal",
        "restored",
    ],
)
def test_verified_reset_closes_failed_execution_without_rewriting_failure(tmp_path, fault):
    directory = tmp_path / "reset-execution"
    journal = NativeExecutionJournal(directory)
    source_bytes = b"verified selected original native"
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    identity = journal.reserve("a" * 32, "closed failed callback", source_sha)
    terminal = {
        **identity,
        "status": "failed",
        "restored": False,
        "output": None,
        "surfaces": None,
        "error": "failed original restoration",
    }
    if fault == "restored":
        terminal["restored"] = True
    if fault != "not-terminal":
        journal.publish_terminal(terminal)
    expected = {
        "source_sha256": source_sha,
        "objects": {"part": {"type": "MESH", "geometry": "c" * 64, "state_sha256": "e" * 64}},
        "active_objects": ["part"],
        "external_libraries": 0,
    }
    observed = json.loads(json.dumps(expected))
    if fault == "different-state":
        observed["objects"]["part"]["geometry"] = "d" * 64
    if fault == "source":
        expected["source_sha256"] = observed["source_sha256"] = "f" * 64

    def asset(name, data):
        path = directory / name
        path.write_bytes(data)
        return asdict(SourceArtifact(name, hashlib.sha256(data).hexdigest(), len(data)))

    evidence = dict(
        source=asset("reset-source.blend", source_bytes),
        backup=asset("reset-backup.blend", b"preserved failed live scene"),
        expected=asset("reset-expected.json", json.dumps(expected).encode()),
        observed=asset("reset-observed.json", json.dumps(observed).encode()),
    )
    if fault == "missing-backup":
        (directory / "reset-backup.blend").unlink()
    before = (directory / "terminal.json").read_bytes() if fault != "not-terminal" else None
    if fault is not None and fault != "late-change":
        with pytest.raises(NativeSceneError):
            journal.acknowledge_reset(**evidence)
        assert not (directory / "reset-acknowledged.json").exists()
    else:
        journal.acknowledge_reset(**evidence)
        if fault == "late-change":
            (directory / "reset-observed.json").write_bytes(b"tampered")
            with pytest.raises(NativeSceneError):
                NativeExecutionJournal(directory).unfinished()
        else:
            assert not NativeExecutionJournal(directory).unfinished()
            assert not (directory / "acknowledged.json").exists()
            assert journal.read_terminal()["restored"] is False
    if before is not None:
        assert (directory / "terminal.json").read_bytes() == before
