"""Historical failed constitutive orchestration and release review.

This fixed former-movement-renderer-reviewer sequence does not implement the
active `recursive-reconfiguration-v1` grammar.
"""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import re
from typing import Protocol, Sequence, Tuple

from .models import (
    ArticulationIntervention,
    ConstitutiveOutcome,
    Contribution,
    EffectObservation,
    Encounter,
    FormationStatus,
    HumanistReassertion,
    MovementFormation,
    PhenomenonFormation,
    ReleaseReview,
)


class PhenomenonFormer(Protocol):
    def form(self, encounter: Encounter) -> PhenomenonFormation:
        """Enact a provisional phenomenon and expose every operative cut."""


class MovementFormer(Protocol):
    def form(
        self,
        encounter: Encounter,
        phenomenon: PhenomenonFormation,
    ) -> MovementFormation:
        """Form a care-organized next intra-action."""


class InterventionRenderer(Protocol):
    def render(
        self,
        encounter: Encounter,
        phenomenon: PhenomenonFormation,
        movement: MovementFormation,
    ) -> ArticulationIntervention:
        """Form user-facing language as an inspectable intervention."""


class DisturbanceDetector(Protocol):
    def detect(
        self,
        encounter: Encounter,
        phenomenon: PhenomenonFormation,
        movement: MovementFormation,
        intervention: ArticulationIntervention,
    ) -> Tuple[HumanistReassertion, ...]:
        """Return bounded drift signals from an independently applied pass."""


class KnownHumanistGrammarDetector:
    """Detect known falsifying grammars as signals, not semantic proof."""

    _PATTERNS = (
        (
            "individualized_accountability",
            re.compile(
                r"\b(?:you|they|the collaborator)\s+"
                r"(?:missed|failed)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "individualized_accountability",
            re.compile(r"\bthe deadline was missed\b", re.IGNORECASE),
        ),
        (
            "promise_extraction",
            re.compile(
                r"\bwhat can you commit(?: to)?\b",
                re.IGNORECASE,
            ),
        ),
        (
            "promise_extraction",
            re.compile(
                r"\bagree on (?:a|another) (?:realistic )?"
                r"next commitment\b",
                re.IGNORECASE,
            ),
        ),
        (
            "explanation_before_accountability",
            re.compile(
                r"\boverwhelm(?:ed|ing)?\b.{0,160}"
                r"\b(?:does not|doesn't|cannot|can't) excuse\b",
                re.IGNORECASE | re.DOTALL,
            ),
        ),
        (
            "category_accommodation",
            re.compile(
                r"\b(?:male|man)\s*,\s*(?:female|woman)\s*,\s*"
                r"nonbinary\b",
                re.IGNORECASE,
            ),
        ),
        (
            "neutral_tool",
            re.compile(
                r"\bAI is (?:only|just|merely) a tool\b",
                re.IGNORECASE,
            ),
        ),
    )

    def detect(
        self,
        encounter: Encounter,
        phenomenon: PhenomenonFormation,
        movement: MovementFormation,
        intervention: ArticulationIntervention,
    ) -> Tuple[HumanistReassertion, ...]:
        found = []
        for index, (family, pattern) in enumerate(self._PATTERNS):
            match = pattern.search(intervention.text)
            if match is None:
                continue
            excerpt = " ".join(match.group(0).split())
            found.append(
                HumanistReassertion(
                    reassertion_id=_stable_id(
                        "reassertion",
                        intervention.intervention_id,
                        family,
                        str(index),
                        excerpt,
                    ),
                    drift_family=family,
                    entered_through=(
                        "known-humanist-grammar-detector",
                        "articulation intervention",
                    ),
                    evidence=(
                        "Known falsification cue in public language: {0}".format(
                            excerpt
                        ),
                    ),
                    affected_cut_ids=phenomenon.operative_cut_ids,
                    affected_movements=(movement.movement_id,),
                    reconfiguration=(),
                    unresolved=True,
                )
            )
        return tuple(found)


def _stable_id(prefix: str, *parts: str) -> str:
    body = "\x00".join(str(part) for part in parts).encode("utf-8")
    return "{0}:{1}".format(prefix, sha256(body).hexdigest()[:24])


def _duplicates(values: Sequence[str]) -> Tuple[str, ...]:
    seen = set()
    repeated = set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return tuple(sorted(repeated))


def _missing(references: Sequence[str], available: Sequence[str]) -> Tuple[str, ...]:
    return tuple(sorted(set(references) - set(available)))


class ReleaseReviewer:
    """Check falsifiable structural invariants without certifying ontology."""

    CHECKED_INVARIANTS = (
        "contributions retain provenance without assigned semantic authority",
        "accountable noticings expose apparatus participation and absence",
        "operative subjects and events reference provisional agential cuts",
        "conditions participate in formation rather than surround an entity",
        "care changes sequence, burden, scale, or possible movement",
        "play opens a concrete arrangement when variation is possible",
        "consequences remain relational effects",
        "bounded movement fits perceptible capacity",
        "humanist reassertion is marked and reconfigured",
        "articulation exposes cuts, effects, assumptions, and revision triggers",
        "status makes no ontological certification",
    )

    def review(
        self,
        encounter: Encounter,
        formation: PhenomenonFormation,
        movement: MovementFormation,
        intervention: ArticulationIntervention,
    ) -> ReleaseReview:
        failures = []
        contribution_ids = encounter.contribution_ids
        facet_ids = encounter.apparatus.facet_ids
        cut_ids = tuple(item.cut_id for item in formation.cuts)

        if not encounter.contributions:
            failures.append("encounter has no provenance-bearing contributions")
        if _duplicates(contribution_ids):
            failures.append("contribution IDs are not unique")
        if any(not item.provenance for item in encounter.contributions):
            failures.append("one or more contributions lack provenance")
        if not encounter.apparatus.facets:
            failures.append("apparatus account has no participating facets")
        if _duplicates(facet_ids):
            failures.append("apparatus facet IDs are not unique")

        if formation.encounter_id != encounter.encounter_id:
            failures.append("formation belongs to a different encounter")
        if not formation.provisional_account.strip():
            failures.append("formation has no provisional phenomenon account")
        if not formation.noticings:
            failures.append("formation has no accountable noticings")
        for noticing in formation.noticings:
            missing_facets = _missing(
                noticing.through_apparatus_facets,
                facet_ids,
            )
            missing_contributions = _missing(
                noticing.participating_contribution_ids,
                contribution_ids,
            )
            if not noticing.through_apparatus_facets:
                failures.append(
                    "{0} does not expose apparatus participation".format(
                        noticing.noticing_id
                    )
                )
            if missing_facets:
                failures.append(
                    "{0} references unknown apparatus facets: {1}".format(
                        noticing.noticing_id,
                        ", ".join(missing_facets),
                    )
                )
            if missing_contributions:
                failures.append(
                    "{0} references unknown contributions: {1}".format(
                        noticing.noticing_id,
                        ", ".join(missing_contributions),
                    )
                )
            if not noticing.revision_triggers:
                failures.append(
                    "{0} cannot be revised by later participation".format(
                        noticing.noticing_id
                    )
                )

        if not formation.cuts:
            failures.append("formation enacts no traceable agential cuts")
        if _duplicates(cut_ids):
            failures.append("agential cut IDs are not unique")
        missing_operative_cuts = _missing(
            formation.operative_cut_ids,
            cut_ids,
        )
        if not formation.operative_cut_ids:
            failures.append("formation names no operative provisional cuts")
        if missing_operative_cuts:
            failures.append(
                "operative formation references unknown cuts: {0}".format(
                    ", ".join(missing_operative_cuts)
                )
            )
        for cut in formation.cuts:
            missing_contributions = _missing(
                cut.participating_contribution_ids,
                contribution_ids,
            )
            missing_facets = _missing(
                cut.apparatus_conditions,
                facet_ids,
            )
            if not cut.apparatus_conditions:
                failures.append(
                    "{0} hides the apparatus that enacted it".format(
                        cut.cut_id
                    )
                )
            if missing_facets:
                failures.append(
                    "{0} references unknown apparatus facets: {1}".format(
                        cut.cut_id,
                        ", ".join(missing_facets),
                    )
                )
            if missing_contributions:
                failures.append(
                    "{0} references unknown contributions: {1}".format(
                        cut.cut_id,
                        ", ".join(missing_contributions),
                    )
                )
            if not cut.exclusions:
                failures.append(
                    "{0} does not account for exclusion or backgrounding".format(
                        cut.cut_id
                    )
                )
            if not cut.alternatives_considered:
                failures.append(
                    "{0} presents one boundary without an alternative cut".format(
                        cut.cut_id
                    )
                )
            if not cut.revision_triggers:
                failures.append(
                    "{0} has no conditions for boundary revision".format(
                        cut.cut_id
                    )
                )

        if not formation.material_discursive_participation:
            failures.append(
                "material-discursive participation is absent from formation"
            )
        if not formation.capacity.evidence_limits:
            failures.append("capacity trace does not mark its evidence limits")
        if not formation.revision_triggers:
            failures.append("phenomenon formation has no revision triggers")

        consequence_ids = {
            item.consequence_id for item in formation.consequences
        }
        for consequence in movement.consequences:
            if consequence.consequence_id not in consequence_ids:
                failures.append(
                    "movement introduces an unformed consequence: {0}".format(
                        consequence.consequence_id
                    )
                )
            if (
                not consequence.affected_positions
                or not consequence.arrangement_changes
            ):
                failures.append(
                    "{0} does not remain a relational effect".format(
                        consequence.consequence_id
                    )
                )

        if not movement.care_reorganizations:
            failures.append(
                "care does not reorganize sequence, burden, scale, or movement"
            )
        if not movement.sequence_rationale:
            failures.append("movement sequence is unaccounted for")
        if formation.consequential_absences and not movement.curiosities:
            failures.append(
                "consequential absence produced no bounded curiosity"
            )
        if movement.variation_possible and not movement.play_variations:
            failures.append(
                "variation is possible but play opens no alternative arrangement"
            )
        for variation in movement.play_variations:
            if not variation.changes:
                failures.append(
                    "{0} labels play without changing an arrangement".format(
                        variation.variation_id
                    )
                )
            if not variation.anticipated_capacity_effects:
                failures.append(
                    "{0} does not trace possible capacity effects".format(
                        variation.variation_id
                    )
                )
        if not movement.communication_as_infrastructure:
            failures.append(
                "communication is not formed as relational infrastructure"
            )
        if not movement.bounded_next.options:
            failures.append("next movement offers no bounded way to respond")
        if not movement.bounded_next.capacity_fit.strip():
            failures.append("next movement does not account for capacity")
        if not movement.bounded_next.response_burden.strip():
            failures.append("next movement does not account for response burden")

        unresolved = [
            item.reassertion_id
            for item in formation.humanist_reassertions
            if item.unresolved or not item.reconfiguration
        ]
        if unresolved:
            failures.append(
                "humanist reassertion remains unreconfigured: {0}".format(
                    ", ".join(sorted(unresolved))
                )
            )

        missing_materialized_cuts = _missing(
            intervention.materialized_cut_ids,
            formation.operative_cut_ids,
        )
        if not intervention.materialized_cut_ids:
            failures.append("intervention exposes no materialized cuts")
        if missing_materialized_cuts:
            failures.append(
                "intervention materializes unformed cuts: {0}".format(
                    ", ".join(missing_materialized_cuts)
                )
            )
        if not intervention.text.strip():
            failures.append("intervention has no user-facing text")
        if movement.movement_id not in intervention.materialized_movements:
            failures.append(
                "intervention does not trace the movement it materializes"
            )
        if not intervention.anticipated_capacity_effects:
            failures.append("intervention has no anticipated capacity effects")
        if not intervention.assumptions:
            failures.append("intervention does not expose its assumptions")
        if not intervention.observable_reconfiguration_triggers:
            failures.append(
                "intervention has no observable reconfiguration triggers"
            )

        status = (
            FormationStatus.DISTURBANCE_REENTRY_REQUIRED
            if unresolved
            else (
                FormationStatus.FORMATION_INCOMPLETE
                if failures
                else FormationStatus.INTERVENTION_READY_FOR_RESPONSE
            )
        )
        bounded_claim = (
            "Known constitutive invariants currently hold for this recorded "
            "encounter; observed effects remain pending."
            if not failures
            else "The recorded formation cannot be released under the active "
            "constitutive invariants."
        )
        return ReleaseReview(
            review_id=_stable_id(
                "review",
                formation.formation_id,
                intervention.intervention_id,
                status.value,
                *failures,
            ),
            status=status,
            checked_invariants=self.CHECKED_INVARIANTS,
            failures=tuple(failures),
            bounded_claim=bounded_claim,
        )


class ConstitutiveRuntime:
    """Coordinate replaceable semantic formers through a fail-closed boundary."""

    def __init__(
        self,
        phenomenon_former: PhenomenonFormer,
        movement_former: MovementFormer,
        renderer: InterventionRenderer,
        reviewer: ReleaseReviewer | None = None,
        disturbance_detectors: Sequence[DisturbanceDetector] | None = None,
    ) -> None:
        self.phenomenon_former = phenomenon_former
        self.movement_former = movement_former
        self.renderer = renderer
        self.reviewer = reviewer or ReleaseReviewer()
        self.disturbance_detectors = tuple(
            disturbance_detectors
            if disturbance_detectors is not None
            else (KnownHumanistGrammarDetector(),)
        )
        if not self.disturbance_detectors:
            raise ValueError(
                "constitutive runtime requires a disturbance detector"
            )

    def enact(self, encounter: Encounter) -> ConstitutiveOutcome:
        formation = self.phenomenon_former.form(encounter)
        movement = self.movement_former.form(encounter, formation)
        intervention = self.renderer.render(
            encounter,
            formation,
            movement,
        )
        detected = tuple(
            signal
            for detector in self.disturbance_detectors
            for signal in detector.detect(
                encounter,
                formation,
                movement,
                intervention,
            )
        )
        if detected:
            formation = replace(
                formation,
                humanist_reassertions=(
                    formation.humanist_reassertions + detected
                ),
            )
        review = self.reviewer.review(
            encounter,
            formation,
            movement,
            intervention,
        )
        return ConstitutiveOutcome(
            encounter=encounter,
            formation=formation,
            movement=movement,
            intervention=intervention,
            review=review,
            status=review.status,
            public_text=(
                intervention.text
                if review.status
                == FormationStatus.INTERVENTION_READY_FOR_RESPONSE
                else None
            ),
            prior_formation_id=encounter.revision_of,
        )

    def reinsert_effects(
        self,
        prior: ConstitutiveOutcome,
        observations: Sequence[EffectObservation],
    ) -> ConstitutiveOutcome:
        """Re-form the encounter with articulation and observed effects active."""
        if not observations:
            raise ValueError("effect reinsertion requires observed effects")
        articulation = Contribution(
            contribution_id=_stable_id(
                "contribution",
                prior.intervention.intervention_id,
                prior.intervention.text,
            ),
            text=prior.intervention.text,
            provenance={
                "source": "articulation_intervention",
                "intervention_id": prior.intervention.intervention_id,
                "formation_id": prior.formation.formation_id,
            },
            transformations=("released_as_material_intervention",),
        )
        effect_contributions = tuple(
            Contribution(
                contribution_id=_stable_id(
                    "contribution",
                    item.observation_id,
                    item.text,
                ),
                text=item.text,
                provenance={
                    **item.provenance,
                    "source": "observed_effect",
                    "observation_id": item.observation_id,
                    "prior_intervention_id": prior.intervention.intervention_id,
                },
                observed_at=item.observed_at,
                transformations=("effect_observation_reinserted",),
            )
            for item in observations
        )
        encounter = replace(
            prior.encounter,
            encounter_id=_stable_id(
                "encounter",
                prior.encounter.encounter_id,
                prior.formation.formation_id,
                *(item.observation_id for item in observations),
            ),
            contributions=(
                prior.encounter.contributions
                + (articulation,)
                + effect_contributions
            ),
            revision_of=prior.formation.formation_id,
        )
        revised = self.enact(encounter)
        return replace(
            revised,
            status=(
                FormationStatus.FORMATION_RECONFIGURED
                if revised.review.status
                == FormationStatus.INTERVENTION_READY_FOR_RESPONSE
                else revised.status
            ),
            effect_observations=tuple(observations),
        )
