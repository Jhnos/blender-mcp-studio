"""Client-neutral FastMCP tool registry for Blender scene operations."""

from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.utilities.types import Image
from mcp.types import ToolAnnotations

from src.adapters.mcp_server.design_tools import register_design_tools
from src.adapters.mcp_server.errors import exclusive, refuse_during_design_stage, tool_error
from src.adapters.mcp_server.schemas import (
    RGBA,
    MaxViewportSize,
    Name,
    ObjectTypeInput,
    OverhangAngle,
    UnitFloat,
    Vec3,
    WallThickness,
)
from src.adapters.verification.authorized_code import VERIFICATION_TIMEOUT_S
from src.core.domain.exceptions import (
    BlenderConnectionError,
    PrintReadinessError,
    SceneOperationError,
)
from src.core.domain.print_readiness import PrintReadinessReport, PrintReadinessSpec
from src.core.domain.scene_operations import (
    BlenderStatus,
    ColorRGBA,
    CreateObjectSpec,
    MaterialSpec,
    ModifyObjectSpec,
    ObjectDetails,
    ObjectType,
    OperationReceipt,
    SceneSummary,
    Vector3,
)
from src.core.domain.verification import VerificationError, VerificationReport, VerificationSuite
from src.core.ports.mechanical_generation_port import InstanceCatalogPort
from src.core.ports.print_readiness_port import PrintReadinessQueryPort
from src.core.ports.scene_operations_port import SceneCommandPort, SceneQueryPort
from src.core.ports.verification_port import VerificationQueryPort
from src.core.use_cases.blender_lease import BlenderLease
from src.core.use_cases.design_pipeline import DesignPipeline


def _vec(value: tuple[float, float, float] | None) -> Vector3 | None:
    return None if value is None else Vector3(*value)


#: The tool call wraps one Blender script; it must outlive the script's own deadline
#: by the transport and decoding overhead, or the client sees a cancelled call
#: instead of the adapter's honest "did not answer within N s".
VERIFICATION_TOOL_TIMEOUT_S = VERIFICATION_TIMEOUT_S + 30.0


def create_mcp_server(
    queries: SceneQueryPort,
    commands: SceneCommandPort,
    print_readiness: PrintReadinessQueryPort,
    verification: VerificationQueryPort,
    *,
    design: DesignPipeline | None = None,
    generation: InstanceCatalogPort | None = None,
    lease: BlenderLease | None = None,
) -> FastMCP:
    """Create the public MCP registry using only incoming application ports.

    ``lease`` is the runtime's one Blender lease (the design pipeline's): scene-changing tools
    answer busy while a design run stage holds it, and long Blender tools hold it themselves.
    """
    shared = lease or (design.lease if design is not None else BlenderLease())

    mcp = FastMCP(
        "blender-mcp-studio",
        instructions=(
            "Use dedicated scene tools; arbitrary Python execution is intentionally unavailable."
        ),
        mask_error_details=True,
        strict_input_validation=True,
    )

    @mcp.tool(
        timeout=5.0,
        annotations=ToolAnnotations(
            title="Blender status",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def blender_status() -> BlenderStatus:
        """Check whether the shared Blender addon connection is currently available."""
        try:
            return await queries.status()
        except (SceneOperationError, BlenderConnectionError) as exc:
            raise tool_error(exc) from exc

    @mcp.tool(
        timeout=10.0,
        annotations=ToolAnnotations(
            title="Get scene info",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def get_scene_info() -> SceneSummary:
        """Return the scene name, counts, and up to ten object summaries."""
        try:
            return await queries.get_scene_info()
        except (SceneOperationError, BlenderConnectionError) as exc:
            raise tool_error(exc) from exc

    @mcp.tool(
        timeout=10.0,
        annotations=ToolAnnotations(
            title="Get object info",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def get_object_info(name: Name) -> ObjectDetails:
        """Return transforms, visibility, and materials for one object by exact name."""
        try:
            return await queries.get_object_info(name)
        except (SceneOperationError, BlenderConnectionError) as exc:
            raise tool_error(exc) from exc

    @mcp.tool(
        timeout=30.0,
        annotations=ToolAnnotations(
            title="Get viewport screenshot",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def get_viewport_screenshot(max_size: MaxViewportSize = 800) -> Image:
        """Capture the active 3D viewport as a PNG limited to 200–1600 pixels."""
        try:
            shot = await queries.get_viewport_screenshot(max_size)
            return Image(data=shot.png_bytes, format="png")
        except (SceneOperationError, BlenderConnectionError) as exc:
            raise tool_error(exc) from exc

    @mcp.tool(
        timeout=30.0,
        annotations=ToolAnnotations(
            title="Check 3D print readiness",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def check_print_readiness(
        selection_only: bool = False,
        apply_modifiers: bool = True,
        min_wall_thickness_mm: WallThickness = 0.8,
        overhang_angle_deg: OverhangAngle = 45.0,
    ) -> PrintReadinessReport:
        """Inspect visible meshes for common slicing risks without changing the scene."""
        refuse_during_design_stage(shared)
        try:
            return await print_readiness.check(
                PrintReadinessSpec(
                    selection_only=selection_only,
                    apply_modifiers=apply_modifiers,
                    min_wall_thickness_mm=min_wall_thickness_mm,
                    overhang_angle_deg=overhang_angle_deg,
                )
            )
        except (PrintReadinessError, BlenderConnectionError) as exc:
            raise tool_error(exc) from exc

    @mcp.tool(
        timeout=30.0,
        annotations=ToolAnnotations(
            title="Create object",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def create_object(
        object_type: ObjectTypeInput,
        name: Name | None = None,
        location: Vec3 = (0.0, 0.0, 0.0),
        scale: Vec3 = (1.0, 1.0, 1.0),
    ) -> OperationReceipt:
        """Create one cube mesh, Bezier curve, light, or camera with a transform."""
        refuse_during_design_stage(shared)
        try:
            spec = CreateObjectSpec(
                object_type=ObjectType(object_type),
                name=name,
                location=Vector3(*location),
                scale=Vector3(*scale),
            )
            return await commands.create_object(spec)
        except (SceneOperationError, BlenderConnectionError) as exc:
            raise tool_error(exc) from exc

    @mcp.tool(
        timeout=30.0,
        annotations=ToolAnnotations(
            title="Modify object",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def modify_object(
        name: Name,
        location: Vec3 | None = None,
        rotation: Vec3 | None = None,
        scale: Vec3 | None = None,
        visible: bool | None = None,
    ) -> OperationReceipt:
        """Set selected transforms or visibility; omitted fields remain unchanged."""
        refuse_during_design_stage(shared)
        try:
            spec = ModifyObjectSpec(
                name=name,
                location=_vec(location),
                rotation=_vec(rotation),
                scale=_vec(scale),
                visible=visible,
            )
            return await commands.modify_object(spec)
        except (SceneOperationError, BlenderConnectionError) as exc:
            raise tool_error(exc) from exc

    @mcp.tool(
        timeout=30.0,
        annotations=ToolAnnotations(
            title="Delete object",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def delete_object(name: Name) -> OperationReceipt:
        """Permanently remove one Blender object by exact name."""
        refuse_during_design_stage(shared)
        try:
            return await commands.delete_object(name)
        except (SceneOperationError, BlenderConnectionError) as exc:
            raise tool_error(exc) from exc

    @mcp.tool(
        timeout=30.0,
        annotations=ToolAnnotations(
            title="Apply material",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def apply_material(
        object_name: Name,
        material_name: Name,
        color: RGBA | None = None,
        metallic: UnitFloat | None = None,
        roughness: UnitFloat | None = None,
    ) -> OperationReceipt:
        """Create or update a Principled BSDF material and apply it to one object."""
        refuse_during_design_stage(shared)
        try:
            rgba = None if color is None else ColorRGBA(*color)
            spec = MaterialSpec(object_name, material_name, rgba, metallic, roughness)
            return await commands.apply_material(spec)
        except (SceneOperationError, BlenderConnectionError) as exc:
            raise tool_error(exc) from exc

    @mcp.tool(
        timeout=5.0,
        annotations=ToolAnnotations(
            title="List verification suites",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def list_verification_suites() -> tuple[VerificationSuite, ...]:
        """List registered model checks, their required model and case coverage."""
        return await verification.list_suites()

    @mcp.tool(
        timeout=VERIFICATION_TOOL_TIMEOUT_S,
        annotations=ToolAnnotations(
            title="Run verification suite",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def run_verification_suite(suite_id: Name) -> VerificationReport:
        """Run a registered suite on the current scene and restore poses and selection.

        Accepts only names from list_verification_suites. Creates temporary fixtures
        or moves electrode poses during checks. Returns individual measured verdicts;
        a failed check is a report, not an execution error. Does not build or load models.
        """
        async with exclusive(shared, "run_verification_suite"):
            try:
                return await verification.run(suite_id)
            except (VerificationError, BlenderConnectionError) as exc:
                raise tool_error(exc) from exc

    register_design_tools(mcp, design=design, generation=generation, lease=shared)
    return mcp
