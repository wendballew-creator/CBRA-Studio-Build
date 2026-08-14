"""Situated formation over transport evidence and apparatus participation.

This boundary does not interpret an arrival or discover a semantic subject.
It makes a proposed noticing accountable to exact transport material and to
the apparatus relation through which that material became perceptible before
allowing the proposal to enact a local cut.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from .models import CutEnactment
from .substrate import InvalidReconfiguration, ReconfigurationSubstrate


@dataclass(frozen=True)
class EvidenceSpan:
    trace_id: str
    start: int
    end: int


@dataclass(frozen=True)
class ApparatusParticipation:
    participation_id: str
    condition: str
    trace_ids: Tuple[str, ...]
    makes_perceptible: Tuple[str, ...]
    obscures_or_excludes: Tuple[str, ...]
    revision_conditions: Tuple[str, ...]


@dataclass(frozen=True)
class SituatedNoticing:
    noticing_id: str
    evidence: Tuple[EvidenceSpan, ...]
    apparatus_participation_ids: Tuple[str, ...]
    became_perceptible: str
    unavailable_or_excluded: Tuple[str, ...]
    revision_conditions: Tuple[str, ...]


@dataclass(frozen=True)
class PositionGrounding:
    position_key: str
    noticing_ids: Tuple[str, ...]


@dataclass(frozen=True)
class SituatedCutProposal:
    cut: CutEnactment
    apparatus_participations: Tuple[ApparatusParticipation, ...]
    noticings: Tuple[SituatedNoticing, ...]
    position_groundings: Tuple[PositionGrounding, ...]


@dataclass(frozen=True)
class AccountableSituatedProposal:
    proposal_id: str
    formation: SituatedCutProposal
    originating_participation_ids: Tuple[str, ...]
    checking_participation_ids: Tuple[str, ...]


@dataclass(frozen=True)
class ProposalOrigination:
    proposal_id: str
    originating_participation_ids: Tuple[str, ...]
    generative_differences: Tuple[str, ...]


@dataclass(frozen=True)
class InspectableOriginationField:
    field_id: str
    opening_conditions: Tuple[str, ...]
    originating_participations: Tuple[ApparatusParticipation, ...]
    proposal_originations: Tuple[ProposalOrigination, ...]
    unavailable_or_ungenerated: Tuple[str, ...]
    revision_conditions: Tuple[str, ...]


class SituatedFormationBoundary:
    """Validate an inspectable proposal and enact its provisional local cut."""

    def __init__(self, substrate: ReconfigurationSubstrate) -> None:
        self._substrate = substrate

    def enact(
        self, proposal: SituatedCutProposal, *, delta_id: str
    ):
        self._validate(proposal)
        return self._substrate.enact_cut(proposal.cut, delta_id=delta_id)

    def _validate(self, proposal: SituatedCutProposal) -> None:
        cut = proposal.cut
        participations = self._unique_by_id(
            proposal.apparatus_participations,
            "participation_id",
            "apparatus participation",
        )
        noticings = self._unique_by_id(
            proposal.noticings, "noticing_id", "situated noticing"
        )
        if not participations or not noticings:
            raise InvalidReconfiguration(
                "situated formation requires apparatus participation and noticing"
            )

        transport_ids = set(self._substrate.state.transports)
        for participation in participations.values():
            if not participation.condition or not participation.trace_ids:
                raise InvalidReconfiguration(
                    "apparatus participation requires a condition and transport basis"
                )
            self._require_unique_refs(
                participation.trace_ids, "apparatus transport basis"
            )
            if set(participation.trace_ids).difference(transport_ids):
                raise InvalidReconfiguration(
                    "apparatus participation references unknown transport"
                )
            if not participation.makes_perceptible:
                raise InvalidReconfiguration(
                    "apparatus participation must state what it makes perceptible"
                )
            if not participation.obscures_or_excludes:
                raise InvalidReconfiguration(
                    "apparatus participation must expose what it obscures or excludes"
                )
            if not participation.revision_conditions:
                raise InvalidReconfiguration(
                    "apparatus participation must remain explicitly revisable"
                )

        noticed_trace_ids = set()
        for noticing in noticings.values():
            if not noticing.became_perceptible or not noticing.evidence:
                raise InvalidReconfiguration(
                    "a noticing requires perceptible material and exact evidence"
                )
            if not noticing.apparatus_participation_ids:
                raise InvalidReconfiguration(
                    "a noticing cannot be detached from apparatus participation"
                )
            self._require_unique_refs(
                noticing.apparatus_participation_ids,
                "noticing apparatus participation",
            )
            self._require_unique_refs(noticing.evidence, "noticing evidence")
            unknown = set(noticing.apparatus_participation_ids).difference(participations)
            if unknown:
                raise InvalidReconfiguration(
                    "a noticing references unknown apparatus participation"
                )
            if not noticing.revision_conditions:
                raise InvalidReconfiguration(
                    "a noticing must remain explicitly revisable"
                )
            if not noticing.unavailable_or_excluded:
                raise InvalidReconfiguration(
                    "a noticing must retain unavailable or excluded material"
                )
            for span in noticing.evidence:
                trace = self._substrate.state.transports.get(span.trace_id)
                if trace is None:
                    raise InvalidReconfiguration("noticing references unknown transport")
                if span.start < 0 or span.end <= span.start or span.end > len(trace.payload):
                    raise InvalidReconfiguration(
                        "noticing evidence must be a nonempty exact transport span"
                    )
                participating_traces = {
                    trace_id
                    for participation_id in noticing.apparatus_participation_ids
                    for trace_id in participations[participation_id].trace_ids
                }
                if span.trace_id not in participating_traces:
                    raise InvalidReconfiguration(
                        "noticing evidence must pass through named apparatus participation"
                    )
                noticed_trace_ids.add(span.trace_id)

        if set(cut.transport_basis) != noticed_trace_ids:
            raise InvalidReconfiguration(
                "cut transport basis must equal its situated noticing evidence"
            )
        if not cut.revision_conditions:
            raise InvalidReconfiguration("a situated cut must remain explicitly revisable")
        if not cut.exclusions:
            raise InvalidReconfiguration("a situated cut must expose its exclusions")

        groundings = self._unique_by_id(
            proposal.position_groundings,
            "position_key",
            "position grounding",
        )
        position_keys = {position.key for position in cut.positions}
        if set(groundings) != position_keys:
            raise InvalidReconfiguration(
                "every local position, and only a local position, requires grounding"
            )
        for grounding in groundings.values():
            if (
                not grounding.noticing_ids
                or len(grounding.noticing_ids) != len(set(grounding.noticing_ids))
                or set(grounding.noticing_ids).difference(noticings)
            ):
                raise InvalidReconfiguration(
                    "position grounding must reference unique recorded situated noticings"
                )

        grounded_noticing_ids = {
            noticing_id
            for grounding in groundings.values()
            for noticing_id in grounding.noticing_ids
        }
        if grounded_noticing_ids != set(noticings):
            raise InvalidReconfiguration(
                "every situated noticing must ground an enacted local position"
            )

        participating_apparatus_ids = {
            participation_id
            for noticing in noticings.values()
            for participation_id in noticing.apparatus_participation_ids
        }
        if participating_apparatus_ids != set(participations):
            raise InvalidReconfiguration(
                "every apparatus participation must participate in a grounded noticing"
            )

    @staticmethod
    def _unique_by_id(items: Sequence[object], attribute: str, label: str):
        indexed = {}
        for item in items:
            identifier = getattr(item, attribute)
            if not identifier or identifier in indexed:
                raise InvalidReconfiguration(f"{label} ids must be nonempty and unique")
            indexed[identifier] = item
        return indexed

    @staticmethod
    def _require_unique_refs(items: Sequence[object], label: str) -> None:
        if len(items) != len(set(items)):
            raise InvalidReconfiguration(f"{label} references must be unique")


class PluralSituatedFormationBoundary:
    """Enact materially different, cross-checked proposals without choosing one."""

    def __init__(self, substrate: ReconfigurationSubstrate) -> None:
        self._substrate = substrate
        self._single = SituatedFormationBoundary(substrate)

    def enact(
        self,
        proposals: Sequence[AccountableSituatedProposal],
        *,
        delta_id: str,
    ):
        if len(proposals) < 2:
            raise InvalidReconfiguration(
                "plural formation requires materially different proposals"
            )
        proposal_ids = [proposal.proposal_id for proposal in proposals]
        if any(not proposal_id for proposal_id in proposal_ids) or len(
            proposal_ids
        ) != len(set(proposal_ids)):
            raise InvalidReconfiguration("plural proposal ids must be nonempty and unique")

        signatures = set()
        shared_transport_basis = None
        for account in proposals:
            self._single._validate(account.formation)
            self._validate_accountability(account)
            transport_basis = frozenset(account.formation.cut.transport_basis)
            if shared_transport_basis is None:
                shared_transport_basis = transport_basis
            elif transport_basis != shared_transport_basis:
                raise InvalidReconfiguration(
                    "plural proposals must remain grounded in the same material arrival basis"
                )
            signature = self._material_signature(account.formation.cut)
            if signature in signatures:
                raise InvalidReconfiguration(
                    "plural proposals must differ materially, not only by ids or provenance"
                )
            signatures.add(signature)

        return self._substrate.enact_concurrent_cuts(
            tuple(account.formation.cut for account in proposals),
            delta_id=delta_id,
        )

    @staticmethod
    def _validate_accountability(account: AccountableSituatedProposal) -> None:
        originators = account.originating_participation_ids
        checkers = account.checking_participation_ids
        SituatedFormationBoundary._require_unique_refs(
            originators, "proposal origin participation"
        )
        SituatedFormationBoundary._require_unique_refs(
            checkers, "proposal checking participation"
        )
        if not originators or not checkers:
            raise InvalidReconfiguration(
                "each plural proposal requires named origin and checking participation"
            )
        if set(originators).intersection(checkers):
            raise InvalidReconfiguration(
                "a proposal cannot be originated and checked by the same participation"
            )
        available = {
            item.participation_id
            for item in account.formation.apparatus_participations
        }
        if set(originators).union(checkers).difference(available):
            raise InvalidReconfiguration(
                "proposal origin and checking must reference participating apparatus"
            )
        participations = {
            item.participation_id: item
            for item in account.formation.apparatus_participations
        }
        origin_signatures = {
            PluralSituatedFormationBoundary._apparatus_signature(
                participations[participation_id]
            )
            for participation_id in originators
        }
        checking_signatures = {
            PluralSituatedFormationBoundary._apparatus_signature(
                participations[participation_id]
            )
            for participation_id in checkers
        }
        if origin_signatures.intersection(checking_signatures):
            raise InvalidReconfiguration(
                "proposal origin and checking require materially distinct apparatus participation"
            )

    @staticmethod
    def _apparatus_signature(participation: ApparatusParticipation):
        return (
            participation.condition,
            tuple(sorted(participation.trace_ids)),
            tuple(sorted(participation.makes_perceptible)),
            tuple(sorted(participation.obscures_or_excludes)),
            tuple(sorted(participation.revision_conditions)),
        )

    @staticmethod
    def _material_signature(cut: CutEnactment):
        """Compare enacted structure while excluding ids, labels, and tuple order."""

        return (
            tuple(sorted(cut.transport_basis)),
            len(cut.positions),
            tuple(
                sorted(
                    (
                        relation.relation_type,
                        relation.source.position_key == relation.target.position_key,
                    )
                    for relation in cut.relations
                )
            ),
            tuple(
                sorted(
                    (
                        allocation.dimension.value,
                        allocation.amount,
                    )
                    for allocation in cut.allocations
                )
            ),
        )


class InspectablePluralOriginationBoundary:
    """Enact a plural field whose proposal origination remains inspectable."""

    def __init__(self, substrate: ReconfigurationSubstrate) -> None:
        self._plural = PluralSituatedFormationBoundary(substrate)

    def enact(
        self,
        field: InspectableOriginationField,
        proposals: Sequence[AccountableSituatedProposal],
        *,
        delta_id: str,
    ):
        self._validate(field, proposals)
        return self._plural.enact(proposals, delta_id=delta_id)

    @staticmethod
    def _validate(
        field: InspectableOriginationField,
        proposals: Sequence[AccountableSituatedProposal],
    ) -> None:
        if not field.field_id or not field.opening_conditions:
            raise InvalidReconfiguration(
                "plural origination requires an identified field and opening conditions"
            )
        if not field.unavailable_or_ungenerated or not field.revision_conditions:
            raise InvalidReconfiguration(
                "plural origination must expose unavailable possibilities and remain revisable"
            )

        participations = SituatedFormationBoundary._unique_by_id(
            field.originating_participations,
            "participation_id",
            "field originating participation",
        )
        if len(participations) < 2:
            raise InvalidReconfiguration(
                "plural origination requires multiple originating participations"
            )
        signatures = {
            PluralSituatedFormationBoundary._apparatus_signature(item)
            for item in participations.values()
        }
        if len(signatures) != len(participations):
            raise InvalidReconfiguration(
                "field originating participations must be materially distinct"
            )

        accounts = SituatedFormationBoundary._unique_by_id(
            proposals, "proposal_id", "plural proposal"
        )
        originations = SituatedFormationBoundary._unique_by_id(
            field.proposal_originations,
            "proposal_id",
            "proposal origination",
        )
        if set(originations) != set(accounts):
            raise InvalidReconfiguration(
                "every submitted proposal, and only a submitted proposal, requires origination"
            )

        participation_use = {
            participation_id: set() for participation_id in participations
        }
        for proposal_id, origination in originations.items():
            SituatedFormationBoundary._require_unique_refs(
                origination.originating_participation_ids,
                "proposal field origin participation",
            )
            if not origination.originating_participation_ids:
                raise InvalidReconfiguration(
                    "each proposal requires originating participation in the field"
                )
            if not origination.generative_differences or any(
                not difference for difference in origination.generative_differences
            ):
                raise InvalidReconfiguration(
                    "each proposal origination must expose a generative difference"
                )
            SituatedFormationBoundary._require_unique_refs(
                origination.generative_differences,
                "proposal generative difference",
            )
            unknown = set(origination.originating_participation_ids).difference(
                participations
            )
            if unknown:
                raise InvalidReconfiguration(
                    "proposal origination references participation outside the opened field"
                )
            account_origins = set(accounts[proposal_id].originating_participation_ids)
            if set(origination.originating_participation_ids) != account_origins:
                raise InvalidReconfiguration(
                    "field origination must equal the proposal's accountable origins"
                )
            formation_participations = {
                item.participation_id: item
                for item in accounts[
                    proposal_id
                ].formation.apparatus_participations
            }
            if any(
                formation_participations.get(participation_id)
                != participations[participation_id]
                for participation_id in origination.originating_participation_ids
            ):
                raise InvalidReconfiguration(
                    "field origins must equal their proposal apparatus participation"
                )
            for participation_id in origination.originating_participation_ids:
                participation_use[participation_id].add(proposal_id)

        complete_field = set(accounts)
        if any(
            proposal_ids == complete_field
            for proposal_ids in participation_use.values()
        ):
            raise InvalidReconfiguration(
                "no originating participation may control the complete proposal field"
            )
        unused = {
            participation_id
            for participation_id, proposal_ids in participation_use.items()
            if not proposal_ids
        }
        if unused:
            raise InvalidReconfiguration(
                "every declared originating participation must generate a submitted proposal"
            )
