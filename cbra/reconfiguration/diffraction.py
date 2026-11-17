"""Cross-arrangement disturbance without ranking or selection.

This slice lets a measured difference in one retained arrangement reopen the
active cuts that made another arrangement available.  It does not infer the
meaning of the difference, choose an arrangement, or certify diffraction as
an ethical achievement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Set, Tuple

from .alternatives import CompetingAlternatives, EffectMeasure, TracedAlternative
from .models import ReconfigurationDelta, StructuralDimension
from .substrate import InvalidReconfiguration, ReconfigurationSubstrate


@dataclass(frozen=True)
class ArrangementDependency:
    """Explicit cuts through which one proposed arrangement became available."""

    alternative_cut_id: str
    enabling_cut_ids: Tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.alternative_cut_id or not self.enabling_cut_ids:
            raise ValueError("arrangement dependency requires alternative and cut ids")
        if len(set(self.enabling_cut_ids)) != len(self.enabling_cut_ids):
            raise ValueError("arrangement enabling cut ids must be unique")


@dataclass(frozen=True)
class ConsequentialDifference:
    """A requested comparison axis, not an interpretation of harm or value."""

    witness_alternative_id: str
    contrasted_alternative_id: str
    dimension: StructuralDimension
    measure: EffectMeasure


@dataclass(frozen=True)
class DiffractiveDisturbanceTrace:
    witness_alternative_id: str
    reopened_alternative_id: str
    dimension: StructuralDimension
    measure: EffectMeasure
    witness_value: float
    reopened_value: float
    enabling_cut_id: str
    invalidated_cut_ids: Tuple[str, ...]
    left_intact_alternative_ids: Tuple[str, ...]
    delta: ReconfigurationDelta


@dataclass(frozen=True)
class DiffractiveArrangementField:
    """Retained alternatives plus explicit availability dependencies and traces."""

    competing: CompetingAlternatives
    dependencies: Tuple[ArrangementDependency, ...]
    disturbances: Tuple[DiffractiveDisturbanceTrace, ...] = ()

    def __post_init__(self) -> None:
        alternative_ids = {
            item.replacement.cut_id for item in self.competing.alternatives
        }
        dependency_ids = {item.alternative_cut_id for item in self.dependencies}
        if dependency_ids != alternative_ids:
            raise InvalidReconfiguration(
                "every retained alternative requires exactly one dependency record"
            )
        if len(dependency_ids) != len(self.dependencies):
            raise InvalidReconfiguration(
                "an alternative cannot acquire duplicate dependency authority"
            )


def disturb_through_arrangement_difference(
    *,
    field: DiffractiveArrangementField,
    substrate: ReconfigurationSubstrate,
    difference: ConsequentialDifference,
    enabling_cut_id: str,
    delta_id: str,
    triggering_trace_ids: Sequence[str],
) -> DiffractiveArrangementField:
    """Reopen a contrasted arrangement through a real cross-arrangement effect.

    The target remains in the retained field as trace evidence.  Its explicit
    enabling cut and every active dependent are invalidated by the substrate.
    """

    alternatives = {
        item.replacement.cut_id: item for item in field.competing.alternatives
    }
    witness = alternatives.get(difference.witness_alternative_id)
    contrasted = alternatives.get(difference.contrasted_alternative_id)
    if witness is None or contrasted is None:
        raise InvalidReconfiguration("difference must reference retained alternatives")
    if witness is contrasted:
        raise InvalidReconfiguration("an arrangement cannot disturb itself")
    already_reopened = {
        item.reopened_alternative_id for item in field.disturbances
    }
    if difference.witness_alternative_id in already_reopened:
        raise InvalidReconfiguration(
            "a reopened arrangement cannot supply a new difference before revision"
        )

    dependencies = {
        item.alternative_cut_id: item for item in field.dependencies
    }
    target_dependency = dependencies[difference.contrasted_alternative_id]
    if enabling_cut_id not in target_dependency.enabling_cut_ids:
        raise InvalidReconfiguration(
            "disturbance must reopen an explicit enabling cut of the contrasted arrangement"
        )
    if enabling_cut_id not in substrate.state.active_cut_ids:
        raise InvalidReconfiguration("arrangement enabling cut must remain active")
    if field.competing.source_cut_id not in _dependency_ancestors(
        substrate, enabling_cut_id
    ):
        raise InvalidReconfiguration(
            "arrangement enabling cut must descend from the competing source cut"
        )

    witness_value = _effect_value(witness, difference.dimension, difference.measure)
    contrasted_value = _effect_value(
        contrasted, difference.dimension, difference.measure
    )
    if witness_value == contrasted_value:
        raise InvalidReconfiguration(
            "equal arrangement effects cannot be called a consequential difference"
        )

    invalidated = _dependent_closure(substrate, enabling_cut_id)
    if len(invalidated) < 2:
        raise InvalidReconfiguration(
            "diffractive movement must change at least two dependent configuration parts"
        )

    delta = substrate.disturb(
        delta_id=delta_id,
        triggering_trace_ids=triggering_trace_ids,
        invalidated_root_ids=(enabling_cut_id,),
        replacements=(),
    )
    alternative_ids = tuple(
        item.replacement.cut_id for item in field.competing.alternatives
    )
    trace = DiffractiveDisturbanceTrace(
        witness_alternative_id=difference.witness_alternative_id,
        reopened_alternative_id=difference.contrasted_alternative_id,
        dimension=difference.dimension,
        measure=difference.measure,
        witness_value=witness_value,
        reopened_value=contrasted_value,
        enabling_cut_id=enabling_cut_id,
        invalidated_cut_ids=delta.invalidated_cut_ids,
        left_intact_alternative_ids=tuple(
            item for item in alternative_ids
            if item != difference.contrasted_alternative_id
        ),
        delta=delta,
    )
    return DiffractiveArrangementField(
        competing=field.competing,
        dependencies=field.dependencies,
        disturbances=field.disturbances + (trace,),
    )


def _effect_value(
    alternative: TracedAlternative,
    dimension: StructuralDimension,
    measure: EffectMeasure,
) -> float:
    effect = next(item for item in alternative.effects if item.dimension == dimension)
    if measure == EffectMeasure.TOTAL:
        return effect.total_after
    if measure == EffectMeasure.MAXIMUM_LOCAL_LOAD:
        return effect.maximum_after
    return float(effect.occupied_positions_after)


def _dependent_closure(
    substrate: ReconfigurationSubstrate, root_id: str
) -> Set[str]:
    invalidated = {root_id}
    changed = True
    while changed:
        changed = False
        for cut_id in substrate.state.active_cut_ids:
            cut = substrate.state.cuts[cut_id]
            if cut_id not in invalidated and set(cut.dependency_ids) & invalidated:
                invalidated.add(cut_id)
                changed = True
    return invalidated


def _dependency_ancestors(
    substrate: ReconfigurationSubstrate, cut_id: str
) -> Set[str]:
    ancestors: Set[str] = set()
    pending = list(substrate.state.cuts[cut_id].dependency_ids)
    while pending:
        dependency_id = pending.pop()
        if dependency_id in ancestors:
            continue
        ancestors.add(dependency_id)
        pending.extend(substrate.state.cuts[dependency_id].dependency_ids)
    return ancestors
