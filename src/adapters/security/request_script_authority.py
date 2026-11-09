"""Exact internal-program permits, scoped to the task that issues them.

The composition root owns one authority; only the native execution adapter may
issue a scope. Clients never supply this capability or an authorized-code set.
Context inheritance is not authorization: children and copied thread contexts
must fail the explicit owner check, even while their parent scope is still live.
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(slots=True)
class _Permit:
    code: str
    timeout: float
    owner: object
    active: bool = True  # Shared by copied contexts; lexical exit revokes every copy.


def _task() -> object | None:
    try:
        return asyncio.current_task()
    except RuntimeError:
        return None


class RequestScriptAuthority:
    def __init__(self) -> None:
        self._permit: ContextVar[_Permit | None] = ContextVar(
            "internal_script_permit", default=None
        )

    @contextmanager
    def scope(self, code: str, *, timeout: float) -> Iterator[None]:
        if not isinstance(code, str) or not code.strip():
            raise ValueError("internal script must be nonempty")
        if type(timeout) not in (int, float):
            raise ValueError("internal script timeout must be finite and positive")
        try:
            deadline = float(timeout)
        except OverflowError as exc:
            raise ValueError("internal script timeout must be finite and positive") from exc
        if not math.isfinite(deadline) or deadline <= 0:
            raise ValueError("internal script timeout must be finite and positive")
        owner = _task()
        if owner is None:
            raise RuntimeError("internal script permit requires an owning asyncio task")
        permit = _Permit(code, deadline, owner)
        token = self._permit.set(permit)
        try:
            yield
        finally:
            permit.active = False
            self._permit.reset(token)

    def timeout_for(self, code: str) -> float | None:
        permit = self._permit.get()
        if (
            permit is None
            or not permit.active
            or permit.owner is not _task()
            or permit.code != code
        ):
            return None
        return permit.timeout
