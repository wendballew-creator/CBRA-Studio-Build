from __future__ import annotations
from typing import Any
from cbra.cbra_runtime_rebuilt.articulation.decoder import decode_articulation, choose_articulation_stock
from cbra.cbra_runtime_rebuilt.runtime.field_state import FieldState
from cbra.cbra_runtime_rebuilt.runtime.history import FieldHistoryEntry
from cbra.cbra_runtime_rebuilt.runtime.history_export import export_history_payload
from cbra.cbra_runtime_rebuilt.runtime.history_inspector import render_history
from cbra.cbra_runtime_rebuilt.schema.payload_models import DebugPayloadModel

def build_debug_payload(state: FieldState, history: list[FieldHistoryEntry]) -> dict[str, Any]:
    current_stock = choose_articulation_stock(state)
    payload = {
        "field_id": state.field_id,
        "timestep": state.timestep,
        "current_articulation_stock": current_stock,
        "current_decoder_text": decode_articulation(state, history),
        "rendered_history": render_history(history),
        "exported_history": export_history_payload(history, field_id=state.field_id, final_timestep=state.timestep),
        "ui": {"panel_kind": "field_debug", "current_articulation_stock": current_stock, "step_count": len(history)},
    }
    return DebugPayloadModel.model_validate(payload).model_dump()
