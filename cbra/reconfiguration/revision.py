"""Counter-cut revision of a reopened arrangement without selection.

This slice preserves the proposal that was disturbed, the disturbance that
reopened it, and the counter-cut through which a revised proposal becomes
available.  It recomputes structural effects; it does not rank alternatives
or declare the revision better, caring, or complete.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Union

from .alternatives import (
    CompetingAlternatives,
    TracedAlternative,
    retain_competing_alternatives,
)
from .diffraction import ArrangementDependency, DiffractiveArrangementField
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
    if isinstance(field, RecursivelyRevisedArrangementField):
        existing_revisions = field.revisions
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
        revised_field, existing_revisions + (revision,)
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
