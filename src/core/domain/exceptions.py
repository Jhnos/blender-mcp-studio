"""Domain exceptions for the Blender MCP Studio."""


class DomainError(Exception):
    """Base domain error."""


class SceneCreationError(DomainError):
    """Raised when a scene operation fails."""


class SceneOperationError(DomainError):
    """A scene operation failed with a recoverable, user-facing reason."""


class SceneExportError(DomainError):
    """A requested scene export could not produce a valid artifact."""


class PrintReadinessError(DomainError):
    """A print-readiness inspection could not produce a trustworthy report."""


class LLMConnectionError(DomainError):
    """Raised when the LLM is unreachable."""


class BlenderConnectionError(DomainError):
    """Raised when Blender MCP socket is unreachable."""


class WorkflowError(DomainError):
    """Raised when a workflow script fails."""
