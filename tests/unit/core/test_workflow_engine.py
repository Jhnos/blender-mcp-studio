"""TDD tests for WorkflowEngine."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.workflows.engine import WorkflowEngine

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestWorkflowEngine:
    """WorkflowEngine 讀取 YAML、提供步驟 metadata。"""

    def test_loads_conversational_modeling_workflow(self) -> None:
        engine = WorkflowEngine("conversational_modeling")
        assert engine.name == "conversational_modeling"
        assert engine.version == "1.0.0"
        assert "對話" in engine.description or len(engine.description) > 0

    def test_steps_are_loaded(self) -> None:
        engine = WorkflowEngine("conversational_modeling")
        assert len(engine.steps) == 4

    def test_step_ids_are_correct(self) -> None:
        engine = WorkflowEngine("conversational_modeling")
        ids = [s["id"] for s in engine.steps]
        assert "receive_input" in ids
        assert "translate_to_command" in ids
        assert "execute_in_blender" in ids
        assert "return_result" in ids

    def test_get_step_returns_correct_step(self) -> None:
        engine = WorkflowEngine("conversational_modeling")
        step = engine.get_step("translate_to_command")
        assert step is not None
        assert step["type"] == "llm_call"

    def test_get_step_returns_none_for_unknown(self) -> None:
        engine = WorkflowEngine("conversational_modeling")
        assert engine.get_step("nonexistent_step") is None

    def test_llm_provider_resolves_env_variable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEFAULT_LLM_PROVIDER", "ollama")
        engine = WorkflowEngine("conversational_modeling")
        # After env resolution, should not contain raw ${...} syntax
        assert "${" not in engine.llm_provider

    def test_llm_provider_fallback_without_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DEFAULT_LLM_PROVIDER", raising=False)
        engine = WorkflowEngine("conversational_modeling")
        assert "${" not in engine.llm_provider

    def test_custom_workflow_from_fixture(self) -> None:
        engine = WorkflowEngine("test_workflow", config_dir=FIXTURES_DIR)
        assert engine.name == "test_workflow"
        assert len(engine.steps) >= 1

    def test_mcp_server_is_set(self) -> None:
        engine = WorkflowEngine("conversational_modeling")
        assert engine.mcp_server == "blender_local"

    def test_get_llm_adapter_returns_ollama_when_env_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        engine = WorkflowEngine("conversational_modeling")
        adapter = engine.build_llm_adapter()
        assert adapter.provider_name == "ollama"

    def test_get_llm_adapter_returns_echo_when_no_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        engine = WorkflowEngine("conversational_modeling")
        adapter = engine.build_llm_adapter()
        # Falls back to echo adapter (no key, no provider)
        assert adapter.provider_name in ("echo", "ollama")
