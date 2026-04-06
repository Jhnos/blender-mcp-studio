"""Pipeline domain entities.

Represents a multi-step modeling pipeline defined in YAML.
Each stage maps to a specific Blender operation with validation criteria.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class StageStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineStage:
    """Single stage in a modeling pipeline."""

    name: str
    description: str
    tool_name: str
    arguments_template: dict  # placeholders resolved at runtime
    validation_key: str | None = None  # response key that must be truthy to pass
    optional: bool = False

    def resolve_arguments(self, context: dict) -> dict:
        """Fill placeholders in arguments_template from context dict."""
        resolved: dict = {}
        for k, v in self.arguments_template.items():
            if isinstance(v, str) and v.startswith("{{") and v.endswith("}}"):
                placeholder = v[2:-2].strip()
                resolved[k] = context.get(placeholder, v)
            else:
                resolved[k] = v
        return resolved


@dataclass
class StageResult:
    """Result of executing a single pipeline stage."""

    stage_name: str
    status: StageStatus
    output: str | None = None
    error: str | None = None


@dataclass
class PipelineResult:
    """Aggregated result of a complete pipeline run."""

    pipeline_name: str
    stage_results: list[StageResult] = field(default_factory=list)
    context: dict = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return all(
            r.status in (StageStatus.DONE, StageStatus.SKIPPED)
            for r in self.stage_results
        )

    @property
    def failed_stage(self) -> StageResult | None:
        return next(
            (r for r in self.stage_results if r.status == StageStatus.FAILED), None
        )
