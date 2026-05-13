from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal

StreamKind = Literal["user_turn","ontology","memory","embodiment","environment","attachment","live_world","prior_trace","institutional_condition","timing","other"]
MediumKind = Literal["text_chat","voice","document","web","mixed","other"]

@dataclass
class Stream:
    stream_id: str = ""
    kind: StreamKind = "other"
    payload: dict[str, Any] = field(default_factory=dict)
    active: bool = True
    participation: float = 0.0
    persistence: float = 0.5
    def clamp(self) -> None:
        self.participation = min(1.0, max(0.0, self.participation))
        self.persistence = min(1.0, max(0.0, self.persistence))

@dataclass
class Coupling:
    source_id: str = ""
    target_id: str = ""
    active: bool = True
    coupling_strength: float = 0.0
    def clamp(self) -> None:
        self.coupling_strength = min(1.0, max(0.0, self.coupling_strength))

@dataclass
class ApparatusState:
    framing: str = "open inquiry"
    medium: MediumKind = "text_chat"
    rules: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    institutional_conditions: list[str] = field(default_factory=list)
    prompting_structure: str = "direct prompt"

@dataclass
class EmergentForm:
    label: str = ""
    lead_stream_ids: list[str] = field(default_factory=list)
    support_stream_ids: list[str] = field(default_factory=list)
    interference_stream_ids: list[str] = field(default_factory=list)
    held_open_stream_ids: list[str] = field(default_factory=list)

@dataclass
class CutState:
    foregrounded: list[str] = field(default_factory=list)
    backgrounded: list[str] = field(default_factory=list)
    held_open: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)

@dataclass
class FieldValues:
    openness: float = 0.50
    difference_activity: float = 0.50
    emergence_level: float = 0.00
    cut_pressure: float = 0.00
    cut_permeability: float = 1.00
    coherence: float = 0.00
    care_tension: float = 0.20
    drift_load: float = 0.00
    def clamp(self) -> None:
        self.openness = min(1.0, max(0.0, self.openness))
        self.difference_activity = min(1.0, max(0.0, self.difference_activity))
        self.emergence_level = min(1.0, max(0.0, self.emergence_level))
        self.cut_pressure = min(1.0, max(0.0, self.cut_pressure))
        self.cut_permeability = min(1.0, max(0.0, self.cut_permeability))
        self.coherence = min(1.0, max(0.0, self.coherence))
        self.care_tension = min(1.0, max(0.0, self.care_tension))
        self.drift_load = min(1.0, max(0.0, self.drift_load))

@dataclass
class DriftFlags:
    ontological_drift: bool = False
    interpretive_compression: bool = False
    capacity_collapse: bool = False
    narrative_dominance: bool = False
    moralization_drift: bool = False
    procedural_bypass: bool = False
    def any(self) -> bool:
        return any([
            self.ontological_drift,
            self.interpretive_compression,
            self.capacity_collapse,
            self.narrative_dominance,
            self.moralization_drift,
            self.procedural_bypass,
        ])

@dataclass
class FieldState:
    field_id: str = ""
    timestep: int = 0
    streams: list[Stream] = field(default_factory=list)
    couplings: list[Coupling] = field(default_factory=list)
    apparatus: ApparatusState = field(default_factory=ApparatusState)
    emergent_form: EmergentForm = field(default_factory=EmergentForm)
    cut: CutState = field(default_factory=CutState)
    field_values: FieldValues = field(default_factory=FieldValues)
    drift_flags: DriftFlags = field(default_factory=DriftFlags)
    def clamp(self) -> None:
        if self.timestep < 0:
            self.timestep = 0
        for s in self.streams:
            s.clamp()
        for c in self.couplings:
            c.clamp()
        self.field_values.clamp()
