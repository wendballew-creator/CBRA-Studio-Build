"""Co-active field transformations for the CBRA native runtime.

Every operator reads the same pre-update field.  The stable function order is
only an ordering for reproducible traces; no operator consumes another
operator's newly produced state during the same update.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
from itertools import combinations
from math import sqrt
import re
from typing import Dict, Iterable, List, Set, Tuple

from .hypotheses import RuntimeHypotheses
from .models import (
    CareConstraint,
    DiffractivePattern,
    FieldState,
    OperatorDelta,
    Relation,
    Stream,
    clamp01,
)


OPERATOR_ORDER = [
    "intra_action",
    "play",
    "diffraction",
    "creative_becoming",
    "care",
]


def _stable_id(prefix: str, *parts: str) -> str:
    body = "|".join(str(part) for part in parts)
    return "{0}:{1}".format(prefix, sha1(body.encode("utf-8")).hexdigest()[:14])


def _active_streams(state: FieldState) -> List[Stream]:
    # Identity ordering makes traces deterministic; it does not order streams
    # by relevance, strength, or fitness.
    return sorted(
        [item for item in state.streams if item.active],
        key=lambda item: item.stream_id,
    )


def _stream_text(stream: Stream) -> str:
    explicit = str(stream.payload.get("text", "") or "").strip()
    if explicit:
        return explicit
    values: List[str] = []
    for key in sorted(stream.payload):
        value = stream.payload[key]
        if isinstance(value, (str, int, float, bool)):
            values.append(str(value))
        elif isinstance(value, list):
            values.extend(str(item) for item in value)
    return " ".join(values).strip()


def _tokens(stream: Stream) -> Set[str]:
    return set(re.findall(r"[a-z0-9]+", _stream_text(stream).lower()))


def relation_for_pair(
    left: Stream,
    right: Stream,
    hypotheses: RuntimeHypotheses,
) -> Relation:
    """Describe relational presence without producing a relevance score."""
    if right.stream_id < left.stream_id:
        left, right = right, left

    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    union = left_tokens | right_tokens
    intersection = left_tokens & right_tokens
    resonance = len(intersection) / len(union) if union else 0.0

    if union:
        difference = 1.0 - resonance
    else:
        difference = (
            hypotheses.no_text_cross_kind_difference
            if left.kind != right.kind
            else hypotheses.no_text_same_kind_difference
        )

    if left.kind == right.kind:
        resonance = clamp01(
            resonance + hypotheses.same_kind_resonance_increment
        )
    else:
        difference = clamp01(
            difference + hypotheses.cross_kind_difference_increment
        )

    apparatus_effect = (
        hypotheses.apparatus_relation_effect
        if "apparatus" in {left.kind, right.kind}
        else 0.0
    )
    participation = sqrt(
        max(0.0, left.participation) * max(0.0, right.participation)
    )
    mutuality = clamp01(
        participation
        * (
            hypotheses.relation_mutuality_base
            + (hypotheses.relation_resonance_weight * resonance)
            + (hypotheses.relation_difference_weight * difference)
            + apparatus_effect
        )
    )

    relation_id = _stable_id("relation", left.stream_id, right.stream_id)
    return Relation(
        relation_id=relation_id,
        left_id=left.stream_id,
        right_id=right.stream_id,
        resonance=resonance,
        difference=difference,
        mutuality=mutuality,
        apparatus_effect=apparatus_effect,
        traces=[
            "relation enacted between {0} and {1}".format(
                left.stream_id,
                right.stream_id,
            )
        ],
    )


def _all_relations(
    state: FieldState,
    hypotheses: RuntimeHypotheses,
) -> List[Relation]:
    streams = _active_streams(state)
    return [
        relation_for_pair(left, right, hypotheses)
        for left, right in combinations(streams, 2)
    ]


def propose_intra_action(
    state: FieldState,
    hypotheses: RuntimeHypotheses,
) -> OperatorDelta:
    delta = OperatorDelta("intra_action", basis_timestep=state.timestep)
    relations = _all_relations(state, hypotheses)
    incident: Dict[str, List[float]] = {
        item.stream_id: [] for item in _active_streams(state)
    }

    for relation in relations:
        relation.active = relation.mutuality >= hypotheses.relation_presence_floor
        delta.relation_updates[relation.relation_id] = relation
        incident[relation.left_id].append(relation.mutuality)
        incident[relation.right_id].append(relation.mutuality)

    for stream_id, values in incident.items():
        if not values:
            continue
        local_mutuality = sum(values) / len(values)
        delta.stream_participation_changes[stream_id] = (
            hypotheses.intra_participation_base
            + (
                hypotheses.intra_participation_mutuality_weight
                * local_mutuality
            )
        )

    active_relations = [item for item in relations if item.active]
    mean_mutuality = (
        sum(item.mutuality for item in active_relations) / len(active_relations)
        if active_relations
        else 0.0
    )
    delta.field_value_changes["relational_intensity"] = (
        mean_mutuality - state.field_values.relational_intensity
    ) * hypotheses.intra_relational_adjustment
    delta.field_value_changes["emergence_level"] = (
        hypotheses.intra_emergence_weight * mean_mutuality
    )
    delta.traces.append(
        "Mutual formation proposed across every active stream pair; no lead stream was chosen."
    )
    return delta


def propose_play(
    state: FieldState,
    hypotheses: RuntimeHypotheses,
) -> OperatorDelta:
    delta = OperatorDelta("play", basis_timestep=state.timestep)
    existing_ids = {item.stream_id for item in state.streams}

    for left, right in combinations(_active_streams(state), 2):
        if left.kind in {"play_variation", "diffractive_trace"}:
            continue
        if right.kind in {"play_variation", "diffractive_trace"}:
            continue
        # Apparatus facets already participate in relations with field
        # material.  Generating variations among apparatus facets alone would
        # amplify the interface description instead of widening the inquiry.
        if left.kind == "apparatus" and right.kind == "apparatus":
            continue
        relation = relation_for_pair(left, right, hypotheses)
        if relation.difference < hypotheses.play_difference_floor:
            continue

        stream_id = _stable_id("play", left.stream_id, right.stream_id)
        if stream_id in existing_ids:
            continue
        delta.proposed_streams.append(
            Stream(
                stream_id=stream_id,
                kind="play_variation",
                payload={
                    "variation": "relational_reconfiguration",
                    "source_stream_ids": [left.stream_id, right.stream_id],
                    "difference": relation.difference,
                },
                participation=hypotheses.play_stream_participation,
                persistence=hypotheses.play_stream_persistence,
                provenance={
                    "operator": "play",
                    "basis_timestep": state.timestep,
                },
            )
        )

    delta.field_value_changes.update(
        {
            "openness": hypotheses.play_openness_change,
            "multiplicity": hypotheses.play_multiplicity_change,
            "cut_permeability": hypotheses.play_permeability_change,
        }
    )
    delta.traces.append(
        "Generative variations preserve both source streams and add relational possibility without resolving either."
    )
    return delta


def propose_diffraction(
    state: FieldState,
    hypotheses: RuntimeHypotheses,
) -> OperatorDelta:
    delta = OperatorDelta("diffraction", basis_timestep=state.timestep)
    relations = _all_relations(state, hypotheses)
    active_differences: List[float] = []
    active_resonances: List[float] = []

    for relation in relations:
        if relation.difference < hypotheses.diffraction_difference_floor:
            continue
        if relation.mutuality < hypotheses.relation_presence_floor:
            continue
        pattern_id = _stable_id(
            "diffraction",
            str(state.timestep + 1),
            relation.relation_id,
        )
        delta.patterns.append(
            DiffractivePattern(
                pattern_id=pattern_id,
                stream_ids=[relation.left_id, relation.right_id],
                relation_ids=[relation.relation_id],
                resonance=relation.resonance,
                difference=relation.difference,
                timestep=state.timestep + 1,
                trace="Difference remains active across {0} and {1}.".format(
                    relation.left_id,
                    relation.right_id,
                ),
            )
        )
        active_differences.append(relation.difference)
        active_resonances.append(relation.resonance)

    if active_differences:
        mean_difference = sum(active_differences) / len(active_differences)
        mean_resonance = sum(active_resonances) / len(active_resonances)
        delta.field_value_changes["difference_activity"] = (
            hypotheses.diffraction_activity_weight * mean_difference
        )
        delta.field_value_changes["multiplicity"] = min(
            hypotheses.diffraction_multiplicity_limit,
            hypotheses.diffraction_multiplicity_base
            + (
                hypotheses.diffraction_multiplicity_per_pattern
                * len(active_differences)
            ),
        )
        delta.field_value_changes["coherence"] = (
            (
                hypotheses.diffraction_coherence_resonance_weight
                * mean_resonance
            )
            - (
                hypotheses.diffraction_coherence_difference_weight
                * mean_difference
            )
        )
    else:
        delta.field_value_changes[
            "openness"
        ] = hypotheses.diffraction_sparse_openness_change

    delta.traces.append(
        "Patterns were traced through difference without collapsing different stream kinds into sameness."
    )
    return delta


def propose_creative_becoming(
    state: FieldState,
    hypotheses: RuntimeHypotheses,
) -> OperatorDelta:
    delta = OperatorDelta("creative_becoming", basis_timestep=state.timestep)
    relations = [
        item
        for item in _all_relations(state, hypotheses)
        if item.mutuality >= hypotheses.emergence_relation_floor
    ]

    if relations:
        mean_strength = sum(item.mutuality for item in relations) / len(relations)
        mean_resonance = sum(item.resonance for item in relations) / len(relations)
        mean_difference = sum(item.difference for item in relations) / len(relations)
        delta.field_value_changes.update(
            {
                "coherence": hypotheses.becoming_coherence_base
                + (
                    hypotheses.becoming_coherence_resonance_weight
                    * mean_resonance
                ),
                "cut_pressure": hypotheses.becoming_cut_pressure_base
                + (
                    hypotheses.becoming_cut_pressure_strength_weight
                    * mean_strength
                ),
                "multiplicity": (
                    hypotheses.becoming_multiplicity_difference_weight
                    * mean_difference
                ),
            }
        )
        delta.field_value_changes["emergence_level"] = (
            hypotheses.becoming_emergence_base
            + (
                hypotheses.becoming_emergence_strength_weight
                * mean_strength
            )
        )
        delta.traces.append(
            "Creative Becoming increased the field's capacity to form without designating a lead stream or predetermining the phenomenon."
        )
    else:
        delta.field_value_changes[
            "openness"
        ] = hypotheses.becoming_sparse_openness_change
        delta.traces.append(
            "No multi-stream constellation stabilized; the field remains open without forced form."
        )
    return delta


def propose_care(
    state: FieldState,
    hypotheses: RuntimeHypotheses,
) -> OperatorDelta:
    delta = OperatorDelta("care", basis_timestep=state.timestep)
    values = state.field_values
    represented_kinds = {item.kind for item in _active_streams(state)}

    if values.cut_pressure >= hypotheses.coercive_cut_pressure:
        delta.field_value_changes.update(
            {
                "cut_permeability": hypotheses.care_reopen_permeability_change,
                "cut_pressure": hypotheses.care_reopen_pressure_change,
                "care_tension": hypotheses.care_reopen_tension_change,
            }
        )
        delta.field_value_changes[
            "openness"
        ] = hypotheses.care_reopen_openness_change
        delta.traces.append(
            "Care countered coercive closure by reopening the prospective boundary."
        )
    else:
        delta.field_value_changes[
            "care_capacity"
        ] = hypotheses.care_capacity_change
        delta.field_value_changes[
            "care_tension"
        ] = hypotheses.care_tension_release

    if len(represented_kinds) > 1:
        delta.field_value_changes[
            "multiplicity"
        ] = hypotheses.care_multiplicity_change
    delta.traces.append(
        "Care acts as a field transformation and constrains every other operator proposal."
    )
    return delta


def constrain_with_care(
    state: FieldState,
    deltas: Iterable[OperatorDelta],
    hypotheses: RuntimeHypotheses,
) -> Tuple[List[OperatorDelta], List[CareConstraint]]:
    constrained = deepcopy(list(deltas))
    records: List[CareConstraint] = []
    protected_ids: Set[str] = set()
    latest_cut = state.latest_cut()
    if latest_cut is not None:
        protected_ids.update(latest_cut.held_open_stream_ids)

    protected_floors = {
        "openness": hypotheses.care_min_openness,
        "multiplicity": hypotheses.care_min_multiplicity,
        "cut_permeability": hypotheses.care_min_permeability,
    }

    for delta in constrained:
        for stream_id, proposed in list(
            delta.stream_participation_changes.items()
        ):
            adjusted = max(
                -hypotheses.care_max_stream_shift,
                min(hypotheses.care_max_stream_shift, proposed),
            )
            if stream_id in protected_ids and adjusted < 0.0:
                adjusted = 0.0
            if adjusted != proposed:
                records.append(
                    CareConstraint(
                        operator_name=delta.operator_name,
                        target="stream:{0}".format(stream_id),
                        proposed_change=proposed,
                        constrained_change=adjusted,
                        reason="held-open material and participation shifts remain non-coercive",
                    )
                )
                delta.stream_participation_changes[stream_id] = adjusted

        for name, proposed in list(delta.field_value_changes.items()):
            adjusted = max(
                -hypotheses.care_max_field_shift,
                min(hypotheses.care_max_field_shift, proposed),
            )
            current = float(getattr(state.field_values, name))
            floor = protected_floors.get(name)
            if floor is not None and current + adjusted < floor:
                adjusted = floor - current
            if (
                name == "cut_pressure"
                and proposed > 0.0
                and state.field_values.cut_pressure
                >= hypotheses.coercive_cut_pressure
            ):
                adjusted = min(
                    adjusted,
                    proposed
                    * hypotheses.care_high_pressure_cut_growth_factor,
                )
            if adjusted != proposed:
                records.append(
                    CareConstraint(
                        operator_name=delta.operator_name,
                        target="field:{0}".format(name),
                        proposed_change=proposed,
                        constrained_change=adjusted,
                        reason="care limits coercive closure and protects field capacity",
                    )
                )
                delta.field_value_changes[name] = adjusted

    return constrained, records


def propose_coactive_updates(
    state: FieldState,
    hypotheses: RuntimeHypotheses,
) -> Tuple[List[OperatorDelta], List[CareConstraint]]:
    proposals = [
        propose_intra_action(state, hypotheses),
        propose_play(state, hypotheses),
        propose_diffraction(state, hypotheses),
        propose_creative_becoming(state, hypotheses),
    ]
    constrained, constraints = constrain_with_care(
        state,
        proposals,
        hypotheses,
    )
    constrained.append(propose_care(state, hypotheses))
    return constrained, constraints
