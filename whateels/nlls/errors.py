"""Domain exceptions raised by the Elemental NLLS services."""


class NLLSError(Exception):
    """Base class for actionable Elemental NLLS errors."""


class InvalidSourceError(NLLSError):
    """The active source does not satisfy the preprocessing contract."""


class InvalidGeometryError(NLLSError):
    """E0/alpha/beta are missing, non-finite, or outside their valid domain."""


class MissingOOSTableError(NLLSError):
    """An OOS file or requested subshell is unavailable."""


class InvalidOOSDataError(NLLSError):
    """An OOS table or a derived physical curve is invalid."""


class EmptyModelError(NLLSError):
    """An area has no valid OOS continuum from which to build a model."""


class UnsupportedModelCompositionError(NLLSError):
    """The requested model composition is not supported."""


class InsufficientReferenceDataError(NLLSError):
    """A reference spectrum has too few finite samples for its model."""


class ReferenceFitError(NLLSError):
    """lmfit did not produce a finite, successful reference fit."""


class InvalidClusteringError(NLLSError):
    """The clustering result cannot define areas for the active dataset."""
