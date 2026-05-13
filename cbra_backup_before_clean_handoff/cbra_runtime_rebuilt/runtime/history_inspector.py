from __future__ import annotations

from typing import Any, Dict, List

from cbra.cbra_runtime_rebuilt.runtime.history import FieldHistoryEntry


def _fmt_float(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    return str(value)


def history_to_rows(history: List[FieldHistoryEntry]) -> List[Dict[str, Any]]:
    rows = []
    for entry in history:
        rows.append(
            {
                "timestep": entry.timestep,
                "articulation_stock": entry.articulation_stock,
                "reintegration_target": entry.reintegration_target or "",
                "operator_names": list(entry.operator_names),
                "coherence_before": entry.before_values.get("coherence"),
                "coherence_after": entry.after_values.get("coherence"),
                "emergence_before": entry.before_values.get("emergence_level"),
                "emergence_after": entry.after_values.get("emergence_level"),
                "lead_before": entry.emergent_form_before.get("label", ""),
                "lead_after": entry.emergent_form_after.get("label", ""),
                "foregrounded_after": list(entry.cut_after.get("foregrounded", [])),
            }
        )
    return rows


def render_history_step(entry: FieldHistoryEntry) -> str:
    lines = []
    lines.append(f"Step {entry.timestep}")
    lines.append(f"  stock: {entry.articulation_stock}")
    if entry.operator_names:
        lines.append(f"  operators: {', '.join(entry.operator_names)}")
    if entry.reintegration_target:
        lines.append(f"  reintegration: {entry.reintegration_target}")
    lines.append(
        "  field_values: "
        f"coherence {_fmt_float(entry.before_values.get('coherence'))} -> {_fmt_float(entry.after_values.get('coherence'))}; "
        f"emergence {_fmt_float(entry.before_values.get('emergence_level'))} -> {_fmt_float(entry.after_values.get('emergence_level'))}"
    )
    lines.append(
        f"  emergent_form: lead '{entry.emergent_form_before.get('label','')}' -> '{entry.emergent_form_after.get('label','')}'"
    )
    return "\n".join(lines)


def render_history(history: List[FieldHistoryEntry]) -> str:
    if not history:
        return "No field history available."
    header = ["Field History", f"steps: {len(history)}"]
    body = [render_history_step(entry) for entry in history]
    return "\n\n".join(header + body)
