"""Client-neutral FastMCP tool registry for Blender scene operations."""

from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image
from mcp.types import ToolAnnotations

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
from src.core.ports.print_readiness_port import PrintReadinessQueryPort
from src.core.ports.scene_operations_port import SceneCommandPort, SceneQueryPort


def _vec(value: tuple[float, float, float] | None) -> Vector3 | None:
    return None if value is None else Vector3(*value)


def _tool_error(exc: Exception) -> ToolError:
    if isinstance(exc, BlenderConnectionError):
        return ToolError("Blender is unavailable. Start Blender and enable the addon on port 9876.")
    return ToolError(str(exc))


def create_mcp_server(
    queries: SceneQueryPort,
    commands: SceneCommandPort,
    print_readiness: PrintReadinessQueryPort,
) -> FastMCP:
    """Create the public MCP registry using only incoming application ports."""

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
            raise _tool_error(exc) from exc

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
            raise _tool_error(exc) from exc

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
            raise _tool_error(exc) from exc

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
            raise _tool_error(exc) from exc

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
            raise _tool_error(exc) from exc

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
        try:
            spec = CreateObjectSpec(
                object_type=ObjectType(object_type),
                name=name,
                location=Vector3(*location),
                scale=Vector3(*scale),
            )
            return await commands.create_object(spec)
        except (SceneOperationError, BlenderConnectionError) as exc:
            raise _tool_error(exc) from exc

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
            raise _tool_error(exc) from exc

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
        try:
            return await commands.delete_object(name)
        except (SceneOperationError, BlenderConnectionError) as exc:
            raise _tool_error(exc) from exc

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
        try:
            rgba = None if color is None else ColorRGBA(*color)
            spec = MaterialSpec(object_name, material_name, rgba, metallic, roughness)
            return await commands.apply_material(spec)
        except (SceneOperationError, BlenderConnectionError) as exc:
            raise _tool_error(exc) from exc

    return mcp
