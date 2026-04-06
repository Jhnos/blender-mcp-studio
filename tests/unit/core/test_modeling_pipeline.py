"""Unit tests for ModelingPipelineUseCase and PipelineLoader."""

from __future__ import annotations

import pytest
import yaml

from src.core.domain.pipeline import PipelineStage, StageStatus
from src.core.use_cases.modeling_pipeline import ModelingPipelineUseCase
from src.core.ports.mcp_port import ToolResult


class MockBlenderForPipeline:
    """Controllable Blender mock for pipeline tests."""

    def __init__(self, fail_tools: set[str] | None = None) -> None:
        self.executed: list[tuple[str, dict]] = []
        self._fail_tools = fail_tools or set()

    async def connect(self): ...
    async def disconnect(self): ...
    async def is_connected(self): return True
    async def get_scene_info(self): return {"objects": []}

    async def execute(self, command):
        self.executed.append((command.tool_name, dict(command.arguments)))
        if command.tool_name in self._fail_tools:
            return ToolResult(success=False, output=None, error="mock failure")
        return ToolResult(success=True, output=f"ok:{command.tool_name}", error=None)

    async def call_tool(self, tool_name, arguments):
        return ToolResult(success=False, output=None, error="not used")


def make_stages(*tool_names: str, optional: bool = False) -> list[PipelineStage]:
    return [
        PipelineStage(
            name=f"stage_{t}",
            description="",
            tool_name=t,
            arguments_template={},
            optional=optional,
        )
        for t in tool_names
    ]


@pytest.mark.asyncio
async def test_pipeline_all_success():
    blender = MockBlenderForPipeline()
    stages = make_stages("create_object", "apply_material", "get_scene_info")
    use_case = ModelingPipelineUseCase(blender=blender)

    result = await use_case.execute(stages, context={}, pipeline_name="test")

    assert result.success is True
    assert len(result.stage_results) == 3
    assert all(r.status == StageStatus.DONE for r in result.stage_results)


@pytest.mark.asyncio
async def test_pipeline_stops_on_required_failure():
    blender = MockBlenderForPipeline(fail_tools={"apply_material"})
    stages = make_stages("create_object", "apply_material", "get_scene_info")
    use_case = ModelingPipelineUseCase(blender=blender)

    result = await use_case.execute(stages, context={}, pipeline_name="test")

    assert result.success is False
    assert result.failed_stage is not None
    assert result.failed_stage.stage_name == "stage_apply_material"
    # get_scene_info should NOT have been executed
    executed_names = [t for t, _ in blender.executed]
    assert "get_scene_info" not in executed_names


@pytest.mark.asyncio
async def test_pipeline_skips_optional_failure():
    blender = MockBlenderForPipeline(fail_tools={"apply_material"})
    stages = [
        PipelineStage("stage_create", "", "create_object", {}, optional=False),
        PipelineStage("stage_mat", "", "apply_material", {}, optional=True),  # optional
        PipelineStage("stage_scene", "", "get_scene_info", {}, optional=False),
    ]
    use_case = ModelingPipelineUseCase(blender=blender)

    result = await use_case.execute(stages, context={}, pipeline_name="test")

    assert result.success is True  # optional failure → skipped, not failed
    assert result.stage_results[1].status == StageStatus.SKIPPED
    assert result.stage_results[2].status == StageStatus.DONE


@pytest.mark.asyncio
async def test_pipeline_resolves_placeholders():
    blender = MockBlenderForPipeline()
    stages = [
        PipelineStage(
            name="stage_create",
            description="",
            tool_name="create_object",
            arguments_template={"name": "{{ object_name }}", "type": "{{ object_type }}"},
        )
    ]
    context = {"object_name": "MyCat", "object_type": "MESH"}
    use_case = ModelingPipelineUseCase(blender=blender)

    await use_case.execute(stages, context=context, pipeline_name="test")

    assert blender.executed[0] == ("create_object", {"name": "MyCat", "type": "MESH"})


@pytest.mark.asyncio
async def test_pipeline_propagates_output_to_context():
    blender = MockBlenderForPipeline()
    stages = make_stages("create_object", "get_scene_info")
    context: dict = {}
    use_case = ModelingPipelineUseCase(blender=blender)

    result = await use_case.execute(stages, context=context, pipeline_name="test")

    # Output of create_object should be in context for subsequent stages
    assert "stage_create_object_output" in context


@pytest.mark.asyncio
async def test_pipeline_validation_key_fails():
    blender = MockBlenderForPipeline()
    stages = [
        PipelineStage(
            name="stage_validate",
            description="",
            tool_name="get_scene_info",
            arguments_template={},
            validation_key="MUST_CONTAIN_THIS",  # not in output "ok:get_scene_info"
        )
    ]
    use_case = ModelingPipelineUseCase(blender=blender)

    result = await use_case.execute(stages, context={}, pipeline_name="test")

    assert result.success is False
    assert result.stage_results[0].status == StageStatus.FAILED


@pytest.mark.asyncio
async def test_pipeline_validation_key_passes():
    blender = MockBlenderForPipeline()
    stages = [
        PipelineStage(
            name="stage_validate",
            description="",
            tool_name="get_scene_info",
            arguments_template={},
            validation_key="ok:",  # present in "ok:get_scene_info"
        )
    ]
    use_case = ModelingPipelineUseCase(blender=blender)

    result = await use_case.execute(stages, context={}, pipeline_name="test")

    assert result.success is True


@pytest.mark.asyncio
async def test_pipeline_loader_loads_yaml(tmp_path):
    yaml_content = {
        "pipelines": {
            "test_pipe": {
                "description": "Test",
                "stages": [
                    {"name": "s1", "tool": "create_object", "arguments": {"type": "MESH"}},
                    {"name": "s2", "tool": "get_scene_info", "optional": True},
                ],
            }
        }
    }
    config_file = tmp_path / "pipeline.yaml"
    config_file.write_text(yaml.dump(yaml_content))

    from src.adapters.pipeline.pipeline_loader import PipelineLoader
    loader = PipelineLoader(config_path=config_file)
    stages = loader.load("test_pipe")

    assert len(stages) == 2
    assert stages[0].name == "s1"
    assert stages[0].tool_name == "create_object"
    assert stages[0].arguments_template == {"type": "MESH"}
    assert stages[1].optional is True


@pytest.mark.asyncio
async def test_pipeline_loader_raises_on_missing_pipeline(tmp_path):
    config_file = tmp_path / "pipeline.yaml"
    config_file.write_text(yaml.dump({"pipelines": {}}))

    from src.adapters.pipeline.pipeline_loader import PipelineLoader
    loader = PipelineLoader(config_path=config_file)

    with pytest.raises(KeyError, match="not found"):
        loader.load("nonexistent")


@pytest.mark.asyncio
async def test_pipeline_loader_lists_pipelines(tmp_path):
    config_file = tmp_path / "pipeline.yaml"
    config_file.write_text(yaml.dump({
        "pipelines": {
            "pipe_a": {"stages": []},
            "pipe_b": {"stages": []},
        }
    }))

    from src.adapters.pipeline.pipeline_loader import PipelineLoader
    loader = PipelineLoader(config_path=config_file)
    names = loader.list_pipelines()

    assert set(names) == {"pipe_a", "pipe_b"}


@pytest.mark.asyncio
async def test_real_yaml_config_loads():
    """Smoke test: the actual modeling_pipeline.yaml is valid and loadable."""
    from src.adapters.pipeline.pipeline_loader import PipelineLoader
    loader = PipelineLoader()
    pipelines = loader.list_pipelines()

    assert "black_cat_phone_stand" in pipelines
    assert "3d_print" in pipelines

    stages = loader.load("black_cat_phone_stand")
    assert len(stages) > 3  # has multiple stages
