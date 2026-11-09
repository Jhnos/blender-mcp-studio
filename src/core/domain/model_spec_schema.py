"""ModelSpec v2 described as JSON Schema, so a client can build a spec without reading source.

The parser (``model_spec.parse_model_spec``) is the authority; this module mirrors its keys,
types and defaults from the same constants. ``example`` is the selected model's declaration,
injected by the application (this pure schema owns no deployed model/version or filesystem
path); it names whatever printer that declaration names. ``template`` (``V2_EXAMPLE``) is a
complete spec v2 shape whose ``print_target`` holds placeholders, because code never names a
machine for a client. Spec v1 is still accepted but is not described here.
"""

from __future__ import annotations

import copy
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

#: Spec v2 shape for a client building its own spec: every value is a placeholder to replace.
V2_EXAMPLE: dict[str, object] = {
    "spec_version": "2",
    "name": "<run and package name>",
    "source": {
        "root_dir": "<root_dir from list_artifacts>",
        "stl_glob": "<glob under root_dir ending in .stl>",
        "project_3mf": "<project 3MF under root_dir>",
    },
    "print_target": {
        "printer": "<printer id from list_printers>",
        "material": "<material from that printer's list>",
    },
    "mechanism": {"suites": []},
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
    example: Mapping[str, object],
) -> dict[str, object]:
    """JSON Schema for spec v2, the selected model as ``example`` and a v2 ``template``.

    ``printers`` are the usable ones here; ``ranges`` maps a printer id to the (min, max) layer
    height of its machine profile, or ``None`` when the profile declares none. ``example`` is
    the application's selected declaration, copied as given.
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
    return {
        "spec_version": "2",
        "schema": schema,
        "example": copy.deepcopy(dict(example)),
        "template": copy.deepcopy(V2_EXAMPLE),
    }
