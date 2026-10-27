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
from src.core.use_cases.batch_transform import BatchTransformService
from src.core.use_cases.conversational_modeling import ConversationalModelingUseCase
from src.core.use_cases.design_pipeline import DesignPipeline
from src.core.use_cases.iterative_refinement import IterativeRefinementUseCase
from src.core.use_cases.mechanical_generation import MechanicalGenerationService
from src.core.use_cases.modeling_pipeline import ModelingPipelineUseCase
from src.core.use_cases.native_revision import NativeRevisionService
from src.core.use_cases.print_readiness import PrintReadinessService
from src.core.use_cases.scene_export import SceneExportService
from src.core.use_cases.scene_operations import SceneOperationsService
from src.core.use_cases.verification import VerificationService
from src.infrastructure.tools_config import ToolsConfig


@dataclass(frozen=True, slots=True)
class AppRuntime:
    """One dependency graph and one Blender connection owner per API process."""

    blender: BlenderPort
    scene_operations: SceneOperationsService
    batch_transform: BatchTransformService
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
    mechanical_generation: MechanicalGenerationService
    verification: VerificationService

    # Use cases are assembled here, not in delivery adapters. Building them in a
    # router hides the wiring behind ``app.state``'s ``Any`` and puts a
    # composition decision in the HTTP layer.
    conversational_modeling: ConversationalModelingUseCase
    modeling_pipeline: ModelingPipelineUseCase
    #: ``None`` when no vision provider is configured; the endpoint reports 503.
    iterative_refinement: IterativeRefinementUseCase | None

    #: Shared by REST and MCP: one pipeline, one Blender lease, one job store.
    design_pipeline: DesignPipeline
    native_revisions: NativeRevisionService
    tools: ToolsConfig


def build_runtime(env_file: Path | None = None) -> AppRuntime:
    """Build concrete outer adapters at the application's only composition root."""
    from src.adapters.artifacts.native_source import FilesystemNativeSource
    from src.adapters.artifacts.native_staging import FilesystemNativeStaging
    from src.adapters.batch_transform.blender_batch_transform import BlenderBatchTransformAdapter
    from src.adapters.events.in_memory_event_bus import InMemoryEventBus
    from src.adapters.export.blender_scene_exporter import BlenderSceneExportAdapter
    from src.adapters.factory.concrete_adapter_factory import ConcreteAdapterFactory
    from src.adapters.generation.authorized_code import (
        GENERATOR_TIMEOUT_S,
        authorized_generator_code,
    )
    from src.adapters.generation.blender_instance_builder import BlenderInstanceBuilder
    from src.adapters.generation.native_runner import NativeRunner
    from src.adapters.jobs.sqlite_job_store import SQLiteJobStore
    from src.adapters.mcp.factory import build_blender_adapter
    from src.adapters.mcp.leased_blender import LeasedBlenderPort
    from src.adapters.mesh.trimesh_cgal_integrity import TrimeshCgalIntegrity
    from src.adapters.packaging.manifest_packager import ManifestPackager
    from src.adapters.polyhaven.polyhaven_adapter import PolyHavenAdapter
    from src.adapters.print_readiness.blender_print_readiness import BlenderPrintReadinessAdapter
    from src.adapters.prompt.blender_context_prompt_builder import BlenderContextPromptBuilder
    from src.adapters.security.blender_code_sandbox import BlenderCodeSandbox
    from src.adapters.security.prompt_injection_sanitizer import PromptInjectionSanitizer
    from src.adapters.security.request_script_authority import RequestScriptAuthority
    from src.adapters.session.sqlite_session_store import SQLiteSessionStore
    from src.adapters.simulation.registered_suites_simulation import RegisteredSuitesSimulation
    from src.adapters.slicing.bambu_studio_cli import BambuStudioCli
    from src.adapters.snapshot.sqlite_snapshot_store import SQLiteSnapshotStore
    from src.adapters.text3d.hunyuan3d_adapter import build_text3d_adapter
    from src.adapters.verification.authorized_code import (
        VERIFICATION_TIMEOUT_S,
        authorized_verification_code,
    )
    from src.adapters.verification.blender_verification import BlenderVerificationAdapter
    from src.adapters.vision.factory import build_vision_adapter
    from src.core.use_cases.artifact_catalog import ArtifactCatalog
    from src.core.use_cases.blender_lease import BlenderLease
    from src.infrastructure.config_loader import default_config_dir, load_selected_model_spec
    from src.infrastructure.env_loader import load_env
    from src.infrastructure.tools_config import load_tools_config
    from src.verification.cable_route_cases import registered_suites

    load_env(env_file)
    authorized = authorized_generator_code() | authorized_verification_code()
    authority = RequestScriptAuthority()
    sandbox = BlenderCodeSandbox(
        authorized=lambda: authorized, scoped_timeout=authority.timeout_for
    )
    lease = BlenderLease()
    backend = build_blender_adapter(
        sandbox=sandbox,
        scoped_timeout=authority.timeout_for,
        script_timeouts={
            **{code: GENERATOR_TIMEOUT_S for code in authorized_generator_code()},
            **{code: VERIFICATION_TIMEOUT_S for code in authorized_verification_code()},
        },
    )
    blender = LeasedBlenderPort(backend, lease)
    adapter_factory = ConcreteAdapterFactory()
    llm = adapter_factory.build_llm_adapter()
    event_bus = InMemoryEventBus()
    prompt_builder = BlenderContextPromptBuilder()
    vision = build_vision_adapter()
    generation = MechanicalGenerationService(BlenderInstanceBuilder(blender))
    verification = VerificationService(BlenderVerificationAdapter(blender), registered_suites())
    tools = load_tools_config()
    native_sources = FilesystemNativeSource(tools.artifact_roots, tools.import_limits)
    artifacts = ArtifactCatalog(
        tools.artifact_roots,
        tools.import_limits.max_stl_files,
        load_selected_model_spec,
        native_sources=native_sources,
    )
    native_revisions = NativeRevisionService(
        artifacts,
        FilesystemNativeStaging(native_sources, tools.design_runs_dir),
        runner=NativeRunner(blender, lease, authority, tools.design_runs_dir),
    )
    design_pipeline = DesignPipeline(
        integrity=TrimeshCgalIntegrity(),
        simulation=RegisteredSuitesSimulation(verification),
        slicing=BambuStudioCli(
            tools.bambu_studio_bin, profiles_dir=default_config_dir() / "slicer-profiles"
        ),
        packaging=ManifestPackager(),
        jobs=SQLiteJobStore(tools.design_jobs_db),
        lease=lease,
        runs_dir=tools.design_runs_dir,
        artifact_roots=tools.artifact_roots,
        limits=tools.import_limits,
        artifacts=artifacts,
    )
    return AppRuntime(
        blender=blender,
        scene_operations=SceneOperationsService(blender),
        batch_transform=BatchTransformService(BlenderBatchTransformAdapter(blender)),
        scene_export=SceneExportService(BlenderSceneExportAdapter(blender)),
        print_readiness=PrintReadinessService(BlenderPrintReadinessAdapter(blender)),
        event_bus=event_bus,
        adapter_factory=adapter_factory,
        sandbox=sandbox,
        sanitizer=PromptInjectionSanitizer(),
        vision=vision,
        prompt_builder=prompt_builder,
        session_store=SQLiteSessionStore(),
        snapshot_store=SQLiteSnapshotStore(),
        polyhaven=PolyHavenAdapter(),
        text3d=build_text3d_adapter(),
        mechanical_generation=generation,
        verification=verification,
        conversational_modeling=ConversationalModelingUseCase(
            llm=llm,
            blender=blender,
            event_bus=event_bus,
            prompt_builder=prompt_builder,
            generation=generation,
        ),
        modeling_pipeline=ModelingPipelineUseCase(blender=blender, llm=llm),
        iterative_refinement=(
            None
            if vision is None
            else IterativeRefinementUseCase(llm=llm, blender=blender, vision=vision)
        ),
        design_pipeline=design_pipeline,
        native_revisions=native_revisions,
        tools=tools,
    )
