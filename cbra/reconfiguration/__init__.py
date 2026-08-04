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
from .alternatives import (
    CompetingAlternatives,
    DimensionEffect,
    EffectDirection,
    EffectMeasure,
    HarmConstraint,
    HarmIncreaseTrace,
    ProhibitedChange,
    TracedAlternative,
    retain_competing_alternatives,
)
from .diffraction import (
    ArrangementDependency,
    ConsequentialDifference,
    DiffractiveArrangementField,
    DiffractiveDisturbanceTrace,
    disturb_through_arrangement_difference,
)
from .revision import (
    ArrangementRevisionTrace,
    RecursivelyRevisedArrangementField,
    revise_reopened_arrangement,
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
    "CompetingAlternatives",
    "DimensionEffect",
    "EffectDirection",
    "EffectMeasure",
    "HarmConstraint",
    "HarmIncreaseTrace",
    "ProhibitedChange",
    "TracedAlternative",
    "retain_competing_alternatives",
    "ArrangementDependency",
    "ConsequentialDifference",
    "DiffractiveArrangementField",
    "DiffractiveDisturbanceTrace",
    "disturb_through_arrangement_difference",
    "ArrangementRevisionTrace",
    "RecursivelyRevisedArrangementField",
    "revise_reopened_arrangement",
]
