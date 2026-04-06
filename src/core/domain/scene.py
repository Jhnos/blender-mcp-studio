"""Scene aggregate root — represents the Blender 3D scene state."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SceneObject(BaseModel):
    """An object within the Blender scene."""

    model_config = {"frozen": True}

    name: str
    object_type: str
    location: tuple[float, float, float] = (0.0, 0.0, 0.0)
    visible: bool = True


class Scene(BaseModel):
    """Aggregate root for the Blender scene."""

    objects: list[SceneObject] = Field(default_factory=list)
    description: str = ""

    def with_object(self, obj: SceneObject) -> "Scene":
        """Add an object, enforcing name uniqueness."""
        from src.core.domain.exceptions import SceneCreationError
        if any(o.name == obj.name for o in self.objects):
            raise SceneCreationError(f"Object name '{obj.name}' already exists in scene")
        return self.model_copy(update={"objects": [*self.objects, obj]})

    def without_object(self, name: str) -> "Scene":
        return self.model_copy(
            update={"objects": [o for o in self.objects if o.name != name]}
        )

    def object_names(self) -> list[str]:
        return [o.name for o in self.objects]
