"""Unit tests for high-level tool -> execute_code translation.

Regression guard: the LLM emits create_object/delete_object/modify_object/
apply_material, but the Blender addon only handles execute_code. Sending those
raw produced "Unknown command type" and the scene never changed. Every
translatable tool must become an execute_code Command here.
"""

from src.core.domain.command import Command
from src.core.use_cases.blender_tool_codegen import translate


def test_create_object_becomes_execute_code():
    out = translate(Command(tool_name="create_object",
                            arguments={"type": "MESH", "name": "foo", "location": [1, 2, 3]}))
    assert out.tool_name == "execute_code"
    code = out.arguments["code"]
    assert "import bpy" in code
    assert "primitive_cube_add" in code
    assert 'obj.name = "foo"' in code


def test_each_translatable_tool_maps_to_execute_code():
    for tool, args in [
        ("create_object", {"type": "MESH"}),
        ("delete_object", {"name": "x"}),
        ("modify_object", {"name": "x", "location": [0, 0, 1]}),
        ("apply_material", {"object_name": "x", "material_name": "m", "color": [1, 0, 0]}),
    ]:
        out = translate(Command(tool_name=tool, arguments=args))
        assert out.tool_name == "execute_code", f"{tool} not translated"
        assert "import bpy" in out.arguments["code"]


def test_passthrough_untranslatable_tools():
    for tool in ["execute_code", "get_scene_info", "get_object_info"]:
        cmd = Command(tool_name=tool, arguments={"code": "x"} if tool == "execute_code" else {})
        assert translate(cmd) is cmd  # unchanged, same object


def test_string_argument_is_a_literal_not_injectable_code():
    # NOTE: the "os.system" below is an INERT test payload (a string), never run.
    # This test asserts the codegen embeds it as a quoted literal, so a crafted
    # object name cannot become executable code in the generated bpy snippet.
    out = translate(Command(tool_name="create_object",
                            arguments={"name": "a'; import os; os.system('x')#"}))
    code = out.arguments["code"]
    # the payload lives inside a quoted string on the name line, not as a statement
    assert "os.system" in code  # present...
    assert "obj.name = " in code
    # ...but only ever inside the assigned string literal
    for line in code.splitlines():
        if "os.system" in line:
            assert line.strip().startswith("obj.name = ")


def test_apply_material_pads_rgb_to_rgba():
    out = translate(Command(tool_name="apply_material",
                            arguments={"object_name": "o", "material_name": "m", "color": [1, 0, 0]}))
    assert "[1.0, 0.0, 0.0, 1.0]" in out.arguments["code"]
