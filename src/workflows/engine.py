"""Workflow engine — loads YAML script definitions and executes them."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from src.core.ports.llm_port import LLMPort
from src.infrastructure.config_loader import load_workflow

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Reads a YAML workflow definition and provides step metadata.

    Supports ${ENV_VAR:-default} syntax in YAML values.
    """

    def __init__(self, workflow_name: str, config_dir: Path | None = None) -> None:
        self._config = load_workflow(workflow_name, config_dir)
        self.name: str = str(self._config.get("name", workflow_name))
        self.version: str = str(self._config.get("version", "1.0.0"))
        self.description: str = str(self._config.get("description", ""))
        self.llm_provider: str = self._resolve_env(str(self._config.get("llm_provider", "ollama")))
        self.mcp_server: str = str(self._config.get("mcp_server", "blender_local"))
        self.steps: list[dict[str, object]] = self._coerce_steps(self._config.get("steps"))

    # ── Public API ────────────────────────────────────────────────────────────

    def get_step(self, step_id: str) -> dict[str, object] | None:
        return next((s for s in self.steps if s.get("id") == step_id), None)

    def build_llm_adapter(self) -> LLMPort:
        """Instantiate the correct LLM adapter via the shared factory."""
        from src.adapters.llm.factory import build_llm_adapter

        return build_llm_adapter(provider=self.llm_provider)

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _coerce_steps(raw: object) -> list[dict[str, object]]:
        """Narrow the YAML-loaded ``steps`` value to a list of mapping steps.

        Every hop is re-annotated back to ``object`` on purpose: ``isinstance``
        cannot check type parameters, so narrowing alone would yield
        ``list[Any]`` / ``dict[Any, Any]`` and silently switch type checking off
        for every later lookup.
        """
        if raw is None:
            return []
        if not isinstance(raw, list):
            logger.warning("workflow 'steps' is %s, expected a list — ignoring", type(raw).__name__)
            return []
        steps: list[dict[str, object]] = []
        for i, entry in enumerate(raw):
            step: object = entry
            if not isinstance(step, dict):  # narrow-ok: keys rebuilt with isinstance(key,str)
                logger.warning(
                    "workflow step %d is %s, expected a mapping — skipping", i, type(step).__name__
                )
                continue
            narrowed: dict[str, object] = {}
            for key, value in step.items():
                if not isinstance(key, str):
                    logger.warning("workflow step %d: ignoring non-string key %r", i, key)
                    continue
                narrowed[key] = value
            steps.append(narrowed)
        return steps

    @staticmethod
    def _resolve_env(value: str) -> str:
        """Expand ${VAR:-default} patterns using the current environment."""

        def replacer(m: re.Match[str]) -> str:
            var, _, default = m.group(1).partition(":-")
            return os.environ.get(var, default)

        return re.sub(r"\$\{([^}]+)\}", replacer, value)
