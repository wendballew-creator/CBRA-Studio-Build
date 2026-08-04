"""Let an oscillation trace become local counter-cut material without command.

Detection remains descriptive.  A separate, explicitly requested transaction
may bind one exact unsupported return to an active enabling formation and
replace that formation with a structurally distinct counter-cut.  Nothing in
the trace selects an arrangement, requires settlement, or stops recursion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from .models import CutEnactment, ReconfigurationDelta, StructuralDimension
from .responsiveness import (
    ResponsivenessAudit,
    ResponsivenessFinding,
    ResponsivenessTrace,
    audit_structural_responsiveness,
)
from .substrate import InvalidReconfiguration, ReconfigurationSubstrate


@dataclass(frozen=True)
class OscillationCounterCutTrace:
    """Evidence joining an unsupported return to one enacted local revision."""

    recurring_witness_id: str
    departing_witness_id: str
    returning_witness_id: str
    reopened_enabling_cut_id: str
    counter_cut_id: str
    disturbance_delta: ReconfigurationDelta
    responsiveness_trace: ResponsivenessTrace


def counter_cut_from_oscillation(
    *,
    audit: ResponsivenessAudit,
    returning_witness_id: str,
    reopened_enabling_cut_id: str,
    counter_cut: CutEnactment,
    delta_id: str,
    triggering_trace_ids: Sequence[str],
    substrate: ReconfigurationSubstrate,
) -> OscillationCounterCutTrace:
    """Enact a proposed counter-cut from one exact oscillation finding.

    The audit is recomputed against substrate history before mutation.  The
    finding authorizes no automatic action: target, counter-cut, and transport
    basis remain explicit inputs and all validation is completed first.
    """

    recorded = audit_structural_responsiveness(audit.witnesses, substrate=substrate)
    if recorded != audit:
        raise InvalidReconfiguration(
            "oscillation counter-cut requires an exact recorded audit"
        )
    traces = tuple(
        item for item in audit.traces if item.witness_id == returning_witness_id
    )
    if len(traces) != 1:
        raise InvalidReconfiguration(
            "oscillation counter-cut requires one exact returning witness"
        )
    finding = traces[0]
    if finding.finding != ResponsivenessFinding.STRUCTURAL_OSCILLATION:
        raise InvalidReconfiguration(
            "only an unsupported structural oscillation can supply this material"
        )
    if finding.recurring_witness_id is None:
        raise InvalidReconfiguration("oscillation trace requires a recurring witness")

    witnesses = {item.witness_id: item for item in audit.witnesses}
    returning = witnesses[finding.witness_id]
    departing = witnesses[finding.prior_witness_id]
    recurring = witnesses[finding.recurring_witness_id]
    if reopened_enabling_cut_id not in returning.enabling_cut_ids:
        raise InvalidReconfiguration(
            "counter-cut target must enable the unsupported return"
        )
    if reopened_enabling_cut_id not in departing.enabling_cut_ids:
        raise InvalidReconfiguration(
            "counter-cut target must participate in the departure and return"
        )
    if reopened_enabling_cut_id not in recurring.enabling_cut_ids:
        raise InvalidReconfiguration(
            "counter-cut target must participate in the recurring formation"
        )
    if reopened_enabling_cut_id not in substrate.state.active_cut_ids:
        raise InvalidReconfiguration(
            "oscillation counter-cut target must remain active"
        )
    if reopened_enabling_cut_id not in counter_cut.lineage_ids:
        raise InvalidReconfiguration(
            "oscillation counter-cut must preserve target formation lineage"
        )
    if counter_cut.cut_id in substrate.state.cuts:
        raise InvalidReconfiguration("oscillation counter-cut id must be new")
    reopened = substrate.state.cuts[reopened_enabling_cut_id]
    if (
        not counter_cut.dependency_ids
        or not set(counter_cut.dependency_ids).issubset(reopened.dependency_ids)
    ):
        raise InvalidReconfiguration(
            "oscillation counter-cut must remain locally anchored"
        )
    if _cut_shape(counter_cut) == _cut_shape(reopened):
        raise InvalidReconfiguration(
            "oscillation counter-cut must be structurally distinct"
        )
    if not set(triggering_trace_ids).issubset(returning.triggering_trace_ids):
        raise InvalidReconfiguration(
            "counter-cut transport basis must be operative in the return"
        )
    if tuple(counter_cut.transport_basis) != tuple(triggering_trace_ids):
        raise InvalidReconfiguration(
            "counter-cut transport basis must match the disturbance evidence"
        )

    # Preflight on a disposable substrate so rejected replacement dependency or
    # topology paths cannot partially mutate the operative history.
    preview = ReconfigurationSubstrate(substrate.state)
    preview.disturb(
        delta_id=delta_id,
        triggering_trace_ids=triggering_trace_ids,
        invalidated_root_ids=(reopened_enabling_cut_id,),
        replacements=(counter_cut,),
    )
    delta = substrate.disturb(
        delta_id=delta_id,
        triggering_trace_ids=triggering_trace_ids,
        invalidated_root_ids=(reopened_enabling_cut_id,),
        replacements=(counter_cut,),
    )
    return OscillationCounterCutTrace(
        recurring_witness_id=recurring.witness_id,
        departing_witness_id=departing.witness_id,
        returning_witness_id=returning.witness_id,
        reopened_enabling_cut_id=reopened_enabling_cut_id,
        counter_cut_id=counter_cut.cut_id,
        disturbance_delta=delta,
        responsiveness_trace=finding,
    )


def _cut_shape(cut: CutEnactment) -> Tuple[object, ...]:
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
