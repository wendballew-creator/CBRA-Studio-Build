"""Dependency-driven cut enactment and invalidation.

All deltas are derived from before/after configuration structure.  Callers do
not submit a prose claim that care, play, or reconfiguration occurred.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Dict, Iterable, Mapping, Sequence, Set, Tuple

from .models import (
    Allocation,
    ConfigurationTrace,
    CutEnactment,
    LocalPositionRef,
    ReconfigurationDelta,
    StructuralDimension,
    TransportTrace,
    frozen_mapping,
)


class StorageOntologyViolation(ValueError):
    """A transport inscription was used as a semantic position or role."""


class InvalidReconfiguration(ValueError):
    """A proposed mutation is untraceable or produces no structural change."""


class ReconfigurationSubstrate:
    def __init__(self, state: ConfigurationTrace | None = None) -> None:
        self._state = state or ConfigurationTrace()
        self._validate_restored_state(self._state)

    @property
    def state(self) -> ConfigurationTrace:
        return self._state

    def record_transport(self, trace: TransportTrace) -> ConfigurationTrace:
        if trace.trace_id in self._state.transports:
            if self._state.transports[trace.trace_id] != trace:
                raise ValueError("transport trace id cannot be rebound")
            return self._state
        transports = dict(self._state.transports)
        transports[trace.trace_id] = trace
        self._state = replace(
            self._state,
            version=self._state.version + 1,
            transports=frozen_mapping(transports),
        )
        return self._state

    def enact_cut(self, cut: CutEnactment, *, delta_id: str) -> ReconfigurationDelta:
        self._validate_new_cut(cut)
        delta = self._derive_delta(
            delta_id=delta_id,
            invalidated_ids=(),
            activated=(cut,),
            triggering_trace_ids=cut.transport_basis,
        )
        self._apply(delta, activated=(cut,))
        return delta

    def enact_concurrent_cuts(
        self, cuts: Sequence[CutEnactment], *, delta_id: str
    ) -> ReconfigurationDelta:
        """Atomically enact an unordered plurality of independently valid cuts."""

        if len(cuts) < 2:
            raise InvalidReconfiguration(
                "concurrent enactment requires more than one cut"
            )
        cut_ids = [cut.cut_id for cut in cuts]
        if len(cut_ids) != len(set(cut_ids)):
            raise InvalidReconfiguration("concurrent cut ids must be unique")
        concurrent_ids = set(cut_ids)
        for cut in cuts:
            if set(cut.dependency_ids).intersection(concurrent_ids):
                raise InvalidReconfiguration(
                    "concurrent cuts cannot hide proposal order through dependencies"
                )
            self._validate_new_cut(cut)
        ordered = tuple(sorted(cuts, key=lambda cut: cut.cut_id))
        triggering_trace_ids = tuple(
            sorted({trace_id for cut in ordered for trace_id in cut.transport_basis})
        )
        delta = self._derive_delta(
            delta_id=delta_id,
            invalidated_ids=(),
            activated=ordered,
            triggering_trace_ids=triggering_trace_ids,
        )
        self._apply(delta, activated=ordered)
        return delta

    def disturb(
        self,
        *,
        delta_id: str,
        triggering_trace_ids: Sequence[str],
        invalidated_root_ids: Sequence[str],
        replacements: Sequence[CutEnactment],
    ) -> ReconfigurationDelta:
        if not triggering_trace_ids:
            raise InvalidReconfiguration("a disturbance requires transport evidence")
        self._require_transport_ids(triggering_trace_ids)
        roots = set(invalidated_root_ids)
        if not roots:
            raise InvalidReconfiguration("a disturbance must identify an affected cut")
        inactive = roots.difference(self._state.active_cut_ids)
        if inactive:
            raise InvalidReconfiguration(
                "disturbance roots must be active: " + ", ".join(sorted(inactive))
            )
        invalidated = self._dependent_closure(roots)
        self._validate_replacement_dependencies(replacements, invalidated)
        for cut in replacements:
            self._validate_new_cut(cut, pending_invalidations=invalidated)
        delta = self._derive_delta(
            delta_id=delta_id,
            invalidated_ids=tuple(sorted(invalidated)),
            activated=tuple(replacements),
            triggering_trace_ids=tuple(triggering_trace_ids),
        )
        if not delta.has_structural_change:
            raise InvalidReconfiguration("proposed disturbance has no structural delta")
        self._apply(delta, activated=tuple(replacements))
        return delta

    def _validate_new_cut(
        self,
        cut: CutEnactment,
        *,
        pending_invalidations: Set[str] | None = None,
    ) -> None:
        if not cut.cut_id or cut.cut_id in self._state.cuts:
            raise InvalidReconfiguration("cut id must be new and nonempty")
        if not (cut.transport_basis or cut.dependency_ids or cut.lineage_ids):
            raise InvalidReconfiguration("a cut requires traceable transport or cut basis")
        self._require_transport_ids(cut.transport_basis)
        position_keys = [position.key for position in cut.positions]
        if not position_keys or len(position_keys) != len(set(position_keys)):
            raise InvalidReconfiguration("cut positions must be nonempty and locally unique")
        local_refs = {LocalPositionRef(cut.cut_id, key) for key in position_keys}
        for relation in cut.relations:
            self._validate_position_ref(relation.source, cut, local_refs)
            self._validate_position_ref(relation.target, cut, local_refs)
        for allocation in cut.allocations:
            self._validate_position_ref(allocation.position, cut, local_refs)
        forbidden = set(self._state.transports)
        if any(position.key in forbidden for position in cut.positions):
            raise StorageOntologyViolation(
                "transport ids cannot become semantic position keys"
            )
        pending = pending_invalidations or set()
        for dependency_id in cut.dependency_ids:
            if dependency_id not in self._state.active_cut_ids or dependency_id in pending:
                raise InvalidReconfiguration(
                    f"cut depends on inactive or disturbed cut: {dependency_id}"
                )
        unknown_lineage = set(cut.lineage_ids).difference(self._state.cuts)
        if unknown_lineage:
            raise InvalidReconfiguration("lineage must reference recorded cuts")

    @staticmethod
    def _validate_position_ref(
        ref: LocalPositionRef,
        owner: CutEnactment,
        owner_refs: Set[LocalPositionRef],
    ) -> None:
        if ref.cut_id != owner.cut_id or ref not in owner_refs:
            raise InvalidReconfiguration(
                "relations and allocations must use positions local to their cut"
            )

    def _validate_replacement_dependencies(
        self,
        replacements: Sequence[CutEnactment],
        invalidated: Set[str],
    ) -> None:
        replacement_ids = {cut.cut_id for cut in replacements}
        if len(replacement_ids) != len(replacements):
            raise InvalidReconfiguration("replacement cut ids must be unique")
        for cut in replacements:
            if set(cut.dependency_ids).intersection(replacement_ids):
                raise InvalidReconfiguration(
                    "one atomic disturbance cannot hide a replacement stage order"
                )
            if set(cut.dependency_ids).intersection(invalidated):
                raise InvalidReconfiguration("replacement depends on an invalidated cut")

    def _require_transport_ids(self, ids: Iterable[str]) -> None:
        unknown = set(ids).difference(self._state.transports)
        if unknown:
            raise InvalidReconfiguration(
                "cut references unknown transport: " + ", ".join(sorted(unknown))
            )

    def _dependent_closure(self, roots: Set[str]) -> Set[str]:
        invalidated = set(roots)
        changed = True
        while changed:
            changed = False
            for cut_id in self._state.active_cut_ids:
                cut = self._state.cuts[cut_id]
                if cut_id not in invalidated and set(cut.dependency_ids) & invalidated:
                    invalidated.add(cut_id)
                    changed = True
        return invalidated

    def _active_allocations(
        self,
        active_ids: Iterable[str],
        extra: Mapping[str, CutEnactment] | None = None,
    ) -> Tuple[Allocation, ...]:
        cuts = dict(self._state.cuts)
        cuts.update(extra or {})
        return tuple(
            allocation
            for cut_id in sorted(active_ids)
            for allocation in cuts[cut_id].allocations
        )

    def _derive_delta(
        self,
        *,
        delta_id: str,
        invalidated_ids: Sequence[str],
        activated: Sequence[CutEnactment],
        triggering_trace_ids: Sequence[str],
    ) -> ReconfigurationDelta:
        if not delta_id or any(item.delta_id == delta_id for item in self._state.deltas):
            raise InvalidReconfiguration("delta id must be new and nonempty")
        before_ids = set(self._state.active_cut_ids)
        after_ids = before_ids.difference(invalidated_ids)
        after_ids.update(cut.cut_id for cut in activated)
        additions = {cut.cut_id: cut for cut in activated}
        before = self._active_allocations(before_ids)
        after = self._active_allocations(after_ids, additions)
        before_totals = self._dimension_totals(before)
        after_totals = self._dimension_totals(after)
        changed_dimensions = tuple(
            dimension
            for dimension in StructuralDimension
            if before_totals[dimension] != after_totals[dimension]
            or self._dimension_distribution(before, dimension)
            != self._dimension_distribution(after, dimension)
        )
        return ReconfigurationDelta(
            delta_id=delta_id,
            activated_cut_ids=tuple(cut.cut_id for cut in activated),
            invalidated_cut_ids=tuple(invalidated_ids),
            changed_dimensions=changed_dimensions,
            allocation_before=before,
            allocation_after=after,
            triggering_trace_ids=tuple(triggering_trace_ids),
        )

    @staticmethod
    def _dimension_totals(
        allocations: Sequence[Allocation],
    ) -> Dict[StructuralDimension, float]:
        totals = {dimension: 0.0 for dimension in StructuralDimension}
        for allocation in allocations:
            totals[allocation.dimension] += allocation.amount
        return totals

    @staticmethod
    def _dimension_distribution(
        allocations: Sequence[Allocation], dimension: StructuralDimension
    ) -> Tuple[float, ...]:
        """Compare allocation shape without treating fresh IDs as change."""

        by_position: Dict[LocalPositionRef, float] = {}
        for item in allocations:
            if item.dimension == dimension:
                by_position[item.position] = (
                    by_position.get(item.position, 0.0) + item.amount
                )
        return tuple(sorted(by_position.values()))

    def _apply(
        self,
        delta: ReconfigurationDelta,
        *,
        activated: Sequence[CutEnactment],
    ) -> None:
        cuts = dict(self._state.cuts)
        cuts.update({cut.cut_id: cut for cut in activated})
        active = set(self._state.active_cut_ids)
        active.difference_update(delta.invalidated_cut_ids)
        active.update(delta.activated_cut_ids)
        invalidated_by = dict(self._state.invalidated_by)
        invalidated_by.update(
            {cut_id: delta.delta_id for cut_id in delta.invalidated_cut_ids}
        )
        self._state = ConfigurationTrace(
            version=self._state.version + 1,
            transports=self._state.transports,
            cuts=cuts,
            active_cut_ids=tuple(sorted(active)),
            invalidated_by=invalidated_by,
            deltas=self._state.deltas + (delta,),
        )

    def _validate_restored_state(self, state: ConfigurationTrace) -> None:
        active = set(state.active_cut_ids)
        if not active.issubset(state.cuts):
            raise InvalidReconfiguration("active cut ids must reference recorded cuts")
        if active.intersection(state.invalidated_by):
            raise InvalidReconfiguration("an invalidated cut cannot remain active")
        for cut_id in active:
            cut = state.cuts[cut_id]
            if not set(cut.dependency_ids).issubset(active):
                raise InvalidReconfiguration("active dependency graph is incomplete")
        visiting: Set[str] = set()
        visited: Set[str] = set()

        def visit(cut_id: str) -> None:
            if cut_id in visiting:
                raise InvalidReconfiguration("active dependency graph contains a cycle")
            if cut_id in visited:
                return
            visiting.add(cut_id)
            for dependency_id in state.cuts[cut_id].dependency_ids:
                visit(dependency_id)
            visiting.remove(cut_id)
            visited.add(cut_id)

        for cut_id in active:
            visit(cut_id)
