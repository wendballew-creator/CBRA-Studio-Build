"""Field formation, co-active updates, reintegration, and runtime movement."""

from __future__ import annotations

from copy import deepcopy
from itertools import combinations
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import uuid4

from .articulation import articulate, form_provisional_cut, reinsert_articulation
from .emergence import emerge_phenomena
from .hypotheses import RuntimeHypotheses
from .models import (
    Apparatus,
    Articulation,
    CycleResult,
    DriftKind,
    DriftSignal,
    FieldSnapshot,
    FieldState,
    FieldValues,
    HistoryEntry,
    OperatorDelta,
    ReintegrationTrace,
    StepTrace,
    Stream,
    clamp01,
)
from .operators import OPERATOR_ORDER, propose_coactive_updates


def _apparatus_streams(
    apparatus: Apparatus,
    hypotheses: RuntimeHypotheses,
) -> List[Stream]:
    facets = {
        "framing": [apparatus.framing],
        "medium": [apparatus.medium],
        "prompts": apparatus.prompts,
        "interfaces": apparatus.interfaces,
        "categories": apparatus.categories,
        "tools": apparatus.tools,
        "models": apparatus.models,
        "institutions": apparatus.institutions,
        "constraints": apparatus.constraints,
        "temporal_pressures": apparatus.temporal_pressures,
    }
    streams: List[Stream] = []
    for facet in sorted(facets):
        values = [str(item) for item in facets[facet] if str(item).strip()]
        if not values:
            continue
        stream_id = "{0}:{1}".format(apparatus.apparatus_id, facet)
        streams.append(
            Stream(
                stream_id=stream_id,
                kind="apparatus",
                payload={
                    "facet": facet,
                    "values": values,
                    "text": " ".join(values),
                },
                participation=hypotheses.apparatus_participation,
                persistence=hypotheses.apparatus_persistence,
                provenance={
                    "apparatus_id": apparatus.apparatus_id,
                    "materialized_facet": facet,
                },
            )
        )
    return streams


def initialize_field(
    streams: Sequence[Stream],
    apparatus: Optional[Apparatus] = None,
    field_id: Optional[str] = None,
    hypotheses: Optional[RuntimeHypotheses] = None,
) -> FieldState:
    hypotheses = hypotheses or RuntimeHypotheses()
    apparatus = deepcopy(apparatus or Apparatus())
    material = [deepcopy(item) for item in streams]
    material.extend(_apparatus_streams(apparatus, hypotheses))

    seen = set()
    duplicates = set()
    for item in material:
        if item.stream_id in seen:
            duplicates.add(item.stream_id)
        seen.add(item.stream_id)
    if duplicates:
        raise ValueError(
            "Stream IDs must be unique; duplicated: {0}".format(
                ", ".join(sorted(duplicates))
            )
        )

    state = FieldState(
        field_id=field_id or "field:{0}".format(uuid4().hex[:12]),
        apparatus=apparatus,
        field_values=FieldValues(
            openness=hypotheses.initial_openness,
            multiplicity=hypotheses.initial_multiplicity,
            difference_activity=hypotheses.initial_difference_activity,
            relational_intensity=hypotheses.initial_relational_intensity,
            emergence_level=hypotheses.initial_emergence_level,
            coherence=hypotheses.initial_coherence,
            cut_pressure=hypotheses.initial_cut_pressure,
            cut_permeability=hypotheses.initial_cut_permeability,
            care_capacity=hypotheses.initial_care_capacity,
            care_tension=hypotheses.initial_care_tension,
            drift_load=hypotheses.initial_drift_load,
        ),
        streams=material,
    )
    state.clamp()
    assert_native_invariants(state)
    return state


def snapshot_field(state: FieldState) -> FieldSnapshot:
    return FieldSnapshot(
        timestep=state.timestep,
        stream_participation={
            item.stream_id: item.participation for item in state.streams
        },
        relation_values={
            item.relation_id: (
                item.resonance,
                item.difference,
                item.mutuality,
            )
            for item in state.relations
        },
        field_values=state.field_values.as_dict(),
        phenomenon_ids=list(state.current_phenomenon_ids),
        cut_id=state.latest_cut().cut_id if state.latest_cut() else None,
        articulation_ids=[
            item.articulation_id for item in state.articulations
        ],
    )


def _integrate_coactive_deltas(
    state: FieldState,
    deltas: Sequence[OperatorDelta],
) -> None:
    stream_changes: Dict[str, float] = {}
    field_changes: Dict[str, float] = {}
    proposed_streams: Dict[str, Stream] = {}
    relation_updates: Dict[str, Relation] = {}

    for delta in deltas:
        for stream_id, change in delta.stream_participation_changes.items():
            stream_changes[stream_id] = stream_changes.get(stream_id, 0.0) + change
        for name, change in delta.field_value_changes.items():
            field_changes[name] = field_changes.get(name, 0.0) + change
        for stream in delta.proposed_streams:
            proposed_streams.setdefault(stream.stream_id, deepcopy(stream))
        for relation_id, relation in delta.relation_updates.items():
            relation_updates[relation_id] = deepcopy(relation)

    for stream_id, change in stream_changes.items():
        stream = state.stream(stream_id)
        if stream is not None:
            stream.participation += change

    for name, change in field_changes.items():
        if not hasattr(state.field_values, name):
            raise ValueError("Unknown field value proposed: {0}".format(name))
        setattr(
            state.field_values,
            name,
            getattr(state.field_values, name) + change,
        )

    existing_stream_ids = {item.stream_id for item in state.streams}
    for stream_id in sorted(proposed_streams):
        if stream_id not in existing_stream_ids:
            state.streams.append(proposed_streams[stream_id])
            existing_stream_ids.add(stream_id)

    existing_relations = {
        item.relation_id: index for index, item in enumerate(state.relations)
    }
    for relation_id in sorted(relation_updates):
        relation = relation_updates[relation_id]
        index = existing_relations.get(relation_id)
        if index is None:
            state.relations.append(relation)
        else:
            state.relations[index] = relation

    current_patterns = []
    known_pattern_ids = {item.pattern_id for item in state.patterns}
    for delta in deltas:
        for pattern in delta.patterns:
            current_patterns.append(pattern.pattern_id)
            if pattern.pattern_id not in known_pattern_ids:
                state.patterns.append(deepcopy(pattern))
                known_pattern_ids.add(pattern.pattern_id)

    state.current_pattern_ids = sorted(set(current_patterns))
    state.current_phenomenon_ids = []
    state.timestep += 1
    state.clamp()


def _relation_density(
    state: FieldState,
    eligible_ids: Optional[Sequence[str]] = None,
) -> float:
    active_ids = list(
        eligible_ids
        if eligible_ids is not None
        else [item.stream_id for item in state.streams if item.active]
    )
    active_id_set = set(active_ids)
    possible = len(list(combinations(active_ids, 2)))
    if possible == 0:
        return 1.0
    active = sum(
        1
        for item in state.relations
        if item.active
        and item.left_id in active_id_set
        and item.right_id in active_id_set
    )
    return min(1.0, active / possible)


def _runtime_drift_signals(
    state: FieldState,
    operator_names: Iterable[str],
    hypotheses: RuntimeHypotheses,
) -> List[DriftSignal]:
    values = state.field_values
    signals: List[DriftSignal] = []

    if (
        values.cut_pressure >= hypotheses.compression_pressure_floor
        and values.cut_permeability
        <= hypotheses.compression_permeability_ceiling
    ):
        signals.append(
            DriftSignal(
                kind=DriftKind.COMPRESSION,
                intensity=values.cut_pressure,
                evidence=[
                    "cut pressure is high while cut permeability is low"
                ],
                detected_at=state.timestep,
            )
        )

    material = [
        item
        for item in state.streams
        if item.active
        and item.kind
        not in {"apparatus", "play_variation", "diffractive_trace"}
    ]
    if len(material) >= 2:
        high = max(item.participation for item in material)
        low = min(item.participation for item in material)
        if (
            high >= hypotheses.narrative_dominance_floor
            and high - low >= hypotheses.narrative_dominance_gap
        ):
            signals.append(
                DriftSignal(
                    kind=DriftKind.NARRATIVE_DOMINANCE,
                    intensity=high - low,
                    evidence=[
                        "one material stream carries disproportionate participation"
                    ],
                    detected_at=state.timestep,
                )
            )

    if (
        values.care_capacity <= hypotheses.capacity_collapse_floor
        or values.care_tension >= hypotheses.capacity_tension_ceiling
    ):
        signals.append(
            DriftSignal(
                kind=DriftKind.CAPACITY_COLLAPSE,
                intensity=max(1.0 - values.care_capacity, values.care_tension),
                evidence=["available care capacity has collapsed"],
                detected_at=state.timestep,
            )
        )

    relation_density = _relation_density(
        state,
        [item.stream_id for item in material],
    )
    if len(material) >= 2 and relation_density < hypotheses.ontological_relation_density_floor:
        signals.append(
            DriftSignal(
                kind=DriftKind.ONTOLOGICAL_DRIFT,
                intensity=1.0 - relation_density,
                evidence=[
                    "material appears as isolated units rather than through relation"
                ],
                detected_at=state.timestep,
            )
        )

    missing = set(OPERATOR_ORDER) - set(operator_names)
    if missing:
        signals.append(
            DriftSignal(
                kind=DriftKind.PROCEDURAL_BYPASS,
                intensity=len(missing) / len(OPERATOR_ORDER),
                evidence=[
                    "operator proposals missing: {0}".format(
                        ", ".join(sorted(missing))
                    )
                ],
                detected_at=state.timestep,
            )
        )

    return signals


def _merge_drift_signals(signals: Iterable[DriftSignal]) -> List[DriftSignal]:
    merged: Dict[DriftKind, DriftSignal] = {}
    for signal in signals:
        signal = deepcopy(signal)
        signal.clamp()
        prior = merged.get(signal.kind)
        if prior is None:
            merged[signal.kind] = signal
            continue
        prior.intensity = max(prior.intensity, signal.intensity)
        prior.evidence = list(dict.fromkeys(prior.evidence + signal.evidence))
        if signal.source != prior.source:
            prior.source = "runtime_and_external"
    return [merged[kind] for kind in DriftKind if kind in merged]


def update_field(
    state: FieldState,
    hypotheses: Optional[RuntimeHypotheses] = None,
) -> StepTrace:
    hypotheses = hypotheses or RuntimeHypotheses()
    basis_timestep = state.timestep
    # Operator functions are pure proposals over this same pre-update state.
    deltas, care_constraints = propose_coactive_updates(state, hypotheses)
    _integrate_coactive_deltas(state, deltas)
    emerge_phenomena(state, hypotheses)
    operator_names = [item.operator_name for item in deltas]
    drift_signals = _merge_drift_signals(
        list(
            _runtime_drift_signals(
                state,
                operator_names,
                hypotheses,
            )
        )
        + list(state.pending_drifts)
    )
    state.pending_drifts = []
    state.active_drifts = drift_signals
    if drift_signals:
        state.field_values.drift_load = clamp01(
            state.field_values.drift_load
            + (
                hypotheses.drift_load_signal_weight
                * sum(item.intensity for item in drift_signals)
            )
        )
    state.clamp()
    assert_native_invariants(state)
    return StepTrace(
        timestep_before=basis_timestep,
        timestep_after=state.timestep,
        calculation_basis_timestep=basis_timestep,
        operator_order=list(OPERATOR_ORDER),
        deltas=deltas,
        care_constraints=care_constraints,
        drift_signals=deepcopy(drift_signals),
        hypotheses=hypotheses.as_dict(),
    )


def _apply_field_changes(
    state: FieldState,
    requested: Dict[str, float],
) -> Dict[str, float]:
    actual: Dict[str, float] = {}
    for name, change in requested.items():
        before = float(getattr(state.field_values, name))
        setattr(state.field_values, name, clamp01(before + change))
        actual[name] = float(getattr(state.field_values, name)) - before
    return actual


def _reintegrate_one(
    state: FieldState,
    signal: DriftSignal,
    hypotheses: RuntimeHypotheses,
) -> ReintegrationTrace:
    strength = hypotheses.reintegration_strength * max(
        hypotheses.reintegration_min_signal_influence,
        signal.intensity,
    )
    requested_fields: Dict[str, float]
    stream_changes: Dict[str, float] = {}
    relation_changes: Dict[str, float] = {}

    if signal.kind == DriftKind.COMPRESSION:
        requested_fields = {
            "openness": strength,
            "cut_permeability": strength,
            "cut_pressure": -strength,
            "coherence": -(
                hypotheses.reintegration_compression_coherence_factor
                * strength
            ),
        }
        trace = "Compression reopened the cut and loosened forced coherence."

    elif signal.kind == DriftKind.NARRATIVE_DOMINANCE:
        material = [
            item
            for item in state.streams
            if item.active and item.kind != "apparatus"
        ]
        mean = (
            sum(item.participation for item in material) / len(material)
            if material
            else 0.0
        )
        for item in material:
            before = item.participation
            item.participation = clamp01(
                item.participation
                + (
                    (mean - item.participation)
                    * max(
                        hypotheses.reintegration_narrative_min_redistribution,
                        strength,
                    )
                )
            )
            stream_changes[item.stream_id] = item.participation - before
        requested_fields = {
            "difference_activity": strength,
            "multiplicity": (
                hypotheses.reintegration_narrative_multiplicity_factor
                * strength
            ),
            "cut_pressure": -(
                hypotheses.reintegration_narrative_pressure_factor
                * strength
            ),
        }
        trace = "Narrative dominance redistributed participation across all material streams without choosing a replacement narrative."

    elif signal.kind == DriftKind.MORALIZATION:
        requested_fields = {
            "openness": strength,
            "cut_permeability": (
                hypotheses.reintegration_moralization_permeability_factor
                * strength
            ),
            "cut_pressure": -(
                hypotheses.reintegration_moralization_pressure_factor
                * strength
            ),
            "coherence": -(
                hypotheses.reintegration_moralization_coherence_factor
                * strength
            ),
            "care_capacity": (
                hypotheses.reintegration_moralization_capacity_factor
                * strength
            ),
        }
        trace = "Moralization softened closure and restored descriptive, revisable orientation."

    elif signal.kind == DriftKind.CAPACITY_COLLAPSE:
        for item in state.streams:
            if not item.active:
                continue
            before = item.participation
            item.participation = clamp01(
                item.participation
                * (
                    1.0
                    - (
                        hypotheses.reintegration_capacity_damping_factor
                        * strength
                    )
                )
            )
            stream_changes[item.stream_id] = item.participation - before
        requested_fields = {
            "care_capacity": strength,
            "care_tension": -strength,
            "cut_pressure": -(
                hypotheses.reintegration_capacity_pressure_factor
                * strength
            ),
            "openness": (
                hypotheses.reintegration_capacity_openness_factor
                * strength
            ),
        }
        trace = "Capacity collapse dampened field intensity while restoring room for care."

    elif signal.kind == DriftKind.ONTOLOGICAL_DRIFT:
        for relation in state.relations:
            before = relation.mutuality
            relation.mutuality = clamp01(
                relation.mutuality
                + (
                    (1.0 - relation.mutuality)
                    * hypotheses.reintegration_ontological_relation_factor
                    * strength
                )
            )
            relation.active = True
            relation_changes[relation.relation_id] = (
                relation.mutuality - before
            )
        requested_fields = {
            "relational_intensity": strength,
            "multiplicity": (
                hypotheses.reintegration_ontological_multiplicity_factor
                * strength
            ),
            "openness": (
                hypotheses.reintegration_ontological_openness_factor
                * strength
            ),
        }
        trace = "Ontological drift strengthened enacted relations rather than treating streams as pre-existing isolated units."

    else:  # procedural bypass
        requested_fields = {
            "openness": (
                hypotheses.reintegration_bypass_openness_factor
                * strength
            ),
            "cut_permeability": (
                hypotheses.reintegration_bypass_permeability_factor
                * strength
            ),
            "cut_pressure": -(
                hypotheses.reintegration_bypass_pressure_factor
                * strength
            ),
        }
        trace = "Procedural bypass kept the field open for a complete co-active update on the next cycle."

    field_changes = _apply_field_changes(state, requested_fields)
    state.clamp()
    return ReintegrationTrace(
        drift_kind=signal.kind,
        field_value_changes=field_changes,
        stream_participation_changes=stream_changes,
        relation_changes=relation_changes,
        trace=trace,
    )


def reintegrate_field(
    state: FieldState,
    signals: Optional[Sequence[DriftSignal]] = None,
    hypotheses: Optional[RuntimeHypotheses] = None,
) -> List[ReintegrationTrace]:
    hypotheses = hypotheses or RuntimeHypotheses()
    signals = list(signals if signals is not None else state.active_drifts)
    traces = [
        _reintegrate_one(state, signal, hypotheses)
        for signal in signals
    ]
    state.field_values.drift_load = clamp01(
        state.field_values.drift_load
        - (hypotheses.reintegration_strength * max(1, len(traces)))
    )
    state.active_drifts = []
    state.clamp()
    assert_native_invariants(state)
    return traces


def run_cycle(
    state: FieldState,
    hypotheses: Optional[RuntimeHypotheses] = None,
) -> CycleResult:
    hypotheses = hypotheses or RuntimeHypotheses()
    before = snapshot_field(state)
    trace = update_field(state, hypotheses)
    reintegrations: List[ReintegrationTrace] = []
    cut = None
    articulation: Optional[Articulation] = None
    reinserted_stream_id = None

    if trace.drift_signals:
        reintegrations = reintegrate_field(
            state,
            trace.drift_signals,
            hypotheses,
        )
    else:
        cut = form_provisional_cut(state, hypotheses)
        if cut is not None:
            articulation = articulate(state, cut)
        if articulation is not None:
            reinserted_stream_id = reinsert_articulation(
                state,
                articulation,
                hypotheses,
            )

    after = snapshot_field(state)
    state.history.append(
        HistoryEntry(
            cycle=len(state.history) + 1,
            before=before,
            step_trace=deepcopy(trace),
            reintegrations=deepcopy(reintegrations),
            cut_id=cut.cut_id if cut is not None else None,
            articulation_id=(
                articulation.articulation_id
                if articulation is not None
                else None
            ),
            after=after,
        )
    )
    assert_native_invariants(state)
    return CycleResult(
        trace=trace,
        reintegrations=reintegrations,
        cut=cut,
        articulation=articulation,
        reinserted_stream_id=reinserted_stream_id,
    )


def run_until_articulation(
    state: FieldState,
    max_cycles: int = 8,
    hypotheses: Optional[RuntimeHypotheses] = None,
) -> Tuple[Optional[Articulation], List[CycleResult]]:
    if max_cycles < 1:
        raise ValueError("max_cycles must be at least 1")
    hypotheses = hypotheses or RuntimeHypotheses()
    results: List[CycleResult] = []
    for _ in range(max_cycles):
        result = run_cycle(state, hypotheses)
        results.append(result)
        if result.articulation is not None:
            return result.articulation, results
    return None, results


def assert_native_invariants(state: FieldState) -> None:
    stream_ids = [item.stream_id for item in state.streams]
    if len(stream_ids) != len(set(stream_ids)):
        raise AssertionError("native field contains duplicate stream IDs")
    stream_id_set = set(stream_ids)

    relation_ids = [item.relation_id for item in state.relations]
    if len(relation_ids) != len(set(relation_ids)):
        raise AssertionError("native field contains duplicate relation IDs")
    for relation in state.relations:
        if relation.left_id not in stream_id_set:
            raise AssertionError("relation left endpoint is absent")
        if relation.right_id not in stream_id_set:
            raise AssertionError("relation right endpoint is absent")

    phenomenon_ids = {item.phenomenon_id for item in state.phenomena}
    if not set(state.current_phenomenon_ids).issubset(phenomenon_ids):
        raise AssertionError("current phenomena must exist in field history")

    cut = state.latest_cut()
    if cut is not None:
        included = set(cut.included_stream_ids)
        held_open = set(cut.held_open_stream_ids)
        if included & held_open:
            raise AssertionError(
                "a stream cannot be both included and held open in one cut"
            )
        if not included.issubset(stream_id_set):
            raise AssertionError("cut includes an absent stream")
        if not held_open.issubset(stream_id_set):
            raise AssertionError("cut holds open an absent stream")
        if cut.excluded_stream_ids:
            raise AssertionError(
                "native core does not semantically discard active material"
            )
