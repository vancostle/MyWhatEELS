"""Pure domain services for the Elemental NLLS workflow.

This package deliberately has no dependency on Panel or the Fitting MVC layer.
"""

from .contracts import (
    AreaModelSpec,
    BroadeningSpec,
    ContinuumSpec,
    DatasetIdentity,
    EdgeSpec,
    ExperimentalGeometry,
    FineStructureSpec,
    FitRange,
    ModelComposition,
    ModelBuildSnapshot,
    NLLSRunRequest,
    ParameterSpec,
    ReferenceFitSnapshot,
    ReferenceFitBatchResult,
    ReferenceFitFailure,
)
from .areas import AreaDefinition, ClusteringAreaAdapter
from .workspace import NLLSWorkspace
from .multifit import ElementalMultifitService, PixelFitSnapshot
from .results import FitStatus, NLLSResultsAccumulator, NLLSResultsAssembler

__all__ = [
    "AreaModelSpec",
    "AreaDefinition",
    "BroadeningSpec",
    "ContinuumSpec",
    "ClusteringAreaAdapter",
    "DatasetIdentity",
    "EdgeSpec",
    "ExperimentalGeometry",
    "FineStructureSpec",
    "FitRange",
    "ModelComposition",
    "ModelBuildSnapshot",
    "NLLSRunRequest",
    "NLLSWorkspace",
    "ElementalMultifitService",
    "PixelFitSnapshot",
    "FitStatus",
    "NLLSResultsAccumulator",
    "NLLSResultsAssembler",
    "ParameterSpec",
    "ReferenceFitSnapshot",
    "ReferenceFitBatchResult",
    "ReferenceFitFailure",
]
