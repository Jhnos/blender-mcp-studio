"""PipelineLoader — loads pipeline stage definitions from YAML config.

Data-driven: add new pipelines by editing YAML without code changes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.core.domain.pipeline import PipelineStage


class PipelineLoader:
    """Reads pipeline definitions from YAML and constructs PipelineStage lists.

    YAML is loaded once per config_path and cached at the class level to
    avoid per-instance lru_cache (which can cause memory leaks on methods).
    """

    _cache: dict[Path, dict[str, Any]] = {}

    def __init__(self, config_path: str | Path = "config/modeling_pipeline.yaml") -> None:
        self._config_path = Path(config_path)

    def _load_raw(self) -> dict[str, Any]:
        if self._config_path not in PipelineLoader._cache:
            with open(self._config_path, encoding="utf-8") as f:
                PipelineLoader._cache[self._config_path] = yaml.safe_load(f) or {}
        return PipelineLoader._cache[self._config_path]

    def load(self, pipeline_name: str) -> list[PipelineStage]:
        """Load stages for a named pipeline from YAML.

        Args:
            pipeline_name: Key in the YAML 'pipelines' dict.

        Returns:
            Ordered list of PipelineStage objects.

        Raises:
            KeyError: if pipeline_name not found in config.
        """
        raw = self._load_raw()
        pipelines = raw.get("pipelines", {})
        if pipeline_name not in pipelines:
            available = list(pipelines.keys())
            raise KeyError(
                f"Pipeline '{pipeline_name}' not found. Available: {available}"
            )

        stages_raw = pipelines[pipeline_name].get("stages", [])
        return [
            PipelineStage(
                name=s["name"],
                description=s.get("description", ""),
                tool_name=s["tool"],
                arguments_template=s.get("arguments", {}),
                validation_key=s.get("validation_key"),
                optional=s.get("optional", False),
            )
            for s in stages_raw
        ]

    def list_pipelines(self) -> list[str]:
        """Return names of all available pipelines."""
        return list(self._load_raw().get("pipelines", {}).keys())

