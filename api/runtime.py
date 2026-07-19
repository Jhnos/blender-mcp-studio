"""Application composition root shared by REST, WebSocket, and MCP."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.core.ports.adapter_factory_port import AdapterFactoryPort
from src.core.ports.blender_port import BlenderPort
from src.core.ports.code_sandbox_port import CodeSandboxPort
from src.core.ports.event_bus_port import EventBusPort
from src.core.ports.input_sanitizer_port import InputSanitizerPort
from src.core.ports.polyhaven_port import PolyHavenPort
from src.core.ports.prompt_builder_port import PromptBuilderPort
from src.core.ports.session_store_port import SessionStorePort
from src.core.ports.snapshot_store_port import SnapshotStorePort
from src.core.ports.text3d_port import Text3DGenerationPort
from src.core.ports.vision_port import VisionPort
from src.core.use_cases.print_readiness import PrintReadinessService
from src.core.use_cases.scene_export import SceneExportService
from src.core.use_cases.scene_operations import SceneOperationsService


@dataclass(frozen=True, slots=True)
class AppRuntime:
    """One dependency graph and one Blender connection owner per API process."""

    blender: BlenderPort
    scene_operations: SceneOperationsService
    scene_export: SceneExportService
    print_readiness: PrintReadinessService
    event_bus: EventBusPort
    adapter_factory: AdapterFactoryPort
    sandbox: CodeSandboxPort
    sanitizer: InputSanitizerPort
    vision: VisionPort | None
    prompt_builder: PromptBuilderPort
    session_store: SessionStorePort
    snapshot_store: SnapshotStorePort
    polyhaven: PolyHavenPort
    text3d: Text3DGenerationPort | None


def build_runtime(env_file: Path | None = None) -> AppRuntime:
    """Build concrete outer adapters at the application's only composition root."""
    from src.adapters.events.in_memory_event_bus import InMemoryEventBus
    from src.adapters.export.blender_scene_exporter import BlenderSceneExportAdapter
    from src.adapters.factory.concrete_adapter_factory import ConcreteAdapterFactory
    from src.adapters.mcp.factory import build_blender_adapter
    from src.adapters.polyhaven.polyhaven_adapter import PolyHavenAdapter
    from src.adapters.print_readiness.blender_print_readiness import BlenderPrintReadinessAdapter
    from src.adapters.prompt.blender_context_prompt_builder import BlenderContextPromptBuilder
    from src.adapters.security.blender_code_sandbox import BlenderCodeSandbox
    from src.adapters.security.prompt_injection_sanitizer import PromptInjectionSanitizer
    from src.adapters.session.sqlite_session_store import SQLiteSessionStore
    from src.adapters.snapshot.sqlite_snapshot_store import SQLiteSnapshotStore
    from src.adapters.text3d.hunyuan3d_adapter import build_text3d_adapter
    from src.adapters.vision.factory import build_vision_adapter
    from src.infrastructure.env_loader import load_env

    load_env(env_file)
    sandbox = BlenderCodeSandbox()
    blender = build_blender_adapter(sandbox=sandbox)
    return AppRuntime(
        blender=blender,
        scene_operations=SceneOperationsService(blender),
        scene_export=SceneExportService(BlenderSceneExportAdapter(blender)),
        print_readiness=PrintReadinessService(BlenderPrintReadinessAdapter(blender)),
        event_bus=InMemoryEventBus(),
        adapter_factory=ConcreteAdapterFactory(),
        sandbox=sandbox,
        sanitizer=PromptInjectionSanitizer(),
        vision=build_vision_adapter(),
        prompt_builder=BlenderContextPromptBuilder(),
        session_store=SQLiteSessionStore(),
        snapshot_store=SQLiteSnapshotStore(),
        polyhaven=PolyHavenAdapter(),
        text3d=build_text3d_adapter(),
    )
