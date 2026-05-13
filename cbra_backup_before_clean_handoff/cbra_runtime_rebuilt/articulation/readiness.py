from __future__ import annotations
from cbra.cbra_runtime_rebuilt.runtime.field_state import FieldState

def ready_to_articulate(state: FieldState) -> bool:
    fv = state.field_values
    flags = state.drift_flags
    if flags.ontological_drift or flags.interpretive_compression or flags.capacity_collapse:
        return False
    return (
        fv.emergence_level >= 0.55
        and fv.cut_pressure >= 0.20
        and fv.cut_permeability >= 0.35
        and fv.coherence >= 0.45
        and fv.drift_load < 0.35
        and bool(state.emergent_form.lead_stream_ids)
    )
