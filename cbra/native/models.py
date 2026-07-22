"""Typed objects for CBRA's changing relational field."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class DriftKind(str, Enum):
    COMPRESSION = "compression"
    NARRATIVE_DOMINANCE = "narrative_dominance"
    MORALIZATION = "moralization"
    CAPACITY_COLLAPSE = "capacity_collapse"
    ONTOLOGICAL_DRIFT = "ontological_drift"
    PROCEDURAL_BYPASS = "procedural_bypass"


@dataclass
class Stream:
    stream_id: str
    kind: str
    participation: float
    persistence: float
    payload: Dict[str, Any] = field(default_factory=dict)
    active: bool = True
    provenance: Dict[str, Any] = field(default_factory=dict)

    def clamp(self) -> None:
        self.participation = clamp01(self.participation)
        self.persistence = clamp01(self.persistence)


@dataclass
class Relation:
    relation_id: str
    left_id: str
    right_id: str
    resonance: float = 0.0
    difference: float = 0.0
    mutuality: float = 0.0
    apparatus_effect: float = 0.0
    active: bool = True
    traces: List[str] = field(default_factory=list)

    def clamp(self) -> None:
        self.resonance = clamp01(self.resonance)
        self.difference = clamp01(self.difference)
        self.mutuality = clamp01(self.mutuality)
        self.apparatus_effect = clamp01(self.apparatus_effect)


@dataclass
class Apparatus:
    apparatus_id: str = "apparatus:default"
    framing: str = "open inquiry"
    medium: str = "text_chat"
    prompts: List[str] = field(default_factory=list)
    interfaces: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    models: List[str] = field(default_factory=list)
    institutions: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    temporal_pressures: List[str] = field(default_factory=list)


@dataclass
class FieldValues:
    openness: float
    multiplicity: float
    difference_activity: float
    relational_intensity: float
    emergence_level: float
    coherence: float
    cut_pressure: float
    cut_permeability: float
    care_capacity: float
    care_tension: float
    drift_load: float

    def clamp(self) -> None:
        for name in self.__dataclass_fields__:
            setattr(self, name, clamp01(getattr(self, name)))

    def as_dict(self) -> Dict[str, float]:
        return {
            name: float(getattr(self, name))
            for name in self.__dataclass_fields__
        }


@dataclass
class DiffractivePattern:
    pattern_id: str
    stream_ids: List[str]
    relation_ids: List[str]
    resonance: float
    difference: float
    timestep: int
    trace: str


@dataclass
class EmergentPhenomenon:
    phenomenon_id: str
    stream_ids: List[str]
    relation_ids: List[str]
    qualities: Dict[str, float]
    timestep: int
    description: str


@dataclass
class ProvisionalCut:
    cut_id: str
    phenomenon_ids: List[str]
    included_stream_ids: List[str]
    held_open_stream_ids: List[str]
    relation_ids: List[str]
    apparatus_id: str
    permeability: float
    timestep: int
    basis: str = "relational_participation_without_ranking"
    excluded_stream_ids: List[str] = field(default_factory=list)


@dataclass
class DriftSignal:
    kind: DriftKind
    intensity: float
    evidence: List[str]
    detected_at: int
    source: str = "runtime"

    def clamp(self) -> None:
        self.intensity = clamp01(self.intensity)


@dataclass
class CareConstraint:
    operator_name: str
    target: str
    proposed_change: float
    constrained_change: float
    reason: str


@dataclass
class OperatorDelta:
    operator_name: str
    basis_timestep: int
    stream_participation_changes: Dict[str, float] = field(default_factory=dict)
    relation_updates: Dict[str, Relation] = field(default_factory=dict)
    field_value_changes: Dict[str, float] = field(default_factory=dict)
    proposed_streams: List[Stream] = field(default_factory=list)
    patterns: List[DiffractivePattern] = field(default_factory=list)
    traces: List[str] = field(default_factory=list)


@dataclass
class FieldSnapshot:
    timestep: int
    stream_participation: Dict[str, float]
    relation_values: Dict[str, Tuple[float, float, float]]
    field_values: Dict[str, float]
    phenomenon_ids: List[str]
    cut_id: Optional[str]
    articulation_ids: List[str]


@dataclass
class StepTrace:
    timestep_before: int
    timestep_after: int
    calculation_basis_timestep: int
    operator_order: List[str]
    deltas: List[OperatorDelta]
    care_constraints: List[CareConstraint]
    drift_signals: List[DriftSignal]
    hypotheses: Dict[str, float]
    coactive: bool = True


@dataclass
class ReintegrationTrace:
    drift_kind: DriftKind
    field_value_changes: Dict[str, float]
    stream_participation_changes: Dict[str, float]
    relation_changes: Dict[str, float]
    trace: str


@dataclass
class Articulation:
    articulation_id: str
    text: str
    cut_id: str
    phenomenon_ids: List[str]
    included_stream_ids: List[str]
    held_open_stream_ids: List[str]
    relation_ids: List[str]
    timestep: int
    provisional: bool = True


@dataclass
class HistoryEntry:
    cycle: int
    before: FieldSnapshot
    step_trace: StepTrace
    reintegrations: List[ReintegrationTrace]
    cut_id: Optional[str]
    articulation_id: Optional[str]
    after: FieldSnapshot


@dataclass
class FieldState:
    field_id: str
    apparatus: Apparatus
    field_values: FieldValues
    streams: List[Stream] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)
    patterns: List[DiffractivePattern] = field(default_factory=list)
    phenomena: List[EmergentPhenomenon] = field(default_factory=list)
    current_pattern_ids: List[str] = field(default_factory=list)
    current_phenomenon_ids: List[str] = field(default_factory=list)
    cuts: List[ProvisionalCut] = field(default_factory=list)
    articulations: List[Articulation] = field(default_factory=list)
    active_drifts: List[DriftSignal] = field(default_factory=list)
    pending_drifts: List[DriftSignal] = field(default_factory=list)
    history: List[HistoryEntry] = field(default_factory=list)
    timestep: int = 0

    def stream(self, stream_id: str) -> Optional[Stream]:
        return next((item for item in self.streams if item.stream_id == stream_id), None)

    def relation(self, relation_id: str) -> Optional[Relation]:
        return next((item for item in self.relations if item.relation_id == relation_id), None)

    def phenomenon(self, phenomenon_id: str) -> Optional[EmergentPhenomenon]:
        return next(
            (item for item in self.phenomena if item.phenomenon_id == phenomenon_id),
            None,
        )

    def latest_cut(self) -> Optional[ProvisionalCut]:
        return self.cuts[-1] if self.cuts else None

    def clamp(self) -> None:
        self.field_values.clamp()
        for item in self.streams:
            item.clamp()
        for item in self.relations:
            item.clamp()
        for item in self.active_drifts:
            item.clamp()


@dataclass
class CycleResult:
    trace: StepTrace
    reintegrations: List[ReintegrationTrace]
    cut: Optional[ProvisionalCut]
    articulation: Optional[Articulation]
    reinserted_stream_id: Optional[str]
