"""Narrow executable substrate for ``recursive-reconfiguration-v1``.

This package implements transport/cut separation, dependency invalidation,
and mechanically derived structural deltas.  It does not implement semantic
formation, public articulation, or CBRA as a whole.
"""

from .models import (
    Allocation,
    ConfigurationTrace,
    CutEnactment,
    CutPosition,
    LocalPositionRef,
    ReconfigurationDelta,
    Relation,
    StructuralDimension,
    TransportTrace,
)
from .arrangements import (
    ArrangementComparison,
    ArrangementExplorer,
    BurdenRedistributionCandidate,
    compare_arrangements,
)
from .substrate import (
    InvalidReconfiguration,
    ReconfigurationSubstrate,
    StorageOntologyViolation,
)

__all__ = [
    "Allocation",
    "ConfigurationTrace",
    "CutEnactment",
    "CutPosition",
    "InvalidReconfiguration",
    "LocalPositionRef",
    "ReconfigurationDelta",
    "ReconfigurationSubstrate",
    "Relation",
    "StorageOntologyViolation",
    "StructuralDimension",
    "ArrangementComparison",
    "ArrangementExplorer",
    "BurdenRedistributionCandidate",
    "compare_arrangements",
    "TransportTrace",
]
