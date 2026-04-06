"""ModelingPipelineUseCase — YAML-driven multi-step 3D modeling pipeline.

Stages: geometry → UV unwrap → material → export
Each stage is independently validated before proceeding to the next.
Stage definitions are loaded from config/modeling_pipeline.yaml (data-driven).

Architecture:
  - Depends on: BlenderPort, LLMChatPort (both injected ports)
  - Stage config is injected (not imported directly) for testability
  - Returns: PipelineResult with per-stage outcomes
"""

from __future__ import annotations

import logging
from typing import Any

from src.core.domain.command import Command
from src.core.domain.pipeline import (
    PipelineResult,
    PipelineStage,
    StageResult,
    StageStatus,
)
from src.core.ports.blender_port import BlenderPort
from src.core.ports.llm_port import LLMChatPort

logger = logging.getLogger(__name__)


class ModelingPipelineUseCase:
    """Execute a sequence of Blender modeling operations defined in YAML.

    Example usage:
        stages = PipelineLoader.load("config/modeling_pipeline.yaml", "black_cat")
        result = await ModelingPipelineUseCase(blender).execute(stages, context)
    """

    def __init__(self, blender: BlenderPort, llm: LLMChatPort | None = None) -> None:
        self._blender = blender
        self._llm = llm

    async def execute(
        self,
        stages: list[PipelineStage],
        context: dict[str, Any],
        pipeline_name: str = "custom",
    ) -> PipelineResult:
        """Run stages sequentially, stopping on first non-optional failure.

        Args:
            stages: Ordered list of pipeline stages.
            context: Key-value context for resolving argument placeholders.
            pipeline_name: Name identifier for this pipeline run.

        Returns:
            PipelineResult with outcomes for all executed stages.
        """
        result = PipelineResult(pipeline_name=pipeline_name, context=context)

        for stage in stages:
            logger.info("Pipeline[%s]: executing stage '%s'", pipeline_name, stage.name)
            stage_result = await self._execute_stage(stage, context)
            result.stage_results.append(stage_result)

            if stage_result.status == StageStatus.DONE and stage_result.output:
                # Propagate output to context for subsequent stages
                context[f"{stage.name}_output"] = stage_result.output

            if stage_result.status == StageStatus.FAILED:
                if stage.optional:
                    logger.warning(
                        "Pipeline[%s]: optional stage '%s' failed — skipping",
                        pipeline_name,
                        stage.name,
                    )
                    stage_result.status = StageStatus.SKIPPED
                else:
                    logger.error(
                        "Pipeline[%s]: required stage '%s' failed — aborting",
                        pipeline_name,
                        stage.name,
                    )
                    break

        return result

    async def _execute_stage(self, stage: PipelineStage, context: dict) -> StageResult:
        """Execute a single pipeline stage and return its outcome."""
        args = stage.resolve_arguments(context)
        command = Command(tool_name=stage.tool_name, arguments=args)

        try:
            tool_result = await self._blender.execute(command)
        except Exception as e:
            return StageResult(
                stage_name=stage.name,
                status=StageStatus.FAILED,
                error=str(e),
            )

        if not tool_result.success:
            return StageResult(
                stage_name=stage.name,
                status=StageStatus.FAILED,
                error=tool_result.error,
            )

        # Validation: if validation_key specified, check output contains it
        if stage.validation_key and tool_result.output and stage.validation_key not in str(tool_result.output):
            return StageResult(
                stage_name=stage.name,
                status=StageStatus.FAILED,
                error=f"Validation failed: '{stage.validation_key}' not in output",
                output=str(tool_result.output),
            )

        return StageResult(
            stage_name=stage.name,
            status=StageStatus.DONE,
            output=str(tool_result.output) if tool_result.output else None,
        )
