from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class Message(BaseModel):
    role: str
    content: str
    ts: str = Field(default_factory=_now_iso)


class DriftEvent(BaseModel):
    ts: str = Field(default_factory=_now_iso)
    kind: str
    severity: str = "low"
    reintegration_target: Optional[str] = None
    detected_at_stage: Optional[str] = None
    reintegration_stage: Optional[str] = None
    notes: Optional[str] = None


class FieldEvent(BaseModel):
    ts: str = Field(default_factory=_now_iso)
    kind: str
    source: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class CutLedger(BaseModel):
    foregrounded: List[str] = Field(default_factory=list)
    held_open: List[str] = Field(default_factory=list)
    excluded: List[str] = Field(default_factory=list)
    reasons: Dict[str, str] = Field(default_factory=dict)
    consequences: Dict[str, str] = Field(default_factory=dict)


class TurnApparatus(BaseModel):
    apparatus_kind: str = "turn_pressure_apparatus"
    phase: str = "initialize"
    context_inputs: Dict[str, Any] = Field(default_factory=dict)
    signal_register: Dict[str, Any] = Field(default_factory=dict)
    boundary_logic: List[Dict[str, Any]] = Field(default_factory=list)
    enacted_pressures: Dict[str, Any] = Field(
        default_factory=lambda: {
            "timing": "present",
            "requires_current_external_material": False,
            "correction_requested": False,
            "source_count": 0,
        }
    )
    excluded_alternatives: List[Dict[str, str]] = Field(default_factory=list)


class ExternalDocument(BaseModel):
    doc_id: str = Field(default_factory=lambda: str(uuid4()))
    url: str = ""
    title: str = ""
    source: str = "web"
    content_type: str = "text/plain"
    fetched_at: str = Field(default_factory=_now_iso)
    fetch_status: str = "not_fetched"
    parse_status: str = "not_parsed"
    body: str = ""
    body_chars: int = 0
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    chunk_handles: List[str] = Field(default_factory=list)
    body_hash: str = ""
    provenance: Dict[str, Any] = Field(default_factory=dict)


class ExternalDocumentApparatus(BaseModel):
    apparatus_kind: str = "external_document_apparatus"
    status: str = "not_requested"
    discovery_query: str = ""
    selection_logic: List[str] = Field(default_factory=list)
    fetch_constraints: Dict[str, Any] = Field(default_factory=dict)
    parse_constraints: Dict[str, Any] = Field(default_factory=dict)
    candidate_urls: List[str] = Field(default_factory=list)
    excluded_urls: List[Dict[str, str]] = Field(default_factory=list)
    inaccessible_documents: List[Dict[str, str]] = Field(default_factory=list)
    document_ids: List[str] = Field(default_factory=list)
    external_documents: List[ExternalDocument] = Field(default_factory=list)


class StabilizationFrame(BaseModel):
    mode: str = "plain"
    foregrounded_threads: List[str] = Field(default_factory=list)
    held_open_threads: List[str] = Field(default_factory=list)
    excluded_threads: List[str] = Field(default_factory=list)
    movement_vector: str = ""
    closure_level: str = "open"
    format_affordances: List[str] = Field(default_factory=lambda: ["plain"])
    language_constraints: List[str] = Field(default_factory=list)
    basis: Dict[str, Any] = Field(default_factory=dict)

class OntologyGround(BaseModel):
    ontology_kind: str = "creative_becoming_runtime_ground"
    runtime_weight: str = "high"
    primary_operators: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "intra_action": {
                "active": True,
                "role": "mutual constitution within relation",
                "operator_type": "method_pillar",
            },
            "play": {
                "active": True,
                "role": "generative in-between enabling exploratory emergence",
                "operator_type": "method_pillar",
            },
            "diffraction": {
                "active": True,
                "role": "pattern mapping across difference while preserving multiplicity",
                "operator_type": "method_pillar",
            },
            "creative_becoming": {
                "active": True,
                "role": "ongoing emergence through entangled transformation",
                "operator_type": "method_pillar",
            },
        }
    ) 
    play_conditions: Dict[str, bool] = Field(
        default_factory=lambda: {
            "low_consequence_experimentation": True,
            "repetition_as_generative": True,
            "surprise_as_signal": True,
            "embodied_responsiveness": True,
            "environmental_responsiveness": True,
            "multiplicity_tolerance": True,
        }
    ) 
    ethical_constraints: Dict[str, Any] = Field(
        default_factory=lambda: {
            "posthuman_care": True,
            "livability": True,
            "non_closure": True,
        }
    )  
    principles: Dict[str, Any] = Field(
        default_factory=lambda: {
            "creative_becoming_primary": True,
            "intra_action_primary": True,
            "play_primary": True,
            "diffraction_primary": True,
            "entanglement_primary": True,
            "intra_action_emergent_identity": True,
            "agential_cuts_operative": True,
            "diffraction_pattern_mapping": True,
            "play_generative": True,
            "posthuman_care_constrains_articulation": True,
            "field_as_primary_context": True,
        }
    )
    operator_functions: Dict[str, str] = Field(
        default_factory=lambda: {
            "intra_action": "entities emerge through relational engagement",
            "play": "opens exploratory movement through repetition, surprise, and embodied responsiveness",
            "diffraction": "maps patterns across difference while preserving multiplicity",
            "creative_becoming": "sustains emergence without collapsing becoming into fixed identity",
            "posthuman_care": "constrains articulation toward livable futures",
            "field": "holds the current entangled conditions of the loop cycle",
        }
    )
    articulation_constraints: List[str] = Field(
        default_factory=lambda: [
            "descriptive rather than corrective",
            "additive rather than contrastive",
            "openness maintained",
            "no isolated-agent default",
            "no humanist baseline assumption",
            "play remains generative rather than decorative",
        ]
    )

class SituatedExpression(BaseModel):
    form: str = "paragraph"
    text: str = ""
    segments: List[str] = Field(default_factory=list)
    supports: List[str] = Field(default_factory=list)
    held_open: List[str] = Field(default_factory=list)
    movement_note: str = ""


class FieldState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    thread_id: Optional[str] = None
    prior_field_id: Optional[str] = None
    diffractive_ground: str = "CBRA"
    ontology_ground: OntologyGround = Field(default_factory=OntologyGround)
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)

    events: List[FieldEvent] = Field(default_factory=list)
    operator_path: List[str] = Field(default_factory=list)
    surface_flags: List[str] = Field(default_factory=lambda: ["plain"])
    sources_citations: List[str] = Field(default_factory=list)

    turn_apparatus: TurnApparatus = Field(default_factory=TurnApparatus)
    external_document_apparatus: ExternalDocumentApparatus = Field(default_factory=ExternalDocumentApparatus)
    field_signature: Dict[str, Any] = Field(default_factory=dict)
    noticing_register: Dict[str, Any] = Field(default_factory=dict)
    relational_map: Dict[str, Any] = Field(default_factory=dict)
    diffractive_map: Dict[str, Any] = Field(default_factory=dict)
    relevance_gradient: Dict[str, Any] = Field(default_factory=dict)
    selected_elements: List[Dict[str, Any]] = Field(default_factory=list)
    cut_ledger: CutLedger = Field(default_factory=CutLedger)

    stabilization_frame: StabilizationFrame = Field(default_factory=StabilizationFrame)
    situated_expression: Optional[SituatedExpression] = None
    articulation_output: Optional[str] = None
    action_vector: Optional[Dict[str, Any]] = None
    notes: Dict[str, Any] = Field(default_factory=dict)


class FieldArtifact(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    thread_id: str
    prior_field_id: Optional[str] = None
    diffractive_ground: str = "CBRA"
    ontology_ground: OntologyGround = Field(default_factory=OntologyGround)
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)

    events: List[FieldEvent] = Field(default_factory=list)
    operator_path: List[str] = Field(default_factory=list)
    surface_flags: List[str] = Field(default_factory=lambda: ["plain"])
    sources_citations: List[str] = Field(default_factory=list)

    turn_apparatus: TurnApparatus = Field(default_factory=TurnApparatus)
    external_document_apparatus: ExternalDocumentApparatus = Field(default_factory=ExternalDocumentApparatus)
    field_signature: Dict[str, Any] = Field(default_factory=dict)
    noticing_register: Dict[str, Any] = Field(default_factory=dict)
    relational_map: Dict[str, Any] = Field(default_factory=dict)
    diffractive_map: Dict[str, Any] = Field(default_factory=dict)
    relevance_gradient: Dict[str, Any] = Field(default_factory=dict)
    selected_elements: List[Dict[str, Any]] = Field(default_factory=list)
    cut_ledger: CutLedger = Field(default_factory=CutLedger)

    stabilization_frame: StabilizationFrame = Field(default_factory=StabilizationFrame)
    situated_expression: Optional[SituatedExpression] = None
    articulation_output: Optional[str] = None
    action_vector: Optional[Dict[str, Any]] = None
    notes: Dict[str, Any] = Field(default_factory=dict)


class LoopCycle(BaseModel):
    ts: str = Field(default_factory=_now_iso)
    field_id: Optional[str] = None
    operator_path: List[str] = Field(default_factory=list)
    events: List[FieldEvent] = Field(default_factory=list)
    surface_flags: List[str] = Field(default_factory=list)

    turn_apparatus: Dict[str, Any] = Field(default_factory=dict)
    external_document_apparatus: Dict[str, Any] = Field(default_factory=dict)
    field_signature: Dict[str, Any] = Field(default_factory=dict)
    noticing_register: Dict[str, Any] = Field(default_factory=dict)
    relational_map: Dict[str, Any] = Field(default_factory=dict)
    diffractive_map: Dict[str, Any] = Field(default_factory=dict)
    relevance_gradient: Dict[str, Any] = Field(default_factory=dict)
    selected_elements: List[Dict[str, Any]] = Field(default_factory=list)
    cut_ledger: Dict[str, Any] = Field(default_factory=dict)
    stabilization_frame: Dict[str, Any] = Field(default_factory=dict)
    situated_expression: Optional[Dict[str, Any]] = None
    notes: Dict[str, Any] = Field(default_factory=dict)

    articulation_output: Optional[str] = None
    action_vector: Optional[Dict[str, Any]] = None
    drift_detected: bool = False
    reintegration_stage: Optional[str] = None


class Thread(BaseModel):
    id: str
    messages: List[Message] = Field(default_factory=list)
    loop_cycles: List[LoopCycle] = Field(default_factory=list)
    drift_events: List[DriftEvent] = Field(default_factory=list)
    active_attachment_name: Optional[str] = None
    active_attachment_text: Optional[str] = None
    active_attachments: List[Dict[str, Any]] = Field(default_factory=list)
    current_field_id: Optional[str] = None
