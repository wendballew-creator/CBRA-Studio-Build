"""Mechanical arrangement variation over already-enacted local cuts.

This module does not infer people, needs, care, or the meaning of a message.
It accepts cut-local positions selected by a semantic apparatus and constructs
an inspectable alternative whose effects are derived from allocations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence, Tuple

from .models import (
    Allocation,
    CutEnactment,
    CutPosition,
    LocalPositionRef,
    Relation,
    StructuralDimension,
)
from .substrate import InvalidReconfiguration, ReconfigurationSubstrate


@dataclass(frozen=True)
class ArrangementComparison:
    """Evidence that an alternative changes arrangement, not merely wording."""

    source_cut_id: str
    alternative_cut_id: str
    changed_dimensions: Tuple[StructuralDimension, ...]
    before_shapes: Tuple[Tuple[StructuralDimension, Tuple[float, ...]], ...]
    after_shapes: Tuple[Tuple[StructuralDimension, Tuple[float, ...]], ...]
    consequence_total_before: float
    consequence_total_after: float

    @property
    def is_material_variation(self) -> bool:
        return bool(self.changed_dimensions)

    @property
    def preserves_consequence(self) -> bool:
        return self.consequence_total_after >= self.consequence_total_before


@dataclass(frozen=True)
class BurdenRedistributionCandidate:
    """A proposed cut plus evidence; not a declaration that care occurred."""

    replacement: CutEnactment
    comparison: ArrangementComparison


class ArrangementExplorer:
    """Construct and compare burden-sharing alternatives within one local cut."""

    def __init__(self, substrate: ReconfigurationSubstrate) -> None:
        self._substrate = substrate

    def redistribute_concentrated_burden(
        self,
        *,
        source_cut_id: str,
        source_position_key: str,
        support_position_keys: Sequence[str],
        alternative_cut_id: str,
        retained_source_fraction: float = 0.5,
    ) -> BurdenRedistributionCandidate:
        if source_cut_id not in self._substrate.state.active_cut_ids:
            raise InvalidReconfiguration("arrangement source must be an active cut")
        if not alternative_cut_id or alternative_cut_id in self._substrate.state.cuts:
            raise InvalidReconfiguration("alternative cut id must be new and nonempty")
        if not 0 <= retained_source_fraction < 1:
            raise InvalidReconfiguration("retained burden fraction must be within [0, 1)")

        source = self._substrate.state.cuts[source_cut_id]
        keys = {position.key for position in source.positions}
        supports = tuple(dict.fromkeys(support_position_keys))
        if source_position_key not in keys:
            raise InvalidReconfiguration("burden source must be local to the source cut")
        if not supports or source_position_key in supports or not set(supports).issubset(keys):
            raise InvalidReconfiguration(
                "support positions must be distinct positions local to the source cut"
            )

        burden_by_position = self._amounts(source, StructuralDimension.BURDEN)
        source_burden = burden_by_position.get(source_position_key, 0.0)
        total_burden = sum(burden_by_position.values())
        if source_burden <= 0 or source_burden <= total_burden / 2:
            raise InvalidReconfiguration("selected burden is not structurally concentrated")

        retained = source_burden * retained_source_fraction
        transferred = source_burden - retained
        share = transferred / len(supports)
        burden_by_position[source_position_key] = retained
        for key in supports:
            burden_by_position[key] = burden_by_position.get(key, 0.0) + share

        replacement = self._rekeyed_replacement(
            source,
            alternative_cut_id=alternative_cut_id,
            burden_by_position=burden_by_position,
        )
        comparison = compare_arrangements(source, replacement)
        if not comparison.is_material_variation:
            raise InvalidReconfiguration("alternative has no structural variation")
        if StructuralDimension.BURDEN not in comparison.changed_dimensions:
            raise InvalidReconfiguration("alternative does not redistribute burden")
        if not comparison.preserves_consequence:
            raise InvalidReconfiguration("redistribution cannot erase consequence")
        return BurdenRedistributionCandidate(
            replacement=replacement, comparison=comparison
        )

    @staticmethod
    def _amounts(cut: CutEnactment, dimension: StructuralDimension) -> Dict[str, float]:
        amounts: Dict[str, float] = {}
        for allocation in cut.allocations:
            if allocation.dimension == dimension:
                key = allocation.position.position_key
                amounts[key] = amounts.get(key, 0.0) + allocation.amount
        return amounts

    @staticmethod
    def _rekeyed_replacement(
        source: CutEnactment,
        *,
        alternative_cut_id: str,
        burden_by_position: Dict[str, float],
    ) -> CutEnactment:
        def ref(old: LocalPositionRef) -> LocalPositionRef:
            return LocalPositionRef(alternative_cut_id, old.position_key)

        non_burden = tuple(
            Allocation(item.dimension, ref(item.position), item.amount)
            for item in source.allocations
            if item.dimension != StructuralDimension.BURDEN
        )
        burdens = tuple(
            Allocation(
                StructuralDimension.BURDEN,
                LocalPositionRef(alternative_cut_id, key),
                amount,
            )
            for key, amount in sorted(burden_by_position.items())
            if amount > 0
        )
        return CutEnactment(
            cut_id=alternative_cut_id,
            transport_basis=source.transport_basis,
            dependency_ids=source.dependency_ids,
            lineage_ids=(source.cut_id,),
            positions=tuple(CutPosition(item.key, item.local_name) for item in source.positions),
            relations=tuple(
                Relation(item.relation_type, ref(item.source), ref(item.target))
                for item in source.relations
            ),
            allocations=non_burden + burdens,
            revision_conditions=source.revision_conditions,
            exclusions=source.exclusions,
        )


def compare_arrangements(
    source: CutEnactment, alternative: CutEnactment
) -> ArrangementComparison:
    """Compare allocation shapes without treating cut IDs or names as change."""

    def distributions(cut: CutEnactment):
        rows = []
        for dimension in StructuralDimension:
            by_position: Dict[str, float] = {}
            for item in cut.allocations:
                if item.dimension == dimension:
                    key = item.position.position_key
                    by_position[key] = by_position.get(key, 0.0) + item.amount
            rows.append((dimension, by_position))
        return tuple(rows)

    before_distributions = distributions(source)
    after_distributions = distributions(alternative)
    before = tuple(
        (dimension, tuple(sorted(distribution.values())))
        for dimension, distribution in before_distributions
    )
    after = tuple(
        (dimension, tuple(sorted(distribution.values())))
        for dimension, distribution in after_distributions
    )
    source_position_keys = {position.key for position in source.positions}
    alternative_position_keys = {position.key for position in alternative.positions}
    positions_correspond = source_position_keys == alternative_position_keys
    changed = tuple(
        dimension
        for (dimension, before_distribution), (_, after_distribution) in zip(
            before_distributions, after_distributions
        )
        if (
            any(
                before_distribution.get(key, 0.0)
                != after_distribution.get(key, 0.0)
                for key in source_position_keys
            )
            if positions_correspond
            else tuple(sorted(before_distribution.values()))
            != tuple(sorted(after_distribution.values()))
        )
    )

    def total(cut: CutEnactment, dimension: StructuralDimension) -> float:
        return sum(
            item.amount for item in cut.allocations if item.dimension == dimension
        )

    return ArrangementComparison(
        source_cut_id=source.cut_id,
        alternative_cut_id=alternative.cut_id,
        changed_dimensions=changed,
        before_shapes=before,
        after_shapes=after,
        consequence_total_before=total(source, StructuralDimension.CONSEQUENCE),
        consequence_total_after=total(alternative, StructuralDimension.CONSEQUENCE),
    )
