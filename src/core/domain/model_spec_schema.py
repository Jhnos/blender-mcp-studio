"""ModelSpec v1 described as JSON Schema, so a client can build a spec without reading source.

The parser (``model_spec.parse_model_spec``) is the authority; this module mirrors its keys,
types and defaults from the same constants, and ``V1_EXAMPLE`` is the v78 gate contract's spec
(``scripts/verify/contracts/design_pipeline_v78.json``; a unit test keeps them equal).
"""

from __future__ import annotations

from src.core.domain.model_spec import (
    MECHANISM_V1_UNSUPPORTED,
    SUPPORTED_SPEC_VERSION,
    ImportedArtifact,
    PrintTarget,
)

V1_EXAMPLE: dict[str, object] = {
    "spec_version": "1",
    "name": "lab-station-v78",
    "source": {
        "root_dir": "雙上臂四點梯形-v78",
        "stl_glob": "STL/列印零件/*.stl",
        "project_3mf": "整機69件-單盤排版-v78.3mf",
    },
    "mechanism": {"suites": []},
}

_PATH_RULES = "relative, no '..', no hidden ('.'-prefixed) part, must stay inside the root"


def describe_model_spec(printers: tuple[str, ...], materials: tuple[str, ...]) -> dict[str, object]:
    """JSON Schema for spec v1 plus a complete worked example; printers/materials from the slicer."""
    source, target = ImportedArtifact(root_dir=""), PrintTarget()
    schema: dict[str, object] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "ModelSpec",
        "type": "object",
        "additionalProperties": False,
        "required": ["spec_version", "name", "source"],
        "properties": {
            "spec_version": {"const": SUPPORTED_SPEC_VERSION},
            "name": {"type": "string", "minLength": 1, "description": "Run and package name."},
            "source": {
                "type": "object",
                "additionalProperties": False,
                "required": ["root_dir"],
                "description": "An existing deliverable directory; find one with list_artifacts.",
                "properties": {
                    "root_dir": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Directory relative to an artifact root (list_artifacts "
                        "root_dir); no hidden part.",
                    },
                    "stl_glob": {
                        "type": "string",
                        "default": source.stl_glob,
                        "description": f"Glob under root_dir ending in .stl; {_PATH_RULES}.",
                    },
                    "project_3mf": {
                        "type": "string",
                        "description": "Project 3MF under root_dir to slice; without it the print "
                        f"stage fails. {_PATH_RULES}.",
                    },
                },
            },
            "print_target": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "printer": {
                        "type": "string",
                        "enum": list(printers),
                        "default": target.printer,
                    },
                    "material": {
                        "type": "string",
                        "enum": list(materials),
                        "default": target.material,
                    },
                    "layer_height_mm": {
                        "type": "number",
                        "exclusiveMinimum": 0,
                        "default": target.layer_height_mm,
                    },
                    "support": {"type": "boolean", "default": target.support},
                    "brim_mm": {"type": "number", "minimum": 0, "default": target.brim_mm},
                },
            },
            "mechanism": {
                "type": "object",
                "additionalProperties": False,
                "description": f"{MECHANISM_V1_UNSUPPORTED}. Omit it or pass an empty list; "
                "the mechanism stage is then not_applicable.",
                "properties": {
                    "suites": {"type": "array", "items": {"type": "string"}, "maxItems": 0}
                },
            },
        },
    }
    return {"spec_version": SUPPORTED_SPEC_VERSION, "schema": schema, "example": V1_EXAMPLE}
