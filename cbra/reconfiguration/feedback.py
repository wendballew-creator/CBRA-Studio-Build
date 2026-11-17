"""Post-return effects re-entering without confirmation or disturbance authority.

Feedback is recorded against one exact current recomputation.  Its uptake is
explicit and local: correspondence leaves the formation open, complication
may reopen one dependent cut, and invalidation may reopen the enabling cut.
None of these dispositions is a score, terminal state, or judgment of value.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Sequence, Tuple

from .alternatives import (
    CompetingAlternatives,
    DimensionEffect,
    TracedAlternative,
    retain_competing_alternatives,
)
from dataclasses import replace

from .diffraction import ArrangementDependency, DiffractiveArrangementField
from .models import CutEnactment, ReconfigurationDelta, StructuralDimension
from .revision import RecursivelyRevisedArrangementField
from .substrate import InvalidReconfiguration, ReconfigurationSubstrate


class FeedbackDisposition(str, Enum):
    CONFIRMS = "confirms"
    COMPLICATES = "complicates"
    INVALIDATES = "invalidates"


@dataclass(frozen=True)
class ObservedDimensionEffect:
    dimension: StructuralDimension
    total: float
    maximum_local_load: float
    occupied_positions: int


@dataclass(frozen=True)
class FormationFeedbackTrace:
    observation_trace_id: str
    alternative_id: str
    enabling_cut_id: str
    expected_trace: TracedAlternative
    observed_effects: Tuple[ObservedDimensionEffect, ...]
    differing_dimensions: Tuple[StructuralDimension, ...]
    disposition: FeedbackDisposition
    affected_cut_id: str | None
    disturbance_delta: ReconfigurationDelta | None


@dataclass(frozen=True)
class FeedbackFieldRevisionTrace:
    """One disturbing feedback trace taken up through a local counter-cut."""

    feedback: FormationFeedbackTrace
    reopened_cut_id: str
    counter_cut_id: str
    prior_alternative_id: str
    recomputed_alternative_id: str
    prior_trace: TracedAlternative
    recomputed_trace: TracedAlternative


@dataclass(frozen=True)
class FeedbackProvenanceClosure:
    """Bounded continuity witness; preserved history remains the evidence."""

    closure_id: str
    predecessor_closure_id: str
    observation_trace_id: str
    disturbance_delta_id: str
    counter_cut_id: str
    recomputed_alternative_id: str


def return_effects_as_feedback(
    *,
    field: RecursivelyRevisedArrangementField,
    substrate: ReconfigurationSubstrate,
    observation_trace_id: str,
    alternative_id: str,
    observed_effects: Sequence[ObservedDimensionEffect],
    disposition: FeedbackDisposition,
    affected_cut_id: str | None = None,
    delta_id: str | None = None,
) -> RecursivelyRevisedArrangementField:
    """Take up observed effects without deriving a command from correspondence.

    The observation must be a recorded transport trace and the alternative
    must be one exact current oscillation-grounded recomputation.  Mutation is
    preflighted and occurs only for an explicitly scoped complication or
    invalidation.
    """

    if observation_trace_id not in substrate.state.transports:
        raise InvalidReconfiguration("feedback requires a recorded observation")
    if any(
        item.observation_trace_id == observation_trace_id for item in field.feedback
    ):
        raise InvalidReconfiguration(
            "one observation cannot manufacture repeated feedback authority"
        )
    current = {
        item.replacement.cut_id: item
        for item in field.field.competing.alternatives
    }
    expected = current.get(alternative_id)
    if expected is None:
        raise InvalidReconfiguration("feedback target must be currently retained")
    oscillation_matches = tuple(
        (revision, affected)
        for revision in field.oscillation_revisions
        for affected in revision.affected
        if affected.recomputed_alternative_id == alternative_id
        and affected.recomputed_trace == expected
    )
    feedback_matches = tuple(
        revision
        for revision in field.feedback_revisions
        if revision.recomputed_alternative_id == alternative_id
        and revision.recomputed_trace == expected
    )
    if len(oscillation_matches) + len(feedback_matches) != 1:
        raise InvalidReconfiguration(
            "feedback requires one exact recorded field recomputation"
        )
    if oscillation_matches:
        revision, affected = oscillation_matches[0]
        enabling_cut_id = revision.counter_cut_id
        prior_alternative_id = affected.prior_alternative_id
    else:
        feedback_revision = feedback_matches[0]
        validate_feedback_provenance_closure(
            field=field,
            substrate=substrate,
            revision=feedback_revision,
        )
        enabling_cut_id = feedback_revision.counter_cut_id
        prior_alternative_id = feedback_revision.prior_alternative_id
    dependencies = {
        item.alternative_cut_id: item.enabling_cut_ids
        for item in field.field.dependencies
    }
    if enabling_cut_id not in dependencies.get(alternative_id, ()):
        raise InvalidReconfiguration("feedback target has inconsistent field lineage")
    if enabling_cut_id not in substrate.state.active_cut_ids:
        raise InvalidReconfiguration("feedback target enabling formation is inactive")
    if prior_alternative_id not in expected.replacement.lineage_ids:
        raise InvalidReconfiguration("feedback target has inconsistent proposal lineage")

    observations = tuple(observed_effects)
    dimensions = tuple(item.dimension for item in observations)
    if not observations or len(set(dimensions)) != len(dimensions):
        raise InvalidReconfiguration(
            "feedback effects must identify unique observed dimensions"
        )
    expected_by_dimension = {item.dimension: item for item in expected.effects}
    differing = tuple(
        item.dimension
        for item in observations
        if not _corresponds(item, expected_by_dimension[item.dimension])
    )

    if disposition == FeedbackDisposition.CONFIRMS:
        if differing:
            raise InvalidReconfiguration(
                "confirmation requires correspondence for every observed dimension"
            )
        if affected_cut_id is not None or delta_id is not None:
            raise InvalidReconfiguration("confirmation cannot mutate the formation")
        trace = FormationFeedbackTrace(
            observation_trace_id, alternative_id, enabling_cut_id, expected,
            observations, differing, disposition, None, None,
        )
        return replace(field, feedback=field.feedback + (trace,))

    if not differing:
        raise InvalidReconfiguration(
            "disturbing feedback requires a recorded structural difference"
        )
    if not affected_cut_id or not delta_id:
        raise InvalidReconfiguration(
            "disturbing feedback requires an explicit affected cut and delta"
        )
    if disposition == FeedbackDisposition.COMPLICATES:
        if affected_cut_id == enabling_cut_id:
            raise InvalidReconfiguration(
                "complication cannot silently become enabling-cut invalidation"
            )
        affected_cut = substrate.state.cuts.get(affected_cut_id)
        if (
            affected_cut is None
            or affected_cut_id not in substrate.state.active_cut_ids
            or enabling_cut_id not in affected_cut.dependency_ids
        ):
            raise InvalidReconfiguration(
                "complication must name an active dependent formation"
            )
    elif disposition == FeedbackDisposition.INVALIDATES:
        if affected_cut_id != enabling_cut_id:
            raise InvalidReconfiguration(
                "invalidation must explicitly name the enabling formation"
            )
    else:
        raise InvalidReconfiguration("unknown feedback disposition")

    delta = substrate.disturb(
        delta_id=delta_id,
        triggering_trace_ids=(observation_trace_id,),
        invalidated_root_ids=(affected_cut_id,),
        replacements=(),
    )
    trace = FormationFeedbackTrace(
        observation_trace_id, alternative_id, enabling_cut_id, expected,
        observations, differing, disposition, affected_cut_id, delta,
    )
    return replace(field, feedback=field.feedback + (trace,))


def revise_field_from_feedback(
    *,
    field: RecursivelyRevisedArrangementField,
    substrate: ReconfigurationSubstrate,
    observation_trace_id: str,
    counter_cut: CutEnactment,
    counter_cut_delta_id: str,
    recomputed_arrangement: CutEnactment,
) -> RecursivelyRevisedArrangementField:
    """Ground one local counter-cut in exact complicating or invalidating feedback.

    Feedback uptake is explicit rather than automatic.  The complete competing
    field is retraced before the counter-cut is enacted, and prior confirmation
    remains evidence only: it supplies no weight, protection, or authority.
    """

    matches = tuple(
        item for item in field.feedback
        if item.observation_trace_id == observation_trace_id
    )
    if len(matches) != 1:
        raise InvalidReconfiguration(
            "feedback revision requires one exact retained feedback trace"
        )
    feedback = matches[0]
    if feedback.disposition == FeedbackDisposition.CONFIRMS:
        raise InvalidReconfiguration(
            "confirming feedback cannot authorize a counter-cut"
        )
    if feedback.disposition not in (
        FeedbackDisposition.COMPLICATES,
        FeedbackDisposition.INVALIDATES,
    ):
        raise InvalidReconfiguration("unknown feedback disposition")
    if feedback.disturbance_delta is None or feedback.affected_cut_id is None:
        raise InvalidReconfiguration(
            "feedback revision requires a recorded local disturbance"
        )
    if any(
        item.feedback.observation_trace_id == observation_trace_id
        for item in field.feedback_revisions
    ):
        raise InvalidReconfiguration(
            "one feedback trace cannot manufacture repeated revision authority"
        )

    recorded_delta = next(
        (
            item for item in substrate.state.deltas
            if item.delta_id == feedback.disturbance_delta.delta_id
        ),
        None,
    )
    if recorded_delta != feedback.disturbance_delta:
        raise InvalidReconfiguration(
            "feedback revision requires the exact recorded disturbance delta"
        )
    reopened_cut_id = feedback.affected_cut_id
    if (
        reopened_cut_id not in feedback.disturbance_delta.invalidated_cut_ids
        or substrate.state.invalidated_by.get(reopened_cut_id)
        != feedback.disturbance_delta.delta_id
    ):
        raise InvalidReconfiguration(
            "feedback revision must match substrate invalidation history"
        )
    if feedback.observation_trace_id not in feedback.disturbance_delta.triggering_trace_ids:
        raise InvalidReconfiguration(
            "feedback disturbance must retain its observation provenance"
        )

    _validate_feedback_target_origin(
        field=field,
        substrate=substrate,
        feedback=feedback,
    )

    current = tuple(field.field.competing.alternatives)
    prior_index = next(
        (
            index for index, item in enumerate(current)
            if item.replacement.cut_id == feedback.alternative_id
        ),
        None,
    )
    if prior_index is None or current[prior_index] != feedback.expected_trace:
        raise InvalidReconfiguration(
            "feedback revision target must remain the exact current projection"
        )
    prior = current[prior_index]
    dependencies = {
        item.alternative_cut_id: item.enabling_cut_ids
        for item in field.field.dependencies
    }
    if feedback.enabling_cut_id not in dependencies.get(feedback.alternative_id, ()):
        raise InvalidReconfiguration(
            "feedback revision target has inconsistent field lineage"
        )

    _validate_feedback_counter_cut(
        field=field,
        substrate=substrate,
        feedback=feedback,
        counter_cut=counter_cut,
    )
    if recomputed_arrangement.cut_id == prior.replacement.cut_id:
        raise InvalidReconfiguration(
            "feedback recomputation requires a new local cut id"
        )
    if prior.replacement.cut_id not in recomputed_arrangement.lineage_ids:
        raise InvalidReconfiguration(
            "feedback recomputation must preserve proposal lineage"
        )
    if counter_cut.cut_id not in recomputed_arrangement.dependency_ids:
        raise InvalidReconfiguration(
            "feedback recomputation must depend on its local counter-cut"
        )

    source = substrate.state.cuts.get(field.field.competing.source_cut_id)
    if source is None:
        raise InvalidReconfiguration("competing source cut is not recorded")
    replacements = tuple(
        recomputed_arrangement if index == prior_index else item.replacement
        for index, item in enumerate(current)
    )
    recomputed = retain_competing_alternatives(
        source=source,
        replacements=replacements,
        constraints=field.field.competing.constraints,
    )
    recomputed_trace = recomputed.alternatives[prior_index]
    if recomputed_trace.effects == prior.effects:
        raise InvalidReconfiguration(
            "feedback counter-cut must freshly change the affected trace"
        )

    substrate.enact_cut(counter_cut, delta_id=counter_cut_delta_id)
    revised_dependencies = tuple(
        ArrangementDependency(
            recomputed_arrangement.cut_id,
            (counter_cut.cut_id,),
        )
        if item.alternative_cut_id == prior.replacement.cut_id
        else item
        for item in field.field.dependencies
    )
    revised_field = DiffractiveArrangementField(
        competing=CompetingAlternatives(
            source_cut_id=recomputed.source_cut_id,
            alternatives=recomputed.alternatives,
            constraints=recomputed.constraints,
        ),
        dependencies=revised_dependencies,
        disturbances=field.field.disturbances,
    )
    revision = FeedbackFieldRevisionTrace(
        feedback=feedback,
        reopened_cut_id=reopened_cut_id,
        counter_cut_id=counter_cut.cut_id,
        prior_alternative_id=prior.replacement.cut_id,
        recomputed_alternative_id=recomputed_arrangement.cut_id,
        prior_trace=prior,
        recomputed_trace=recomputed_trace,
    )
    predecessor_closure_id = _origin_closure_id(field, feedback)
    closure = _form_provenance_closure(revision, predecessor_closure_id)
    return replace(
        field,
        field=revised_field,
        feedback_revisions=field.feedback_revisions + (revision,),
        provenance_closures=field.provenance_closures + (closure,),
    )


def validate_feedback_provenance_closure(
    *,
    field: RecursivelyRevisedArrangementField,
    substrate: ReconfigurationSubstrate,
    revision: FeedbackFieldRevisionTrace,
) -> None:
    """Validate present continuity without recursively traversing its history."""

    matches = tuple(
        item for item in field.provenance_closures
        if item.recomputed_alternative_id == revision.recomputed_alternative_id
        and item.counter_cut_id == revision.counter_cut_id
    )
    if len(matches) != 1:
        raise InvalidReconfiguration(
            "feedback recomputation requires one exact provenance closure"
        )
    closure = matches[0]
    expected = _form_provenance_closure(revision, closure.predecessor_closure_id)
    if closure != expected:
        raise InvalidReconfiguration("feedback provenance closure is inconsistent")
    _validate_feedback_recomputation_lineage(
        field=field,
        substrate=substrate,
        revision=revision,
    )
    if closure.predecessor_closure_id.startswith("feedback:"):
        predecessor_id = closure.predecessor_closure_id.removeprefix("feedback:")
        predecessors = tuple(
            item for item in field.provenance_closures
            if item.closure_id == predecessor_id
            and item.recomputed_alternative_id == revision.prior_alternative_id
        )
        if len(predecessors) != 1:
            raise InvalidReconfiguration(
                "feedback provenance closure requires its retained predecessor"
            )
    elif closure.predecessor_closure_id.startswith("oscillation:"):
        if closure.predecessor_closure_id != f"oscillation:{revision.prior_alternative_id}":
            raise InvalidReconfiguration(
                "feedback provenance closure has inconsistent oscillation origin"
            )
        roots = tuple(
            affected
            for oscillation_revision in field.oscillation_revisions
            for affected in oscillation_revision.affected
            if affected.recomputed_alternative_id == revision.prior_alternative_id
            and affected.recomputed_trace == revision.prior_trace
        )
        if len(roots) != 1:
            raise InvalidReconfiguration(
                "feedback provenance closure requires its oscillation origin"
            )
    else:
        raise InvalidReconfiguration("feedback provenance closure has no valid origin")


def _origin_closure_id(
    field: RecursivelyRevisedArrangementField,
    feedback: FormationFeedbackTrace,
) -> str:
    prior_closures = tuple(
        item for item in field.provenance_closures
        if item.recomputed_alternative_id == feedback.alternative_id
    )
    if len(prior_closures) == 1:
        return f"feedback:{prior_closures[0].closure_id}"
    oscillation_matches = tuple(
        affected
        for revision in field.oscillation_revisions
        for affected in revision.affected
        if affected.recomputed_alternative_id == feedback.alternative_id
        and affected.recomputed_trace == feedback.expected_trace
    )
    if len(prior_closures) == 0 and len(oscillation_matches) == 1:
        return f"oscillation:{feedback.alternative_id}"
    raise InvalidReconfiguration(
        "feedback revision requires one locally closed originating recomputation"
    )


def _form_provenance_closure(
    revision: FeedbackFieldRevisionTrace,
    predecessor_closure_id: str,
) -> FeedbackProvenanceClosure:
    feedback = revision.feedback
    assert feedback.disturbance_delta is not None
    material = "\x1f".join((
        predecessor_closure_id,
        feedback.observation_trace_id,
        feedback.disturbance_delta.delta_id,
        revision.reopened_cut_id,
        revision.counter_cut_id,
        revision.prior_alternative_id,
        revision.recomputed_alternative_id,
        repr(revision.prior_trace),
        repr(revision.recomputed_trace),
    ))
    return FeedbackProvenanceClosure(
        closure_id=sha256(material.encode()).hexdigest(),
        predecessor_closure_id=predecessor_closure_id,
        observation_trace_id=feedback.observation_trace_id,
        disturbance_delta_id=feedback.disturbance_delta.delta_id,
        counter_cut_id=revision.counter_cut_id,
        recomputed_alternative_id=revision.recomputed_alternative_id,
    )


def _validate_feedback_counter_cut(
    *,
    field: RecursivelyRevisedArrangementField,
    substrate: ReconfigurationSubstrate,
    feedback: FormationFeedbackTrace,
    counter_cut: CutEnactment,
) -> None:
    reopened_cut_id = feedback.affected_cut_id
    assert reopened_cut_id is not None
    if reopened_cut_id not in counter_cut.lineage_ids:
        raise InvalidReconfiguration(
            "feedback counter-cut must preserve reopened formation lineage"
        )
    source_cut_id = field.field.competing.source_cut_id
    if source_cut_id not in counter_cut.dependency_ids:
        raise InvalidReconfiguration(
            "feedback counter-cut must remain dependent on the competing source"
        )
    if feedback.observation_trace_id not in counter_cut.transport_basis:
        raise InvalidReconfiguration(
            "feedback counter-cut must retain observation provenance"
        )
    if counter_cut.cut_id in substrate.state.cuts:
        raise InvalidReconfiguration("feedback counter-cut id must be new")
    reopened = substrate.state.cuts.get(reopened_cut_id)
    if reopened is None:
        raise InvalidReconfiguration("feedback-reopened formation is not recorded")
    if _cut_shape(counter_cut) == _cut_shape(reopened):
        raise InvalidReconfiguration(
            "relabelled feedback formation cannot serve as a counter-cut"
        )


def _validate_feedback_recomputation_lineage(
    *,
    field: RecursivelyRevisedArrangementField,
    substrate: ReconfigurationSubstrate,
    revision: FeedbackFieldRevisionTrace,
) -> None:
    feedback = revision.feedback
    if feedback not in field.feedback:
        raise InvalidReconfiguration(
            "feedback recomputation requires retained feedback lineage"
        )
    if feedback.disturbance_delta is None:
        raise InvalidReconfiguration(
            "feedback recomputation requires a disturbing observation"
        )
    recorded_delta = next(
        (
            item for item in substrate.state.deltas
            if item.delta_id == feedback.disturbance_delta.delta_id
        ),
        None,
    )
    counter_cut = substrate.state.cuts.get(revision.counter_cut_id)
    if (
        recorded_delta != feedback.disturbance_delta
        or feedback.affected_cut_id != revision.reopened_cut_id
        or substrate.state.invalidated_by.get(revision.reopened_cut_id)
        != feedback.disturbance_delta.delta_id
        or feedback.observation_trace_id
        not in feedback.disturbance_delta.triggering_trace_ids
        or counter_cut is None
        or revision.reopened_cut_id not in counter_cut.lineage_ids
        or feedback.observation_trace_id not in counter_cut.transport_basis
    ):
        raise InvalidReconfiguration(
            "feedback recomputation requires exact disturbance lineage"
        )


def _validate_feedback_target_origin(
    *,
    field: RecursivelyRevisedArrangementField,
    substrate: ReconfigurationSubstrate,
    feedback: FormationFeedbackTrace,
) -> None:
    """Verify current recomputation provenance without consulting its depth."""

    oscillation_matches = tuple(
        (revision, affected)
        for revision in field.oscillation_revisions
        for affected in revision.affected
        if affected.recomputed_alternative_id == feedback.alternative_id
        and affected.recomputed_trace == feedback.expected_trace
    )
    feedback_matches = tuple(
        revision
        for revision in field.feedback_revisions
        if revision.recomputed_alternative_id == feedback.alternative_id
        and revision.recomputed_trace == feedback.expected_trace
    )
    if len(oscillation_matches) + len(feedback_matches) != 1:
        raise InvalidReconfiguration(
            "feedback revision requires one exact originating recomputation"
        )
    if feedback_matches:
        validate_feedback_provenance_closure(
            field=field,
            substrate=substrate,
            revision=feedback_matches[0],
        )


def _cut_shape(cut: CutEnactment):
    allocations = tuple(sorted(
        (
            item.dimension.value,
            item.position.position_key,
            item.amount,
        )
        for item in cut.allocations
    ))
    relations = tuple(sorted(
        (
            item.relation_type,
            item.source.position_key,
            item.target.position_key,
        )
        for item in cut.relations
    ))
    return (
        tuple(item.key for item in cut.positions),
        relations,
        allocations,
        len(cut.dependency_ids),
    )


def _corresponds(
    observed: ObservedDimensionEffect, expected: DimensionEffect
) -> bool:
    return (
        observed.total == expected.total_after
        and observed.maximum_local_load == expected.maximum_after
        and observed.occupied_positions == expected.occupied_positions_after
    )
