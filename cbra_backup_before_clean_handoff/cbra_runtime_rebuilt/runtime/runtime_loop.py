from __future__ import annotations

from uuid import uuid4
from typing import List, Optional, Tuple

from cbra.cbra_runtime_rebuilt.runtime.field_state import (
    ApparatusState,
    CutState,
    EmergentForm,
    FieldState,
    FieldValues,
    DriftFlags,
    Stream,
)
from cbra.cbra_runtime_rebuilt.articulation.decoder import decode_articulation
from cbra.cbra_runtime_rebuilt.articulation.readiness import ready_to_articulate
from cbra.cbra_runtime_rebuilt.runtime.history import snapshot_before, finalize_entry, FieldHistoryEntry
from cbra.cbra_runtime_rebuilt.runtime.operators import RuntimeStepTrace, step_field


def _new_field_id() -> str:
    return "field_" + uuid4().hex[:12]


def _clamp01(x: float) -> float:
    return min(1.0, max(0.0, x))


def _default_rules() -> List[str]:
    return ["descriptive", "additive", "non_coercive"]


def _infer_framing(streams: List[Stream]) -> str:
    kinds = {s.kind for s in streams if s.active}
    if "live_world" in kinds:
        return "situated live-world inquiry"
    if "attachment" in kinds:
        return "document-grounded inquiry"
    if "ontology" in kinds:
        return "conceptual inquiry"
    return "open inquiry"


def _infer_prompting_structure(streams: List[Stream]) -> str:
    for s in streams:
        if s.kind == "user_turn":
            text = str(s.payload.get("text", "")).strip()
            if text.endswith("?"):
                return "direct question"
            if len(text) > 240:
                return "extended prompt"
    return "direct prompt"


def _seed_initial_field_values(streams: List[Stream]) -> FieldValues:
    active_count = len([s for s in streams if s.active])
    return FieldValues(
        openness=_clamp01(0.55),
        difference_activity=_clamp01(0.45),
        emergence_level=_clamp01(0.05 if active_count > 0 else 0.0),
        cut_pressure=_clamp01(0.02 if active_count > 0 else 0.0),
        cut_permeability=1.0,
        coherence=_clamp01(0.08 if active_count >= 2 else 0.03),
        care_tension=0.20,
        drift_load=0.00,
    )


def initialize_field(
    streams: List[Stream],
    field_id: Optional[str] = None,
    medium: str = "text_chat",
    roles: Optional[List[str]] = None,
    institutional_conditions: Optional[List[str]] = None,
) -> FieldState:
    clean_streams = [
        Stream(
            stream_id=s.stream_id,
            kind=s.kind,
            payload=dict(s.payload),
            active=s.active,
            participation=_clamp01(s.participation),
            persistence=_clamp01(s.persistence),
        )
        for s in streams
    ]
    apparatus = ApparatusState(
        framing=_infer_framing(clean_streams),
        medium=medium,
        rules=_default_rules(),
        roles=list(roles or ["user", "assistant"]),
        institutional_conditions=list(institutional_conditions or []),
        prompting_structure=_infer_prompting_structure(clean_streams),
    )
    state = FieldState(
        field_id=field_id or _new_field_id(),
        timestep=0,
        streams=clean_streams,
        couplings=[],
        apparatus=apparatus,
        emergent_form=EmergentForm(),
        cut=CutState(),
        field_values=_seed_initial_field_values(clean_streams),
        drift_flags=DriftFlags(),
    )
    state.clamp()
    return state


def reintegrate_field(state: FieldState) -> str:
    fv = state.field_values
    if state.drift_flags.ontological_drift or state.drift_flags.procedural_bypass:
        target = "Field Entry"
        state.emergent_form.lead_stream_ids = []
        state.emergent_form.label = ""
        state.cut.foregrounded = []
        fv.coherence = min(fv.coherence, 0.35)
        fv.cut_pressure = min(fv.cut_pressure, 0.18)
        fv.cut_permeability = max(fv.cut_permeability, 0.70)
    elif state.drift_flags.interpretive_compression:
        target = "Noticing"
        fv.coherence = min(fv.coherence, 0.42)
        fv.cut_pressure = min(fv.cut_pressure, 0.22)
        fv.cut_permeability = max(fv.cut_permeability, 0.80)
    elif state.drift_flags.capacity_collapse:
        target = "Relational Framing"
        fv.care_tension = min(fv.care_tension, 0.45)
        fv.cut_permeability = max(fv.cut_permeability, 0.65)
        fv.coherence = min(fv.coherence, 0.48)
        fv.openness = max(fv.openness, 0.60)
    elif state.drift_flags.narrative_dominance:
        target = "Diffractive Mapping"
        fv.coherence = min(fv.coherence, 0.46)
        fv.difference_activity = max(fv.difference_activity, 0.70)
        fv.cut_pressure = min(fv.cut_pressure, 0.26)
        fv.cut_permeability = max(fv.cut_permeability, 0.68)
    elif state.drift_flags.moralization_drift:
        target = "Articulation"
        fv.coherence = min(fv.coherence, 0.50)
        fv.cut_pressure = min(fv.cut_pressure, 0.24)
        fv.cut_permeability = max(fv.cut_permeability, 0.75)
        fv.care_tension = max(0.15, min(fv.care_tension, 0.40))
    else:
        target = "Field Entry"
        fv.coherence = min(fv.coherence, 0.40)
        fv.cut_pressure = min(fv.cut_pressure, 0.20)
        fv.cut_permeability = max(fv.cut_permeability, 0.60)

    fv.drift_load = max(0.0, fv.drift_load - 0.18)
    state.drift_flags.ontological_drift = False
    state.drift_flags.interpretive_compression = False
    state.drift_flags.capacity_collapse = False
    state.drift_flags.narrative_dominance = False
    state.drift_flags.moralization_drift = False
    state.drift_flags.procedural_bypass = False
    state.clamp()
    return target


def run_until_articulation(
    state: FieldState,
    max_steps: int = 8,
) -> Tuple[str, List[RuntimeStepTrace], List[str], List[FieldHistoryEntry]]:
    traces = []
    reintegrations = []
    history = []
    for _ in range(max_steps):
        entry = snapshot_before(state)
        trace = step_field(state)
        traces.append(trace)
        reintegration_target = None
        if state.drift_flags.any():
            reintegration_target = reintegrate_field(state)
            reintegrations.append(reintegration_target)
        operator_names = [delta.operator_name for delta in trace.deltas]
        history.append(finalize_entry(entry, state, reintegration_target=reintegration_target, operator_names=operator_names))
        if ready_to_articulate(state):
            return decode_articulation(state, history), traces, reintegrations, history
    return decode_articulation(state, history), traces, reintegrations, history
