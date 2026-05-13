from __future__ import annotations

from dataclasses import dataclass, field

from cbra.cbra_runtime_rebuilt.runtime.field_state import FieldState, Stream, Coupling


@dataclass
class OperatorDelta:
    operator_name: str
    updated_stream_ids: list[str] = field(default_factory=list)
    updated_couplings: list[tuple[str, str]] = field(default_factory=list)
    field_value_changes: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class RuntimeStepTrace:
    timestep: int
    deltas: list[OperatorDelta] = field(default_factory=list)


def _clamp01(x: float) -> float:
    return min(1.0, max(0.0, x))


def _active_streams(state: FieldState) -> list[Stream]:
    return [s for s in state.streams if s.active]


def _find_stream(state: FieldState, stream_id: str) -> Stream | None:
    for s in state.streams:
        if s.stream_id == stream_id:
            return s
    return None


def _ensure_minimum_couplings(state: FieldState) -> None:
    active = _active_streams(state)
    if len(active) < 2:
        return

    existing = {(c.source_id, c.target_id) for c in state.couplings}
    for i in range(len(active) - 1):
        a = active[i]
        b = active[i + 1]
        if (a.stream_id, b.stream_id) not in existing:
            state.couplings.append(
                Coupling(
                    source_id=a.stream_id,
                    target_id=b.stream_id,
                    active=True,
                    coupling_strength=0.25,
                )
            )


def _apply_temporal_carry_forward(state: FieldState) -> OperatorDelta:
    delta = OperatorDelta(operator_name="temporal_carry_forward")

    lead_ids = set(state.emergent_form.lead_stream_ids)
    support_ids = set(state.emergent_form.support_stream_ids)
    held_open_ids = set(state.emergent_form.held_open_stream_ids)
    interference_ids = set(state.emergent_form.interference_stream_ids)

    for s in state.streams:
        if not s.active:
            continue
        before = s.participation

        # gentle field-wide fade
        s.participation = _clamp01(s.participation - 0.03)

        # persistence carries material forward without forcing sameness
        s.participation = _clamp01(s.participation + 0.02 * s.persistence)

        # current field configuration carries some strands differently
        if s.stream_id in lead_ids:
            s.participation = _clamp01(s.participation + 0.01)
        if s.stream_id in support_ids:
            s.participation = _clamp01(s.participation + 0.015)
        if s.stream_id in held_open_ids or s.stream_id in interference_ids:
            s.participation = _clamp01(s.participation + 0.008)

        if s.participation != before:
            delta.updated_stream_ids.append(s.stream_id)

    active_ids = {s.stream_id for s in state.streams if s.active}
    for c in state.couplings:
        if not c.active or c.source_id not in active_ids or c.target_id not in active_ids:
            continue
        before = c.coupling_strength
        src = _find_stream(state, c.source_id)
        tgt = _find_stream(state, c.target_id)
        persistence_factor = ((src.persistence if src else 0.5) + (tgt.persistence if tgt else 0.5)) / 2.0

        # couplings also soften over time, but persistent material keeps some relational trace
        c.coupling_strength = _clamp01(c.coupling_strength - 0.04 + 0.02 * persistence_factor)

        if (c.source_id in support_ids or c.target_id in support_ids) and (c.source_id in lead_ids or c.target_id in lead_ids):
            c.coupling_strength = _clamp01(c.coupling_strength + 0.015)
        if c.source_id in interference_ids or c.target_id in interference_ids:
            c.coupling_strength = _clamp01(c.coupling_strength + 0.01)

        if c.coupling_strength != before:
            delta.updated_couplings.append((c.source_id, c.target_id))

    if state.field_values.coherence > 0:
        state.field_values.coherence = _clamp01(state.field_values.coherence - 0.01)
    if state.field_values.cut_pressure > 0:
        state.field_values.cut_pressure = _clamp01(state.field_values.cut_pressure - 0.01)

    delta.field_value_changes["coherence"] = state.field_values.coherence
    delta.field_value_changes["cut_pressure"] = state.field_values.cut_pressure
    delta.notes.append("Applied temporal fade and persistence-based carry-forward to streams and couplings.")
    return delta


def apply_intra_action(state: FieldState) -> OperatorDelta:
    delta = OperatorDelta(operator_name="intra_action")
    active = _active_streams(state)
    _ensure_minimum_couplings(state)

    for s in active:
        before = s.participation
        base_gain = 0.02 * s.persistence
        if s.kind in {"user_turn", "ontology"}:
            base_gain += 0.05
        elif s.kind in {"attachment", "live_world"}:
            base_gain += 0.04
        elif s.kind in {"memory", "embodiment", "environment"}:
            base_gain += 0.025

        relational_bonus = 0.0
        for c in state.couplings:
            if not c.active:
                continue
            if c.source_id == s.stream_id or c.target_id == s.stream_id:
                relational_bonus += 0.03 * c.coupling_strength

        s.participation = _clamp01(s.participation + min(0.14, base_gain + relational_bonus))
        if s.participation != before:
            delta.updated_stream_ids.append(s.stream_id)

    coupling_values = []
    for c in state.couplings:
        if not c.active:
            continue
        src = _find_stream(state, c.source_id)
        tgt = _find_stream(state, c.target_id)
        if src and tgt and src.active and tgt.active:
            similarity = 1.0 - abs(src.participation - tgt.participation)
            old = c.coupling_strength
            c.coupling_strength = _clamp01(
                c.coupling_strength + 0.05 + 0.08 * ((src.participation + tgt.participation) / 2.0) + 0.04 * similarity
            )
            coupling_values.append(c.coupling_strength)
            if c.coupling_strength != old:
                delta.updated_couplings.append((c.source_id, c.target_id))

    avg_coupling = sum(coupling_values) / len(coupling_values) if coupling_values else 0.0
    state.field_values.emergence_level = _clamp01(
        state.field_values.emergence_level + 0.06 + 0.10 * avg_coupling + 0.04 * min(1.0, len(active) / 4.0)
    )
    state.field_values.cut_pressure = _clamp01(
        state.field_values.cut_pressure + 0.05 + 0.08 * state.field_values.emergence_level
    )

    delta.field_value_changes["emergence_level"] = state.field_values.emergence_level
    delta.field_value_changes["cut_pressure"] = state.field_values.cut_pressure
    delta.notes.append("Updated participation through kind and coupling, then raised emergence and cut pressure.")
    return delta


def apply_play(state: FieldState) -> OperatorDelta:
    delta = OperatorDelta(operator_name="play")
    active = _active_streams(state)

    state.field_values.openness = _clamp01(state.field_values.openness + 0.08)
    state.field_values.cut_permeability = _clamp01(state.field_values.cut_permeability + 0.05)

    for s in active:
        if s.kind in {"memory", "embodiment", "environment", "other"}:
            before = s.participation
            s.participation = _clamp01(s.participation + 0.04)
            if s.participation != before:
                delta.updated_stream_ids.append(s.stream_id)

    delta.field_value_changes["openness"] = state.field_values.openness
    delta.field_value_changes["cut_permeability"] = state.field_values.cut_permeability
    delta.notes.append("Increased exploratory openness and kept the field more revisable.")
    return delta


def apply_diffraction(state: FieldState) -> OperatorDelta:
    delta = OperatorDelta(operator_name="diffraction")
    active = _active_streams(state)

    kinds = {}
    for s in active:
        kinds.setdefault(s.kind, []).append(s)

    difference_seed = min(1.0, len(kinds) / 4.0)
    state.field_values.difference_activity = _clamp01(
        state.field_values.difference_activity + 0.04 + 0.10 * difference_seed
    )

    interference: list[str] = []
    for s in active:
        if s.kind in {"memory", "environment", "attachment", "live_world"} and s.participation >= 0.40:
            interference.append(s.stream_id)

    state.emergent_form.interference_stream_ids = sorted(set(interference))

    for c in state.couplings:
        if not c.active:
            continue
        src = _find_stream(state, c.source_id)
        tgt = _find_stream(state, c.target_id)
        if not src or not tgt or not src.active or not tgt.active:
            continue
        if src.kind != tgt.kind:
            old = c.coupling_strength
            c.coupling_strength = _clamp01(c.coupling_strength + 0.04)
            if c.coupling_strength != old:
                delta.updated_couplings.append((c.source_id, c.target_id))

    if len(interference) >= 2:
        state.field_values.coherence = _clamp01(state.field_values.coherence - 0.03)
        delta.notes.append("Detected multiple interference strands; softened premature coherence.")
    else:
        state.field_values.coherence = _clamp01(state.field_values.coherence + 0.015)

    delta.field_value_changes["difference_activity"] = state.field_values.difference_activity
    delta.field_value_changes["coherence"] = state.field_values.coherence
    delta.notes.append("Mapped cross-kind difference and registered interference streams.")
    return delta


def apply_becoming(state: FieldState) -> OperatorDelta:
    delta = OperatorDelta(operator_name="becoming")
    active = [s for s in _active_streams(state) if s.participation > 0.32]

    if active:
        def becoming_score(s: Stream) -> float:
            local_coupling = 0.0
            for c in state.couplings:
                if c.active and (c.source_id == s.stream_id or c.target_id == s.stream_id):
                    local_coupling += c.coupling_strength
            return s.participation + 0.10 * local_coupling

        lead = max(active, key=becoming_score)
        support = []
        held_open = []
        for s in active:
            if s.stream_id == lead.stream_id:
                continue
            if s.kind in {"memory", "embodiment", "environment"}:
                held_open.append(s.stream_id)
            else:
                support.append(s.stream_id)

        state.emergent_form.label = lead.kind if not lead.payload else str(
            lead.payload.get("concept")
            or lead.payload.get("title")
            or lead.payload.get("text")
            or lead.payload.get("label")
            or lead.kind
        )[:80]
        state.emergent_form.lead_stream_ids = [lead.stream_id]
        state.emergent_form.support_stream_ids = support[:4]
        state.emergent_form.held_open_stream_ids = held_open[:4]

        state.cut.foregrounded = [state.emergent_form.label] if state.emergent_form.label else [lead.stream_id]
        state.cut.backgrounded = support[:4]
        state.cut.held_open = held_open[:4]
        state.cut.excluded = []

        support_factor = min(1.0, len(support) / 3.0)
        held_factor = min(1.0, len(held_open) / 3.0)
        state.field_values.emergence_level = _clamp01(state.field_values.emergence_level + 0.05 + 0.06 * support_factor)
        state.field_values.coherence = _clamp01(state.field_values.coherence + 0.06 + 0.04 * support_factor - 0.02 * held_factor)

        delta.updated_stream_ids.extend([lead.stream_id] + support[:4] + held_open[:4])
        delta.notes.append(f"Stabilized temporary form around lead stream '{lead.stream_id}' using relational support.")
    else:
        state.field_values.coherence = _clamp01(state.field_values.coherence - 0.02)
        delta.notes.append("No strong active cluster yet; coherence softened slightly.")

    delta.field_value_changes["emergence_level"] = state.field_values.emergence_level
    delta.field_value_changes["coherence"] = state.field_values.coherence
    return delta


def apply_care(state: FieldState) -> OperatorDelta:
    delta = OperatorDelta(operator_name="care")

    if state.field_values.cut_pressure > 0.75 and state.field_values.cut_permeability < 0.40:
        state.field_values.care_tension = _clamp01(state.field_values.care_tension + 0.12)
        state.field_values.cut_permeability = _clamp01(state.field_values.cut_permeability + 0.10)
        state.field_values.coherence = _clamp01(state.field_values.coherence - 0.04)
        delta.notes.append("Countered coercive closure by reopening the field.")
    else:
        state.field_values.care_tension = _clamp01(state.field_values.care_tension + 0.02)

    drift = 0.0
    if state.field_values.coherence > 0.92:
        drift += 0.10
    if state.field_values.cut_pressure > 0.90 and state.field_values.cut_permeability < 0.25:
        drift += 0.20
    if len(state.emergent_form.lead_stream_ids) == 0 and state.field_values.cut_pressure > 0.60:
        drift += 0.10

    state.field_values.drift_load = _clamp01(state.field_values.drift_load + drift)

    state.drift_flags.ontological_drift = state.field_values.coherence > 0.96
    state.drift_flags.interpretive_compression = (
        state.field_values.cut_pressure > 0.85 and state.field_values.cut_permeability < 0.20
    )
    state.drift_flags.capacity_collapse = state.field_values.care_tension > 0.85
    state.drift_flags.narrative_dominance = (
        len(state.emergent_form.lead_stream_ids) == 1 and len(state.emergent_form.support_stream_ids) == 0
        and state.field_values.coherence > 0.80
    )
    state.drift_flags.moralization_drift = False
    state.drift_flags.procedural_bypass = False

    delta.field_value_changes["care_tension"] = state.field_values.care_tension
    delta.field_value_changes["cut_permeability"] = state.field_values.cut_permeability
    delta.field_value_changes["coherence"] = state.field_values.coherence
    delta.field_value_changes["drift_load"] = state.field_values.drift_load
    delta.notes.append("Applied livability constraints and updated drift signals.")
    return delta


def apply_operator_stack(state: FieldState) -> RuntimeStepTrace:
    trace = RuntimeStepTrace(timestep=state.timestep)

    temporal = _apply_temporal_carry_forward(state)
    trace.deltas.append(temporal)

    for fn in (
        apply_intra_action,
        apply_play,
        apply_diffraction,
        apply_becoming,
        apply_care,
    ):
        trace.deltas.append(fn(state))
    state.clamp()
    return trace


def step_field(state: FieldState) -> RuntimeStepTrace:
    state.timestep += 1
    return apply_operator_stack(state)
