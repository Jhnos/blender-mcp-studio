"""Execute one closed native callback over the runtime's existing port and lease."""

from __future__ import annotations

import asyncio
import hashlib
import math
import re
import sys
import uuid
from pathlib import Path

from src.adapters.artifacts.native_execution import NativeExecutionJournal
from src.adapters.artifacts.native_source import read_source_asset
from src.adapters.security.request_script_authority import RequestScriptAuthority
from src.core.domain.command import Command
from src.core.domain.exceptions import BlenderConnectionError, BlenderExecutionUncertainError
from src.core.domain.native_revision import (
    NativeRevisionResult,
    NativeSceneError,
    PreparedNativeRevision,
)
from src.core.ports.blender_port import BlenderPort
from src.core.use_cases.blender_lease import BlenderLease, run_to_completion
from src.verification.generator_imports import module_file_for, reload_modules_for

NATIVE_COMMAND_TIMEOUT_S = 300.0
NATIVE_COMPLETION_TIMEOUT_S = 600.0

ROOT = Path(__file__).resolve().parents[3]
_OWNERS = ("LS_FIT_lcd_back", "LS_FIT_lid", "TE_pH_temp_three_point_wrist")


def build_native_program(prepared: PreparedNativeRevision, runs_dir: Path) -> tuple[str, Path]:
    relative = prepared.staged.directory
    if re.fullmatch(r"[0-9a-f]{32}/native-source", relative) is None:
        raise NativeSceneError("native execution requires an existing job snapshot")
    snapshot = runs_dir / relative
    if any(p.is_symlink() for p in (snapshot, *snapshot.parents)):
        raise NativeSceneError("native execution snapshot must not be symlinked")
    source = prepared.staged.source
    read_source_asset(snapshot, source.native, 512 * 1024 * 1024)
    canonical = {}
    for name in _OWNERS:
        matches = [p for p in source.parts if Path(p.path).stem == name]
        if len(matches) != 1:
            raise NativeSceneError("native recipe source owner is missing or ambiguous")
        canonical[name] = matches[0]
        read_source_asset(snapshot, matches[0], matches[0].size_bytes)
    directory = snapshot.parent / "native-execution"
    modules = reload_modules_for(ROOT, ROOT / "scripts/native_revision_execution.py")
    checker = ROOT / "scripts/verify/native_revision_checks.py"
    checker_modules = reload_modules_for(ROOT, checker)
    files = (
        ROOT / "scripts/native_revision_execution.py",
        checker,
        *(module_file_for(ROOT, name) for name in (*modules, *checker_modules)),
    )
    fingerprints = {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
    }
    # Reuse the dependency-derived resident-interpreter bootstrap; never hand-copy reloads.
    # Only trusted values captured by the service enter this closed program.
    body = f"""import sys, importlib, hashlib
from pathlib import Path
sys.path.insert(0, {str(ROOT)!r})
for _relative, _expected in {fingerprints!r}.items():
    if hashlib.sha256((Path({str(ROOT)!r}) / _relative).read_bytes()).hexdigest() != _expected:
        raise RuntimeError("native callback source fingerprint changed")
for _name in {modules!r}:
    importlib.reload(importlib.import_module(_name))
_values = importlib.import_module("src.core.domain.native_revision")
SourceArtifact, NativeRevisionRequest = _values.SourceArtifact, _values.NativeRevisionRequest
run = importlib.reload(importlib.import_module("scripts.native_revision_execution")).run
run(Path({str(directory)!r}), Path({str(snapshot)!r}), {source.native!r}, {canonical!r}, {prepared.request!r}, Path({sys.executable!r}), _native_program_sha256)
"""
    return body, directory


class NativeRunner:
    def __init__(
        self,
        blender: BlenderPort,
        lease: BlenderLease,
        authority: RequestScriptAuthority,
        runs_dir: Path,
        *,
        completion_timeout: float = NATIVE_COMPLETION_TIMEOUT_S,
        poll_interval: float = 0.1,
    ) -> None:
        if any(
            not math.isfinite(value) or value <= 0 for value in (completion_timeout, poll_interval)
        ):
            raise ValueError("native observation deadlines must be finite and positive")
        self._blender, self._lease, self._authority = blender, lease, authority
        self._runs_dir = runs_dir.absolute()
        self._timeout, self._poll = completion_timeout, poll_interval
        self._owned_ticket: str | None = None
        self._unresolved_run_ids: tuple[str, ...] = ()

    @property
    def unresolved_run_ids(self) -> tuple[str, ...]:
        return self._unresolved_run_ids

    @staticmethod
    def dispatch_program(body: str) -> str:
        return f"import hashlib\n_native_body = {body!r}\nexec(compile(_native_body, '<native-revision>', 'exec'), {{'_native_program_sha256': hashlib.sha256(_native_body.encode()).hexdigest()}})"

    def program(self, prepared: PreparedNativeRevision) -> tuple[str, Path]:
        return build_native_program(prepared, self._runs_dir)

    async def execute(self, prepared: PreparedNativeRevision) -> NativeRevisionResult:
        # This worker itself owns both the lease and the exact-program grant.
        started = asyncio.Event()
        return await run_to_completion(self._execute(prepared, started), started=started)

    async def _execute(
        self, prepared: PreparedNativeRevision, started: asyncio.Event
    ) -> NativeRevisionResult:
        async with self._lease.hold("native-revision"):
            body, directory = await asyncio.to_thread(self.program, prepared)
            journal = NativeExecutionJournal(directory)
            started.set()  # Reservation and dispatch now require a terminal drain.
            identity = journal.reserve(uuid.uuid4().hex, body, prepared.staged.source.native.sha256)
            run_id = directory.parent.name
            self._unresolved_run_ids = (*self._unresolved_run_ids, run_id)
            code = self.dispatch_program(body)
            try:
                with self._authority.scope(code, timeout=NATIVE_COMMAND_TIMEOUT_S):
                    await self._blender.execute(
                        Command(tool_name="execute_code", arguments={"code": code})
                    )
            except BlenderExecutionUncertainError:
                # Completion comes from the journal, never from transport observation.
                self._owned_ticket = self._lease.recovery_ticket
            except BlenderConnectionError as exc:
                journal.publish_terminal(
                    {
                        **identity,
                        "status": "failed",
                        "restored": True,
                        "output": None,
                        "surfaces": None,
                        "error": "native command was not sent: " + str(exc)[:1024],
                    }
                )
            except BaseException:
                self._lease.quarantine()
                self._owned_ticket = self._lease.recovery_ticket
                raise
            deadline = asyncio.get_running_loop().time() + self._timeout
            try:
                while journal.read_terminal() is None:
                    if asyncio.get_running_loop().time() >= deadline:
                        raise BlenderExecutionUncertainError(
                            "native callback completion is unresolved; durable recovery is required"
                        )
                    await asyncio.sleep(self._poll)
                terminal = journal.acknowledge()
                self._unresolved_run_ids = tuple(r for r in self._unresolved_run_ids if r != run_id)
            except BaseException:
                self._lease.quarantine()
                self._owned_ticket = self._lease.recovery_ticket
                raise
            if self._owned_ticket is not None:
                self._lease.resolve_quarantine(self._owned_ticket)
                self._owned_ticket = None
            if terminal["status"] != "completed":
                raise NativeSceneError(
                    "native callback failed after verified restoration; see its job-owned evidence"
                )
            native = journal.artifact(terminal["output"], "candidate.blend", 512 * 1024 * 1024)
            surfaces = journal.artifact(
                terminal["surfaces"], "changed-surfaces.json", 128 * 1024 * 1024
            )
            return NativeRevisionResult(
                prepared, directory.relative_to(self._runs_dir).as_posix(), native, surfaces
            )

    async def recover_unfinished(self) -> int:
        """Inspect durable native receipts before existing orphan-job status recovery."""
        unresolved = []
        for directory in sorted(self._runs_dir.glob("*/native-execution")):
            journal = NativeExecutionJournal(directory)
            try:
                if not journal.unfinished():
                    continue
                terminal = journal.read_terminal()
                if terminal is not None and terminal["restored"] is True:
                    journal.acknowledge()
                else:
                    unresolved.append(directory.parent.name)
            except NativeSceneError:
                unresolved.append(directory.parent.name)
        self._unresolved_run_ids = tuple(unresolved)
        if unresolved:
            ticket = hashlib.sha256("\n".join(unresolved).encode()).hexdigest()
            if self._owned_ticket is None:
                self._lease.restore_quarantine(ticket)
                self._owned_ticket = ticket
        elif self._owned_ticket is not None:
            self._lease.resolve_quarantine(self._owned_ticket)
            self._owned_ticket = None
        return len(unresolved)
