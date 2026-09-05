"""Run a Blender script through the shared port and report a typed outcome.

The anti-corruption boundary for ``bpy`` source. Routers state *what* they want
done; the modules in this package own the dialect and the escaping. Keeping the
script text in a delivery adapter made HTTP code the place where Blender
knowledge lived, contradicting the documented invariant that the Blender
adapters are the only translation chokepoint (docs/01-architecture.md).

**Transport failures propagate; script failures are returned.** Those are two
different things and the endpoints used to conflate them in two different ways:
the object routes swallowed every exception into ``success=False`` and answered
500, while the snapshot routes caught the same exception and answered 503. Now a
``BlenderConnectionError`` travels to the application-wide handler and becomes
503 everywhere, and only a script that ran and failed comes back as an outcome.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.domain.command import Command
from src.core.ports.blender_port import BlenderPort


@dataclass(frozen=True, slots=True)
class ScriptOutcome:
    """Result of one Blender script that actually executed."""

    success: bool
    output: object | None
    error: str | None


def quote(value: str) -> str:
    """Escape a value for interpolation into a single-quoted Python literal."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


async def run_script(blender: BlenderPort, code: str) -> ScriptOutcome:
    """Execute ``code`` in Blender.

    Raises whatever the port raises — a transport problem is not a script
    result, and turning it into ``success=False`` is the silent fallback that
    made an unreachable Blender look like a failed rename.
    """
    command = Command(tool_name="execute_code", arguments={"code": code})
    result = await blender.execute(command)
    return ScriptOutcome(success=result.success, output=result.output, error=result.error)
