from __future__ import annotations

from uuid import uuid4

from cbra_runtime.runtime.field_state import (
    ApparatusState,
    CutState,
    EmergentForm,
    FieldState,
    FieldValues,
    DriftFlags,
    Stream,
)
from cbra_runtime.runtime.operators import RuntimeStepTrace, step_field
from cbra_runtime.articulation.readiness import ready_to_articulate
from cbra_runtime.articulation.decoder import decode_articulation
from cbra_runtime.runtime.history import snapshot_before, finalize_entry, FieldHistoryEntry


def _new_field_id() -> str:
    return f"field_{uuid4().hex[:12]}"


def _clamp01(x: float) -> float:
    return min(1.0, max(0.0, x))


def _default_rules() -> list[str]:
    return ["descriptive", "additive", "non_coercive"]


def _infer_framing(streams: list[Stream]) -> str:
    kinds = {s.kind for s in streams if s.active}
    if "live_world" in kinds:
        return "situated live-world inquiry"
    if "attachment" in kinds:
        return "document-grounded inquiry"
    if "ontology" in kinds:
        return "conceptual inquiry"
    return "open inquiry"


def _infer_prompting_structure(streams: list[Stream]) -> str:
    for s in streams:
        if s.kind == "user_turn":
            text = str(s.payload.get("text", "")).strip()
            if text.endswith("?"):
                return "direct question"
            if len(text) > 240:
                return "extended prompt"
    return "direct prompt"


def _seed_initial_field_values(streams: list[Stream]) -> FieldValues:
    active_count = len([s for s in streams if s.active])

    openness = 0.55
    difference_activity = 0.45
    emergence_level = 0.05 if active_count > 0 else 0.0
    cut_pressure = 0.02 if active_count > 0 else 0.0
    cut_permeability = 1.00
    coherence = 0.08 if active_count >= 2 else 0.03
    care_tension = 0.20
    drift_load = 0.00

    return FieldValues(
        openness=_clamp01(openness),
        difference_activity=_clamp01(difference_activity),
        emergence_level=_clamp01(emergence_level),
        cut_pressure=_clamp01(cut_pressure),
        cut_permeability=_clamp01(cut_permeability),
        coherence=_clamp01(coherence),
        care_tension=_clamp01(care_tension),
        drift_load=_clamp01(drift_load),
    )


def initialize_field(
    streams: list[Stream],
    *,
    field_id: str | None = None,
    medium: str = "text_chat",
    roles: list[str] | None = None,
    institutional_conditions: list[str] | None = None,
) -> FieldState:
    clean_streams: list[Stream] = []
    for s in streams:
        copied = Stream(
            stream_id=s.stream_id,
            kind=s.kind,
            payload=dict(s.payload),
            active=s.active,
            participation=_clamp01(s.participation),
            persistence=_clamp01(s.persistence),
        )
        clean_streams.append(copied)

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
    flags = state.drift_flags
    fv = state.field_values

    if flags.ontological_drift or flags.procedural_bypass:
        target = "Field Entry"
        fv.coherence = min(fv.coherence, 0.35)
        fv.cut_pressure = min(fv.cut_pressure, 0.18)
        fv.emergence_level = min(fv.emergence_level, 0.45)
        state.cut.foregrounded = []
        state.cut.backgrounded = []
    elif flags.interpretive_compression or flags.narrative_dominance:
        target = "Noticing"
        fv.coherence = min(fv.coherence, 0.42)
        fv.cut_pressure = min(fv.cut_pressure, 0.22)
        state.cut.held_open = sorted(set(state.cut.held_open + state.emergent_form.support_stream_ids))
    elif flags.capacity_collapse or flags.moralization_drift:
        target = "Relational Framing"
        fv.care_tension = min(fv.care_tension, 0.45)
        fv.cut_permeability = max(fv.cut_permeability, 0.55)
        fv.coherence = min(fv.coherence, 0.48)
    else:
        target = "Field Entry"

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
) -> tuple[str, list[RuntimeStepTrace], list[str], list[FieldHistoryEntry]]:
    traces: list[RuntimeStepTrace] = []
    reintegrations: list[str] = []
    history: list[FieldHistoryEntry] = []

    for _ in range(max_steps):
        entry = snapshot_before(state)
        trace = step_field(state)
        traces.append(trace)

        reintegration_target: str | None = None
        if state.drift_flags.any():
            reintegration_target = reintegrate_field(state)
            reintegrations.append(reintegration_target)

        operator_names = [delta.operator_name for delta in trace.deltas]
        history.append(finalize_entry(entry, state, reintegration_target=reintegration_target, operator_names=operator_names))

        if ready_to_articulate(state):
            return decode_articulation(state), traces, reintegrations, history

    return decode_articulation(state), traces, reintegrations, history

    return decode_articulation(state), traces, reintegrations
