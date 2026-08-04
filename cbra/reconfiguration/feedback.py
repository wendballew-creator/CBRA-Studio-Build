"""Post-return effects re-entering without confirmation or disturbance authority.

Feedback is recorded against one exact current recomputation.  Its uptake is
explicit and local: correspondence leaves the formation open, complication
may reopen one dependent cut, and invalidation may reopen the enabling cut.
None of these dispositions is a score, terminal state, or judgment of value.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence, Tuple

from .alternatives import DimensionEffect, TracedAlternative
from dataclasses import replace

from .models import ReconfigurationDelta, StructuralDimension
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
    matches = tuple(
        (revision, affected)
        for revision in field.oscillation_revisions
        for affected in revision.affected
        if affected.recomputed_alternative_id == alternative_id
        and affected.recomputed_trace == expected
    )
    if len(matches) != 1:
        raise InvalidReconfiguration(
            "feedback requires one exact recorded field recomputation"
        )
    revision, affected = matches[0]
    enabling_cut_id = revision.counter_cut_id
    dependencies = {
        item.alternative_cut_id: item.enabling_cut_ids
        for item in field.field.dependencies
    }
    if enabling_cut_id not in dependencies.get(alternative_id, ()):
        raise InvalidReconfiguration("feedback target has inconsistent field lineage")
    if enabling_cut_id not in substrate.state.active_cut_ids:
        raise InvalidReconfiguration("feedback target enabling formation is inactive")
    if affected.prior_alternative_id not in expected.replacement.lineage_ids:
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


def _corresponds(
    observed: ObservedDimensionEffect, expected: DimensionEffect
) -> bool:
    return (
        observed.total == expected.total_after
        and observed.maximum_local_load == expected.maximum_after
        and observed.occupied_positions == expected.occupied_positions_after
    )
