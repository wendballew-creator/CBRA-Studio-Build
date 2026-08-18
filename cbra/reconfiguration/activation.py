"""Dependency-activated proposal participation without a formation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Protocol, Sequence, Tuple

from .formation import (
    ApparatusParticipation,
    EvidenceSpan,
    PluralSituatedFormationBoundary,
    RecordedPluralOriginationAssembly,
    RecordedProposalContribution,
    SituatedFormationBoundary,
)
from .substrate import InvalidReconfiguration, ReconfigurationSubstrate
from .models import TransportTrace


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
    revision_conditions: Tuple[str, ...]


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
        self._validate_activation()

    @property
    def activation_trace(self) -> OriginationActivationTrace:
        invitation_ids = set(self._invitations)
        answered_ids = set(self._answers)
        return OriginationActivationTrace(
            field_id=self._field_id,
            unresolved_relation_ids=tuple(sorted(self._relations)),
            invitation_ids=tuple(sorted(invitation_ids)),
            answered_invitation_ids=tuple(sorted(answered_ids)),
            unanswered_invitation_ids=tuple(
                sorted(invitation_ids.difference(answered_ids))
            ),
            revision_conditions=self._revision_conditions,
        )

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

    def _participation_request(
        self, invitation_id: str
    ) -> ProposalParticipationRequest:
        invitation = self._invitations.get(invitation_id)
        if invitation is None:
            raise InvalidReconfiguration(
                "proposal participation requires an active invitation"
            )
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
