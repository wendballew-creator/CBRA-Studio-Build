from __future__ import annotations

from typing import Any, Dict, List

from cbra.cbra_runtime_rebuilt.runtime.history import FieldHistoryEntry


def history_entry_to_dict(entry: FieldHistoryEntry) -> Dict[str, Any]:
    return {
        "timestep": int(entry.timestep),
        "before_values": dict(entry.before_values),
        "after_values": dict(entry.after_values),
        "emergent_form_before": dict(entry.emergent_form_before),
        "emergent_form_after": dict(entry.emergent_form_after),
        "cut_before": dict(entry.cut_before),
        "cut_after": dict(entry.cut_after),
        "drift_flags_before": dict(entry.drift_flags_before),
        "drift_flags_after": dict(entry.drift_flags_after),
        "reintegration_target": entry.reintegration_target,
        "articulation_stock": str(entry.articulation_stock),
        "operator_names": list(entry.operator_names),
    }


def export_history(history: List[FieldHistoryEntry]) -> List[Dict[str, Any]]:
    return [history_entry_to_dict(entry) for entry in history]


def export_history_payload(
    history: List[FieldHistoryEntry],
    field_id: str = "",
    final_timestep: int = 0,
) -> Dict[str, Any]:
    steps = export_history(history)
    articulation_stocks = list(dict.fromkeys(
        step["articulation_stock"] for step in steps if step.get("articulation_stock")
    ))
    final_articulation_stock = articulation_stocks[-1] if articulation_stocks else ""
    return {
        "field_id": field_id or "",
        "final_timestep": int(final_timestep or (history[-1].timestep if history else 0)),
        "step_count": len(steps),
        "articulation_stocks_seen": articulation_stocks,
        "final_articulation_stock": final_articulation_stock,
        "history": steps,
    }
