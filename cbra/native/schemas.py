"""Versioned boundary schemas for architecture-native CBRA state.

The Pydantic models in this module validate data at the serialization edge.
They deliberately mirror, rather than replace, the live dataclasses in
``cbra.native.models``.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from pydantic import (
    BaseModel,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
)

try:
    from pydantic import ConfigDict
except ImportError:  # Pydantic 1
    ConfigDict = None

from .models import (
    Apparatus,
    Articulation,
    ArticulationBasis,
    ArticulationCandidate,
    ArticulationEvaluation,
    ArticulationFormation,
    ArticulationMaterial,
    CareConstraint,
    CyclePhase,
    DiffractivePattern,
    DriftKind,
    DriftSignal,
    EmergentPhenomenon,
    FieldSnapshot,
    FieldState,
    FieldValues,
    HistoryEntry,
    OperatorDelta,
    PhaseSnapshot,
    ProvisionalCut,
    ReentryTarget,
    ReintegrationTrace,
    Relation,
    StepTrace,
    Stream,
)
from .session_models import (
    NativeSession,
    ReintegrationReference,
    TurnOutcomeKind,
    TurnRecord,
)


SCHEMA_VERSION = 1
CHECKPOINT_PAYLOAD_TYPE = "native_field_checkpoint"
TRACE_PAYLOAD_TYPE = "native_lifecycle_trace"
SESSION_PAYLOAD_TYPE = "native_thread_session"


def assert_json_compatible(value: Any, path: str = "value") -> None:
    """Reject values that canonical JSON cannot preserve without coercion."""
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("{0} contains a non-finite float".format(path))
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            assert_json_compatible(
                item,
                "{0}[{1}]".format(path, index),
            )
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(
                    "{0} contains a non-string object key".format(path)
                )
            assert_json_compatible(
                item,
                "{0}.{1}".format(path, key),
            )
        return
    raise ValueError(
        "{0} contains non-JSON-compatible type {1}".format(
            path,
            type(value).__name__,
        )
    )


def model_validate(model_type, value):
    """Validate with Pydantic 1 or 2 without weakening the schema."""
    if hasattr(model_type, "model_validate"):
        return model_type.model_validate(value)
    return model_type.parse_obj(value)


def model_dump(model: BaseModel) -> Dict[str, Any]:
    """Return Python data with Pydantic 1 or 2."""
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="python")
    return model.dict()


if hasattr(BaseModel, "model_validate"):

    class BoundaryModel(BaseModel):
        """Closed, immutable schema used only at a persistence boundary."""

        model_config = ConfigDict(extra="forbid", frozen=True)

else:

    class BoundaryModel(BaseModel):
        """Closed, immutable schema used only at a persistence boundary."""

        class Config:
            extra = "forbid"
            allow_mutation = False


class StreamSchema(BoundaryModel):
    stream_id: StrictStr
    kind: StrictStr
    participation: StrictFloat
    persistence: StrictFloat
    payload: Dict[StrictStr, Any]
    active: StrictBool
    provenance: Dict[StrictStr, Any]

    @classmethod
    def from_native(cls, item: Stream) -> "StreamSchema":
        assert_json_compatible(
            item.payload,
            "stream {0} payload".format(item.stream_id),
        )
        assert_json_compatible(
            item.provenance,
            "stream {0} provenance".format(item.stream_id),
        )
        return cls(
            stream_id=item.stream_id,
            kind=item.kind,
            participation=item.participation,
            persistence=item.persistence,
            payload=item.payload,
            active=item.active,
            provenance=item.provenance,
        )

    def to_native(self) -> Stream:
        return Stream(
            stream_id=self.stream_id,
            kind=self.kind,
            participation=self.participation,
            persistence=self.persistence,
            payload=dict(self.payload),
            active=self.active,
            provenance=dict(self.provenance),
        )


class RelationSchema(BoundaryModel):
    relation_id: StrictStr
    left_id: StrictStr
    right_id: StrictStr
    co_presence: StrictFloat
    resonance: StrictFloat
    difference: StrictFloat
    interference: StrictFloat
    lineage: StrictFloat
    mutuality: StrictFloat
    apparatus_effect: StrictFloat
    active: StrictBool
    traces: List[StrictStr]

    @classmethod
    def from_native(cls, item: Relation) -> "RelationSchema":
        return cls(**item.__dict__)

    def to_native(self) -> Relation:
        return Relation(**model_dump(self))


class ApparatusSchema(BoundaryModel):
    apparatus_id: StrictStr
    framing: StrictStr
    medium: StrictStr
    prompts: List[StrictStr]
    interfaces: List[StrictStr]
    categories: List[StrictStr]
    tools: List[StrictStr]
    models: List[StrictStr]
    institutions: List[StrictStr]
    constraints: List[StrictStr]
    temporal_pressures: List[StrictStr]

    @classmethod
    def from_native(cls, item: Apparatus) -> "ApparatusSchema":
        return cls(**item.__dict__)

    def to_native(self) -> Apparatus:
        return Apparatus(**model_dump(self))


class FieldValuesSchema(BoundaryModel):
    openness: StrictFloat
    multiplicity: StrictFloat
    difference_activity: StrictFloat
    relational_intensity: StrictFloat
    emergence_level: StrictFloat
    coherence: StrictFloat
    cut_pressure: StrictFloat
    cut_permeability: StrictFloat
    care_capacity: StrictFloat
    care_tension: StrictFloat
    drift_load: StrictFloat

    @classmethod
    def from_native(cls, item: FieldValues) -> "FieldValuesSchema":
        return cls(**item.as_dict())

    def to_native(self) -> FieldValues:
        return FieldValues(**model_dump(self))


class DiffractivePatternSchema(BoundaryModel):
    pattern_id: StrictStr
    stream_ids: List[StrictStr]
    relation_ids: List[StrictStr]
    resonance: StrictFloat
    difference: StrictFloat
    timestep: StrictInt
    trace: StrictStr

    @classmethod
    def from_native(
        cls,
        item: DiffractivePattern,
    ) -> "DiffractivePatternSchema":
        return cls(**item.__dict__)

    def to_native(self) -> DiffractivePattern:
        return DiffractivePattern(**model_dump(self))


class EmergentPhenomenonSchema(BoundaryModel):
    phenomenon_id: StrictStr
    stream_ids: List[StrictStr]
    relation_ids: List[StrictStr]
    qualities: Dict[StrictStr, StrictFloat]
    timestep: StrictInt
    description: StrictStr

    @classmethod
    def from_native(
        cls,
        item: EmergentPhenomenon,
    ) -> "EmergentPhenomenonSchema":
        return cls(**item.__dict__)

    def to_native(self) -> EmergentPhenomenon:
        return EmergentPhenomenon(**model_dump(self))


class ProvisionalCutSchema(BoundaryModel):
    cut_id: StrictStr
    phenomenon_ids: List[StrictStr]
    included_stream_ids: List[StrictStr]
    held_open_stream_ids: List[StrictStr]
    relation_ids: List[StrictStr]
    apparatus_id: StrictStr
    permeability: StrictFloat
    timestep: StrictInt
    basis: StrictStr
    excluded_stream_ids: List[StrictStr]

    @classmethod
    def from_native(cls, item: ProvisionalCut) -> "ProvisionalCutSchema":
        return cls(**item.__dict__)

    def to_native(self) -> ProvisionalCut:
        return ProvisionalCut(**model_dump(self))


class DriftSignalSchema(BoundaryModel):
    kind: DriftKind
    intensity: StrictFloat
    evidence: List[StrictStr]
    detected_at: StrictInt
    source: StrictStr

    @classmethod
    def from_native(cls, item: DriftSignal) -> "DriftSignalSchema":
        return cls(
            kind=item.kind,
            intensity=item.intensity,
            evidence=item.evidence,
            detected_at=item.detected_at,
            source=item.source,
        )

    def to_native(self) -> DriftSignal:
        return DriftSignal(
            kind=self.kind,
            intensity=self.intensity,
            evidence=list(self.evidence),
            detected_at=self.detected_at,
            source=self.source,
        )


class CareConstraintSchema(BoundaryModel):
    operator_name: StrictStr
    target: StrictStr
    proposed_change: StrictFloat
    constrained_change: StrictFloat
    reason: StrictStr

    @classmethod
    def from_native(
        cls,
        item: CareConstraint,
    ) -> "CareConstraintSchema":
        return cls(**item.__dict__)

    def to_native(self) -> CareConstraint:
        return CareConstraint(**model_dump(self))


class OperatorDeltaSchema(BoundaryModel):
    operator_name: StrictStr
    basis_timestep: StrictInt
    stream_participation_changes: Dict[StrictStr, StrictFloat]
    relation_updates: Dict[StrictStr, RelationSchema]
    field_value_changes: Dict[StrictStr, StrictFloat]
    proposed_streams: List[StreamSchema]
    patterns: List[DiffractivePatternSchema]
    traces: List[StrictStr]

    @classmethod
    def from_native(cls, item: OperatorDelta) -> "OperatorDeltaSchema":
        return cls(
            operator_name=item.operator_name,
            basis_timestep=item.basis_timestep,
            stream_participation_changes=item.stream_participation_changes,
            relation_updates={
                key: RelationSchema.from_native(value)
                for key, value in item.relation_updates.items()
            },
            field_value_changes=item.field_value_changes,
            proposed_streams=[
                StreamSchema.from_native(value)
                for value in item.proposed_streams
            ],
            patterns=[
                DiffractivePatternSchema.from_native(value)
                for value in item.patterns
            ],
            traces=item.traces,
        )

    def to_native(self) -> OperatorDelta:
        return OperatorDelta(
            operator_name=self.operator_name,
            basis_timestep=self.basis_timestep,
            stream_participation_changes=dict(
                self.stream_participation_changes
            ),
            relation_updates={
                key: value.to_native()
                for key, value in self.relation_updates.items()
            },
            field_value_changes=dict(self.field_value_changes),
            proposed_streams=[
                value.to_native() for value in self.proposed_streams
            ],
            patterns=[value.to_native() for value in self.patterns],
            traces=list(self.traces),
        )


class StepTraceSchema(BoundaryModel):
    timestep_before: StrictInt
    timestep_after: StrictInt
    calculation_basis_timestep: StrictInt
    operator_order: List[StrictStr]
    deltas: List[OperatorDeltaSchema]
    care_constraints: List[CareConstraintSchema]
    drift_signals: List[DriftSignalSchema]
    hypotheses: Dict[StrictStr, StrictFloat]
    reentry_targets_applied: List[ReentryTarget]
    coactive: StrictBool

    @classmethod
    def from_native(cls, item: StepTrace) -> "StepTraceSchema":
        return cls(
            timestep_before=item.timestep_before,
            timestep_after=item.timestep_after,
            calculation_basis_timestep=item.calculation_basis_timestep,
            operator_order=item.operator_order,
            deltas=[
                OperatorDeltaSchema.from_native(value)
                for value in item.deltas
            ],
            care_constraints=[
                CareConstraintSchema.from_native(value)
                for value in item.care_constraints
            ],
            drift_signals=[
                DriftSignalSchema.from_native(value)
                for value in item.drift_signals
            ],
            hypotheses=item.hypotheses,
            reentry_targets_applied=item.reentry_targets_applied,
            coactive=item.coactive,
        )

    def to_native(self) -> StepTrace:
        return StepTrace(
            timestep_before=self.timestep_before,
            timestep_after=self.timestep_after,
            calculation_basis_timestep=self.calculation_basis_timestep,
            operator_order=list(self.operator_order),
            deltas=[value.to_native() for value in self.deltas],
            care_constraints=[
                value.to_native() for value in self.care_constraints
            ],
            drift_signals=[
                value.to_native() for value in self.drift_signals
            ],
            hypotheses=dict(self.hypotheses),
            reentry_targets_applied=list(self.reentry_targets_applied),
            coactive=self.coactive,
        )


class ReintegrationTraceSchema(BoundaryModel):
    drift_kind: DriftKind
    reentry_target: ReentryTarget
    signal_intensity: StrictFloat
    signal_evidence: List[StrictStr]
    signal_source: StrictStr
    signal_detected_at: StrictInt
    field_value_changes: Dict[StrictStr, StrictFloat]
    stream_participation_changes: Dict[StrictStr, StrictFloat]
    relation_changes: Dict[StrictStr, StrictFloat]
    invalidated_pattern_ids: List[StrictStr]
    invalidated_phenomenon_ids: List[StrictStr]
    invalidated_cut_id: Optional[StrictStr]
    invalidated_candidate_id: Optional[StrictStr]
    invalidated_evaluation_id: Optional[StrictStr]
    invalidated_articulation_id: Optional[StrictStr]
    target_enactment: StrictStr
    trace: StrictStr

    @classmethod
    def from_native(
        cls,
        item: ReintegrationTrace,
    ) -> "ReintegrationTraceSchema":
        return cls(**item.__dict__)

    def to_native(self) -> ReintegrationTrace:
        return ReintegrationTrace(**model_dump(self))


class ArticulationMaterialSchema(BoundaryModel):
    stream_id: StrictStr
    kind: StrictStr
    text: StrictStr
    source_stream_ids: List[StrictStr]
    provenance: Dict[StrictStr, Any]

    @classmethod
    def from_native(
        cls,
        item: ArticulationMaterial,
    ) -> "ArticulationMaterialSchema":
        assert_json_compatible(
            item.provenance,
            "articulation material {0} provenance".format(item.stream_id),
        )
        return cls(**item.__dict__)

    def to_native(self) -> ArticulationMaterial:
        return ArticulationMaterial(
            stream_id=self.stream_id,
            kind=self.kind,
            text=self.text,
            source_stream_ids=list(self.source_stream_ids),
            provenance=dict(self.provenance),
        )


class ArticulationFormationSchema(BoundaryModel):
    phenomenon_id: StrictStr
    materials: List[ArticulationMaterialSchema]
    relation_ids: List[StrictStr]
    qualities: Dict[StrictStr, StrictFloat]
    apparatus_stream_ids: List[StrictStr]
    prior_articulation_ids: List[StrictStr]
    play_variation_ids: List[StrictStr]

    @classmethod
    def from_native(
        cls,
        item: ArticulationFormation,
    ) -> "ArticulationFormationSchema":
        return cls(
            phenomenon_id=item.phenomenon_id,
            materials=[
                ArticulationMaterialSchema.from_native(value)
                for value in item.materials
            ],
            relation_ids=item.relation_ids,
            qualities=item.qualities,
            apparatus_stream_ids=item.apparatus_stream_ids,
            prior_articulation_ids=item.prior_articulation_ids,
            play_variation_ids=item.play_variation_ids,
        )

    def to_native(self) -> ArticulationFormation:
        return ArticulationFormation(
            phenomenon_id=self.phenomenon_id,
            materials=[value.to_native() for value in self.materials],
            relation_ids=list(self.relation_ids),
            qualities=dict(self.qualities),
            apparatus_stream_ids=list(self.apparatus_stream_ids),
            prior_articulation_ids=list(self.prior_articulation_ids),
            play_variation_ids=list(self.play_variation_ids),
        )


class ArticulationBasisSchema(BoundaryModel):
    cut_id: StrictStr
    apparatus_id: StrictStr
    formations: List[ArticulationFormationSchema]
    held_open_materials: List[ArticulationMaterialSchema]
    included_stream_ids: List[StrictStr]
    held_open_stream_ids: List[StrictStr]
    relation_ids: List[StrictStr]

    @classmethod
    def from_native(
        cls,
        item: ArticulationBasis,
    ) -> "ArticulationBasisSchema":
        return cls(
            cut_id=item.cut_id,
            apparatus_id=item.apparatus_id,
            formations=[
                ArticulationFormationSchema.from_native(value)
                for value in item.formations
            ],
            held_open_materials=[
                ArticulationMaterialSchema.from_native(value)
                for value in item.held_open_materials
            ],
            included_stream_ids=item.included_stream_ids,
            held_open_stream_ids=item.held_open_stream_ids,
            relation_ids=item.relation_ids,
        )

    def to_native(self) -> ArticulationBasis:
        return ArticulationBasis(
            cut_id=self.cut_id,
            apparatus_id=self.apparatus_id,
            formations=[value.to_native() for value in self.formations],
            held_open_materials=[
                value.to_native() for value in self.held_open_materials
            ],
            included_stream_ids=list(self.included_stream_ids),
            held_open_stream_ids=list(self.held_open_stream_ids),
            relation_ids=list(self.relation_ids),
        )


class ArticulationCandidateSchema(BoundaryModel):
    candidate_id: StrictStr
    text: StrictStr
    basis: ArticulationBasisSchema
    timestep: StrictInt

    @classmethod
    def from_native(
        cls,
        item: ArticulationCandidate,
    ) -> "ArticulationCandidateSchema":
        return cls(
            candidate_id=item.candidate_id,
            text=item.text,
            basis=ArticulationBasisSchema.from_native(item.basis),
            timestep=item.timestep,
        )

    def to_native(self) -> ArticulationCandidate:
        return ArticulationCandidate(
            candidate_id=self.candidate_id,
            text=self.text,
            basis=self.basis.to_native(),
            timestep=self.timestep,
        )


class ArticulationEvaluationSchema(BoundaryModel):
    evaluation_id: StrictStr
    candidate_id: StrictStr
    accepted: StrictBool
    drift_signals: List[DriftSignalSchema]
    evidence: List[StrictStr]
    timestep: StrictInt

    @classmethod
    def from_native(
        cls,
        item: ArticulationEvaluation,
    ) -> "ArticulationEvaluationSchema":
        return cls(
            evaluation_id=item.evaluation_id,
            candidate_id=item.candidate_id,
            accepted=item.accepted,
            drift_signals=[
                DriftSignalSchema.from_native(value)
                for value in item.drift_signals
            ],
            evidence=item.evidence,
            timestep=item.timestep,
        )

    def to_native(self) -> ArticulationEvaluation:
        return ArticulationEvaluation(
            evaluation_id=self.evaluation_id,
            candidate_id=self.candidate_id,
            accepted=self.accepted,
            drift_signals=[
                value.to_native() for value in self.drift_signals
            ],
            evidence=list(self.evidence),
            timestep=self.timestep,
        )


class ArticulationSchema(BoundaryModel):
    articulation_id: StrictStr
    candidate_id: StrictStr
    evaluation_id: StrictStr
    text: StrictStr
    cut_id: StrictStr
    phenomenon_ids: List[StrictStr]
    included_stream_ids: List[StrictStr]
    held_open_stream_ids: List[StrictStr]
    relation_ids: List[StrictStr]
    lineage_stream_ids: List[StrictStr]
    timestep: StrictInt
    provisional: StrictBool

    @classmethod
    def from_native(cls, item: Articulation) -> "ArticulationSchema":
        return cls(**item.__dict__)

    def to_native(self) -> Articulation:
        return Articulation(**model_dump(self))


class FieldSnapshotSchema(BoundaryModel):
    field_id: StrictStr
    timestep: StrictInt
    apparatus: ApparatusSchema
    streams: List[StreamSchema]
    relations: List[RelationSchema]
    patterns: List[DiffractivePatternSchema]
    phenomena: List[EmergentPhenomenonSchema]
    cuts: List[ProvisionalCutSchema]
    articulation_candidates: List[ArticulationCandidateSchema]
    articulation_evaluations: List[ArticulationEvaluationSchema]
    articulations: List[ArticulationSchema]
    field_values: Dict[StrictStr, StrictFloat]
    current_pattern_ids: List[StrictStr]
    current_phenomenon_ids: List[StrictStr]
    current_cut_id: Optional[StrictStr]
    current_candidate_id: Optional[StrictStr]
    current_evaluation_id: Optional[StrictStr]
    current_articulation_id: Optional[StrictStr]
    articulation_eligible: StrictBool
    active_drifts: List[DriftSignalSchema]
    pending_drifts: List[DriftSignalSchema]
    pending_reentry_targets: List[ReentryTarget]

    @classmethod
    def from_native(
        cls,
        item: FieldSnapshot,
    ) -> "FieldSnapshotSchema":
        return cls(
            field_id=item.field_id,
            timestep=item.timestep,
            apparatus=ApparatusSchema.from_native(item.apparatus),
            streams=[
                StreamSchema.from_native(value) for value in item.streams
            ],
            relations=[
                RelationSchema.from_native(value)
                for value in item.relations
            ],
            patterns=[
                DiffractivePatternSchema.from_native(value)
                for value in item.patterns
            ],
            phenomena=[
                EmergentPhenomenonSchema.from_native(value)
                for value in item.phenomena
            ],
            cuts=[
                ProvisionalCutSchema.from_native(value)
                for value in item.cuts
            ],
            articulation_candidates=[
                ArticulationCandidateSchema.from_native(value)
                for value in item.articulation_candidates
            ],
            articulation_evaluations=[
                ArticulationEvaluationSchema.from_native(value)
                for value in item.articulation_evaluations
            ],
            articulations=[
                ArticulationSchema.from_native(value)
                for value in item.articulations
            ],
            field_values=item.field_values,
            current_pattern_ids=list(item.current_pattern_ids),
            current_phenomenon_ids=list(item.current_phenomenon_ids),
            current_cut_id=item.current_cut_id,
            current_candidate_id=item.current_candidate_id,
            current_evaluation_id=item.current_evaluation_id,
            current_articulation_id=item.current_articulation_id,
            articulation_eligible=item.articulation_eligible,
            active_drifts=[
                DriftSignalSchema.from_native(value)
                for value in item.active_drifts
            ],
            pending_drifts=[
                DriftSignalSchema.from_native(value)
                for value in item.pending_drifts
            ],
            pending_reentry_targets=list(item.pending_reentry_targets),
        )

    def to_native(self) -> FieldSnapshot:
        return FieldSnapshot(
            field_id=self.field_id,
            timestep=self.timestep,
            apparatus=self.apparatus.to_native(),
            streams=tuple(value.to_native() for value in self.streams),
            relations=tuple(value.to_native() for value in self.relations),
            patterns=tuple(value.to_native() for value in self.patterns),
            phenomena=tuple(value.to_native() for value in self.phenomena),
            cuts=tuple(value.to_native() for value in self.cuts),
            articulation_candidates=tuple(
                value.to_native()
                for value in self.articulation_candidates
            ),
            articulation_evaluations=tuple(
                value.to_native()
                for value in self.articulation_evaluations
            ),
            articulations=tuple(
                value.to_native() for value in self.articulations
            ),
            field_values=dict(self.field_values),
            current_pattern_ids=tuple(self.current_pattern_ids),
            current_phenomenon_ids=tuple(self.current_phenomenon_ids),
            current_cut_id=self.current_cut_id,
            current_candidate_id=self.current_candidate_id,
            current_evaluation_id=self.current_evaluation_id,
            current_articulation_id=self.current_articulation_id,
            articulation_eligible=self.articulation_eligible,
            active_drifts=tuple(
                value.to_native() for value in self.active_drifts
            ),
            pending_drifts=tuple(
                value.to_native() for value in self.pending_drifts
            ),
            pending_reentry_targets=tuple(
                self.pending_reentry_targets
            ),
        )


class PhaseSnapshotSchema(BoundaryModel):
    phase: CyclePhase
    field: FieldSnapshotSchema

    @classmethod
    def from_native(
        cls,
        item: PhaseSnapshot,
    ) -> "PhaseSnapshotSchema":
        return cls(
            phase=item.phase,
            field=FieldSnapshotSchema.from_native(item.field),
        )

    def to_native(self) -> PhaseSnapshot:
        return PhaseSnapshot(
            phase=self.phase,
            field=self.field.to_native(),
        )


class HistoryEntrySchema(BoundaryModel):
    cycle: StrictInt
    phases: List[PhaseSnapshotSchema]
    step_trace: StepTraceSchema
    reintegrations: List[ReintegrationTraceSchema]
    cut_id: Optional[StrictStr]
    candidate_id: Optional[StrictStr]
    evaluation_id: Optional[StrictStr]
    articulation_id: Optional[StrictStr]

    @classmethod
    def from_native(
        cls,
        item: HistoryEntry,
    ) -> "HistoryEntrySchema":
        return cls(
            cycle=item.cycle,
            phases=[
                PhaseSnapshotSchema.from_native(value)
                for value in item.phases
            ],
            step_trace=StepTraceSchema.from_native(item.step_trace),
            reintegrations=[
                ReintegrationTraceSchema.from_native(value)
                for value in item.reintegrations
            ],
            cut_id=item.cut_id,
            candidate_id=item.candidate_id,
            evaluation_id=item.evaluation_id,
            articulation_id=item.articulation_id,
        )

    def to_native(self) -> HistoryEntry:
        return HistoryEntry(
            cycle=self.cycle,
            phases=tuple(value.to_native() for value in self.phases),
            step_trace=self.step_trace.to_native(),
            reintegrations=tuple(
                value.to_native() for value in self.reintegrations
            ),
            cut_id=self.cut_id,
            candidate_id=self.candidate_id,
            evaluation_id=self.evaluation_id,
            articulation_id=self.articulation_id,
        )


class FieldStateSchema(BoundaryModel):
    field_id: StrictStr
    apparatus: ApparatusSchema
    field_values: FieldValuesSchema
    streams: List[StreamSchema]
    relations: List[RelationSchema]
    patterns: List[DiffractivePatternSchema]
    phenomena: List[EmergentPhenomenonSchema]
    current_pattern_ids: List[StrictStr]
    current_phenomenon_ids: List[StrictStr]
    cuts: List[ProvisionalCutSchema]
    articulation_candidates: List[ArticulationCandidateSchema]
    articulation_evaluations: List[ArticulationEvaluationSchema]
    articulations: List[ArticulationSchema]
    current_cut_id: Optional[StrictStr]
    current_candidate_id: Optional[StrictStr]
    current_evaluation_id: Optional[StrictStr]
    current_articulation_id: Optional[StrictStr]
    articulation_eligible: StrictBool
    active_drifts: List[DriftSignalSchema]
    pending_drifts: List[DriftSignalSchema]
    pending_reentry_targets: List[ReentryTarget]
    history: List[HistoryEntrySchema]
    timestep: StrictInt

    @classmethod
    def from_native(cls, item: FieldState) -> "FieldStateSchema":
        return cls(
            field_id=item.field_id,
            apparatus=ApparatusSchema.from_native(item.apparatus),
            field_values=FieldValuesSchema.from_native(item.field_values),
            streams=[
                StreamSchema.from_native(value) for value in item.streams
            ],
            relations=[
                RelationSchema.from_native(value)
                for value in item.relations
            ],
            patterns=[
                DiffractivePatternSchema.from_native(value)
                for value in item.patterns
            ],
            phenomena=[
                EmergentPhenomenonSchema.from_native(value)
                for value in item.phenomena
            ],
            current_pattern_ids=item.current_pattern_ids,
            current_phenomenon_ids=item.current_phenomenon_ids,
            cuts=[
                ProvisionalCutSchema.from_native(value)
                for value in item.cuts
            ],
            articulation_candidates=[
                ArticulationCandidateSchema.from_native(value)
                for value in item.articulation_candidates
            ],
            articulation_evaluations=[
                ArticulationEvaluationSchema.from_native(value)
                for value in item.articulation_evaluations
            ],
            articulations=[
                ArticulationSchema.from_native(value)
                for value in item.articulations
            ],
            current_cut_id=item.current_cut_id,
            current_candidate_id=item.current_candidate_id,
            current_evaluation_id=item.current_evaluation_id,
            current_articulation_id=item.current_articulation_id,
            articulation_eligible=item.articulation_eligible,
            active_drifts=[
                DriftSignalSchema.from_native(value)
                for value in item.active_drifts
            ],
            pending_drifts=[
                DriftSignalSchema.from_native(value)
                for value in item.pending_drifts
            ],
            pending_reentry_targets=item.pending_reentry_targets,
            history=[
                HistoryEntrySchema.from_native(value)
                for value in item.history
            ],
            timestep=item.timestep,
        )

    def to_native(self) -> FieldState:
        return FieldState(
            field_id=self.field_id,
            apparatus=self.apparatus.to_native(),
            field_values=self.field_values.to_native(),
            streams=[value.to_native() for value in self.streams],
            relations=[value.to_native() for value in self.relations],
            patterns=[value.to_native() for value in self.patterns],
            phenomena=[value.to_native() for value in self.phenomena],
            current_pattern_ids=list(self.current_pattern_ids),
            current_phenomenon_ids=list(self.current_phenomenon_ids),
            cuts=[value.to_native() for value in self.cuts],
            articulation_candidates=[
                value.to_native()
                for value in self.articulation_candidates
            ],
            articulation_evaluations=[
                value.to_native()
                for value in self.articulation_evaluations
            ],
            articulations=[
                value.to_native() for value in self.articulations
            ],
            current_cut_id=self.current_cut_id,
            current_candidate_id=self.current_candidate_id,
            current_evaluation_id=self.current_evaluation_id,
            current_articulation_id=self.current_articulation_id,
            articulation_eligible=self.articulation_eligible,
            active_drifts=[
                value.to_native() for value in self.active_drifts
            ],
            pending_drifts=[
                value.to_native() for value in self.pending_drifts
            ],
            pending_reentry_targets=list(self.pending_reentry_targets),
            history=tuple(value.to_native() for value in self.history),
            timestep=self.timestep,
        )


class ReintegrationReferenceSchema(BoundaryModel):
    cycle: StrictInt
    index: StrictInt
    drift_kind: DriftKind
    reentry_target: ReentryTarget

    @classmethod
    def from_native(
        cls,
        item: ReintegrationReference,
    ) -> "ReintegrationReferenceSchema":
        return cls(
            cycle=item.cycle,
            index=item.index,
            drift_kind=item.drift_kind,
            reentry_target=item.reentry_target,
        )

    def to_native(self) -> ReintegrationReference:
        return ReintegrationReference(
            cycle=self.cycle,
            index=self.index,
            drift_kind=self.drift_kind,
            reentry_target=self.reentry_target,
        )


class TurnRecordSchema(BoundaryModel):
    turn_id: StrictStr
    revision: StrictInt
    material_digest: StrictStr
    user_stream_id: StrictStr
    additional_stream_ids: List[StrictStr]
    cycle_start: StrictInt
    cycle_end: StrictInt
    candidate_ids: List[StrictStr]
    evaluation_ids: List[StrictStr]
    articulation_ids: List[StrictStr]
    reintegrations: List[ReintegrationReferenceSchema]
    outcome: TurnOutcomeKind

    @classmethod
    def from_native(cls, item: TurnRecord) -> "TurnRecordSchema":
        return cls(
            turn_id=item.turn_id,
            revision=item.revision,
            material_digest=item.material_digest,
            user_stream_id=item.user_stream_id,
            additional_stream_ids=list(item.additional_stream_ids),
            cycle_start=item.cycle_start,
            cycle_end=item.cycle_end,
            candidate_ids=list(item.candidate_ids),
            evaluation_ids=list(item.evaluation_ids),
            articulation_ids=list(item.articulation_ids),
            reintegrations=[
                ReintegrationReferenceSchema.from_native(value)
                for value in item.reintegrations
            ],
            outcome=item.outcome,
        )

    def to_native(self) -> TurnRecord:
        return TurnRecord(
            turn_id=self.turn_id,
            revision=self.revision,
            material_digest=self.material_digest,
            user_stream_id=self.user_stream_id,
            additional_stream_ids=tuple(self.additional_stream_ids),
            cycle_start=self.cycle_start,
            cycle_end=self.cycle_end,
            candidate_ids=tuple(self.candidate_ids),
            evaluation_ids=tuple(self.evaluation_ids),
            articulation_ids=tuple(self.articulation_ids),
            reintegrations=tuple(
                value.to_native() for value in self.reintegrations
            ),
            outcome=self.outcome,
        )


class NativeSessionSchema(BoundaryModel):
    thread_id: StrictStr
    field_id: StrictStr
    field: FieldStateSchema
    revision: StrictInt
    turns: List[TurnRecordSchema]

    @classmethod
    def from_native(cls, item: NativeSession) -> "NativeSessionSchema":
        return cls(
            thread_id=item.thread_id,
            field_id=item.field_id,
            field=FieldStateSchema.from_native(item.field),
            revision=item.revision,
            turns=[
                TurnRecordSchema.from_native(value)
                for value in item.turns
            ],
        )

    def to_native(self) -> NativeSession:
        return NativeSession(
            thread_id=self.thread_id,
            field_id=self.field_id,
            field=self.field.to_native(),
            revision=self.revision,
            turns=tuple(value.to_native() for value in self.turns),
        )


class TracePayloadSchema(BoundaryModel):
    field_id: StrictStr
    entries: List[HistoryEntrySchema]


class IntegritySchema(BoundaryModel):
    algorithm: StrictStr
    payload_sha256: StrictStr


class CheckpointEnvelopeSchema(BoundaryModel):
    schema_version: StrictInt
    payload_type: StrictStr
    integrity: IntegritySchema
    payload: FieldStateSchema


class TraceEnvelopeSchema(BoundaryModel):
    schema_version: StrictInt
    payload_type: StrictStr
    integrity: IntegritySchema
    payload: TracePayloadSchema


class SessionEnvelopeSchema(BoundaryModel):
    schema_version: StrictInt
    payload_type: StrictStr
    integrity: IntegritySchema
    payload: NativeSessionSchema
