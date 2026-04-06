"""Workflow engine — loads YAML script definitions and executes them."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from src.infrastructure.config_loader import load_workflow


class WorkflowEngine:
    """Reads a YAML workflow definition and provides step metadata.

    Supports ${ENV_VAR:-default} syntax in YAML values.
    """

    def __init__(self, workflow_name: str, config_dir: Path | None = None) -> None:
        self._config = load_workflow(workflow_name, config_dir)
        self.name: str = str(self._config.get("name", workflow_name))
        self.version: str = str(self._config.get("version", "1.0.0"))
        self.description: str = str(self._config.get("description", ""))
        self.llm_provider: str = self._resolve_env(
            str(self._config.get("llm_provider", "ollama"))
        )
        self.mcp_server: str = str(self._config.get("mcp_server", "blender_local"))
        self.steps: list[dict[str, Any]] = list(
            self._config.get("steps", [])  # type: ignore[arg-type]
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def get_step(self, step_id: str) -> dict[str, Any] | None:
        return next((s for s in self.steps if s.get("id") == step_id), None)

    def build_llm_adapter(self):  # type: ignore[return]
        """Instantiate the correct LLM adapter via the shared factory."""
        from src.adapters.llm.factory import build_llm_adapter
        return build_llm_adapter(provider=self.llm_provider)

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_env(value: str) -> str:
        """Expand ${VAR:-default} patterns using the current environment."""
        def replacer(m: re.Match) -> str:
            var, _, default = m.group(1).partition(":-")
            return os.environ.get(var, default)

        return re.sub(r"\$\{([^}]+)\}", replacer, value)

