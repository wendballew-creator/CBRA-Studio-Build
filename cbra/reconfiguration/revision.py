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
    if isinstance(field, RecursivelyRevisedArrangementField):
        existing_revisions = field.revisions
        existing_reentries = field.reentries
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
        revised_field, existing_revisions + (revision,), existing_reentries
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
    if len(witness_revisions) != 1:
        raise InvalidReconfiguration(
            "re-entry witness requires one exact recorded recomputation"
        )
    witness_revision = witness_revisions[0]
    _validate_reentry_revision_lineage(
        field=field,
        substrate=substrate,
        witness=witness,
        revision=witness_revision,
    )

    dependencies = {
        item.alternative_cut_id: item for item in field.field.dependencies
    }
    witness_dependency = dependencies[difference.witness_alternative_id]
    if witness_revision.counter_cut_id not in witness_dependency.enabling_cut_ids:
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
        witness_counter_cut_id=witness_revision.counter_cut_id,
        target_enabling_cut_id=enabling_cut_id,
        disturbance=disturbance,
    )
    return RecursivelyRevisedArrangementField(
        field=disturbed_field,
        revisions=field.revisions,
        reentries=field.reentries + (reentry,),
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
