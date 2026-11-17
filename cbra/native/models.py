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


class ReentryTarget(str, Enum):
    FIELD_ENTRY = "Field Entry"
    NOTICING = "Noticing"
    RELATIONAL_FRAMING = "Relational Framing"
    DIFFRACTIVE_MAPPING = "Diffractive Mapping"
    ARTICULATION = "Articulation"


class CyclePhase(str, Enum):
    BEFORE_UPDATE = "before_update"
    AFTER_UPDATE_AND_EMERGENCE = "after_update_and_emergence"
    AFTER_DRIFT_DETECTION = "after_drift_detection"
    AFTER_ARTICULATION_EVALUATION = "after_articulation_evaluation"
    AFTER_REINTEGRATION_OR_ARTICULATION = (
        "after_reintegration_or_articulation"
    )


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
    co_presence: float = 0.0
    resonance: float = 0.0
    difference: float = 0.0
    interference: float = 0.0
    lineage: float = 0.0
    mutuality: float = 0.0
    apparatus_effect: float = 0.0
    active: bool = True
    traces: List[str] = field(default_factory=list)

    def clamp(self) -> None:
        self.co_presence = clamp01(self.co_presence)
        self.resonance = clamp01(self.resonance)
        self.difference = clamp01(self.difference)
        self.interference = clamp01(self.interference)
        self.lineage = clamp01(self.lineage)
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
class StepTrace:
    timestep_before: int
    timestep_after: int
    calculation_basis_timestep: int
    operator_order: List[str]
    deltas: List[OperatorDelta]
    care_constraints: List[CareConstraint]
    drift_signals: List[DriftSignal]
    hypotheses: Dict[str, float]
    reentry_targets_applied: List[ReentryTarget] = field(default_factory=list)
    coactive: bool = True


@dataclass
class ReintegrationTrace:
    drift_kind: DriftKind
    reentry_target: ReentryTarget
    signal_intensity: float
    signal_evidence: List[str]
    signal_source: str
    signal_detected_at: int
    field_value_changes: Dict[str, float]
    stream_participation_changes: Dict[str, float]
    relation_changes: Dict[str, float]
    invalidated_pattern_ids: List[str]
    invalidated_phenomenon_ids: List[str]
    invalidated_cut_id: Optional[str]
    invalidated_candidate_id: Optional[str]
    invalidated_evaluation_id: Optional[str]
    invalidated_articulation_id: Optional[str]
    target_enactment: str
    trace: str


@dataclass
class ArticulationMaterial:
    """One stream's non-ranked place in an articulation basis."""

    stream_id: str
    kind: str
    text: str
    source_stream_ids: List[str]
    provenance: Dict[str, Any]


@dataclass
class ArticulationFormation:
    """One current phenomenon preserved as a distinct expressive formation."""

    phenomenon_id: str
    materials: List[ArticulationMaterial]
    relation_ids: List[str]
    qualities: Dict[str, float]
    apparatus_stream_ids: List[str]
    prior_articulation_ids: List[str]
    play_variation_ids: List[str]


@dataclass
class ArticulationBasis:
    """Structured field material from which a candidate is rendered."""

    cut_id: str
    apparatus_id: str
    formations: List[ArticulationFormation]
    held_open_materials: List[ArticulationMaterial]
    included_stream_ids: List[str]
    held_open_stream_ids: List[str]
    relation_ids: List[str]


@dataclass
class ArticulationCandidate:
    candidate_id: str
    text: str
    basis: ArticulationBasis
    timestep: int


@dataclass
class ArticulationEvaluation:
    evaluation_id: str
    candidate_id: str
    accepted: bool
    drift_signals: List[DriftSignal]
    evidence: List[str]
    timestep: int


@dataclass
class Articulation:
    articulation_id: str
    candidate_id: str
    evaluation_id: str
    text: str
    cut_id: str
    phenomenon_ids: List[str]
    included_stream_ids: List[str]
    held_open_stream_ids: List[str]
    relation_ids: List[str]
    lineage_stream_ids: List[str]
    timestep: int
    provisional: bool = True


@dataclass(frozen=True)
class FieldSnapshot:
    """A complete nonrecursive copy of the field at one lifecycle phase."""

    field_id: str
    timestep: int
    apparatus: Apparatus
    streams: Tuple[Stream, ...]
    relations: Tuple[Relation, ...]
    patterns: Tuple[DiffractivePattern, ...]
    phenomena: Tuple[EmergentPhenomenon, ...]
    cuts: Tuple[ProvisionalCut, ...]
    articulation_candidates: Tuple[ArticulationCandidate, ...]
    articulation_evaluations: Tuple[ArticulationEvaluation, ...]
    articulations: Tuple[Articulation, ...]
    field_values: Dict[str, float]
    current_pattern_ids: Tuple[str, ...]
    current_phenomenon_ids: Tuple[str, ...]
    current_cut_id: Optional[str]
    current_candidate_id: Optional[str]
    current_evaluation_id: Optional[str]
    current_articulation_id: Optional[str]
    articulation_eligible: bool
    active_drifts: Tuple[DriftSignal, ...]
    pending_drifts: Tuple[DriftSignal, ...]
    pending_reentry_targets: Tuple[ReentryTarget, ...]

    @property
    def stream_participation(self) -> Dict[str, float]:
        return {
            item.stream_id: item.participation for item in self.streams
        }

    @property
    def relation_values(
        self,
    ) -> Dict[str, Tuple[float, float, float, float, float, float, float]]:
        return {
            item.relation_id: (
                item.co_presence,
                item.resonance,
                item.difference,
                item.interference,
                item.lineage,
                item.mutuality,
                item.apparatus_effect,
            )
            for item in self.relations
        }

    @property
    def phenomenon_ids(self) -> List[str]:
        return list(self.current_phenomenon_ids)

    @property
    def cut_id(self) -> Optional[str]:
        return self.current_cut_id

    @property
    def articulation_ids(self) -> List[str]:
        return [item.articulation_id for item in self.articulations]


@dataclass(frozen=True)
class PhaseSnapshot:
    phase: CyclePhase
    field: FieldSnapshot


@dataclass(frozen=True)
class HistoryEntry:
    cycle: int
    phases: Tuple[PhaseSnapshot, ...]
    step_trace: StepTrace
    reintegrations: Tuple[ReintegrationTrace, ...]
    cut_id: Optional[str]
    candidate_id: Optional[str]
    evaluation_id: Optional[str]
    articulation_id: Optional[str]

    def snapshot_at(self, phase: CyclePhase) -> FieldSnapshot:
        for item in self.phases:
            if item.phase == phase:
                return item.field
        raise KeyError("Cycle phase was not recorded: {0}".format(phase.value))

    @property
    def before(self) -> FieldSnapshot:
        return self.snapshot_at(CyclePhase.BEFORE_UPDATE)

    @property
    def after_update_and_emergence(self) -> FieldSnapshot:
        return self.snapshot_at(CyclePhase.AFTER_UPDATE_AND_EMERGENCE)

    @property
    def after_drift_detection(self) -> FieldSnapshot:
        return self.snapshot_at(CyclePhase.AFTER_DRIFT_DETECTION)

    @property
    def after_articulation_evaluation(self) -> FieldSnapshot:
        return self.snapshot_at(CyclePhase.AFTER_ARTICULATION_EVALUATION)

    @property
    def after(self) -> FieldSnapshot:
        return self.snapshot_at(
            CyclePhase.AFTER_REINTEGRATION_OR_ARTICULATION
        )


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
    articulation_candidates: List[ArticulationCandidate] = field(
        default_factory=list
    )
    articulation_evaluations: List[ArticulationEvaluation] = field(
        default_factory=list
    )
    articulations: List[Articulation] = field(default_factory=list)
    current_cut_id: Optional[str] = None
    current_candidate_id: Optional[str] = None
    current_evaluation_id: Optional[str] = None
    current_articulation_id: Optional[str] = None
    articulation_eligible: bool = False
    active_drifts: List[DriftSignal] = field(default_factory=list)
    pending_drifts: List[DriftSignal] = field(default_factory=list)
    pending_reentry_targets: List[ReentryTarget] = field(default_factory=list)
    history: Tuple[HistoryEntry, ...] = field(default_factory=tuple)
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

    def current_cut(self) -> Optional[ProvisionalCut]:
        if self.current_cut_id is None:
            return None
        return next(
            (
                item
                for item in self.cuts
                if item.cut_id == self.current_cut_id
            ),
            None,
        )

    def current_articulation(self) -> Optional[Articulation]:
        if self.current_articulation_id is None:
            return None
        return next(
            (
                item
                for item in self.articulations
                if item.articulation_id == self.current_articulation_id
            ),
            None,
        )

    def current_candidate(self) -> Optional[ArticulationCandidate]:
        if self.current_candidate_id is None:
            return None
        return next(
            (
                item
                for item in self.articulation_candidates
                if item.candidate_id == self.current_candidate_id
            ),
            None,
        )

    def current_evaluation(self) -> Optional[ArticulationEvaluation]:
        if self.current_evaluation_id is None:
            return None
        return next(
            (
                item
                for item in self.articulation_evaluations
                if item.evaluation_id == self.current_evaluation_id
            ),
            None,
        )

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
    articulation_candidate: Optional[ArticulationCandidate]
    articulation_evaluation: Optional[ArticulationEvaluation]
    articulation: Optional[Articulation]
    reinserted_stream_id: Optional[str]
