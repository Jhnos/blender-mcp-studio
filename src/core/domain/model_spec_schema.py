"""ModelSpec v2 described as JSON Schema, so a client can build a spec without reading source.

The parser (``model_spec.parse_model_spec``) is the authority; this module mirrors its keys,
types and defaults from the same constants. ``V2_EXAMPLE`` is a complete worked spec. Spec v1
is still accepted but is not described here; ``V1_EXAMPLE`` is the v78 gate contract's spec
(``scripts/verify/contracts/design_pipeline_v78.json``; a unit test keeps them equal).
"""

from __future__ import annotations

from collections.abc import Mapping

from src.core.domain.model_spec import (
    JOB_DEFAULTS as JOB,
)
from src.core.domain.model_spec import (
    LEGACY_V1_MATERIAL,
    LEGACY_V1_PRINTER,
    MECHANISM_V1_UNSUPPORTED,
    ImportedArtifact,
)
from src.core.domain.printer_catalog import PrinterProfile

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

V2_EXAMPLE: dict[str, object] = {
    **V1_EXAMPLE,
    "spec_version": "2",
    "print_target": {"printer": LEGACY_V1_PRINTER, "material": LEGACY_V1_MATERIAL},
}

_PATH_RULES = "relative, no '..', no hidden ('.'-prefixed) part, must stay inside the root"


def _layer_height(printer: PrinterProfile, bounds: tuple[float, float] | None) -> dict[str, object]:
    keys = [float(h) for h, _ in printer.processes]
    if bounds is None:
        return {
            "enum": keys,
            "description": f"{printer.id}'s machine profile declares no layer-height range, so "
            "only these exact catalog heights are accepted (mm).",
        }
    return {
        "minimum": bounds[0],
        "maximum": bounds[1],
        "description": f"{printer.id}'s machine range in mm. An exact catalog height "
        f"({', '.join(f'{k:g}' for k in keys)}) uses that process; any other in-range height "
        "uses the nearest base process.",
    }


def _per_printer(printer: PrinterProfile, bounds: tuple[float, float] | None) -> dict[str, object]:
    """What ``printer`` accepts: its own materials and layer heights."""
    return {
        "if": {"properties": {"printer": {"const": printer.id}}, "required": ["printer"]},
        "then": {
            "properties": {
                "material": {"enum": [m for m, _ in printer.filaments]},
                "layer_height_mm": _layer_height(printer, bounds),
            }
        },
    }


def describe_model_spec(
    printers: tuple[PrinterProfile, ...],
    ranges: Mapping[str, tuple[float, float] | None],
) -> dict[str, object]:
    """JSON Schema for spec v2 plus a worked example.

    ``printers`` are the usable ones here; ``ranges`` maps a printer id to the (min, max) layer
    height of its machine profile, or ``None`` when the profile declares none.
    """
    source = ImportedArtifact(root_dir="")
    schema: dict[str, object] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "ModelSpec",
        "type": "object",
        "additionalProperties": False,
        "required": ["spec_version", "name", "source", "print_target"],
        "description": "spec_version 1 is still accepted: a missing printer/material then falls "
        f"back to {LEGACY_V1_PRINTER} / {LEGACY_V1_MATERIAL} and the run report says so. "
        "Spec v2 never chooses a machine for you.",
        "properties": {
            "spec_version": {"const": "2"},
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
                "required": ["printer", "material"],
                "description": "printer and material are required: list_printers shows the "
                "choices; the material and layer height must be ones that printer offers.",
                "properties": {
                    "printer": {"type": "string", "enum": [p.id for p in printers]},
                    "material": {
                        "type": "string",
                        "enum": sorted({m for p in printers for m, _ in p.filaments}),
                    },
                    "layer_height_mm": {
                        "type": "number",
                        "exclusiveMinimum": 0,
                        "default": JOB.layer_height_mm,
                    },
                    "support": {"type": "boolean", "default": JOB.support},
                    "brim_mm": {"type": "number", "minimum": 0, "default": JOB.brim_mm},
                },
                "allOf": [_per_printer(p, ranges.get(p.id)) for p in printers],
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
    return {"spec_version": "2", "schema": schema, "example": V2_EXAMPLE}
