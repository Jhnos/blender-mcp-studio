"""Domain exceptions for the Blender MCP Studio."""


class DomainError(Exception):
    """Base domain error."""


class SceneCreationError(DomainError):
    """Raised when a scene operation fails."""


class LLMConnectionError(DomainError):
    """Raised when the LLM is unreachable."""


class BlenderConnectionError(DomainError):
    """Raised when Blender MCP socket is unreachable."""


class WorkflowError(DomainError):
    """Raised when a workflow script fails."""
