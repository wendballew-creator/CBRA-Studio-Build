from __future__ import annotations
from typing import Any
from cbra.cbra_runtime_rebuilt.runtime.field_state import FieldState
from cbra.cbra_runtime_rebuilt.runtime.history import FieldHistoryEntry
from cbra.cbra_runtime_rebuilt.runtime.debug_payload import build_debug_payload
from cbra.cbra_runtime_rebuilt.schema.payload_models import DebugAPIResponseModel, DebugPanelContractModel, DebugPayloadModel

def build_debug_response(state: FieldState, history: list[FieldHistoryEntry]) -> DebugPayloadModel:
    return DebugPayloadModel.model_validate(build_debug_payload(state, history))
def build_debug_api_response(state: FieldState, history: list[FieldHistoryEntry]) -> DebugAPIResponseModel:
    return DebugAPIResponseModel(ok=True, payload=build_debug_response(state, history))
def build_debug_response_dict(state: FieldState, history: list[FieldHistoryEntry]) -> dict[str, Any]:
    return build_debug_api_response(state, history).model_dump()
def build_panel_contract(state: FieldState, history: list[FieldHistoryEntry]) -> DebugPanelContractModel:
    payload = build_debug_response(state, history)
    return DebugPanelContractModel(
        panel_kind=payload.ui.get("panel_kind", "field_debug"),
        field_id=payload.field_id,
        timestep=payload.timestep,
        current_articulation_stock=payload.current_articulation_stock,
        current_decoder_text=payload.current_decoder_text,
        rendered_history=payload.rendered_history,
        step_count=payload.ui.get("step_count", 0),
    )
def build_panel_contract_dict(state: FieldState, history: list[FieldHistoryEntry]) -> dict[str, Any]:
    return build_panel_contract(state, history).model_dump()
