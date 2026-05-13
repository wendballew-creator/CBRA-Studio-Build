from __future__ import annotations
from typing import Any, Dict, List, Optional, Union, Any
from cbra.cbra_runtime_rebuilt.interfaces.input_api_adapter import build_input_envelope, envelope_to_field_state
from cbra.cbra_runtime_rebuilt.interfaces.debug_api_adapter import build_debug_api_response
from cbra.cbra_runtime_rebuilt.runtime.session import RuntimeSession
from cbra.cbra_runtime_rebuilt.schema.payload_models import DebugAPIResponseModel

def debug_runtime_endpoint(*, streams: list[dict[str, Any]], medium: str = "text_chat", roles: Optional[List[str]] = None, institutional_conditions: Optional[List[str]] = None, field_id: Optional[str] = None, max_steps: int = 8) -> DebugAPIResponseModel:
    envelope = build_input_envelope(streams=streams, medium=medium, roles=roles, institutional_conditions=institutional_conditions, field_id=field_id)
    state = envelope_to_field_state(envelope)
    session = RuntimeSession(state=state)
    session.run(max_steps=max_steps)
    return build_debug_api_response(session.state, session.history)
def debug_runtime_endpoint_dict(**kwargs) -> dict[str, Any]:
    return debug_runtime_endpoint(**kwargs).model_dump()
