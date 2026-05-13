from __future__ import annotations
from typing import Any, Literal, List, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict
from dataclasses import dataclass, field
import uuid

@dataclass
class Stream:
    stream_id: str = ""
    kind: str = "other"
    payload: dict = field(default_factory=dict)
    active: bool = True
    participation: float = 0.0
    persistence: float = 0.5

    def clamp(self):
        self.participation = max(0.0, min(1.0, self.participation))
        self.persistence = max(0.0, min(1.0, self.persistence))

@dataclass
class FieldValues:
    openness: float = 0.5
    difference_activity: float = 0.0
    emergence_level: float = 0.0
    cut_pressure: float = 0.0
    cut_permeability: float = 1.0
    coherence: float = 0.0
    care_tension: float = 0.2

    def clamp(self):
        for attr in ["openness", "difference_activity", "emergence_level", "cut_pressure", "cut_permeability", "coherence", "care_tension"]:
            val = getattr(self, attr)
            setattr(self, attr, max(0.0, min(1.0, val)))

@dataclass
class DriftFlags:
    interpretive_compression: bool = False
    
@dataclass
class FieldState:
    id: str
    field_signature: Dict[str, Any] = field(default_factory=dict)
    streams: List[Stream] = field(default_factory=list)
    field_values: FieldValues = field(default_factory=FieldValues)
    drift_flags: DriftFlags = field(default_factory=DriftFlags)
    notes: Dict[str, Any] = field(default_factory=dict)
    timestep: int = 0

    def clamp(self):
        self.field_values.clamp()
        for s in self.streams:
            s.clamp()
            
    def clear_drift_flags(self):
        self.drift_flags.interpretive_compression = False
