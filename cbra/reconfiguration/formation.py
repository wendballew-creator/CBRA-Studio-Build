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
