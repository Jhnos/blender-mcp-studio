"""Caps on what one design run may read; values come from config/tools.yaml."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImportLimits:
    max_stl_files: int
    max_stl_bytes: int
    max_3mf_bytes: int
    max_total_stl_bytes: int
