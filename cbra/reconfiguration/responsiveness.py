"""Audit recursive responsiveness without a stopping rule or preference.

Structural recurrence is not itself a failure: a prior allocation topology may
return because new material has become operative.  This slice calls recurrence
``oscillation`` only when the same structural state returns without a newly
operative transport trace, harm-boundary crossing, or enabling dependency.
The audit records evidence; it never stops, ranks, selects, or stabilizes the
field.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence, Tuple

from .alternatives import TracedAlternative
from .models import StructuralDimension
from .substrate import InvalidReconfiguration, ReconfigurationSubstrate


class ResponsivenessFinding(str, Enum):
    MATERIAL_CHANGE = "material_change"
    MATERIAL_RECURRENCE = "material_recurrence"
    STRUCTURAL_OSCILLATION = "structural_oscillation"
    STRUCTURAL_PERSISTENCE = "structural_persistence"


@dataclass(frozen=True)
class ArrangementStateWitness:
    """One historical state and the explicit material basis operative in it."""

    witness_id: str
    trace: TracedAlternative
    enabling_cut_ids: Tuple[str, ...]
    operative_delta_ids: Tuple[str, ...]
    triggering_trace_ids: Tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.witness_id:
            raise ValueError("responsiveness witness id must be nonempty")
        if not self.enabling_cut_ids:
            raise ValueError("responsiveness witness requires an enabling formation")
        if len(set(self.enabling_cut_ids)) != len(self.enabling_cut_ids):
            raise ValueError("responsiveness enabling cuts must be unique")
        if not self.operative_delta_ids:
            raise ValueError("responsiveness witness requires an operative delta")
        if len(set(self.operative_delta_ids)) != len(self.operative_delta_ids):
            raise ValueError("responsiveness operative deltas must be unique")
        if len(set(self.triggering_trace_ids)) != len(self.triggering_trace_ids):
            raise ValueError("responsiveness triggering traces must be unique")


@dataclass(frozen=True)
class ResponsivenessTrace:
    witness_id: str
    prior_witness_id: str
    finding: ResponsivenessFinding
    recurring_witness_id: str | None
    new_triggering_trace_ids: Tuple[str, ...]
    changed_enabling_formation: bool
    changed_harm_evidence: bool
    structural_change: bool


@dataclass(frozen=True)
class ResponsivenessAudit:
    """Chronological evidence with no terminal, preferred, or settled state."""

    witnesses: Tuple[ArrangementStateWitness, ...]
    traces: Tuple[ResponsivenessTrace, ...]


def audit_structural_responsiveness(
    witnesses: Sequence[ArrangementStateWitness],
    *,
    substrate: ReconfigurationSubstrate,
) -> ResponsivenessAudit:
    """Distinguish material responsiveness from unsupported recurrence.

    Sequence position supplies historical adjacency only.  It confers no
    authority, and the audit has no convergence threshold or iteration limit.
    """

    witnesses = tuple(witnesses)
    if len(witnesses) < 2:
        raise InvalidReconfiguration(
            "responsiveness audit requires at least two historical states"
        )
    if len({item.witness_id for item in witnesses}) != len(witnesses):
        raise InvalidReconfiguration("responsiveness witness ids must be unique")
    for witness in witnesses:
        if not set(witness.enabling_cut_ids).issubset(substrate.state.cuts):
            raise InvalidReconfiguration(
                "responsiveness enabling formations must be recorded"
            )
        deltas = {
            item.delta_id: item for item in substrate.state.deltas
        }
        if not set(witness.operative_delta_ids).issubset(deltas):
            raise InvalidReconfiguration(
                "responsiveness operative deltas must be recorded"
            )
        recorded_triggers = {
            trace_id
            for delta_id in witness.operative_delta_ids
            for trace_id in deltas[delta_id].triggering_trace_ids
        }
        if set(witness.triggering_trace_ids) != recorded_triggers:
            raise InvalidReconfiguration(
                "responsiveness triggering traces must match operative deltas"
            )

    traces = []
    seen_by_signature = {_signature(witnesses[0].trace): witnesses[0]}
    prior = witnesses[0]
    for current in witnesses[1:]:
        current_signature = _signature(current.trace)
        prior_signature = _signature(prior.trace)
        recurring = seen_by_signature.get(current_signature)
        new_transport = tuple(
            item
            for item in current.triggering_trace_ids
            if item not in prior.triggering_trace_ids
        )
        changed_enabling = set(current.enabling_cut_ids) != set(prior.enabling_cut_ids)
        changed_harm = _harm_signature(current.trace) != _harm_signature(prior.trace)
        structural_change = current_signature != prior_signature
        has_new_material = bool(new_transport or changed_enabling or changed_harm)

        if recurring is not None and has_new_material:
            finding = ResponsivenessFinding.MATERIAL_RECURRENCE
        elif not structural_change:
            finding = ResponsivenessFinding.STRUCTURAL_PERSISTENCE
        elif recurring is not None:
            finding = ResponsivenessFinding.STRUCTURAL_OSCILLATION
        else:
            finding = ResponsivenessFinding.MATERIAL_CHANGE

        traces.append(
            ResponsivenessTrace(
                witness_id=current.witness_id,
                prior_witness_id=prior.witness_id,
                finding=finding,
                recurring_witness_id=(recurring.witness_id if recurring else None),
                new_triggering_trace_ids=new_transport,
                changed_enabling_formation=changed_enabling,
                changed_harm_evidence=changed_harm,
                structural_change=structural_change,
            )
        )
        seen_by_signature.setdefault(current_signature, current)
        prior = current

    return ResponsivenessAudit(witnesses=witnesses, traces=tuple(traces))


def _harm_signature(trace: TracedAlternative):
    return frozenset(
        (
            item.constraint_id,
            item.dimension,
            item.measure,
            item.prohibited_change,
            item.before,
            item.after,
        )
        for item in trace.harm_increases
    )


def _signature(trace: TracedAlternative):
    amounts = {
        dimension: {} for dimension in StructuralDimension
    }
    for allocation in trace.replacement.allocations:
        by_position = amounts[allocation.dimension]
        key = allocation.position.position_key
        by_position[key] = by_position.get(key, 0.0) + allocation.amount
    return tuple(
        (
            dimension.value,
            tuple(sorted(amounts[dimension].items())),
        )
        for dimension in StructuralDimension
    )
