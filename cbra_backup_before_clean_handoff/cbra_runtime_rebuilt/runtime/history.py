from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

from cbra.cbra_runtime_rebuilt.runtime.field_state import FieldState
from cbra.cbra_runtime_rebuilt.articulation.decoder import choose_articulation_stock


@dataclass
class FieldHistoryEntry:
    timestep: int
    before_values: Dict[str, float] = field(default_factory=dict)
    after_values: Dict[str, float] = field(default_factory=dict)
    emergent_form_before: Dict[str, Any] = field(default_factory=dict)
    emergent_form_after: Dict[str, Any] = field(default_factory=dict)
    cut_before: Dict[str, Any] = field(default_factory=dict)
    cut_after: Dict[str, Any] = field(default_factory=dict)
    drift_flags_before: Dict[str, Any] = field(default_factory=dict)
    drift_flags_after: Dict[str, Any] = field(default_factory=dict)
    reintegration_target: Optional[str] = None
    articulation_stock: str = "plain_conceptual"
    operator_names: List[str] = field(default_factory=list)


def snapshot_before(state: FieldState) -> FieldHistoryEntry:
    return FieldHistoryEntry(
        timestep=state.timestep,
        before_values=asdict(state.field_values),
        emergent_form_before=asdict(state.emergent_form),
        cut_before=asdict(state.cut),
        drift_flags_before=asdict(state.drift_flags),
        articulation_stock=choose_articulation_stock(state),
    )


def finalize_entry(
    entry: FieldHistoryEntry,
    state: FieldState,
    reintegration_target: Optional[str] = None,
    operator_names: Optional[List[str]] = None,
) -> FieldHistoryEntry:
    entry.after_values = asdict(state.field_values)
    entry.emergent_form_after = asdict(state.emergent_form)
    entry.cut_after = asdict(state.cut)
    entry.drift_flags_after = asdict(state.drift_flags)
    entry.reintegration_target = reintegration_target
    entry.articulation_stock = choose_articulation_stock(state)
    entry.operator_names = list(operator_names or [])
    return entry
