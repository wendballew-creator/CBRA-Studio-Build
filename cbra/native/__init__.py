"""Architecture-native CBRA field runtime.

This package is intentionally not wired to the existing API yet.  It is the
executable substrate for validating field formation, co-active operators,
emergence, provisional cuts, articulation, and reinsertion before interface
concerns are allowed to shape the core.
"""

from .articulation import articulate, form_provisional_cut, reinsert_articulation
from .emergence import emerge_phenomena
from .hypotheses import RuntimeHypotheses
from .models import (
    Apparatus,
    Articulation,
    CycleResult,
    DiffractivePattern,
    DriftKind,
    DriftSignal,
    EmergentPhenomenon,
    FieldState,
    FieldValues,
    ProvisionalCut,
    Relation,
    Stream,
)
from .runtime import (
    initialize_field,
    reintegrate_field,
    run_cycle,
    run_until_articulation,
    update_field,
)

__all__ = [
    "Apparatus",
    "Articulation",
    "CycleResult",
    "DiffractivePattern",
    "DriftKind",
    "DriftSignal",
    "EmergentPhenomenon",
    "FieldState",
    "FieldValues",
    "ProvisionalCut",
    "Relation",
    "RuntimeHypotheses",
    "Stream",
    "articulate",
    "emerge_phenomena",
    "form_provisional_cut",
    "initialize_field",
    "reinsert_articulation",
    "reintegrate_field",
    "run_cycle",
    "run_until_articulation",
    "update_field",
]
