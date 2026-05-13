from __future__ import annotations
from typing import Any
from cbra.cbra_runtime_rebuilt.runtime.field_state import Stream, FieldState
from cbra.cbra_runtime_rebuilt.runtime.runtime_loop import initialize_field
from cbra.cbra_runtime_rebuilt.schema.payload_models import RuntimeInputEnvelopeModel, RuntimeInputRequestModel

def build_input_request(*, streams: list[dict[str, Any]], medium: str = "text_chat", roles: list[str] | None = None, institutional_conditions: list[str] | None = None, field_id: str | None = None) -> RuntimeInputRequestModel:
    return RuntimeInputRequestModel.model_validate({
        "streams": streams,
        "medium": medium,
        "roles": list(roles or ["user", "assistant"]),
        "institutional_conditions": list(institutional_conditions or []),
        "field_id": field_id,
    })
def build_input_envelope(**kwargs) -> RuntimeInputEnvelopeModel:
    return RuntimeInputEnvelopeModel(ok=True, request=build_input_request(**kwargs))
def request_to_runtime_streams(request: RuntimeInputRequestModel) -> list[Stream]:
    return [Stream(stream_id=i.stream_id, kind=i.kind, payload=dict(i.payload), active=i.active, participation=i.participation, persistence=i.persistence) for i in request.streams]
def envelope_to_field_state(envelope: RuntimeInputEnvelopeModel) -> FieldState:
    req = envelope.request
    return initialize_field(request_to_runtime_streams(req), field_id=req.field_id, medium=req.medium, roles=req.roles, institutional_conditions=req.institutional_conditions)
def build_field_state_from_input(**kwargs) -> FieldState:
    return envelope_to_field_state(build_input_envelope(**kwargs))
def build_input_request_dict(**kwargs) -> dict[str, Any]:
    return build_input_request(**kwargs).model_dump()
def build_input_envelope_dict(**kwargs) -> dict[str, Any]:
    return build_input_envelope(**kwargs).model_dump()
