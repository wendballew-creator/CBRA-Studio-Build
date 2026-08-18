"""Dependency-activated proposal participation without a formation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Protocol, Sequence, Tuple

from .formation import (
    AccountableSituatedProposal,
    ApparatusParticipation,
    EvidenceSpan,
    PluralSituatedFormationBoundary,
    PositionGrounding,
    RecordedPluralOriginationAssembly,
    RecordedProposalContribution,
    SituatedCutProposal,
    SituatedFormationBoundary,
    SituatedNoticing,
)
from .substrate import InvalidReconfiguration, ReconfigurationSubstrate
from .models import CutEnactment, CutPosition, Relation, TransportTrace


@dataclass(frozen=True)
class UnresolvedArrivalRelation:
    relation_id: str
    evidence: Tuple[EvidenceSpan, ...]
    became_unresolved: str
    exclusions: Tuple[str, ...]
    revision_conditions: Tuple[str, ...]


@dataclass(frozen=True)
class ProposalParticipationInvitation:
    invitation_id: str
    unresolved_relation_ids: Tuple[str, ...]
    participation: ApparatusParticipation
    difference_opened: str
    limits: Tuple[str, ...]
    deactivation_conditions: Tuple[str, ...]


@dataclass(frozen=True)
class OriginationActivationTrace:
    field_id: str
    unresolved_relation_ids: Tuple[str, ...]
    invitation_ids: Tuple[str, ...]
    answered_invitation_ids: Tuple[str, ...]
    unanswered_invitation_ids: Tuple[str, ...]
    invalidated_invitation_ids: Tuple[str, ...]
    reopened_relation_ids: Tuple[str, ...]
    revision_conditions: Tuple[str, ...]


@dataclass(frozen=True)
class FormationReopeningTrace:
    reopening_id: str
    activation_field_id: str
    activation_contribution_ids: Tuple[str, ...]
    triggering_trace_ids: Tuple[str, ...]
    reopened_relation_ids: Tuple[str, ...]
    invalidated_invitation_ids: Tuple[str, ...]
    invalidated_proposal_ids: Tuple[str, ...]
    invalidated_cut_ids: Tuple[str, ...]
    substrate_delta_id: str | None
    activation_unavailable_or_ungenerated: Tuple[str, ...]
    activation_revision_conditions: Tuple[str, ...]


@dataclass(frozen=True)
class InvitationEvidence:
    trace_id: str
    start: int
    end: int
    payload: bytes


@dataclass(frozen=True)
class ProposalParticipationRequest:
    invitation_id: str
    unresolved_relation_ids: Tuple[str, ...]
    evidence: Tuple[InvitationEvidence, ...]
    participation: ApparatusParticipation
    difference_opened: str
    limits: Tuple[str, ...]
    deactivation_conditions: Tuple[str, ...]


@dataclass(frozen=True)
class ProposalEmissionMaterial:
    channel: str
    payload: bytes
    provenance: Mapping[str, Any]


class ProposalGeneratingParticipant(Protocol):
    def emit(
        self, request: ProposalParticipationRequest
    ) -> ProposalEmissionMaterial: ...


@dataclass(frozen=True)
class ProposedNoticingMaterial:
    noticing_id: str
    evidence: Tuple[EvidenceSpan, ...]
    became_perceptible: str
    unavailable_or_excluded: Tuple[str, ...]
    revision_conditions: Tuple[str, ...]


@dataclass(frozen=True)
class ProposedFormationMaterial:
    cut: CutEnactment
    noticings: Tuple[ProposedNoticingMaterial, ...]
    position_groundings: Tuple[PositionGrounding, ...]
    generative_differences: Tuple[str, ...]


@dataclass(frozen=True)
class FormationTransformationRequest:
    invitation_id: str
    unresolved_relation_ids: Tuple[str, ...]
    arrival_evidence: Tuple[InvitationEvidence, ...]
    emission_evidence: InvitationEvidence
    originating_participation: ApparatusParticipation
    transformation_participation: ApparatusParticipation


class FormationMaterialTransformer(Protocol):
    def transform(
        self, request: FormationTransformationRequest
    ) -> ProposedFormationMaterial: ...


@dataclass(frozen=True)
class FormationChallengeRequest:
    transformation: FormationTransformationRequest
    proposed: ProposedFormationMaterial


@dataclass(frozen=True)
class FormationChallengeMaterial:
    checking_participation: ApparatusParticipation
    counter_positions: Tuple[CutPosition, ...]
    counter_relations: Tuple[Relation, ...]
    counter_position_groundings: Tuple[PositionGrounding, ...]
    complications: Tuple[str, ...]
    additional_exclusions: Tuple[str, ...]
    reopening_conditions: Tuple[str, ...]


class FormationCounterParticipant(Protocol):
    def challenge(
        self, request: FormationChallengeRequest
    ) -> FormationChallengeMaterial: ...


@dataclass(frozen=True)
class RelationMaterialActivationContribution:
    contribution_id: str
    participation: ApparatusParticipation
    triggering_evidence: Tuple[EvidenceSpan, ...]
    unresolved_relation_ids: Tuple[str, ...]
    differences_made: Tuple[str, ...]
    exclusions: Tuple[str, ...]
    revision_conditions: Tuple[str, ...]


class InspectableReopeningActivationAssembly:
    """Accumulate plural accounts of how later material disturbs relations."""

    def __init__(
        self,
        formation: DependencyActivatedOriginationAssembly,
        *,
        field_id: str,
        reopening_id: str,
        unavailable_or_ungenerated: Sequence[str],
        revision_conditions: Sequence[str],
    ) -> None:
        if (
            not field_id
            or not reopening_id
            or not unavailable_or_ungenerated
            or not revision_conditions
        ):
            raise InvalidReconfiguration(
                "reopening activation requires field, reopening, unavailable, and revision material"
            )
        self._formation = formation
        self._field_id = field_id
        self._reopening_id = reopening_id
        self._unavailable_or_ungenerated = tuple(unavailable_or_ungenerated)
        self._revision_conditions = tuple(revision_conditions)
        self._contributions = {}

    @property
    def contributions(self) -> Tuple[RelationMaterialActivationContribution, ...]:
        return tuple(self._contributions.values())

    def record(self, contribution: RelationMaterialActivationContribution) -> None:
        if not isinstance(contribution, RelationMaterialActivationContribution):
            raise InvalidReconfiguration(
                "reopening activation requires a typed contribution"
            )
        if (
            not contribution.contribution_id
            or contribution.contribution_id in self._contributions
        ):
            raise InvalidReconfiguration(
                "reopening activation contribution id must be new and nonempty"
            )
        self._formation._validate_reopening_activation_contribution(contribution)
        signature = PluralSituatedFormationBoundary._apparatus_signature(
            contribution.participation
        )
        if any(
            existing.participation.participation_id
            == contribution.participation.participation_id
            for existing in self._contributions.values()
        ):
            raise InvalidReconfiguration(
                "one participation cannot supply multiple reopening activation contributions"
            )
        if any(
            PluralSituatedFormationBoundary._apparatus_signature(
                existing.participation
            ) == signature
            for existing in self._contributions.values()
        ):
            raise InvalidReconfiguration(
                "reopening activation participations must be materially distinct"
            )
        self._contributions[contribution.contribution_id] = contribution

    def enact(self, *, delta_id: str) -> FormationReopeningTrace:
        if len(self._contributions) < 2:
            raise InvalidReconfiguration(
                "relation-to-material activation requires plural participation"
            )
        relation_use = {}
        for contribution in self._contributions.values():
            for relation_id in contribution.unresolved_relation_ids:
                relation_use.setdefault(relation_id, set()).add(
                    contribution.participation.participation_id
                )
        if any(len(participation_ids) < 2 for participation_ids in relation_use.values()):
            raise InvalidReconfiguration(
                "every reopened relation requires materially plural activation"
            )
        return self._formation._reopen_from_activation(
            field_id=self._field_id,
            reopening_id=self._reopening_id,
            contributions=tuple(self._contributions.values()),
            unavailable_or_ungenerated=self._unavailable_or_ungenerated,
            revision_conditions=self._revision_conditions,
            delta_id=delta_id,
        )


class DependencyActivatedOriginationAssembly:
    """Retain emissions answering plural invitations from unresolved relations."""

    def __init__(
        self,
        substrate: ReconfigurationSubstrate,
        *,
        field_id: str,
        unresolved_relations: Sequence[UnresolvedArrivalRelation],
        invitations: Sequence[ProposalParticipationInvitation],
        unavailable_or_ungenerated: Sequence[str],
        revision_conditions: Sequence[str],
    ) -> None:
        self._substrate = substrate
        self._field_id = field_id
        self._relations = SituatedFormationBoundary._unique_by_id(
            unresolved_relations,
            "relation_id",
            "unresolved arrival relation",
        )
        self._invitations = SituatedFormationBoundary._unique_by_id(
            invitations,
            "invitation_id",
            "proposal participation invitation",
        )
        self._unavailable_or_ungenerated = tuple(unavailable_or_ungenerated)
        self._revision_conditions = tuple(revision_conditions)
        self._answers = {}
        self._invitation_emissions = {
            invitation_id: set() for invitation_id in self._invitations
        }
        self._invalidated_invitation_ids = set()
        self._reopened_relation_ids = set()
        self._reopening_traces = []
        self._validate_activation()

    @property
    def activation_trace(self) -> OriginationActivationTrace:
        invitation_ids = set(self._invitations)
        answered_ids = set(self._answers)
        active_invitation_ids = invitation_ids.difference(
            self._invalidated_invitation_ids
        )
        return OriginationActivationTrace(
            field_id=self._field_id,
            unresolved_relation_ids=tuple(sorted(self._relations)),
            invitation_ids=tuple(sorted(invitation_ids)),
            answered_invitation_ids=tuple(sorted(answered_ids)),
            unanswered_invitation_ids=tuple(
                sorted(active_invitation_ids.difference(answered_ids))
            ),
            invalidated_invitation_ids=tuple(
                sorted(self._invalidated_invitation_ids)
            ),
            reopened_relation_ids=tuple(sorted(self._reopened_relation_ids)),
            revision_conditions=self._revision_conditions,
        )

    @property
    def reopening_traces(self) -> Tuple[FormationReopeningTrace, ...]:
        return tuple(self._reopening_traces)

    def record(
        self,
        *,
        invitation_id: str,
        contribution: RecordedProposalContribution,
    ) -> None:
        invitation = self._invitations.get(invitation_id)
        if invitation is None:
            raise InvalidReconfiguration(
                "proposal contribution must answer an active invitation"
            )
        self._require_active_invitation(invitation_id)
        if invitation_id in self._answers:
            raise InvalidReconfiguration(
                "an invitation cannot be rebound to another proposal contribution"
            )
        if contribution.contribution_id in {
            item.contribution_id for item in self._answers.values()
        }:
            raise InvalidReconfiguration(
                "recorded contribution ids must remain unique across invitations"
            )
        if contribution.proposal.proposal_id in {
            item.proposal.proposal_id for item in self._answers.values()
        }:
            raise InvalidReconfiguration(
                "one proposal cannot answer multiple participation invitations"
            )
        if contribution.originating_participation != invitation.participation:
            raise InvalidReconfiguration(
                "proposal contribution must use the invited apparatus participation"
            )
        emission_trace_ids = {
            span.trace_id for span in contribution.emission_evidence
        }
        if (
            not emission_trace_ids
            or emission_trace_ids.difference(
                self._invitation_emissions[invitation_id]
            )
        ):
            raise InvalidReconfiguration(
                "proposal contribution must use emissions produced for its invitation"
            )
        shared_basis = self._shared_arrival_basis()
        if set(contribution.proposal.formation.cut.transport_basis) != shared_basis:
            raise InvalidReconfiguration(
                "invited proposal must remain grounded in the unresolved arrival basis"
            )
        existing_emission_traces = {
            span.trace_id
            for item in self._answers.values()
            for span in item.emission_evidence
        }
        if existing_emission_traces.intersection(
            span.trace_id for span in contribution.emission_evidence
        ):
            raise InvalidReconfiguration(
                "one proposal emission cannot answer multiple invitations"
            )

        validator = RecordedPluralOriginationAssembly(
            self._substrate,
            field_id=self._field_id,
            opening_conditions=self._opening_conditions(),
            unavailable_or_ungenerated=self._unavailable_or_ungenerated,
            revision_conditions=self._revision_conditions,
        )
        validator.record(contribution)
        self._answers[invitation_id] = contribution

    def invoke(
        self,
        *,
        invitation_id: str,
        participant: ProposalGeneratingParticipant,
        trace_id: str,
        observed_at: str,
    ) -> EvidenceSpan:
        if not trace_id or trace_id in self._substrate.state.transports:
            raise InvalidReconfiguration(
                "invitation emission trace id must be new and nonempty"
            )
        self._require_active_invitation(invitation_id)
        request = self._participation_request(invitation_id)
        emission = participant.emit(request)
        if (
            not isinstance(emission, ProposalEmissionMaterial)
            or not emission.channel
            or not isinstance(emission.payload, bytes)
            or not emission.payload
            or not isinstance(emission.provenance, Mapping)
        ):
            raise InvalidReconfiguration(
                "proposal participant must emit nonempty opaque transport material"
            )
        provenance = dict(emission.provenance)
        provenance.update(
            {
                "invitation_id": invitation_id,
                "unresolved_relation_ids": request.unresolved_relation_ids,
                "arrival_trace_ids": tuple(
                    sorted({evidence.trace_id for evidence in request.evidence})
                ),
            }
        )
        if emission.channel == "model-output":
            required_provenance = {
                "provider",
                "model",
                "effective_configuration",
                "prompt_dependencies",
                "source_dependencies",
                "known_limits",
                "human_centered_training_apparatus",
            }
            if required_provenance.difference(provenance) or any(
                not provenance[key] for key in required_provenance
            ):
                raise InvalidReconfiguration(
                    "model participant must expose its complete apparatus provenance"
                )
            source_dependencies = set(provenance.get("source_dependencies", ()))
            arrival_trace_ids = {
                evidence.trace_id for evidence in request.evidence
            }
            if source_dependencies != arrival_trace_ids:
                raise InvalidReconfiguration(
                    "model emission source dependencies must equal invitation evidence"
                )
        trace = TransportTrace(
            trace_id=trace_id,
            channel=emission.channel,
            digest=sha256(emission.payload).hexdigest(),
            payload=emission.payload,
            observed_at=observed_at,
            provenance=provenance,
        )
        self._substrate.record_transport(trace)
        self._invitation_emissions[invitation_id].add(trace_id)
        return EvidenceSpan(trace_id, 0, len(emission.payload))

    def transform_and_record(
        self,
        *,
        invitation_id: str,
        emission_trace_id: str,
        transformer: FormationMaterialTransformer,
        transformation_participation: ApparatusParticipation,
        counter_participant: FormationCounterParticipant,
        proposal_id: str,
        contribution_id: str,
    ) -> RecordedProposalContribution:
        invitation = self._invitations.get(invitation_id)
        if invitation is None:
            raise InvalidReconfiguration(
                "formation transformation requires an active invitation"
            )
        self._require_active_invitation(invitation_id)
        if emission_trace_id not in self._invitation_emissions[invitation_id]:
            raise InvalidReconfiguration(
                "formation transformation requires emission from its invitation"
            )
        emission_trace = self._substrate.state.transports[emission_trace_id]
        emission_span = EvidenceSpan(
            emission_trace_id, 0, len(emission_trace.payload)
        )
        transformation = FormationTransformationRequest(
            invitation_id=invitation_id,
            unresolved_relation_ids=invitation.unresolved_relation_ids,
            arrival_evidence=self._participation_request(invitation_id).evidence,
            emission_evidence=InvitationEvidence(
                emission_trace_id,
                0,
                len(emission_trace.payload),
                emission_trace.payload,
            ),
            originating_participation=invitation.participation,
            transformation_participation=transformation_participation,
        )
        self._validate_transformation_participation(
            invitation,
            emission_trace_id,
            transformation_participation,
        )
        proposed = transformer.transform(transformation)
        if not isinstance(proposed, ProposedFormationMaterial):
            raise InvalidReconfiguration(
                "formation transformer must return provisional formation material"
            )
        self._validate_proposed_material(proposed)
        challenge = counter_participant.challenge(
            FormationChallengeRequest(transformation, proposed)
        )
        if not isinstance(challenge, FormationChallengeMaterial):
            raise InvalidReconfiguration(
                "counter participant must return formation challenge material"
            )
        self._validate_challenge(invitation, proposed, challenge)

        cut = proposed.cut
        if cut.cut_id != proposal_id:
            raise InvalidReconfiguration(
                "proposal id must equal its cut-local formation id"
            )
        cut = CutEnactment(
            cut_id=cut.cut_id,
            transport_basis=cut.transport_basis,
            dependency_ids=cut.dependency_ids,
            lineage_ids=cut.lineage_ids,
            positions=cut.positions + challenge.counter_positions,
            relations=cut.relations + challenge.counter_relations,
            allocations=cut.allocations,
            revision_conditions=tuple(
                dict.fromkeys(
                    cut.revision_conditions + challenge.reopening_conditions
                )
            ),
            exclusions=tuple(
                dict.fromkeys(cut.exclusions + challenge.additional_exclusions)
            ),
        )
        if (
            PluralSituatedFormationBoundary._apparatus_signature(
                transformation_participation
            )
            == PluralSituatedFormationBoundary._apparatus_signature(
                challenge.checking_participation
            )
        ):
            raise InvalidReconfiguration(
                "formation transformation and checking participation must be distinct"
            )
        apparatus_ids = (
            invitation.participation.participation_id,
            transformation_participation.participation_id,
            challenge.checking_participation.participation_id,
        )
        proposal = AccountableSituatedProposal(
            proposal_id=proposal_id,
            formation=SituatedCutProposal(
                cut=cut,
                apparatus_participations=(
                    invitation.participation,
                    transformation_participation,
                    challenge.checking_participation,
                ),
                noticings=tuple(
                    SituatedNoticing(
                        noticing_id=noticing.noticing_id,
                        evidence=noticing.evidence,
                        apparatus_participation_ids=apparatus_ids,
                        became_perceptible=noticing.became_perceptible,
                        unavailable_or_excluded=tuple(
                            dict.fromkeys(
                                noticing.unavailable_or_excluded
                                + challenge.complications
                            )
                        ),
                        revision_conditions=tuple(
                            dict.fromkeys(
                                noticing.revision_conditions
                                + challenge.reopening_conditions
                            )
                        ),
                    )
                    for noticing in proposed.noticings
                ),
                position_groundings=(
                    proposed.position_groundings
                    + challenge.counter_position_groundings
                ),
            ),
            originating_participation_ids=(
                invitation.participation.participation_id,
            ),
            checking_participation_ids=(
                challenge.checking_participation.participation_id,
            ),
        )
        contribution = RecordedProposalContribution(
            contribution_id=contribution_id,
            proposal=proposal,
            originating_participation=invitation.participation,
            emission_evidence=(emission_span,),
            generative_differences=proposed.generative_differences,
        )
        self.record(invitation_id=invitation_id, contribution=contribution)
        return contribution

    def _validate_reopening_activation_contribution(
        self, contribution: RelationMaterialActivationContribution
    ) -> None:
        if (
            not contribution.triggering_evidence
            or not contribution.unresolved_relation_ids
            or not contribution.differences_made
            or not contribution.exclusions
            or not contribution.revision_conditions
            or any(not item for item in contribution.differences_made)
        ):
            raise InvalidReconfiguration(
                "relation-material activation requires evidence, relations, differences, limits, and revision"
            )
        SituatedFormationBoundary._require_unique_refs(
            contribution.triggering_evidence, "reopening activation evidence"
        )
        SituatedFormationBoundary._require_unique_refs(
            contribution.unresolved_relation_ids,
            "reopening activation unresolved relation",
        )
        SituatedFormationBoundary._require_unique_refs(
            contribution.differences_made, "reopening activation difference"
        )
        if set(contribution.unresolved_relation_ids).difference(self._relations):
            raise InvalidReconfiguration(
                "reopening activation references unknown unresolved relation"
            )
        trace_ids = set()
        for span in contribution.triggering_evidence:
            trace = self._substrate.state.transports.get(span.trace_id)
            if trace is None:
                raise InvalidReconfiguration(
                    "reopening activation references unknown transport"
                )
            if span.start < 0 or span.end <= span.start or span.end > len(trace.payload):
                raise InvalidReconfiguration(
                    "reopening activation requires nonempty exact transport spans"
                )
            trace_ids.add(span.trace_id)
        if trace_ids.intersection(self._shared_arrival_basis()):
            raise InvalidReconfiguration(
                "original arrival evidence cannot masquerade as later disturbance"
            )
        participation = contribution.participation
        if (
            not participation.condition
            or set(participation.trace_ids) != trace_ids
            or not participation.makes_perceptible
            or not participation.obscures_or_excludes
            or not participation.revision_conditions
        ):
            raise InvalidReconfiguration(
                "reopening activation participation must expose its exact later-material apparatus"
            )

    def _reopen_from_activation(
        self,
        *,
        field_id: str,
        reopening_id: str,
        contributions: Sequence[RelationMaterialActivationContribution],
        unavailable_or_ungenerated: Sequence[str],
        revision_conditions: Sequence[str],
        delta_id: str,
    ) -> FormationReopeningTrace:
        if (
            not reopening_id
            or any(trace.reopening_id == reopening_id for trace in self._reopening_traces)
        ):
            raise InvalidReconfiguration(
                "formation reopening id must be new and nonempty"
            )
        if not delta_id:
            raise InvalidReconfiguration(
                "formation reopening delta id must be nonempty"
            )
        if not field_id or not unavailable_or_ungenerated or not revision_conditions:
            raise InvalidReconfiguration(
                "formation reopening requires an inspectable activation field"
            )
        contribution_ids = [item.contribution_id for item in contributions]
        SituatedFormationBoundary._require_unique_refs(
            contribution_ids, "reopening activation contribution"
        )
        triggering_trace_ids = tuple(sorted({
            span.trace_id
            for contribution in contributions
            for span in contribution.triggering_evidence
        }))
        unresolved_relation_ids = tuple(sorted({
            relation_id
            for contribution in contributions
            for relation_id in contribution.unresolved_relation_ids
        }))
        if set(unresolved_relation_ids).intersection(self._reopened_relation_ids):
            raise InvalidReconfiguration(
                "an unresolved relation cannot be reopened twice in one assembly"
            )

        invalidated_invitation_ids = tuple(sorted(self._invitations))
        invalidated_proposal_ids = tuple(
            sorted(answer.proposal.proposal_id for answer in self._answers.values())
        )
        active_cut_ids = set(self._substrate.state.active_cut_ids)
        active_roots = tuple(
            sorted(set(invalidated_proposal_ids).intersection(active_cut_ids))
        )
        delta = None
        if active_roots:
            delta = self._substrate.disturb(
                delta_id=delta_id,
                triggering_trace_ids=tuple(triggering_trace_ids),
                invalidated_root_ids=active_roots,
                replacements=(),
            )

        trace = FormationReopeningTrace(
            reopening_id=reopening_id,
            activation_field_id=field_id,
            activation_contribution_ids=tuple(sorted(contribution_ids)),
            triggering_trace_ids=tuple(sorted(triggering_trace_ids)),
            reopened_relation_ids=tuple(sorted(unresolved_relation_ids)),
            invalidated_invitation_ids=invalidated_invitation_ids,
            invalidated_proposal_ids=invalidated_proposal_ids,
            invalidated_cut_ids=(
                delta.invalidated_cut_ids if delta is not None else ()
            ),
            substrate_delta_id=(delta.delta_id if delta is not None else None),
            activation_unavailable_or_ungenerated=tuple(
                unavailable_or_ungenerated
            ),
            activation_revision_conditions=tuple(revision_conditions),
        )
        self._reopened_relation_ids.update(unresolved_relation_ids)
        self._invalidated_invitation_ids.update(invalidated_invitation_ids)
        self._answers.clear()
        for invitation_id in invalidated_invitation_ids:
            self._invitation_emissions[invitation_id].clear()
        self._reopening_traces.append(trace)
        return trace

    def enact(self, *, delta_id: str):
        if len(self._answers) < 2:
            raise InvalidReconfiguration(
                "activated origination requires answers from multiple invitations"
            )
        answered_invitations = tuple(
            self._invitations[invitation_id] for invitation_id in self._answers
        )
        signatures = {
            PluralSituatedFormationBoundary._apparatus_signature(
                invitation.participation
            )
            for invitation in answered_invitations
        }
        if len(signatures) != len(answered_invitations):
            raise InvalidReconfiguration(
                "answered invitations require materially distinct participation"
            )

        unanswered = tuple(
            "unanswered invitation: " + invitation_id
            for invitation_id in self._invitations
            if invitation_id not in self._answers
        )
        assembly = RecordedPluralOriginationAssembly(
            self._substrate,
            field_id=self._field_id,
            opening_conditions=self._opening_conditions(),
            unavailable_or_ungenerated=(
                self._unavailable_or_ungenerated + unanswered
            ),
            revision_conditions=self._revision_conditions,
        )
        for contribution in self._answers.values():
            assembly.record(contribution)
        return assembly.enact(delta_id=delta_id)

    def _validate_activation(self) -> None:
        if not self._field_id or not self._relations:
            raise InvalidReconfiguration(
                "dependency activation requires an identified field and unresolved relation"
            )
        if len(self._invitations) < 2:
            raise InvalidReconfiguration(
                "an unresolved field must open materially plural participation"
            )
        if not self._unavailable_or_ungenerated or not self._revision_conditions:
            raise InvalidReconfiguration(
                "activated origination must retain unavailable material and revision conditions"
            )

        transport_ids = set(self._substrate.state.transports)
        relation_trace_ids = set()
        for relation in self._relations.values():
            if (
                not relation.evidence
                or not relation.became_unresolved
                or not relation.exclusions
                or not relation.revision_conditions
            ):
                raise InvalidReconfiguration(
                    "unresolved relation requires evidence, limits, and revision conditions"
                )
            SituatedFormationBoundary._require_unique_refs(
                relation.evidence, "unresolved relation evidence"
            )
            for span in relation.evidence:
                trace = self._substrate.state.transports.get(span.trace_id)
                if trace is None:
                    raise InvalidReconfiguration(
                        "unresolved relation references unknown transport"
                    )
                if span.start < 0 or span.end <= span.start or span.end > len(trace.payload):
                    raise InvalidReconfiguration(
                        "unresolved relation requires a nonempty exact transport span"
                    )
                relation_trace_ids.add(span.trace_id)

        activated_relation_ids = set()
        signatures = set()
        for invitation in self._invitations.values():
            if (
                not invitation.unresolved_relation_ids
                or not invitation.difference_opened
                or not invitation.limits
                or not invitation.deactivation_conditions
            ):
                raise InvalidReconfiguration(
                    "participation invitation requires relations, limits, and deactivation conditions"
                )
            SituatedFormationBoundary._require_unique_refs(
                invitation.unresolved_relation_ids,
                "invitation unresolved relation",
            )
            if set(invitation.unresolved_relation_ids).difference(self._relations):
                raise InvalidReconfiguration(
                    "participation invitation references an unknown unresolved relation"
                )
            participation = invitation.participation
            if (
                not participation.condition
                or not participation.trace_ids
                or not participation.makes_perceptible
                or not participation.obscures_or_excludes
                or not participation.revision_conditions
            ):
                raise InvalidReconfiguration(
                    "invited apparatus participation must remain inspectable and revisable"
                )
            if set(participation.trace_ids).difference(transport_ids):
                raise InvalidReconfiguration(
                    "invited apparatus participation references unknown transport"
                )
            invitation_basis = {
                span.trace_id
                for relation_id in invitation.unresolved_relation_ids
                for span in self._relations[relation_id].evidence
            }
            if set(participation.trace_ids) != invitation_basis:
                raise InvalidReconfiguration(
                    "invited participation must arise from its unresolved relation evidence"
                )
            signature = PluralSituatedFormationBoundary._apparatus_signature(
                participation
            )
            if signature in signatures:
                raise InvalidReconfiguration(
                    "participation invitations must be materially distinct"
                )
            signatures.add(signature)
            activated_relation_ids.update(invitation.unresolved_relation_ids)

        if activated_relation_ids != set(self._relations):
            raise InvalidReconfiguration(
                "every unresolved relation must activate proposal participation"
            )
        if not relation_trace_ids:
            raise InvalidReconfiguration(
                "dependency activation requires arrival transport evidence"
            )

    def _validate_proposed_material(
        self, proposed: ProposedFormationMaterial
    ) -> None:
        if (
            not proposed.noticings
            or not proposed.position_groundings
            or not proposed.generative_differences
            or any(not item for item in proposed.generative_differences)
        ):
            raise InvalidReconfiguration(
                "provisional formation requires noticings, groundings, and differences"
            )
        SituatedFormationBoundary._require_unique_refs(
            proposed.generative_differences,
            "provisional generative difference",
        )
        if set(proposed.cut.transport_basis) != self._shared_arrival_basis():
            raise InvalidReconfiguration(
                "provisional cut must remain grounded in unresolved arrival material"
            )
        for noticing in proposed.noticings:
            if (
                not noticing.noticing_id
                or not noticing.evidence
                or not noticing.became_perceptible
                or not noticing.unavailable_or_excluded
                or not noticing.revision_conditions
            ):
                raise InvalidReconfiguration(
                    "provisional noticing must expose evidence, limits, and revision"
                )

    def _validate_transformation_participation(
        self,
        invitation: ProposalParticipationInvitation,
        emission_trace_id: str,
        participation: ApparatusParticipation,
    ) -> None:
        expected_basis = set(invitation.participation.trace_ids).union(
            {emission_trace_id}
        )
        if (
            not participation.condition
            or set(participation.trace_ids) != expected_basis
            or not participation.makes_perceptible
            or not participation.obscures_or_excludes
            or not participation.revision_conditions
        ):
            raise InvalidReconfiguration(
                "formation transformation apparatus must expose arrival and emission participation"
            )
        if (
            PluralSituatedFormationBoundary._apparatus_signature(participation)
            == PluralSituatedFormationBoundary._apparatus_signature(
                invitation.participation
            )
        ):
            raise InvalidReconfiguration(
                "formation transformation must differ from proposal origination"
            )

    @staticmethod
    def _validate_challenge(
        invitation: ProposalParticipationInvitation,
        proposed: ProposedFormationMaterial,
        challenge: FormationChallengeMaterial,
    ) -> None:
        if (
            not challenge.counter_positions
            or not challenge.counter_relations
            or not challenge.counter_position_groundings
            or not challenge.complications
            or not challenge.additional_exclusions
            or not challenge.reopening_conditions
        ):
            raise InvalidReconfiguration(
                "formation challenge must add counter-positions and relations"
            )
        existing_keys = {position.key for position in proposed.cut.positions}
        counter_keys = [position.key for position in challenge.counter_positions]
        if (
            any(not key for key in counter_keys)
            or len(counter_keys) != len(set(counter_keys))
            or existing_keys.intersection(counter_keys)
        ):
            raise InvalidReconfiguration(
                "counter-position keys must be new and locally unique"
            )
        available_keys = existing_keys.union(counter_keys)
        if any(
            relation.source.cut_id != proposed.cut.cut_id
            or relation.target.cut_id != proposed.cut.cut_id
            or relation.source.position_key not in available_keys
            or relation.target.position_key not in available_keys
            for relation in challenge.counter_relations
        ):
            raise InvalidReconfiguration(
                "counter-relations must remain inside the proposed local cut"
            )
        grounding_keys = {
            grounding.position_key
            for grounding in challenge.counter_position_groundings
        }
        if grounding_keys != set(counter_keys):
            raise InvalidReconfiguration(
                "every counter-position, and only a counter-position, requires grounding"
            )
        noticing_ids = {noticing.noticing_id for noticing in proposed.noticings}
        if any(
            not grounding.noticing_ids
            or set(grounding.noticing_ids).difference(noticing_ids)
            for grounding in challenge.counter_position_groundings
        ):
            raise InvalidReconfiguration(
                "counter-position grounding must use proposed situated noticings"
            )
        original_signature = PluralSituatedFormationBoundary._material_signature(
            proposed.cut
        )
        challenged_cut = CutEnactment(
            cut_id=proposed.cut.cut_id,
            transport_basis=proposed.cut.transport_basis,
            dependency_ids=proposed.cut.dependency_ids,
            lineage_ids=proposed.cut.lineage_ids,
            positions=proposed.cut.positions + challenge.counter_positions,
            relations=proposed.cut.relations + challenge.counter_relations,
            allocations=proposed.cut.allocations,
            revision_conditions=proposed.cut.revision_conditions,
            exclusions=proposed.cut.exclusions,
        )
        if (
            PluralSituatedFormationBoundary._material_signature(challenged_cut)
            == original_signature
        ):
            raise InvalidReconfiguration(
                "formation challenge must change the cut's structural shape"
            )
        checker = challenge.checking_participation
        if set(checker.trace_ids) != set(invitation.participation.trace_ids):
            raise InvalidReconfiguration(
                "checking participation must encounter the same arrival basis"
            )
        if (
            PluralSituatedFormationBoundary._apparatus_signature(checker)
            == PluralSituatedFormationBoundary._apparatus_signature(
                invitation.participation
            )
        ):
            raise InvalidReconfiguration(
                "formation counter-participation must be materially distinct"
            )

    def _participation_request(
        self, invitation_id: str
    ) -> ProposalParticipationRequest:
        invitation = self._invitations.get(invitation_id)
        if invitation is None:
            raise InvalidReconfiguration(
                "proposal participation requires an active invitation"
            )
        self._require_active_invitation(invitation_id)
        evidence = tuple(
            InvitationEvidence(
                trace_id=span.trace_id,
                start=span.start,
                end=span.end,
                payload=self._substrate.state.transports[
                    span.trace_id
                ].payload[span.start:span.end],
            )
            for relation_id in invitation.unresolved_relation_ids
            for span in self._relations[relation_id].evidence
        )
        return ProposalParticipationRequest(
            invitation_id=invitation.invitation_id,
            unresolved_relation_ids=invitation.unresolved_relation_ids,
            evidence=evidence,
            participation=invitation.participation,
            difference_opened=invitation.difference_opened,
            limits=invitation.limits,
            deactivation_conditions=invitation.deactivation_conditions,
        )

    def _shared_arrival_basis(self):
        return {
            span.trace_id
            for relation in self._relations.values()
            for span in relation.evidence
        }

    def _opening_conditions(self):
        return tuple(
            "unresolved relation: " + relation.relation_id
            for relation in self._relations.values()
        )

    def _require_active_invitation(self, invitation_id: str) -> None:
        if invitation_id in self._invalidated_invitation_ids:
            raise InvalidReconfiguration(
                "later material has invalidated this participation invitation"
            )
