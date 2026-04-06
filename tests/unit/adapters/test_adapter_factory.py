"""Tests for AdapterFactoryPort and ConcreteAdapterFactory."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.core.ports.adapter_factory_port import AdapterFactoryPort


def test_adapter_factory_port_is_abstract() -> None:
    with pytest.raises(TypeError):
        AdapterFactoryPort()  # type: ignore[abstract]


def test_concrete_factory_returns_llm_port(monkeypatch) -> None:
    from src.adapters.factory.concrete_adapter_factory import ConcreteAdapterFactory
    from src.core.ports.llm_port import LLMChatPort

    mock_llm = MagicMock(spec=LLMChatPort)
    monkeypatch.setattr(
        "src.adapters.llm.factory.build_llm_adapter",
        lambda provider=None: mock_llm,
    )

    factory = ConcreteAdapterFactory()
    llm = factory.build_llm_adapter()
    assert llm is mock_llm


def test_concrete_factory_returns_blender_port(monkeypatch) -> None:
    from src.adapters.factory.concrete_adapter_factory import ConcreteAdapterFactory
    from src.core.ports.blender_port import BlenderPort

    mock_blender = MagicMock(spec=BlenderPort)
    monkeypatch.setattr(
        "src.adapters.mcp.factory.build_blender_adapter",
        lambda host=None, port=None: mock_blender,
    )

    factory = ConcreteAdapterFactory()
    blender = factory.build_blender_adapter()
    assert blender is mock_blender


def test_mock_factory_satisfies_port() -> None:
    """A mock factory can fully replace the concrete one — testability confirmed."""
    class MockFactory(AdapterFactoryPort):
        def build_llm_adapter(self, provider=None):
            return MagicMock()

        def build_blender_adapter(self, host=None, port=None):
            return MagicMock()

    factory = MockFactory()
    assert factory.build_llm_adapter() is not None
    assert factory.build_blender_adapter() is not None
