"""Field formation, co-active updates, reintegration, and runtime movement."""

from __future__ import annotations

from copy import deepcopy
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import uuid4

from .articulation import (
    ArticulationRenderer,
    ArticulationRendererBinding,
    accept_articulation,
    assert_renderer_binding,
    evaluate_articulation_candidate,
    form_articulation_candidate,
    form_provisional_cut,
    ready_for_provisional_cut,
    reinsert_articulation,
)
from .emergence import emerge_phenomena
from .hypotheses import RuntimeHypotheses
from .models import (
    Apparatus,
    Articulation,
    ArticulationCandidate,
    ArticulationEvaluation,
    CyclePhase,
    CycleResult,
    DriftKind,
    DriftSignal,
    FieldSnapshot,
    FieldState,
    FieldValues,
    HistoryEntry,
    OperatorDelta,
    PhaseSnapshot,
    ReentryTarget,
    ReintegrationTrace,
    StepTrace,
    Stream,
    clamp01,
)
from .operators import OPERATOR_ORDER, propose_coactive_updates


DRIFT_REENTRY_TARGETS = {
    DriftKind.ONTOLOGICAL_DRIFT: ReentryTarget.FIELD_ENTRY,
    DriftKind.COMPRESSION: ReentryTarget.NOTICING,
    DriftKind.CAPACITY_COLLAPSE: ReentryTarget.RELATIONAL_FRAMING,
    DriftKind.NARRATIVE_DOMINANCE: ReentryTarget.DIFFRACTIVE_MAPPING,
    DriftKind.MORALIZATION: ReentryTarget.ARTICULATION,
    DriftKind.PROCEDURAL_BYPASS: ReentryTarget.FIELD_ENTRY,
}


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
    """Copy every runtime formation except recursive history."""
    return FieldSnapshot(
        field_id=state.field_id,
        timestep=state.timestep,
        apparatus=deepcopy(state.apparatus),
        streams=tuple(deepcopy(state.streams)),
        relations=tuple(deepcopy(state.relations)),
        patterns=tuple(deepcopy(state.patterns)),
        phenomena=tuple(deepcopy(state.phenomena)),
        cuts=tuple(deepcopy(state.cuts)),
        articulation_candidates=tuple(
            deepcopy(state.articulation_candidates)
        ),
        articulation_evaluations=tuple(
            deepcopy(state.articulation_evaluations)
        ),
        articulations=tuple(deepcopy(state.articulations)),
        field_values=state.field_values.as_dict(),
        current_pattern_ids=tuple(state.current_pattern_ids),
        current_phenomenon_ids=tuple(state.current_phenomenon_ids),
        current_cut_id=state.current_cut_id,
        current_candidate_id=state.current_candidate_id,
        current_evaluation_id=state.current_evaluation_id,
        current_articulation_id=state.current_articulation_id,
        articulation_eligible=state.articulation_eligible,
        active_drifts=tuple(deepcopy(state.active_drifts)),
        pending_drifts=tuple(deepcopy(state.pending_drifts)),
        pending_reentry_targets=tuple(state.pending_reentry_targets),
    )


def _integrate_coactive_deltas(
    state: FieldState,
    deltas: Sequence[OperatorDelta],
) -> List[ReentryTarget]:
    reentry_targets_applied = list(
        dict.fromkeys(state.pending_reentry_targets)
    )
    state.pending_reentry_targets = []

    # A new field update makes prior formations historical.  Their records
    # remain in the append-only collections, while current identities are
    # cleared before new patterns and phenomena can emerge.
    state.current_pattern_ids = []
    state.current_phenomenon_ids = []
    state.current_cut_id = None
    state.current_candidate_id = None
    state.current_evaluation_id = None
    state.current_articulation_id = None
    state.articulation_eligible = False

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

    # Relations are current enactments, not an accumulating complete graph.
    # Prior configurations remain available through FieldSnapshot history.
    state.relations = [
        relation_updates[relation_id]
        for relation_id in sorted(relation_updates)
    ]

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
    return reentry_targets_applied


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

    # Sparse enacted topology is compatible with active held-open material.
    # It is therefore not sufficient evidence of ontological drift.  Until a
    # detector can observe isolated-agent or fixed-identity reasoning, this
    # drift form enters through explicit pending signals rather than graph
    # density, which would force the field back toward universal connection.

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


def _update_field_with_phase_snapshots(
    state: FieldState,
    hypotheses: RuntimeHypotheses,
) -> Tuple[StepTrace, FieldSnapshot, FieldSnapshot]:
    basis_timestep = state.timestep
    # Operator functions are pure proposals over this same pre-update state.
    deltas, care_constraints = propose_coactive_updates(state, hypotheses)
    reentry_targets_applied = _integrate_coactive_deltas(state, deltas)
    emerge_phenomena(state, hypotheses)
    after_update_and_emergence = snapshot_field(state)
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
    state.articulation_eligible = ready_for_provisional_cut(
        state,
        hypotheses,
    )
    state.clamp()
    assert_native_invariants(state)
    after_drift_detection = snapshot_field(state)
    trace = StepTrace(
        timestep_before=basis_timestep,
        timestep_after=state.timestep,
        calculation_basis_timestep=basis_timestep,
        operator_order=list(OPERATOR_ORDER),
        deltas=deltas,
        care_constraints=care_constraints,
        drift_signals=deepcopy(drift_signals),
        hypotheses=hypotheses.as_dict(),
        reentry_targets_applied=reentry_targets_applied,
    )
    return trace, after_update_and_emergence, after_drift_detection


def update_field(
    state: FieldState,
    hypotheses: Optional[RuntimeHypotheses] = None,
) -> StepTrace:
    hypotheses = hypotheses or RuntimeHypotheses()
    trace, _, _ = _update_field_with_phase_snapshots(state, hypotheses)
    return trace


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
    signal = deepcopy(signal)
    signal.clamp()
    reentry_target = DRIFT_REENTRY_TARGETS[signal.kind]
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
        target_enactment = (
            "Noticing is reopened by increasing openness and permeability "
            "while loosening pressure and forced coherence."
        )

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
        target_enactment = (
            "Diffractive Mapping is reopened by redistributing participation "
            "and restoring difference without installing a replacement story."
        )

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
        target_enactment = (
            "Articulation is reopened by softening evaluative closure and "
            "restoring descriptive, revisable expression."
        )

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
        target_enactment = (
            "Relational Framing is reopened by reducing intensity and making "
            "capacity and care constraints visible again."
        )

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
        target_enactment = (
            "Field Entry is reopened by strengthening enacted relation, "
            "multiplicity, and situated openness."
        )

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
        target_enactment = (
            "Field Entry is reopened by restoring permeability and openness "
            "before the next complete co-active update."
        )

    field_changes = _apply_field_changes(state, requested_fields)
    state.clamp()
    return ReintegrationTrace(
        drift_kind=signal.kind,
        reentry_target=reentry_target,
        signal_intensity=signal.intensity,
        signal_evidence=list(signal.evidence),
        signal_source=signal.source,
        signal_detected_at=signal.detected_at,
        field_value_changes=field_changes,
        stream_participation_changes=stream_changes,
        relation_changes=relation_changes,
        invalidated_pattern_ids=[],
        invalidated_phenomenon_ids=[],
        invalidated_cut_id=None,
        invalidated_candidate_id=None,
        invalidated_evaluation_id=None,
        invalidated_articulation_id=None,
        target_enactment=target_enactment,
        trace=trace,
    )


def _invalidate_current_formations(
    state: FieldState,
) -> Tuple[
    List[str],
    List[str],
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
]:
    pattern_ids = list(state.current_pattern_ids)
    phenomenon_ids = list(state.current_phenomenon_ids)
    cut_id = state.current_cut_id
    candidate_id = state.current_candidate_id
    evaluation_id = state.current_evaluation_id
    articulation_id = state.current_articulation_id
    state.current_pattern_ids = []
    state.current_phenomenon_ids = []
    state.current_cut_id = None
    state.current_candidate_id = None
    state.current_evaluation_id = None
    state.current_articulation_id = None
    state.articulation_eligible = False
    return (
        pattern_ids,
        phenomenon_ids,
        cut_id,
        candidate_id,
        evaluation_id,
        articulation_id,
    )


def reintegrate_field(
    state: FieldState,
    signals: Optional[Sequence[DriftSignal]] = None,
    hypotheses: Optional[RuntimeHypotheses] = None,
) -> List[ReintegrationTrace]:
    hypotheses = hypotheses or RuntimeHypotheses()
    signals = list(signals if signals is not None else state.active_drifts)
    if not signals:
        return []
    traces = [
        _reintegrate_one(state, signal, hypotheses)
        for signal in signals
    ]
    invalidated = _invalidate_current_formations(state)
    for trace in traces:
        trace.invalidated_pattern_ids = list(invalidated[0])
        trace.invalidated_phenomenon_ids = list(invalidated[1])
        trace.invalidated_cut_id = invalidated[2]
        trace.invalidated_candidate_id = invalidated[3]
        trace.invalidated_evaluation_id = invalidated[4]
        trace.invalidated_articulation_id = invalidated[5]

    state.pending_reentry_targets = list(
        dict.fromkeys(
            state.pending_reentry_targets
            + [item.reentry_target for item in traces]
        )
    )
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
    renderer: Optional[ArticulationRenderer] = None,
    renderer_binding: Optional[ArticulationRendererBinding] = None,
) -> CycleResult:
    hypotheses = hypotheses or RuntimeHypotheses()
    assert_renderer_binding(
        state.apparatus,
        renderer,
        renderer_binding,
    )
    before = snapshot_field(state)
    (
        trace,
        after_update_and_emergence,
        after_drift_detection,
    ) = _update_field_with_phase_snapshots(state, hypotheses)
    reintegrations: List[ReintegrationTrace] = []
    cut = None
    candidate: Optional[ArticulationCandidate] = None
    evaluation: Optional[ArticulationEvaluation] = None
    articulation: Optional[Articulation] = None
    reinserted_stream_id = None

    if trace.drift_signals:
        after_articulation_evaluation = snapshot_field(state)
        reintegrations = reintegrate_field(
            state,
            trace.drift_signals,
            hypotheses,
        )
    else:
        cut = form_provisional_cut(state, hypotheses)
        if cut is not None:
            if renderer is None:
                candidate = form_articulation_candidate(
                    state,
                    cut,
                    hypotheses,
                )
            else:
                candidate = form_articulation_candidate(
                    state,
                    cut,
                    hypotheses,
                    renderer,
                    renderer_binding,
                )
        if candidate is not None:
            evaluation = evaluate_articulation_candidate(
                state,
                candidate,
                hypotheses,
            )
            if evaluation.drift_signals:
                state.field_values.drift_load = clamp01(
                    state.field_values.drift_load
                    + (
                        hypotheses.drift_load_signal_weight
                        * sum(
                            item.intensity
                            for item in evaluation.drift_signals
                        )
                    )
                )
                state.clamp()
        after_articulation_evaluation = snapshot_field(state)
        if evaluation is not None and evaluation.accepted:
            articulation = accept_articulation(
                state,
                candidate,
                evaluation,
            )
            if articulation is not None:
                reinserted_stream_id = reinsert_articulation(
                    state,
                    articulation,
                    hypotheses,
                )
        elif evaluation is not None:
            reintegrations = reintegrate_field(
                state,
                evaluation.drift_signals,
                hypotheses,
            )

    after = snapshot_field(state)
    history_entry = HistoryEntry(
        cycle=len(state.history) + 1,
        phases=(
            PhaseSnapshot(CyclePhase.BEFORE_UPDATE, before),
            PhaseSnapshot(
                CyclePhase.AFTER_UPDATE_AND_EMERGENCE,
                after_update_and_emergence,
            ),
            PhaseSnapshot(
                CyclePhase.AFTER_DRIFT_DETECTION,
                after_drift_detection,
            ),
            PhaseSnapshot(
                CyclePhase.AFTER_ARTICULATION_EVALUATION,
                after_articulation_evaluation,
            ),
            PhaseSnapshot(
                CyclePhase.AFTER_REINTEGRATION_OR_ARTICULATION,
                after,
            ),
        ),
        step_trace=deepcopy(trace),
        reintegrations=tuple(deepcopy(reintegrations)),
        cut_id=cut.cut_id if cut is not None else None,
        candidate_id=(
            candidate.candidate_id
            if candidate is not None
            else None
        ),
        evaluation_id=(
            evaluation.evaluation_id
            if evaluation is not None
            else None
        ),
        articulation_id=(
            articulation.articulation_id
            if articulation is not None
            else None
        ),
    )
    state.history = state.history + (history_entry,)
    assert_native_invariants(state)
    return CycleResult(
        trace=trace,
        reintegrations=reintegrations,
        cut=cut,
        articulation_candidate=candidate,
        articulation_evaluation=evaluation,
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
        if not relation.active:
            raise AssertionError(
                "native field stores enacted relations only"
            )
        if relation.left_id not in stream_id_set:
            raise AssertionError("relation left endpoint is absent")
        if relation.right_id not in stream_id_set:
            raise AssertionError("relation right endpoint is absent")

    phenomenon_ids = {item.phenomenon_id for item in state.phenomena}
    if not set(state.current_phenomenon_ids).issubset(phenomenon_ids):
        raise AssertionError("current phenomena must exist in field history")

    pattern_ids = {item.pattern_id for item in state.patterns}
    if not set(state.current_pattern_ids).issubset(pattern_ids):
        raise AssertionError("current patterns must exist in field history")

    cut_ids = {item.cut_id for item in state.cuts}
    if (
        state.current_cut_id is not None
        and state.current_cut_id not in cut_ids
    ):
        raise AssertionError("current cut must exist in field history")

    candidate_ids = {
        item.candidate_id for item in state.articulation_candidates
    }
    if len(candidate_ids) != len(state.articulation_candidates):
        raise AssertionError("articulation candidate IDs must be unique")
    if (
        state.current_candidate_id is not None
        and state.current_candidate_id not in candidate_ids
    ):
        raise AssertionError(
            "current candidate must exist in field history"
        )

    evaluation_ids = {
        item.evaluation_id for item in state.articulation_evaluations
    }
    evaluations_by_id = {
        item.evaluation_id: item
        for item in state.articulation_evaluations
    }
    if len(evaluation_ids) != len(state.articulation_evaluations):
        raise AssertionError("articulation evaluation IDs must be unique")
    if (
        state.current_evaluation_id is not None
        and state.current_evaluation_id not in evaluation_ids
    ):
        raise AssertionError(
            "current evaluation must exist in field history"
        )
    for evaluation in state.articulation_evaluations:
        if evaluation.candidate_id not in candidate_ids:
            raise AssertionError(
                "articulation evaluation references an absent candidate"
            )

    articulation_ids = {
        item.articulation_id for item in state.articulations
    }
    if (
        state.current_articulation_id is not None
        and state.current_articulation_id not in articulation_ids
    ):
        raise AssertionError(
            "current articulation must exist in field history"
        )
    if (
        state.current_articulation_id is not None
        and state.current_cut_id is None
    ):
        raise AssertionError("a current articulation requires a current cut")
    if (
        state.current_candidate_id is not None
        and state.current_cut_id is None
    ):
        raise AssertionError("a current candidate requires a current cut")
    if (
        state.current_evaluation_id is not None
        and state.current_candidate_id is None
    ):
        raise AssertionError(
            "a current evaluation requires a current candidate"
        )
    if state.current_evaluation_id is not None:
        current_evaluation = evaluations_by_id[state.current_evaluation_id]
        if current_evaluation.candidate_id != state.current_candidate_id:
            raise AssertionError(
                "current evaluation must evaluate the current candidate"
            )
    if (
        state.current_articulation_id is not None
        and (
            state.current_candidate_id is None
            or state.current_evaluation_id is None
        )
    ):
        raise AssertionError(
            "an accepted articulation requires its current candidate "
            "and evaluation"
        )
    for articulation in state.articulations:
        if articulation.candidate_id not in candidate_ids:
            raise AssertionError(
                "accepted articulation references an absent candidate"
            )
        evaluation = evaluations_by_id.get(articulation.evaluation_id)
        if evaluation is None or not evaluation.accepted:
            raise AssertionError(
                "accepted articulation requires an accepted evaluation"
            )
    if state.active_drifts and state.articulation_eligible:
        raise AssertionError("drift suspends articulation eligibility")
    if state.articulation_eligible and not state.current_phenomenon_ids:
        raise AssertionError(
            "articulation eligibility requires current phenomena"
        )

    for cut in state.cuts:
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
