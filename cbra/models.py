from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


class Message(BaseModel):
    role: str
    content: str
    ts: str = Field(default_factory=_now_iso)


class DriftEvent(BaseModel):
    ts: str = Field(default_factory=_now_iso)
    kind: str
    severity: str = "low"
    reintegration_target: Optional[str] = None
    notes: Optional[str] = None


class FieldArtifact(BaseModel):
    """
    First-class persisted 'field' object. This becomes the canonical substrate
    for loop execution + diffractive mapping, with language as downstream translation.
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    thread_id: str

    # Default diffractive orientation
    # Default diffractive ground (CBRA ontology)
    diffractive_ground: str = "CBRA"

    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)

    sources_citations: List[str] = Field(default_factory=list)

    field_signature: Dict[str, Any] = Field(default_factory=dict)
    noticing_register: Dict[str, Any] = Field(default_factory=dict)
    relational_map: Dict[str, Any] = Field(default_factory=dict)
    diffractive_map: Dict[str, Any] = Field(default_factory=dict)
    relevance_gradient: Dict[str, Any] = Field(default_factory=dict)

    selected_elements: List[Dict[str, Any]] = Field(default_factory=list)
    notes: Dict[str, Any] = Field(default_factory=dict)


class LoopCycle(BaseModel):
    ts: str = Field(default_factory=_now_iso)

    # Link to the canonical field artifact (added for commit 1)
    field_id: Optional[str] = None

    field_signature: Dict[str, Any] = Field(default_factory=dict)
    noticing_register: Dict[str, Any] = Field(default_factory=dict)
    relational_map: Dict[str, Any] = Field(default_factory=dict)
    diffractive_map: Dict[str, Any] = Field(default_factory=dict)
    relevance_gradient: Dict[str, Any] = Field(default_factory=dict)

    articulation_output: Optional[str] = None
    action_vector: Optional[Dict[str, Any]] = None

    drift_detected: bool = False
    reintegration_stage: Optional[str] = None

class Thread(BaseModel):
    id: str
    messages: List[Message] = Field(default_factory=list)
    loop_cycles: List[LoopCycle] = Field(default_factory=list)
    drift_events: List[DriftEvent] = Field(default_factory=list)

    # Track the currently active field artifact
    current_field_id: Optional[str] = None
