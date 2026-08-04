"""Counter-cut revision of a reopened arrangement without selection.

This slice preserves the proposal that was disturbed, the disturbance that
reopened it, and the counter-cut through which a revised proposal becomes
available.  It recomputes structural effects; it does not rank alternatives
or declare the revision better, caring, or complete.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple, Union

from .alternatives import (
    CompetingAlternatives,
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
from .models import CutEnactment, StructuralDimension
from .oscillation import OscillationCounterCutTrace
from .substrate import InvalidReconfiguration, ReconfigurationSubstrate


@dataclass(frozen=True)
class ArrangementRevisionTrace:
    disturbance_delta_id: str
    reopened_alternative_id: str
    invalidated_enabling_cut_id: str
    counter_cut_id: str
    revised_alternative_id: str
    prior_trace: TracedAlternative
    recomputed_trace: TracedAlternative


@dataclass(frozen=True)
class RecursivelyRevisedArrangementField:
    field: DiffractiveArrangementField
    revisions: Tuple[ArrangementRevisionTrace, ...]
    reentries: Tuple["RecursiveDiffractiveReentryTrace", ...] = ()
    oscillation_revisions: Tuple["OscillationFieldRevisionTrace", ...] = ()
    feedback: Tuple["FormationFeedbackTrace", ...] = ()
    feedback_revisions: Tuple["FeedbackFieldRevisionTrace", ...] = ()


@dataclass(frozen=True)
class OscillationDependentRevision:
    prior_alternative_id: str
    recomputed_alternative_id: str
    prior_trace: TracedAlternative
    recomputed_trace: TracedAlternative


@dataclass(frozen=True)
class OscillationFieldRevisionTrace:
    """Cycle material returned to the field without becoming a resolution."""

    oscillation_counter_cut: OscillationCounterCutTrace
    counter_cut_id: str
    affected: Tuple[OscillationDependentRevision, ...]


@dataclass(frozen=True)
class RecursiveDiffractiveReentryTrace:
    """A recomputed witness re-entering through active formation, not seniority."""

    witness_alternative_id: str
    witness_counter_cut_id: str
    target_enabling_cut_id: str
    disturbance: DiffractiveDisturbanceTrace


def revise_reopened_arrangement(
    *,
    field: Union[DiffractiveArrangementField, RecursivelyRevisedArrangementField],
    substrate: ReconfigurationSubstrate,
    disturbance_delta_id: str,
    counter_cut: CutEnactment,
    counter_cut_delta_id: str,
    revised_arrangement: CutEnactment,
) -> RecursivelyRevisedArrangementField:
    """Enact a counter-cut and recompute one disturbed arrangement.

    All structural validation occurs before the substrate is changed.  The
    revised proposal replaces the stale proposal only in the current retained
    projection; the old trace remains inside ``ArrangementRevisionTrace``.
    """

    existing_revisions: Tuple[ArrangementRevisionTrace, ...] = ()
    existing_reentries: Tuple[RecursiveDiffractiveReentryTrace, ...] = ()
    existing_oscillation_revisions: Tuple[OscillationFieldRevisionTrace, ...] = ()
    existing_feedback: Tuple["FormationFeedbackTrace", ...] = ()
    existing_feedback_revisions: Tuple["FeedbackFieldRevisionTrace", ...] = ()
    if isinstance(field, RecursivelyRevisedArrangementField):
        existing_revisions = field.revisions
        existing_reentries = field.reentries
        existing_oscillation_revisions = field.oscillation_revisions
        existing_feedback = field.feedback
        existing_feedback_revisions = field.feedback_revisions
        field = field.field

    disturbance = next(
        (
            item
            for item in field.disturbances
            if item.delta.delta_id == disturbance_delta_id
        ),
        None,
    )
    if disturbance is None:
        raise InvalidReconfiguration("revision requires a recorded disturbance")
    recorded_delta = next(
        (
            item
            for item in substrate.state.deltas
            if item.delta_id == disturbance_delta_id
        ),
        None,
    )
    if recorded_delta is None or recorded_delta != disturbance.delta:
        raise InvalidReconfiguration(
            "revision disturbance must match the substrate's recorded delta"
        )
    if any(
        revision.reopened_alternative_id == disturbance.reopened_alternative_id
        for revision in existing_revisions
    ):
        raise InvalidReconfiguration("reopened arrangement already has a revision")

    alternatives = tuple(field.competing.alternatives)
    prior_index = next(
        (
            index
            for index, item in enumerate(alternatives)
            if item.replacement.cut_id == disturbance.reopened_alternative_id
        ),
        None,
    )
    if prior_index is None:
        raise InvalidReconfiguration("reopened arrangement is absent from retained field")
    prior = alternatives[prior_index]

    _validate_counter_cut(
        field=field,
        substrate=substrate,
        invalidated_enabling_cut_id=disturbance.enabling_cut_id,
        counter_cut=counter_cut,
    )
    if revised_arrangement.cut_id == prior.replacement.cut_id:
        raise InvalidReconfiguration("recomputed arrangement requires a new local cut id")
    if prior.replacement.cut_id not in revised_arrangement.lineage_ids:
        raise InvalidReconfiguration(
            "recomputed arrangement must preserve lineage to the reopened proposal"
        )
    if counter_cut.cut_id not in revised_arrangement.dependency_ids:
        raise InvalidReconfiguration(
            "recomputed arrangement must depend on the explicit counter-cut"
        )

    source = substrate.state.cuts.get(field.competing.source_cut_id)
    if source is None:
        raise InvalidReconfiguration("competing source cut is not recorded")
    proposed = tuple(
        revised_arrangement if index == prior_index else item.replacement
        for index, item in enumerate(alternatives)
    )
    # Preflight the complete field. This rejects cosmetic recomputation,
    # duplicates, changed local correspondence, and untraceable effects before
    # the counter-cut can mutate substrate state.
    recomputed = retain_competing_alternatives(
        source=source,
        replacements=proposed,
        constraints=field.competing.constraints,
    )
    recomputed_trace = recomputed.alternatives[prior_index]
    if recomputed_trace.effects == prior.effects:
        raise InvalidReconfiguration(
            "counter-cut must recompute a structurally changed arrangement trace"
        )

    substrate.enact_cut(counter_cut, delta_id=counter_cut_delta_id)

    dependencies = tuple(
        ArrangementDependency(revised_arrangement.cut_id, (counter_cut.cut_id,))
        if item.alternative_cut_id == prior.replacement.cut_id
        else item
        for item in field.dependencies
    )
    revised_field = DiffractiveArrangementField(
        competing=CompetingAlternatives(
            source_cut_id=recomputed.source_cut_id,
            alternatives=recomputed.alternatives,
            constraints=recomputed.constraints,
        ),
        dependencies=dependencies,
        disturbances=field.disturbances,
    )
    revision = ArrangementRevisionTrace(
        disturbance_delta_id=disturbance_delta_id,
        reopened_alternative_id=prior.replacement.cut_id,
        invalidated_enabling_cut_id=disturbance.enabling_cut_id,
        counter_cut_id=counter_cut.cut_id,
        revised_alternative_id=revised_arrangement.cut_id,
        prior_trace=prior,
        recomputed_trace=recomputed_trace,
    )
    return RecursivelyRevisedArrangementField(
        revised_field,
        existing_revisions + (revision,),
        existing_reentries,
        existing_oscillation_revisions,
        existing_feedback,
        existing_feedback_revisions,
    )


def return_oscillation_counter_cut_to_field(
    *,
    field: RecursivelyRevisedArrangementField,
    substrate: ReconfigurationSubstrate,
    oscillation_counter_cut: OscillationCounterCutTrace,
    recomputed_arrangements: Sequence[CutEnactment],
) -> RecursivelyRevisedArrangementField:
    """Retrace every current projection dependent on an oscillating formation.

    The oscillation transaction has already enacted its counter-cut.  This
    transaction returns that material to the competing field.  It neither
    chooses a projection nor protects the new counter-cut from later re-entry.
    """

    recorded_delta = next(
        (
            item
            for item in substrate.state.deltas
            if item.delta_id == oscillation_counter_cut.disturbance_delta.delta_id
        ),
        None,
    )
    if recorded_delta != oscillation_counter_cut.disturbance_delta:
        raise InvalidReconfiguration(
            "field return requires the exact recorded oscillation disturbance"
        )
    finding = oscillation_counter_cut.responsiveness_trace
    if (
        oscillation_counter_cut.returning_witness_id != finding.witness_id
        or oscillation_counter_cut.departing_witness_id != finding.prior_witness_id
        or oscillation_counter_cut.recurring_witness_id
        != finding.recurring_witness_id
    ):
        raise InvalidReconfiguration(
            "oscillation field return requires internally exact audit lineage"
        )
    counter_cut = substrate.state.cuts.get(oscillation_counter_cut.counter_cut_id)
    if counter_cut is None or counter_cut.cut_id not in substrate.state.active_cut_ids:
        raise InvalidReconfiguration(
            "oscillation-grounded counter-cut must remain active during field return"
        )
    if (
        oscillation_counter_cut.reopened_enabling_cut_id
        not in counter_cut.lineage_ids
    ):
        raise InvalidReconfiguration(
            "oscillation-grounded counter-cut must preserve reopened lineage"
        )
    if (
        substrate.state.invalidated_by.get(
            oscillation_counter_cut.reopened_enabling_cut_id
        )
        != oscillation_counter_cut.disturbance_delta.delta_id
    ):
        raise InvalidReconfiguration(
            "oscillation field return must match substrate invalidation history"
        )
    if any(
        item.oscillation_counter_cut.disturbance_delta.delta_id
        == oscillation_counter_cut.disturbance_delta.delta_id
        for item in field.oscillation_revisions
    ):
        raise InvalidReconfiguration(
            "one oscillation disturbance cannot be returned to the field twice"
        )

    invalidated = set(oscillation_counter_cut.disturbance_delta.invalidated_cut_ids)
    dependencies = {
        item.alternative_cut_id: item for item in field.field.dependencies
    }
    current = tuple(field.field.competing.alternatives)
    affected = tuple(
        item
        for item in current
        if set(dependencies[item.replacement.cut_id].enabling_cut_ids) & invalidated
    )
    if not affected:
        raise InvalidReconfiguration(
            "oscillation disturbance must affect a retained field formation"
        )

    proposed_by_lineage = {}
    for proposed in recomputed_arrangements:
        matches = tuple(
            prior
            for prior in affected
            if prior.replacement.cut_id in proposed.lineage_ids
        )
        if len(matches) != 1:
            raise InvalidReconfiguration(
                "each recomputation must preserve one affected proposal lineage"
            )
        prior_id = matches[0].replacement.cut_id
        if prior_id in proposed_by_lineage:
            raise InvalidReconfiguration(
                "each affected formation requires exactly one recomputation"
            )
        if proposed.cut_id == prior_id:
            raise InvalidReconfiguration(
                "oscillation recomputation requires a new local cut id"
            )
        if counter_cut.cut_id not in proposed.dependency_ids:
            raise InvalidReconfiguration(
                "oscillation recomputation must depend on its counter-cut"
            )
        proposed_by_lineage[prior_id] = proposed
    affected_ids = {item.replacement.cut_id for item in affected}
    if set(proposed_by_lineage) != affected_ids:
        raise InvalidReconfiguration(
            "all cycle-dependent field formations must be recomputed together"
        )

    source = substrate.state.cuts.get(field.field.competing.source_cut_id)
    if source is None:
        raise InvalidReconfiguration("competing source cut is not recorded")
    replacements = tuple(
        proposed_by_lineage.get(item.replacement.cut_id, item.replacement)
        for item in current
    )
    recomputed = retain_competing_alternatives(
        source=source,
        replacements=replacements,
        constraints=field.field.competing.constraints,
    )
    recomputed_by_id = {
        item.replacement.cut_id: item for item in recomputed.alternatives
    }
    affected_traces = tuple(
        OscillationDependentRevision(
            prior_alternative_id=prior.replacement.cut_id,
            recomputed_alternative_id=proposed_by_lineage[
                prior.replacement.cut_id
            ].cut_id,
            prior_trace=prior,
            recomputed_trace=recomputed_by_id[
                proposed_by_lineage[prior.replacement.cut_id].cut_id
            ],
        )
        for prior in affected
    )
    if any(
        item.prior_trace.effects == item.recomputed_trace.effects
        for item in affected_traces
    ):
        raise InvalidReconfiguration(
            "oscillation counter-cut must freshly change each affected trace"
        )

    revised_dependencies = tuple(
        ArrangementDependency(
            proposed_by_lineage[item.alternative_cut_id].cut_id,
            (counter_cut.cut_id,),
        )
        if item.alternative_cut_id in proposed_by_lineage
        else item
        for item in field.field.dependencies
    )
    revised_field = DiffractiveArrangementField(
        competing=recomputed,
        dependencies=revised_dependencies,
        disturbances=field.field.disturbances,
    )
    trace = OscillationFieldRevisionTrace(
        oscillation_counter_cut=oscillation_counter_cut,
        counter_cut_id=counter_cut.cut_id,
        affected=affected_traces,
    )
    return RecursivelyRevisedArrangementField(
        field=revised_field,
        revisions=field.revisions,
        reentries=field.reentries,
        oscillation_revisions=field.oscillation_revisions + (trace,),
        feedback=field.feedback,
        feedback_revisions=field.feedback_revisions,
    )


def reenter_recomputed_arrangement_difference(
    *,
    field: RecursivelyRevisedArrangementField,
    substrate: ReconfigurationSubstrate,
    difference: ConsequentialDifference,
    enabling_cut_id: str,
    delta_id: str,
    triggering_trace_ids: Sequence[str],
) -> RecursivelyRevisedArrangementField:
    """Let a current recomputed trace disturb another active formation.

    Authority derives only from current structural correspondence, recorded
    revision lineage, and an active enabling cut.  Revision tuple position,
    depth, recency, and repetition are not inputs to the operation.
    """

    current = {
        item.replacement.cut_id: item for item in field.field.competing.alternatives
    }
    witness = current.get(difference.witness_alternative_id)
    if witness is None:
        raise InvalidReconfiguration("re-entry witness must be currently retained")

    witness_revisions = tuple(
        item
        for item in field.revisions
        if item.revised_alternative_id == difference.witness_alternative_id
        and item.recomputed_trace == witness
    )
    oscillation_revisions = tuple(
        (field_revision, item)
        for field_revision in field.oscillation_revisions
        for item in field_revision.affected
        if item.recomputed_alternative_id == difference.witness_alternative_id
        and item.recomputed_trace == witness
    )
    if len(witness_revisions) + len(oscillation_revisions) != 1:
        raise InvalidReconfiguration(
            "re-entry witness requires one exact recorded recomputation"
        )
    if witness_revisions:
        witness_revision = witness_revisions[0]
        witness_counter_cut_id = witness_revision.counter_cut_id
        _validate_reentry_revision_lineage(
            field=field,
            substrate=substrate,
            witness=witness,
            revision=witness_revision,
        )
    else:
        oscillation_revision, dependent_revision = oscillation_revisions[0]
        witness_counter_cut_id = oscillation_revision.counter_cut_id
        _validate_oscillation_reentry_lineage(
            substrate=substrate,
            witness=witness,
            field_revision=oscillation_revision,
            dependent_revision=dependent_revision,
        )

    dependencies = {
        item.alternative_cut_id: item for item in field.field.dependencies
    }
    witness_dependency = dependencies[difference.witness_alternative_id]
    if witness_counter_cut_id not in witness_dependency.enabling_cut_ids:
        raise InvalidReconfiguration(
            "re-entry witness must remain enabled by its recorded counter-cut"
        )
    if not set(witness_dependency.enabling_cut_ids).issubset(
        substrate.state.active_cut_ids
    ):
        raise InvalidReconfiguration(
            "re-entry witness requires an active enabling formation"
        )

    disturbed_field = disturb_through_arrangement_difference(
        field=field.field,
        substrate=substrate,
        difference=difference,
        enabling_cut_id=enabling_cut_id,
        delta_id=delta_id,
        triggering_trace_ids=triggering_trace_ids,
    )
    disturbance = disturbed_field.disturbances[-1]
    reentry = RecursiveDiffractiveReentryTrace(
        witness_alternative_id=difference.witness_alternative_id,
        witness_counter_cut_id=witness_counter_cut_id,
        target_enabling_cut_id=enabling_cut_id,
        disturbance=disturbance,
    )
    return RecursivelyRevisedArrangementField(
        field=disturbed_field,
        revisions=field.revisions,
        reentries=field.reentries + (reentry,),
        oscillation_revisions=field.oscillation_revisions,
        feedback=field.feedback,
        feedback_revisions=field.feedback_revisions,
    )


def _validate_oscillation_reentry_lineage(
    *,
    substrate: ReconfigurationSubstrate,
    witness: TracedAlternative,
    field_revision: OscillationFieldRevisionTrace,
    dependent_revision: OscillationDependentRevision,
) -> None:
    oscillation = field_revision.oscillation_counter_cut
    if dependent_revision.prior_alternative_id not in witness.replacement.lineage_ids:
        raise InvalidReconfiguration(
            "oscillation-recomputed witness does not preserve proposal lineage"
        )
    counter_cut = substrate.state.cuts.get(field_revision.counter_cut_id)
    if counter_cut is None:
        raise InvalidReconfiguration(
            "oscillation-recomputed witness counter-cut is not recorded"
        )
    if oscillation.reopened_enabling_cut_id not in counter_cut.lineage_ids:
        raise InvalidReconfiguration(
            "oscillation-recomputed counter-cut does not preserve reopened lineage"
        )
    recorded_delta = next(
        (
            item
            for item in substrate.state.deltas
            if item.delta_id == oscillation.disturbance_delta.delta_id
        ),
        None,
    )
    if (
        recorded_delta != oscillation.disturbance_delta
        or substrate.state.invalidated_by.get(
            oscillation.reopened_enabling_cut_id
        )
        != oscillation.disturbance_delta.delta_id
    ):
        raise InvalidReconfiguration(
            "oscillation-recomputed witness requires exact disturbance lineage"
        )


def _validate_reentry_revision_lineage(
    *,
    field: RecursivelyRevisedArrangementField,
    substrate: ReconfigurationSubstrate,
    witness: TracedAlternative,
    revision: ArrangementRevisionTrace,
) -> None:
    if revision.reopened_alternative_id not in witness.replacement.lineage_ids:
        raise InvalidReconfiguration(
            "re-entry witness does not preserve its recorded proposal lineage"
        )
    counter_cut = substrate.state.cuts.get(revision.counter_cut_id)
    if counter_cut is None:
        raise InvalidReconfiguration("re-entry counter-cut is not recorded")
    if revision.invalidated_enabling_cut_id not in counter_cut.lineage_ids:
        raise InvalidReconfiguration(
            "re-entry counter-cut does not preserve reopened formation lineage"
        )
    if (
        substrate.state.invalidated_by.get(revision.invalidated_enabling_cut_id)
        != revision.disturbance_delta_id
    ):
        raise InvalidReconfiguration(
            "re-entry revision does not match substrate invalidation history"
        )
    disturbance = next(
        (
            item
            for item in field.field.disturbances
            if item.delta.delta_id == revision.disturbance_delta_id
        ),
        None,
    )
    recorded_delta = next(
        (
            item
            for item in substrate.state.deltas
            if item.delta_id == revision.disturbance_delta_id
        ),
        None,
    )
    if (
        disturbance is None
        or recorded_delta != disturbance.delta
        or disturbance.reopened_alternative_id != revision.reopened_alternative_id
        or disturbance.enabling_cut_id != revision.invalidated_enabling_cut_id
    ):
        raise InvalidReconfiguration(
            "re-entry revision requires exact recorded disturbance lineage"
        )


def _validate_counter_cut(
    *,
    field: DiffractiveArrangementField,
    substrate: ReconfigurationSubstrate,
    invalidated_enabling_cut_id: str,
    counter_cut: CutEnactment,
) -> None:
    if invalidated_enabling_cut_id not in substrate.state.invalidated_by:
        raise InvalidReconfiguration("counter-cut target must already be reopened")
    if invalidated_enabling_cut_id not in counter_cut.lineage_ids:
        raise InvalidReconfiguration(
            "counter-cut must preserve lineage to the reopened enabling cut"
        )
    source_cut_id = field.competing.source_cut_id
    if source_cut_id not in counter_cut.dependency_ids:
        raise InvalidReconfiguration(
            "counter-cut must remain dependent on the competing source cut"
        )
    if counter_cut.cut_id in substrate.state.cuts:
        raise InvalidReconfiguration("counter-cut id must be new")
    reopened = substrate.state.cuts[invalidated_enabling_cut_id]
    if _cut_shape(counter_cut) == _cut_shape(reopened):
        raise InvalidReconfiguration(
            "relabelled enabling formation cannot serve as a counter-cut"
        )


def _cut_shape(cut: CutEnactment):
    """A local topology signature that ignores technical IDs and prose labels."""

    allocations = tuple(
        (
            dimension.value,
            tuple(
                sorted(
                    item.amount
                    for item in cut.allocations
                    if item.dimension == dimension
                )
            ),
        )
        for dimension in StructuralDimension
    )
    degrees = {position.key: [0, 0] for position in cut.positions}
    for relation in cut.relations:
        degrees[relation.source.position_key][0] += 1
        degrees[relation.target.position_key][1] += 1
    return (
        len(cut.positions),
        tuple(sorted(tuple(value) for value in degrees.values())),
        allocations,
    )
