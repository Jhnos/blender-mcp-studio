"""CodeSandboxPort — abstract interface for validating generated Blender code.

Security concern: LLM-generated code sent to Blender via execute_code tool
could contain dangerous Python constructs (os, subprocess, file I/O outside
project, etc.). This port validates before execution without blocking valid
bpy operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SandboxResult:
    """Result of code sandbox validation."""

    allowed: bool
    violations: tuple[str, ...]

    @property
    def has_violations(self) -> bool:
        return bool(self.violations)


class CodeSandboxPort(ABC):
    """Validates Python code before it is sent to Blender's exec() endpoint."""

    @abstractmethod
    def validate(self, code: str) -> SandboxResult:
        """Check code for dangerous patterns.

        Returns SandboxResult with allowed=True if the code is safe,
        or allowed=False with a list of violations if it should be blocked.
        """
