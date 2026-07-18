"""Strict FastMCP boundary types for public Blender scene tools."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
Name = Annotated[str, Field(strict=True, min_length=1, max_length=63)]
Vec3 = tuple[FiniteFloat, FiniteFloat, FiniteFloat]
RGBA = tuple[
    Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)],
    Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)],
    Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)],
    Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)],
]
ObjectTypeInput = Literal["MESH", "CURVE", "LIGHT", "CAMERA"]
UnitFloat = Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
MaxViewportSize = Annotated[int, Field(strict=True, ge=200, le=1600)]
