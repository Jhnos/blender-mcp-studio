"""Domain exceptions for the Blender MCP Studio."""


class DomainError(Exception):
    """Base domain error."""


class SceneCreationError(DomainError):
    """Raised when a scene operation fails."""


class SceneOperationError(DomainError):
    """A scene operation failed with a recoverable, user-facing reason."""


class BatchTransformError(SceneOperationError):
    """A batch transform request or execution could not be completed safely."""


class SceneExportError(DomainError):
    """A requested scene export could not produce a valid artifact."""


class PrintReadinessError(DomainError):
    """A print-readiness inspection could not produce a trustworthy report."""


class LLMConnectionError(DomainError):
    """Raised when the LLM is unreachable."""


class ExternalServiceError(DomainError):
    """An external service the studio depends on answered with a failure.

    Vision, text-to-3D and LLM providers are outside this process. When one
    of them fails, the request was well-formed and Blender was fine: the
    honest HTTP status is 502, not the 500 a blanket ``except`` used to
    manufacture, and not the 422 a generic domain error would imply.
    """


class VisionAnalysisError(ExternalServiceError):
    """The vision provider could not analyse the image."""


class TextTo3DError(ExternalServiceError):
    """The text-to-3D provider could not produce a mesh."""


class LLMProviderError(ExternalServiceError):
    """The LLM provider was reached and answered with a failure.

    Distinct from ``LLMConnectionError`` (unreachable, a 503): a 4xx/5xx or
    an overloaded model is the provider's failure, a 502.
    """


class BlenderConnectionError(DomainError):
    """Raised when Blender MCP socket is unreachable."""


class UnknownInstanceError(DomainError):
    """A build was asked for a slug that is not in the instance registry.

    The registry is the whole input surface of the generation path: the slug
    indexes a closed set, and nothing else from the request reaches the code
    Blender runs. A slug that is not in it is a 404, not a malformed request.
    """


class MechanicalGenerationError(ExternalServiceError):
    """A generator ran inside Blender and did not produce what it declared.

    Blender is outside this process. A generator that raises, or that ships a
    part list the instance does not declare, is that external system failing —
    a 502. It is not a 200 with surprising content: the manifest, the package
    tests and the README are all written against the declared list.
    """
