from __future__ import annotations

from dataclasses import dataclass, field, asdict
from copy import deepcopy

from cbra_runtime.runtime.field_state import FieldState
from cbra_runtime.articulation.decoder import choose_articulation_stock


@dataclass(slots=True)
class FieldHistoryEntry:
    timestep: int
    before_values: dict[str, float] = field(default_factory=dict)
    after_values: dict[str, float] = field(default_factory=dict)
    emergent_form_before: dict = field(default_factory=dict)
    emergent_form_after: dict = field(default_factory=dict)
    cut_before: dict = field(default_factory=dict)
    cut_after: dict = field(default_factory=dict)
    reintegration_target: str | None = None
    articulation_stock: str = "plain_conceptual"
    operator_names: list[str] = field(default_factory=list)


def snapshot_before(state: FieldState) -> FieldHistoryEntry:
    return FieldHistoryEntry(
        timestep=state.timestep,
        before_values=asdict(state.field_values),
        emergent_form_before=asdict(state.emergent_form),
        cut_before=asdict(state.cut),
        articulation_stock=choose_articulation_stock(state),
    )


def finalize_entry(entry: FieldHistoryEntry, state: FieldState, *, reintegration_target: str | None = None, operator_names: list[str] | None = None) -> FieldHistoryEntry:
    entry.after_values = asdict(state.field_values)
    entry.emergent_form_after = asdict(state.emergent_form)
    entry.cut_after = asdict(state.cut)
    entry.reintegration_target = reintegration_target
    entry.articulation_stock = choose_articulation_stock(state)
    entry.operator_names = list(operator_names or [])
    return entry
