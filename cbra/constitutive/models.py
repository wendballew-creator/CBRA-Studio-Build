"""Traceable products of constitutive phenomenon formation.

These records are not a domain ontology.  They make the apparatus's temporary
cuts inspectable without treating the cut products as pre-existing entities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class FormationStatus(str, Enum):
    FORMATION_INCOMPLETE = "formation_incomplete"
    DISTURBANCE_REENTRY_REQUIRED = "disturbance_reentry_required"
    INTERVENTION_READY_FOR_RESPONSE = "intervention_ready_for_response"
    EFFECT_OBSERVATION_PENDING = "effect_observation_pending"
    FORMATION_RECONFIGURED = "formation_reconfigured"


@dataclass(frozen=True)
class Contribution:
    """Provenance-bearing material before semantic or ontological assignment."""

    contribution_id: str
    text: str
    provenance: Dict[str, Any]
    observed_at: Optional[str] = None
    medium: Optional[str] = None
    transformations: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ApparatusFacet:
    facet_id: str
    description: str
    material_conditions: Tuple[str, ...] = ()
    makes_perceptible: Tuple[str, ...] = ()
    backgrounds: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ApparatusAccount:
    apparatus_id: str
    facets: Tuple[ApparatusFacet, ...]
    known_humanist_tendencies: Tuple[str, ...]
    unavailable_channels: Tuple[str, ...] = ()

    @property
    def facet_ids(self) -> Tuple[str, ...]:
        return tuple(item.facet_id for item in self.facets)


@dataclass(frozen=True)
class Encounter:
    encounter_id: str
    contributions: Tuple[Contribution, ...]
    apparatus: ApparatusAccount
    revision_of: Optional[str] = None

    @property
    def contribution_ids(self) -> Tuple[str, ...]:
        return tuple(item.contribution_id for item in self.contributions)


@dataclass(frozen=True)
class AccountableNoticing:
    noticing_id: str
    became_perceptible: str
    through_apparatus_facets: Tuple[str, ...]
    participating_contribution_ids: Tuple[str, ...]
    not_available: Tuple[str, ...]
    possible_humanist_habits: Tuple[str, ...]
    revision_triggers: Tuple[str, ...]


@dataclass(frozen=True)
class AgentialCut:
    cut_id: str
    temporary_boundary: str
    cut_product: str
    apparatus_conditions: Tuple[str, ...]
    participating_contribution_ids: Tuple[str, ...]
    makes_actionable: Tuple[str, ...]
    exclusions: Tuple[str, ...]
    differential_effects: Tuple[str, ...]
    alternatives_considered: Tuple[str, ...]
    revision_triggers: Tuple[str, ...]
    permeability: str


@dataclass(frozen=True)
class CapacityTrace:
    capacities_made_perceptible: Tuple[str, ...]
    possible_expansions: Tuple[str, ...]
    possible_compressions: Tuple[str, ...]
    response_burdens: Tuple[str, ...]
    evidence_limits: Tuple[str, ...]


@dataclass(frozen=True)
class RelationalConsequence:
    consequence_id: str
    effect: str
    affected_positions: Tuple[str, ...]
    participating_contribution_ids: Tuple[str, ...]
    arrangement_changes: Tuple[str, ...]
    evidence_limits: Tuple[str, ...]


@dataclass(frozen=True)
class HumanistReassertion:
    reassertion_id: str
    drift_family: str
    entered_through: Tuple[str, ...]
    evidence: Tuple[str, ...]
    affected_cut_ids: Tuple[str, ...]
    affected_movements: Tuple[str, ...]
    reconfiguration: Tuple[str, ...]
    unresolved: bool


@dataclass(frozen=True)
class PhenomenonFormation:
    formation_id: str
    encounter_id: str
    provisional_account: str
    noticings: Tuple[AccountableNoticing, ...]
    cuts: Tuple[AgentialCut, ...]
    operative_cut_ids: Tuple[str, ...]
    active_differences: Tuple[str, ...]
    material_discursive_participation: Tuple[str, ...]
    more_than_human_participation: Tuple[str, ...]
    differential_power: Tuple[str, ...]
    consequential_absences: Tuple[str, ...]
    consequences: Tuple[RelationalConsequence, ...]
    capacity: CapacityTrace
    humanist_reassertions: Tuple[HumanistReassertion, ...]
    revision_triggers: Tuple[str, ...]


@dataclass(frozen=True)
class CuriosityEnactment:
    absence: str
    bounded_question: str
    why_consequential: str
    response_burden: str


@dataclass(frozen=True)
class PlayVariation:
    variation_id: str
    arrangement: str
    changes: Tuple[str, ...]
    preserves: Tuple[str, ...]
    anticipated_capacity_effects: Tuple[str, ...]
    consequence_redistribution: Tuple[str, ...]


@dataclass(frozen=True)
class BoundedNextMovement:
    movement_id: str
    options: Tuple[str, ...]
    capacity_fit: str
    response_burden: str
    follow_up_condition: str


@dataclass(frozen=True)
class MovementFormation:
    movement_id: str
    care_reorganizations: Tuple[str, ...]
    sequence_rationale: Tuple[str, ...]
    curiosities: Tuple[CuriosityEnactment, ...]
    play_variations: Tuple[PlayVariation, ...]
    variation_possible: bool
    consequences: Tuple[RelationalConsequence, ...]
    communication_as_infrastructure: Tuple[str, ...]
    bounded_next: BoundedNextMovement
    diffractive_traces: Tuple[str, ...]
    conditions_preserved_open: Tuple[str, ...]


@dataclass(frozen=True)
class ArticulationIntervention:
    intervention_id: str
    text: str
    materialized_cut_ids: Tuple[str, ...]
    materialized_movements: Tuple[str, ...]
    anticipated_capacity_effects: Tuple[str, ...]
    possibilities_opened: Tuple[str, ...]
    possibilities_foreclosed: Tuple[str, ...]
    assumptions: Tuple[str, ...]
    possible_humanist_reassertions: Tuple[str, ...]
    observable_reconfiguration_triggers: Tuple[str, ...]


@dataclass(frozen=True)
class ReleaseReview:
    review_id: str
    status: FormationStatus
    checked_invariants: Tuple[str, ...]
    failures: Tuple[str, ...]
    bounded_claim: str


@dataclass(frozen=True)
class EffectObservation:
    observation_id: str
    text: str
    provenance: Dict[str, Any]
    observed_at: Optional[str] = None


@dataclass(frozen=True)
class ConstitutiveOutcome:
    encounter: Encounter
    formation: PhenomenonFormation
    movement: MovementFormation
    intervention: ArticulationIntervention
    review: ReleaseReview
    status: FormationStatus
    public_text: Optional[str]
    prior_formation_id: Optional[str] = None
    effect_observations: Tuple[EffectObservation, ...] = field(
        default_factory=tuple
    )
