from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class HistoryStepModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timestep: int
    before_values: Dict[str, float] = Field(default_factory=dict)
    after_values: Dict[str, float] = Field(default_factory=dict)
    emergent_form_before: Dict[str, Any] = Field(default_factory=dict)
    emergent_form_after: Dict[str, Any] = Field(default_factory=dict)
    cut_before: Dict[str, Any] = Field(default_factory=dict)
    cut_after: Dict[str, Any] = Field(default_factory=dict)
    drift_flags_before: Dict[str, Any] = Field(default_factory=dict)
    drift_flags_after: Dict[str, Any] = Field(default_factory=dict)
    reintegration_target: Optional[str] = None
    articulation_stock: str = ""
    operator_names: List[str] = Field(default_factory=list)


class ExportedHistoryPayloadModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field_id: str = ""
    final_timestep: int = 0
    step_count: int = 0
    articulation_stocks_seen: List[str] = Field(default_factory=list)
    final_articulation_stock: str = ""
    history: List[HistoryStepModel] = Field(default_factory=list)


class SnapshotPayloadModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field_state: Dict[str, Any] = Field(default_factory=dict)
    history: ExportedHistoryPayloadModel
    ui: Dict[str, Any] = Field(default_factory=dict)


class DebugPayloadModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field_id: str = ""
    timestep: int = 0
    current_articulation_stock: str = ""
    current_decoder_text: str = ""
    rendered_history: str = ""
    exported_history: ExportedHistoryPayloadModel
    ui: Dict[str, Any] = Field(default_factory=dict)


class DebugAPIResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ok: bool = True
    payload: DebugPayloadModel


class DebugPanelContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    panel_kind: str = "field_debug"
    field_id: str = ""
    timestep: int = 0
    current_articulation_stock: str = ""
    current_decoder_text: str = ""
    rendered_history: str = ""
    step_count: int = 0


class InputStreamModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stream_id: str = ""
    kind: str = "other"
    payload: Dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    participation: float = 0.0
    persistence: float = 0.5


class RuntimeInputRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    streams: List[InputStreamModel] = Field(default_factory=list)
    medium: str = "text_chat"
    roles: List[str] = Field(default_factory=lambda: ["user", "assistant"])
    institutional_conditions: List[str] = Field(default_factory=list)
    field_id: Optional[str] = None


class RuntimeInputEnvelopeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ok: bool = True
    request: RuntimeInputRequestModel
