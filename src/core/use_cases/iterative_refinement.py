"""IterativeRefinementUseCase — Generate → Screenshot → Vision Analyze → Refine loop.

Implements the core V2 differentiator: AI sees its own output and iteratively
improves it until the vision model is satisfied or max_iterations reached.

Architecture:
  - Depends on: LLMChatPort, BlenderPort, VisionPort (all injected ports)
  - Returns: RefinementResult with all iterations recorded
  - Publishes domain events per iteration

Data-driven: iterations count and convergence signal controlled by config.
"""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field

from src.core.domain.command import Command, CommandParser
from src.core.domain.session import Session
from src.core.ports.blender_port import BlenderPort
from src.core.ports.llm_port import LLMChatPort, LLMToolChatPort, ToolDefinition
from src.core.ports.vision_port import VisionPort

logger = logging.getLogger(__name__)

_CONVERGENCE_KEYWORDS = frozenset([
    "looks good", "complete", "done", "accurate", "matches",
    "符合", "完成", "準確", "正確", "很好", "很棒", "完美",
])

_VISION_PROMPT_TEMPLATE = """\
You are reviewing a Blender 3D viewport screenshot.
The user's original request was: "{user_request}"

Analyze the scene:
1. Does it match what the user asked for?
2. What's missing or incorrect?
3. Suggest specific improvements (as a bullet list).

If the scene already matches the request well, say "looks good" at the start.
"""

_REFINEMENT_SYSTEM_PROMPT = """\
You are a 3D modeling assistant. Based on the vision analysis of the current Blender scene,
generate corrective tool calls to improve the model.
Focus only on the specific issues identified in the analysis.
"""


@dataclass
class RefinementIteration:
    """Record of a single refinement iteration."""

    iteration: int
    vision_analysis: str
    commands_executed: list[str] = field(default_factory=list)
    converged: bool = False


@dataclass
class RefinementResult:
    """Final result of the iterative refinement process."""

    session: Session
    iterations: list[RefinementIteration]
    final_screenshot: bytes | None
    converged: bool

    @property
    def iteration_count(self) -> int:
        return len(self.iterations)


class IterativeRefinementUseCase:
    """Vision-guided iterative refinement of 3D models.

    Loop:
      1. Take viewport screenshot
      2. Send to VisionPort for analysis
      3. Check convergence (vision says "looks good")
      4. If not converged: generate corrective commands via LLM
      5. Execute commands in Blender
      6. Repeat until converged or max_iterations reached
    """

    def __init__(
        self,
        llm: LLMChatPort,
        blender: BlenderPort,
        vision: VisionPort,
        max_iterations: int = 3,
    ) -> None:
        self._llm = llm
        self._blender = blender
        self._vision = vision
        self._max_iterations = max_iterations
        self._use_tool_calling = isinstance(llm, LLMToolChatPort)

    async def execute(
        self,
        session: Session,
        user_request: str,
    ) -> RefinementResult:
        """Run the iterative refinement loop.

        Args:
            session: Current conversation session (for LLM context).
            user_request: Original user description of the desired 3D model.

        Returns:
            RefinementResult with all iterations recorded.
        """
        iterations: list[RefinementIteration] = []
        current_session = session

        for i in range(1, self._max_iterations + 1):
            logger.info("Refinement iteration %d/%d", i, self._max_iterations)

            # Step 1: screenshot
            screenshot_bytes = await self._capture_screenshot()
            if screenshot_bytes is None:
                logger.warning("Could not capture screenshot, stopping refinement")
                break

            # Step 2: vision analysis
            prompt = _VISION_PROMPT_TEMPLATE.format(user_request=user_request)
            analysis = await self._vision.analyze_image(screenshot_bytes, prompt)
            vision_text = analysis.description
            logger.info("Vision analysis (iter %d): %s...", i, vision_text[:100])

            iteration = RefinementIteration(iteration=i, vision_analysis=vision_text)

            # Step 3: check convergence
            converged = self._is_converged(vision_text)
            iteration.converged = converged
            iterations.append(iteration)

            if converged:
                logger.info("Converged after %d iteration(s)", i)
                return RefinementResult(
                    session=current_session,
                    iterations=iterations,
                    final_screenshot=screenshot_bytes,
                    converged=True,
                )

            # Step 4: generate corrective commands
            refinement_msg = (
                f"Vision analysis of current Blender scene:\n{vision_text}\n\n"
                f"Please make corrective adjustments to better match: {user_request}"
            )
            refinement_session = current_session.add_message("user", refinement_msg)

            try:
                commands = await self._get_commands(refinement_session)
            except Exception as e:
                logger.warning("LLM refinement call failed: %s", e)
                break

            # Step 5: execute commands
            for cmd in commands:
                result = await self._blender.execute(cmd)
                status = "✅" if result.success else f"❌ {result.error}"
                iteration.commands_executed.append(f"{cmd.tool_name}: {status}")
                logger.info("Refinement command %s: %s", cmd.tool_name, status)

            current_session = refinement_session.add_message(
                "assistant",
                f"Applied {len(commands)} refinement(s) based on vision analysis.",
            )

        # Capture final screenshot
        final_shot = await self._capture_screenshot()
        return RefinementResult(
            session=current_session,
            iterations=iterations,
            final_screenshot=final_shot,
            converged=False,
        )

    async def _capture_screenshot(self) -> bytes | None:
        try:
            tmp = tempfile.mktemp(suffix=".png")
            result = await self._blender.call_tool(
                "get_viewport_screenshot", {"filepath": tmp}
            )
            if result.success and os.path.exists(tmp):
                with open(tmp, "rb") as f:
                    data = f.read()
                os.unlink(tmp)
                return data
        except Exception as e:
            logger.debug("Screenshot failed: %s", e)
        return None

    async def _get_commands(self, session: Session) -> list[Command]:
        """Get corrective commands from LLM — tool calling or regex fallback."""
        if self._use_tool_calling:
            assert isinstance(self._llm, LLMToolChatPort)
            from src.core.use_cases.conversational_modeling import _BLENDER_TOOLS
            response = await self._llm.chat_with_tools(
                messages=session.messages,
                tools=_BLENDER_TOOLS,
                system_prompt=_REFINEMENT_SYSTEM_PROMPT,
            )
            return [
                Command(tool_name=tc.name, arguments=tc.arguments)
                for tc in response.tool_calls
            ]
        else:
            response = await self._llm.chat(
                messages=session.messages,
                system_prompt=_REFINEMENT_SYSTEM_PROMPT,
            )
            cmd = CommandParser.from_llm_output(response.content)
            return [cmd] if cmd else []

    @staticmethod
    def _is_converged(vision_text: str) -> bool:
        lower = vision_text.lower()
        return any(kw in lower for kw in _CONVERGENCE_KEYWORDS)
