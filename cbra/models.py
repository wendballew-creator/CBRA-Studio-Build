from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel


class Message(BaseModel):
    role: str                # "user" or "assistant"
    content: str
    timestamp: datetime


class LoopCycle(BaseModel):
    # These start as dicts. Later we can tighten them into richer models.
    field_signature: Dict[str, Any] = {}
    noticing_register: Dict[str, Any] = {}
    relational_map: Dict[str, Any] = {}
    diffractive_map: Dict[str, Any] = {}
    relevance_gradient: Dict[str, Any] = {}

    articulation_output: str = ""
    action_vector: Optional[str] = None

    drift_detected: bool = False
    reintegration_stage: Optional[str] = None


class DriftEvent(BaseModel):
    type: str
    detected_at_stage: str
    reintegration_stage: str
    timestamp: datetime


class Thread(BaseModel):
    id: str
    messages: List[Message] = []
    loop_history: List[LoopCycle] = []
    drift_events: List[DriftEvent] = []
    created_at: datetime
    updated_at: datetime
