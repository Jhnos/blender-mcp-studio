"""Durable, exclusive receipts inside an existing native job; not another job store."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from src.adapters.artifacts.native_source import read_source_asset, unique_native_object
from src.core.domain.native_revision import NativeSceneError, NativeSourceError, SourceArtifact
from src.infrastructure.narrowing import as_sequence, as_str_keyed_exact

_BUDGET = 65536
_ID_KEYS = {"protocol", "nonce", "program_sha256", "source_sha256"}
_TERMINAL_KEYS = _ID_KEYS | {"status", "restored", "output", "surfaces", "error"}


def _safe(path: Path) -> None:
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise NativeSceneError("native execution paths must not be symlinked")


def _publish(path: Path, payload: dict[str, object]) -> None:
    _safe(path)
    data = json.dumps(payload, sort_keys=True, allow_nan=False).encode()
    if len(data) > _BUDGET:
        raise NativeSceneError("native execution receipt exceeds its byte budget")
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=".execution-", dir=path.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        temporary.unlink()
        temporary = None
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as exc:
        raise NativeSceneError(
            "native execution receipt could not be published exclusively"
        ) from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _read(path: Path) -> dict[str, object]:
    _safe(path)
    try:
        with path.open("rb") as handle:
            payload = handle.read(_BUDGET + 1)
        if len(payload) > _BUDGET:
            raise NativeSceneError("native execution receipt exceeds its byte budget")
        result = as_str_keyed_exact(json.loads(payload, object_pairs_hook=unique_native_object))
        if result is None:
            raise NativeSceneError("native execution receipt must be an object")
        return result
    except (OSError, ValueError, NativeSourceError) as exc:
        raise NativeSceneError("native execution receipt is unavailable or invalid") from exc


class NativeExecutionJournal:
    def __init__(self, directory: Path) -> None:
        self.directory = directory.absolute()

    def reserve(self, nonce: str, program: str, source_sha256: str) -> dict[str, object]:
        identity: dict[str, object] = {
            "protocol": 1,
            "nonce": nonce,
            "program_sha256": hashlib.sha256(program.encode()).hexdigest(),
            "source_sha256": source_sha256,
        }
        self._identity(identity)
        _safe(self.directory)
        try:
            self.directory.mkdir(parents=True)
        except OSError as exc:
            raise NativeSceneError("native execution job already exists or is unavailable") from exc
        _publish(self.directory / "pending.json", identity)
        return identity

    @staticmethod
    def _identity(value: dict[str, object]) -> dict[str, object]:
        if (
            set(value) != _ID_KEYS
            or type(value.get("protocol")) is not int
            or value["protocol"] != 1
        ):
            raise NativeSceneError("invalid native execution identity")
        for key, width in (("nonce", 32), ("program_sha256", 64), ("source_sha256", 64)):
            text = value.get(key)
            if not isinstance(text, str) or re.fullmatch(rf"[0-9a-f]{{{width}}}", text) is None:
                raise NativeSceneError("invalid native execution identity")
        return value

    def identity(self) -> dict[str, object]:
        return self._identity(_read(self.directory / "pending.json"))

    def mark_started(self, program_sha256: str, source_sha256: str) -> dict[str, object]:
        identity = self.identity()
        if (
            identity["program_sha256"] != program_sha256
            or identity["source_sha256"] != source_sha256
        ):
            raise NativeSceneError("native callback does not match its reserved execution")
        _publish(self.directory / "started.json", identity)
        return identity

    def publish_terminal(self, terminal: dict[str, object]) -> None:
        # Preserve even a failed-restoration diagnostic. Consumers validate before acknowledging.
        _publish(self.directory / "terminal.json", terminal)

    def read_terminal(self) -> dict[str, object] | None:
        identity = self.identity()
        path = self.directory / "terminal.json"
        _safe(path)
        if not path.exists():
            return None
        value = _read(path)
        if set(value) != _TERMINAL_KEYS or any(
            value[key] != item for key, item in identity.items()
        ):
            raise NativeSceneError("native terminal does not match its pending execution")
        self._identity({key: value[key] for key in _ID_KEYS})
        if type(value["restored"]) is not bool or value["status"] not in ("completed", "failed"):
            raise NativeSceneError("invalid native terminal state")
        if value["status"] == "completed":
            if value["error"] is not None:
                raise NativeSceneError("completed native terminal contains an error")
            self.artifact(value["output"], "candidate.blend", 512 * 1024 * 1024)
            self.artifact(value["surfaces"], "changed-surfaces.json", 128 * 1024 * 1024)
        elif (
            not isinstance(value["error"], str)
            or not value["error"]
            or value["output"] is not None
            or value["surfaces"] is not None
        ):
            raise NativeSceneError("failed native terminal has no coherent diagnostic")
        return value

    def artifact(self, raw: object, name: str, budget: int) -> SourceArtifact:
        value = as_str_keyed_exact(raw)
        if value is None or set(value) != {"path", "sha256", "size_bytes"}:
            raise NativeSceneError("invalid native output identity")
        path, sha, size = value["path"], value["sha256"], value["size_bytes"]
        if path != name or not isinstance(sha, str) or type(size) is not int or size <= 0:
            raise NativeSceneError("invalid native output identity")
        receipt = SourceArtifact(name, sha, size)
        try:
            read_source_asset(self.directory, receipt, budget)
        except NativeSourceError as exc:
            raise NativeSceneError("native output disagrees with its completion receipt") from exc
        return receipt

    def acknowledge(self) -> dict[str, object]:
        terminal = self.read_terminal()
        if terminal is None or terminal["restored"] is not True:
            raise NativeSceneError("native completion and original restoration are unproven")
        acknowledgement = {
            **self.identity(),
            "terminal_sha256": hashlib.sha256(
                (self.directory / "terminal.json").read_bytes()
            ).hexdigest(),
        }
        path = self.directory / "acknowledged.json"
        _safe(path)
        if path.exists():
            if _read(path) != acknowledgement:
                raise NativeSceneError("native acknowledgement does not match its terminal")
        else:
            _publish(path, acknowledgement)
        return terminal

    def unfinished(self) -> bool:
        pending = self.directory / "pending.json"
        _safe(pending)
        if not pending.exists():
            if self.directory.exists() and any(self.directory.iterdir()):
                raise NativeSceneError("native execution files exist without a pending identity")
            return False
        self.identity()
        reset = self.directory / "reset-acknowledged.json"
        _safe(reset)
        if reset.exists():
            value = _read(reset)
            if set(value) != _ID_KEYS | {
                "mode",
                "terminal_sha256",
                "source",
                "backup",
                "expected",
                "observed",
            }:
                raise NativeSceneError("invalid native reset acknowledgement")
            expected = self._validated_reset(
                **{key: value[key] for key in ("source", "backup", "expected", "observed")}
            )
            if value != expected:
                raise NativeSceneError("native reset acknowledgement does not match its evidence")
            return False
        ack = self.directory / "acknowledged.json"
        _safe(ack)
        if not ack.exists():
            return True
        self.acknowledge()
        return False

    def _validated_reset(
        self, *, source: object, backup: object, expected: object, observed: object
    ) -> dict[str, object]:
        """Local maintenance evidence; never a caller-controlled recovery ticket or success."""
        terminal = self.read_terminal()
        if terminal is None or terminal["status"] != "failed" or terminal["restored"] is not False:
            raise NativeSceneError("verified reset requires a terminal failed restoration")
        assets = {}
        for key, raw, suffix, budget in (
            ("source", source, "blend", 512 * 1024 * 1024),
            ("backup", backup, "blend", 512 * 1024 * 1024),
            ("expected", expected, "json", _BUDGET),
            ("observed", observed, "json", _BUDGET),
        ):
            self.artifact(raw, f"reset-{key}.{suffix}", budget)
            assets[key] = raw
        source_value = as_str_keyed_exact(source)
        assert source_value is not None
        identity = self.identity()
        if source_value["sha256"] != identity["source_sha256"]:
            raise NativeSceneError("reset source differs from the failed native execution")
        baseline = _read(self.directory / "reset-expected.json")
        loaded = _read(self.directory / "reset-observed.json")
        objects = as_str_keyed_exact(baseline.get("objects"))
        active = as_sequence(baseline.get("active_objects"))
        if (
            set(baseline) != {"source_sha256", "objects", "active_objects", "external_libraries"}
            or baseline != loaded
            or baseline.get("source_sha256") != identity["source_sha256"]
            or type(baseline.get("external_libraries")) is not int
            or baseline["external_libraries"] != 0
            or not objects
            or len(objects) > 10000
            or active is None
            or len(active) != len(objects)
            or any(not isinstance(name, str) or name not in objects for name in active)
            or len(set(active)) != len(objects)
        ):
            raise NativeSceneError("independent reset baseline and loaded native state disagree")
        for obj in objects.values():
            row = as_str_keyed_exact(obj)
            if row is None or set(row) != {"type", "geometry", "state_sha256"}:
                raise NativeSceneError("reset object evidence is incomplete")
            if (
                not isinstance(row["type"], str)
                or re.fullmatch(r"[A-Z_]{1,32}", row["type"]) is None
            ):
                raise NativeSceneError("reset object type is invalid")
            for value in (
                row["state_sha256"],
                *([row["geometry"]] if row["type"] == "MESH" else []),
            ):
                if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                    raise NativeSceneError("reset object fingerprint is invalid")
            if row["type"] != "MESH" and row["geometry"] is not None:
                raise NativeSceneError("reset non-mesh geometry is invalid")
        return {
            **identity,
            "mode": "verified-selected-source-reset",
            "terminal_sha256": hashlib.sha256(
                (self.directory / "terminal.json").read_bytes()
            ).hexdigest(),
            **assets,
        }

    def acknowledge_reset(
        self, *, source: object, backup: object, expected: object, observed: object
    ) -> None:
        """Seal an independently verified operator reset; preserve the failed terminal forever."""
        value = self._validated_reset(
            source=source, backup=backup, expected=expected, observed=observed
        )
        _publish(self.directory / "reset-acknowledged.json", value)
