"""Concurrent arrangement traces without ranking or selection.

The records in this module retain structurally distinct proposed cuts and
trace their effects against explicit local constraints.  A constraint breach
is not a score and the collection has no preferred or winning alternative.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, Sequence, Tuple

from .arrangements import ArrangementComparison, compare_arrangements
from .models import CutEnactment, StructuralDimension
from .substrate import InvalidReconfiguration


class EffectMeasure(str, Enum):
    TOTAL = "total"
    MAXIMUM_LOCAL_LOAD = "maximum_local_load"
    OCCUPIED_POSITIONS = "occupied_positions"


class EffectDirection(str, Enum):
    INCREASED = "increased"
    DECREASED = "decreased"
    UNCHANGED = "unchanged"
    REDISTRIBUTED = "redistributed"


class ProhibitedChange(str, Enum):
    INCREASE = "increase"
    DECREASE = "decrease"


@dataclass(frozen=True)
class DimensionEffect:
    dimension: StructuralDimension
    total_before: float
    total_after: float
    maximum_before: float
    maximum_after: float
    occupied_positions_before: int
    occupied_positions_after: int
    direction: EffectDirection


@dataclass(frozen=True)
class HarmConstraint:
    """An explicit local boundary; never an inferred universal ethic."""

    constraint_id: str
    dimension: StructuralDimension
    measure: EffectMeasure
    prohibited_change: ProhibitedChange

    def __post_init__(self) -> None:
        if not self.constraint_id:
            raise ValueError("harm constraint id must be nonempty")


@dataclass(frozen=True)
class HarmIncreaseTrace:
    constraint_id: str
    dimension: StructuralDimension
    measure: EffectMeasure
    prohibited_change: ProhibitedChange
    before: float
    after: float


@dataclass(frozen=True)
class TracedAlternative:
    replacement: CutEnactment
    comparison: ArrangementComparison
    effects: Tuple[DimensionEffect, ...]
    harm_increases: Tuple[HarmIncreaseTrace, ...]

    @property
    def crosses_harm_constraint(self) -> bool:
        return bool(self.harm_increases)


@dataclass(frozen=True)
class CompetingAlternatives:
    """A non-ranked set of materially distinct possibilities."""

    source_cut_id: str
    alternatives: Tuple[TracedAlternative, ...]
    constraints: Tuple[HarmConstraint, ...]

    def __post_init__(self) -> None:
        if len(self.alternatives) < 2:
            raise InvalidReconfiguration(
                "competing variation requires at least two material alternatives"
            )


def retain_competing_alternatives(
    *,
    source: CutEnactment,
    replacements: Sequence[CutEnactment],
    constraints: Sequence[HarmConstraint],
) -> CompetingAlternatives:
    """Trace alternatives in input order without scoring, ranking, or choosing."""

    if len({item.constraint_id for item in constraints}) != len(constraints):
        raise InvalidReconfiguration("harm constraint ids must be unique")
    constraint_shapes = {
        (item.dimension, item.measure, item.prohibited_change) for item in constraints
    }
    if len(constraint_shapes) != len(constraints):
        raise InvalidReconfiguration(
            "duplicate harm boundaries cannot create implicit weighting"
        )

    source_keys = {item.key for item in source.positions}
    for replacement in replacements:
        if {item.key for item in replacement.positions} != source_keys:
            raise InvalidReconfiguration(
                "arrangement alternatives must preserve local position correspondence"
            )

    traced = tuple(
        _trace_alternative(source, replacement, constraints)
        for replacement in replacements
    )
    signatures = tuple(_structural_signature(item.replacement) for item in traced)
    if len(set(signatures)) != len(signatures):
        raise InvalidReconfiguration(
            "relabelled or duplicated topology does not create competing variation"
        )
    return CompetingAlternatives(
        source_cut_id=source.cut_id,
        alternatives=traced,
        constraints=tuple(constraints),
    )


def _trace_alternative(
    source: CutEnactment,
    replacement: CutEnactment,
    constraints: Sequence[HarmConstraint],
) -> TracedAlternative:
    comparison = compare_arrangements(source, replacement)
    if not comparison.is_material_variation:
        raise InvalidReconfiguration("alternative has no structural variation")
    effects = tuple(
        _dimension_effect(source, replacement, item) for item in StructuralDimension
    )
    by_dimension = {item.dimension: item for item in effects}
    breaches = tuple(
        breach
        for constraint in constraints
        for breach in (_constraint_breach(constraint, by_dimension[constraint.dimension]),)
        if breach is not None
    )
    return TracedAlternative(
        replacement=replacement,
        comparison=comparison,
        effects=effects,
        harm_increases=breaches,
    )


def _amounts(cut: CutEnactment, dimension: StructuralDimension) -> Dict[str, float]:
    values: Dict[str, float] = {}
    for allocation in cut.allocations:
        if allocation.dimension == dimension:
            key = allocation.position.position_key
            values[key] = values.get(key, 0.0) + allocation.amount
    return values


def _dimension_effect(
    source: CutEnactment,
    replacement: CutEnactment,
    dimension: StructuralDimension,
) -> DimensionEffect:
    before = _amounts(source, dimension)
    after = _amounts(replacement, dimension)
    total_before, total_after = sum(before.values()), sum(after.values())
    maximum_before = max(before.values(), default=0.0)
    maximum_after = max(after.values(), default=0.0)
    occupied_before = sum(value > 0 for value in before.values())
    occupied_after = sum(value > 0 for value in after.values())
    if total_after > total_before:
        direction = EffectDirection.INCREASED
    elif total_after < total_before:
        direction = EffectDirection.DECREASED
    elif before != after:
        direction = EffectDirection.REDISTRIBUTED
    else:
        direction = EffectDirection.UNCHANGED
    return DimensionEffect(
        dimension=dimension,
        total_before=total_before,
        total_after=total_after,
        maximum_before=maximum_before,
        maximum_after=maximum_after,
        occupied_positions_before=occupied_before,
        occupied_positions_after=occupied_after,
        direction=direction,
    )


def _constraint_breach(
    constraint: HarmConstraint, effect: DimensionEffect
) -> HarmIncreaseTrace | None:
    if constraint.measure == EffectMeasure.TOTAL:
        before, after = effect.total_before, effect.total_after
    elif constraint.measure == EffectMeasure.MAXIMUM_LOCAL_LOAD:
        before, after = effect.maximum_before, effect.maximum_after
    else:
        before = float(effect.occupied_positions_before)
        after = float(effect.occupied_positions_after)
    crossed = (
        after > before
        if constraint.prohibited_change == ProhibitedChange.INCREASE
        else after < before
    )
    if not crossed:
        return None
    return HarmIncreaseTrace(
        constraint_id=constraint.constraint_id,
        dimension=constraint.dimension,
        measure=constraint.measure,
        prohibited_change=constraint.prohibited_change,
        before=before,
        after=after,
    )


def _structural_signature(
    cut: CutEnactment,
) -> Tuple[Tuple[str, Tuple[Tuple[str, float], ...]], ...]:
    """Ignore cut IDs, local names, relations, and prose when testing multiplicity."""

    return tuple(
        (
            dimension.value,
            tuple(sorted(_amounts(cut, dimension).items())),
        )
        for dimension in StructuralDimension
    )
