from dataclasses import replace
from hashlib import sha256
import inspect
import unittest

from cbra.reconfiguration.formation import (
    AccountableSituatedProposal,
    ApparatusParticipation,
    EvidenceSpan,
    InspectableOriginationField,
    InspectablePluralOriginationBoundary,
    PositionGrounding,
    PluralSituatedFormationBoundary,
    ProposalOrigination,
    RecordedPluralOriginationAssembly,
    RecordedProposalContribution,
    SituatedCutProposal,
    SituatedFormationBoundary,
    SituatedNoticing,
)
from cbra.reconfiguration.activation import (
    DependencyActivatedOriginationAssembly,
    ExecutableReopeningActivationAssembly,
    FormationChallengeMaterial,
    FormationReopeningTrace,
    FormationTransformationRequest,
    InspectableReopeningActivationAssembly,
    InvitationEvidence,
    OriginationActivationTrace,
    ProposalEmissionMaterial,
    ProposalParticipationRequest,
    RelationMaterialActivationContribution,
    RelationMaterialActivationChallenge,
    RelationMaterialActivationRequest,
    RelationMaterialTransformationRequest,
    ProposedRelationMaterialActivation,
    ProposedFormationMaterial,
    ProposedNoticingMaterial,
    ProposalParticipationInvitation,
    UnresolvedArrivalRelation,
)
from cbra.reconfiguration.models import (
    CutEnactment,
    CutPosition,
    LocalPositionRef,
    Relation,
    TransportTrace,
)
from cbra.reconfiguration.substrate import InvalidReconfiguration, ReconfigurationSubstrate


def fixture():
    substrate = ReconfigurationSubstrate()
    substrate.record_transport(
        TransportTrace("arrival-1", "text", "digest", b"we need another arrangement", "now")
    )
    proposal = SituatedCutProposal(
        cut=CutEnactment(
            cut_id="cut-1",
            transport_basis=("arrival-1",),
            dependency_ids=(),
            lineage_ids=(),
            positions=(CutPosition("utterance", "locally addressable wording"),),
            revision_conditions=("later material alters what this wording can support",),
            exclusions=("conditions not present in the arrival",),
        ),
        apparatus_participations=(
            ApparatusParticipation(
                "apparatus-1",
                "byte-preserving text ingress and exact-span access",
                ("arrival-1",),
                ("the contributed wording",),
                ("tone, body, setting, and unavailable history",),
                ("a later arrival or transformation changes the available material",),
            ),
        ),
        noticings=(
            SituatedNoticing(
                "noticing-1",
                (EvidenceSpan("arrival-1", 0, 27),),
                ("apparatus-1",),
                "the arrival contains wording available for local address",
                ("conditions outside the contributed bytes",),
                ("later material disturbs this local addressability",),
            ),
        ),
        position_groundings=(PositionGrounding("utterance", ("noticing-1",)),),
    )
    return substrate, proposal


def plural_fixture():
    substrate, first = fixture()
    checker = ApparatusParticipation(
        "apparatus-check",
        "independent exact-span and grounding-account review",
        ("arrival-1",),
        ("whether the proposed account remains grounded in the arrival",),
        ("conditions unavailable to the checking apparatus",),
        ("different material or apparatus participation reopens the check",),
    )
    first_noticing = replace(
        first.noticings[0],
        apparatus_participation_ids=("apparatus-1", "apparatus-check"),
    )
    first = replace(
        first,
        apparatus_participations=first.apparatus_participations + (checker,),
        noticings=(first_noticing,),
    )
    second = replace(
        first,
        cut=replace(
            first.cut,
            cut_id="cut-2",
            positions=(
                CutPosition(
                    "constraint", "wording that locally constrains an arrangement"
                ),
                CutPosition(
                    "arrangement", "the locally implicated arrangement"
                ),
            ),
            relations=(
                Relation(
                    "constrains",
                    LocalPositionRef("cut-2", "constraint"),
                    LocalPositionRef("cut-2", "arrangement"),
                ),
            ),
            exclusions=("whether the wording identifies a singular request",),
        ),
        position_groundings=(
            PositionGrounding("constraint", ("noticing-1",)),
            PositionGrounding("arrangement", ("noticing-1",)),
        ),
    )
    return substrate, (
        AccountableSituatedProposal(
            "proposal-1", first, ("apparatus-1",), ("apparatus-check",)
        ),
        AccountableSituatedProposal(
            "proposal-2", second, ("apparatus-1",), ("apparatus-check",)
        ),
    )


def origination_fixture():
    substrate, proposals = plural_fixture()
    second_origin = ApparatusParticipation(
        "apparatus-2",
        "relation-sensitive reading of exact arrival material",
        ("arrival-1",),
        ("how wording may configure more than one local position",),
        ("embodied and historical conditions unavailable to this reading",),
        ("another apparatus relation changes what can be generated",),
    )
    first = proposals[0]
    second = replace(
        proposals[1],
        formation=replace(
            proposals[1].formation,
            apparatus_participations=(
                second_origin,
                proposals[1].formation.apparatus_participations[1],
            ),
            noticings=(
                replace(
                    proposals[1].formation.noticings[0],
                    apparatus_participation_ids=("apparatus-2", "apparatus-check"),
                ),
            ),
        ),
        originating_participation_ids=("apparatus-2",),
    )
    proposals = (first, second)
    field = InspectableOriginationField(
        "origin-field-1",
        ("one arrival is opened through distinct apparatus relations",),
        (first.formation.apparatus_participations[0], second_origin),
        (
            ProposalOrigination(
                "proposal-1",
                ("apparatus-1",),
                ("forms one locally addressable position",),
            ),
            ProposalOrigination(
                "proposal-2",
                ("apparatus-2",),
                ("forms a relation between two local positions",),
            ),
        ),
        ("cuts requiring apparatus conditions not participating here",),
        ("new participation or material arrival reopens proposal origination",),
    )
    return substrate, field, proposals


def recorded_origination_fixture():
    substrate, field, proposals = origination_fixture()
    substrate.record_transport(
        TransportTrace(
            "emission-1", "model-output", "emission-digest-1",
            b"one locally addressable position", "now",
            provenance={
                "provider": "provider-a",
                "model": "model-a",
                "effective_configuration": "configuration-a",
                "prompt_dependencies": ("prompt-a",),
                "source_dependencies": ("arrival-1",),
                "known_limits": ("text-only participation",),
                "human_centered_training_apparatus": True,
            },
        )
    )
    substrate.record_transport(
        TransportTrace(
            "emission-2", "model-output", "emission-digest-2",
            b"a relation between two local positions", "now",
            provenance={
                "provider": "provider-b",
                "model": "model-b",
                "effective_configuration": "configuration-b",
                "prompt_dependencies": ("prompt-b",),
                "source_dependencies": ("arrival-1",),
                "known_limits": ("text-only participation",),
                "human_centered_training_apparatus": True,
            },
        )
    )
    assembly = RecordedPluralOriginationAssembly(
        substrate,
        field_id=field.field_id,
        opening_conditions=field.opening_conditions,
        unavailable_or_ungenerated=field.unavailable_or_ungenerated,
        revision_conditions=field.revision_conditions,
    )
    contributions = (
        RecordedProposalContribution(
            "contribution-1",
            proposals[0],
            field.originating_participations[0],
            (EvidenceSpan("emission-1", 0, 32),),
            field.proposal_originations[0].generative_differences,
        ),
        RecordedProposalContribution(
            "contribution-2",
            proposals[1],
            field.originating_participations[1],
            (EvidenceSpan("emission-2", 0, 38),),
            field.proposal_originations[1].generative_differences,
        ),
    )
    return substrate, assembly, contributions


def activated_origination_fixture(
    include_unanswered=False,
    reverse_invitations=False,
    reverse_invocations=False,
):
    substrate, _, contributions = recorded_origination_fixture()
    relation = UnresolvedArrivalRelation(
        "relation-1",
        (EvidenceSpan("arrival-1", 0, 27),),
        "the arrival supports incompatible local formations",
        ("relations unavailable outside the arrival bytes",),
        ("later material changes the unresolved difference",),
    )
    invitations = [
        ProposalParticipationInvitation(
            "invitation-1",
            ("relation-1",),
            contributions[0].originating_participation,
            "a locally addressable position",
            ("cannot establish a singular intention",),
            ("the unresolved relation is revised or invalidated",),
        ),
        ProposalParticipationInvitation(
            "invitation-2",
            ("relation-1",),
            contributions[1].originating_participation,
            "a relation among locally formed positions",
            ("cannot establish an exhaustive arrangement",),
            ("the unresolved relation is revised or invalidated",),
        ),
    ]
    if include_unanswered:
        invitations.append(ProposalParticipationInvitation(
            "invitation-unanswered",
            ("relation-1",),
            replace(
                contributions[0].originating_participation,
                participation_id="apparatus-unanswered",
                condition="embodied participation unavailable in this runtime",
                makes_perceptible=("bodily response not available to text ingress",),
            ),
            "an embodied difference unavailable to recorded emissions",
            ("no embodied sensor or report participates",),
            ("embodied material enters the configuration",),
        ))
    invitation_sequence = tuple(invitations)
    if reverse_invitations:
        invitation_sequence = tuple(reversed(invitation_sequence))
    assembly = DependencyActivatedOriginationAssembly(
        substrate,
        field_id="activated-field-1",
        unresolved_relations=(relation,),
        invitations=invitation_sequence,
        unavailable_or_ungenerated=("apparatus relations not participating here",),
        revision_conditions=("new arrival material reopens activation",),
    )
    invocation_specs = (
        (
            "invitation-1",
            FixtureProposalParticipant(
                b"one locally addressable position", "provider-a", "model-a"
            ),
            "activated-emission-1",
        ),
        (
            "invitation-2",
            FixtureProposalParticipant(
                b"a relation between two local positions", "provider-b", "model-b"
            ),
            "activated-emission-2",
        ),
    )
    if reverse_invocations:
        invocation_specs = tuple(reversed(invocation_specs))
    spans = {}
    for invitation_id, participant, trace_id in invocation_specs:
        spans[invitation_id] = assembly.invoke(
            invitation_id=invitation_id,
            participant=participant,
            trace_id=trace_id,
            observed_at="now",
        )
    contributions = (
        replace(
            contributions[0],
            emission_evidence=(spans["invitation-1"],),
        ),
        replace(
            contributions[1],
            emission_evidence=(spans["invitation-2"],),
        ),
    )
    return substrate, assembly, contributions, tuple(invitations)


class FixtureProposalParticipant:
    def __init__(self, payload, provider, model):
        self.payload = payload
        self.provider = provider
        self.model = model
        self.requests = []

    def emit(self, request):
        self.requests.append(request)
        return ProposalEmissionMaterial(
            channel="model-output",
            payload=self.payload,
            provenance={
                "provider": self.provider,
                "model": self.model,
                "effective_configuration": "fixture-configuration",
                "prompt_dependencies": ("fixture-prompt",),
                "source_dependencies": tuple(
                    sorted({item.trace_id for item in request.evidence})
                ),
                "known_limits": ("fixture participation",),
                "human_centered_training_apparatus": True,
            },
        )


class FailingProposalParticipant:
    def emit(self, request):
        raise RuntimeError("participant unavailable")


class OpaqueModelParticipant:
    def emit(self, request):
        return ProposalEmissionMaterial(
            channel="model-output",
            payload=b"opaque model proposal",
            provenance={
                "source_dependencies": tuple(
                    sorted({item.trace_id for item in request.evidence})
                ),
            },
        )


class SemanticFormerParticipant:
    def __init__(self, contribution):
        self.contribution = contribution

    def emit(self, request):
        return self.contribution


class FixtureActivationParticipant:
    def __init__(self, payload, provider, model):
        self.payload = payload
        self.provider = provider
        self.model = model
        self.requests = []

    def emit(self, request):
        self.requests.append(request)
        return ProposalEmissionMaterial(
            channel="model-output",
            payload=self.payload,
            provenance={
                "provider": self.provider,
                "model": self.model,
                "effective_configuration": "activation-fixture-configuration",
                "prompt_dependencies": ("activation-fixture-prompt",),
                "source_dependencies": tuple(
                    sorted(
                        {item.trace_id for item in request.later_material}.union({
                            span.trace_id
                            for relation in request.unresolved_relations
                            for span in relation.evidence
                        })
                    )
                ),
                "known_limits": ("text-only activation participation",),
                "human_centered_training_apparatus": True,
            },
        )


class FixtureActivationTransformer:
    def __init__(self, difference):
        self.difference = difference
        self.requests = []

    def transform(self, request):
        self.requests.append(request)
        return ProposedRelationMaterialActivation(
            unresolved_relation_ids=("relation-1",),
            differences_made=(self.difference,),
            exclusions=("relations not expressed by this transformation",),
            revision_conditions=("another transformation reopens this account",),
        )


class FixtureActivationCounterParticipant:
    def __init__(self, participation):
        self.participation = participation

    def challenge(self, request, proposed):
        return RelationMaterialActivationChallenge(
            checking_participation=self.participation,
            relation_ids=proposed.unresolved_relation_ids,
            complications=("counter-participation complicates the activation",),
            additional_exclusions=("counter-material remains partial",),
            reopening_conditions=("further counter-material reopens activation",),
        )


class FixtureFormationTransformer:
    def __init__(self, source_contribution):
        self.source = source_contribution
        self.requests = []

    def transform(self, request):
        self.requests.append(request)
        formation = self.source.proposal.formation
        return ProposedFormationMaterial(
            cut=formation.cut,
            noticings=tuple(
                ProposedNoticingMaterial(
                    noticing.noticing_id,
                    noticing.evidence,
                    noticing.became_perceptible,
                    noticing.unavailable_or_excluded,
                    noticing.revision_conditions,
                )
                for noticing in formation.noticings
            ),
            position_groundings=formation.position_groundings,
            generative_differences=self.source.generative_differences,
        )


class MixedArrivalFormationTransformer:
    def __init__(self, cut_id, position_count):
        self.cut_id = cut_id
        self.position_count = position_count

    def transform(self, request):
        positions = tuple(
            CutPosition(f"position-{index}", f"arrival-formed position {index}")
            for index in range(1, self.position_count + 1)
        )
        relations = ()
        if len(positions) > 1:
            relations = (
                Relation(
                    "changes-with",
                    LocalPositionRef(self.cut_id, positions[0].key),
                    LocalPositionRef(self.cut_id, positions[1].key),
                ),
            )
        noticing_id = "noticing-" + self.cut_id
        return ProposedFormationMaterial(
            cut=CutEnactment(
                cut_id=self.cut_id,
                transport_basis=tuple(sorted({
                    item.trace_id for item in request.arrival_evidence
                })),
                dependency_ids=(),
                lineage_ids=(),
                positions=positions,
                relations=relations,
                revision_conditions=("later mixed arrival reopens this cut",),
                exclusions=("mixed arrival relations not formed here",),
            ),
            noticings=(ProposedNoticingMaterial(
                noticing_id=noticing_id,
                evidence=tuple(
                    EvidenceSpan(item.trace_id, item.start, item.end)
                    for item in request.arrival_evidence
                ),
                became_perceptible="mixed arrivals participate in one local formation",
                unavailable_or_excluded=("unrecorded material conditions",),
                revision_conditions=("another arrival changes this noticing",),
            ),),
            position_groundings=tuple(
                PositionGrounding(position.key, (noticing_id,))
                for position in positions
            ),
            generative_differences=(
                f"forms {self.position_count} locally related positions",
            ),
        )


class FixtureFormationCounterParticipant:
    def __init__(self, checking_participation):
        self.checking_participation = checking_participation
        self.requests = []

    def challenge(self, request):
        self.requests.append(request)
        cut = request.proposed.cut
        counter_key = "counter-" + cut.positions[0].key
        return FormationChallengeMaterial(
            checking_participation=self.checking_participation,
            counter_positions=(
                CutPosition(counter_key, "counter-participating local limit"),
            ),
            counter_relations=(
                Relation(
                    "complicates",
                    LocalPositionRef(cut.cut_id, counter_key),
                    LocalPositionRef(cut.cut_id, cut.positions[0].key),
                ),
            ),
            counter_position_groundings=(
                PositionGrounding(
                    counter_key,
                    (request.proposed.noticings[0].noticing_id,),
                ),
            ),
            complications=("the proposed distinction remains locally contestable",),
            additional_exclusions=("relations exposed only by counter-participation",),
            reopening_conditions=("counter-material disturbs the proposed distinction",),
        )


class InvalidFormationTransformer:
    def transform(self, request):
        return b"preformed semantic answer"


class StringOnlyFormationCounterParticipant:
    def __init__(self, checking_participation):
        self.checking_participation = checking_participation

    def challenge(self, request):
        return FormationChallengeMaterial(
            checking_participation=self.checking_participation,
            counter_positions=(),
            counter_relations=(),
            counter_position_groundings=(),
            complications=("prose-only complication",),
            additional_exclusions=("prose-only exclusion",),
            reopening_conditions=("prose-only reopening",),
        )


class UngroundedFormationCounterParticipant(FixtureFormationCounterParticipant):
    def challenge(self, request):
        return replace(
            super().challenge(request),
            counter_position_groundings=(),
        )


def transformation_participation(contribution, emission_trace_id):
    origin = contribution.originating_participation
    return ApparatusParticipation(
        "transform-" + origin.participation_id,
        "provisional formation transformation over arrival and emission material",
        tuple(sorted(set(origin.trace_ids).union({emission_trace_id}))),
        ("cut-local distinctions proposed by the emission",),
        ("semantic relations not expressible through this transformation",),
        ("counter-participation or later material reopens the transformation",),
    )


def transform_activated_contributions(assembly, contributions):
    transformed = []
    for index, contribution in enumerate(contributions, start=1):
        emission_trace_id = f"activated-emission-{index}"
        transformed.append(assembly.transform_and_record(
            invitation_id=f"invitation-{index}",
            emission_trace_id=emission_trace_id,
            transformer=FixtureFormationTransformer(contribution),
            transformation_participation=transformation_participation(
                contribution, emission_trace_id
            ),
            counter_participant=FixtureFormationCounterParticipant(
                contribution.proposal.formation.apparatus_participations[1]
            ),
            proposal_id=f"cut-{index}",
            contribution_id=f"transformed-contribution-{index}",
        ))
    return tuple(transformed)


def reopening_activation(
    assembly, trace_id="later-material", contribution_count=2, reverse=False
):
    activation = InspectableReopeningActivationAssembly(
        assembly,
        field_id="reopening-activation-field-1",
        reopening_id="reopening-1",
        unavailable_or_ungenerated=(
            "later-material relations not made perceptible here",
        ),
        revision_conditions=(
            "further material or participation reopens this activation",
        ),
    )
    specs = tuple(enumerate((
        "material-discursive reading of the later span",
        "embodied counter-reading of the later span",
    ), start=1))[:contribution_count]
    if reverse:
        specs = tuple(reversed(specs))
    for index, condition in specs:
        participation = ApparatusParticipation(
            f"reopening-apparatus-{index}",
            condition,
            tuple(sorted({trace_id, "arrival-1"})),
            (f"difference {index} in how later material disturbs relation-1",),
            (f"conditions unavailable to reopening account {index}",),
            (f"different participation reopens account {index}",),
        )
        activation.record(RelationMaterialActivationContribution(
            contribution_id=f"reopening-account-{index}",
            participation=participation,
            apparatus_participations=(participation,),
            emission_evidence=(),
            triggering_evidence=(EvidenceSpan(trace_id, 0, 45),),
            unresolved_relation_ids=("relation-1",),
            differences_made=(f"relation-material difference {index}",),
            exclusions=(f"excluded activation possibility {index}",),
            revision_conditions=(f"later difference reopens account {index}",),
        ))
    return activation


def executable_reopening_activation(substrate, assembly, contribution_count=2):
    activation = ExecutableReopeningActivationAssembly(
        assembly,
        field_id="executable-reopening-field-1",
        reopening_id="executable-reopening-1",
        later_material_evidence=(EvidenceSpan("later-material", 0, 45),),
        unavailable_or_ungenerated=("activation apparatus not participating",),
        revision_conditions=("further material reopens executable activation",),
    )
    for index in range(1, contribution_count + 1):
        origin = ApparatusParticipation(
            f"activation-origin-{index}",
            f"activation origin condition {index}",
            ("arrival-1", "later-material"),
            (f"origin difference {index}",),
            (f"origin exclusion {index}",),
            (f"origin revision {index}",),
        )
        emission_id = f"activation-emission-{index}"
        activation.invoke(
            participation=origin,
            participant=FixtureActivationParticipant(
                f"activation emission {index}".encode(),
                f"provider-{index}",
                f"model-{index}",
            ),
            trace_id=emission_id,
            observed_at="later",
        )
        transformation = ApparatusParticipation(
            f"activation-transform-{index}",
            f"activation transformation condition {index}",
            ("arrival-1", "later-material", emission_id),
            (f"transformed difference {index}",),
            (f"transformation exclusion {index}",),
            (f"transformation revision {index}",),
        )
        checker = ApparatusParticipation(
            f"activation-check-{index}",
            f"activation counter condition {index}",
            ("arrival-1", "later-material"),
            (f"counter difference {index}",),
            (f"counter exclusion {index}",),
            (f"counter revision {index}",),
        )
        activation.transform_and_record(
            emission_trace_id=emission_id,
            transformer=FixtureActivationTransformer(
                f"relation-material transformation {index}"
            ),
            transformation_participation=transformation,
            counter_participant=FixtureActivationCounterParticipant(checker),
            contribution_id=f"executable-activation-contribution-{index}",
        )
    return activation


class SituatedFormationTests(unittest.TestCase):
    def test_enacts_cut_only_through_exact_situated_evidence(self):
        substrate, proposal = fixture()
        delta = SituatedFormationBoundary(substrate).enact(
            proposal, delta_id="formation-1"
        )
        self.assertEqual(("cut-1",), delta.activated_cut_ids)
        self.assertEqual(("cut-1",), substrate.state.active_cut_ids)

    def test_rejects_out_of_bounds_evidence_atomically(self):
        substrate, proposal = fixture()
        noticing = replace(
            proposal.noticings[0],
            evidence=(EvidenceSpan("arrival-1", 0, 999),),
        )
        self.assert_atomic_rejection(substrate, replace(proposal, noticings=(noticing,)))

    def test_rejects_unmarked_apparatus_atomically(self):
        substrate, proposal = fixture()
        noticing = replace(
            proposal.noticings[0], apparatus_participation_ids=("missing",)
        )
        self.assert_atomic_rejection(substrate, replace(proposal, noticings=(noticing,)))

    def test_rejects_transport_basis_not_equal_to_evidence_atomically(self):
        substrate, proposal = fixture()
        self.assert_atomic_rejection(
            substrate, replace(proposal, cut=replace(proposal.cut, transport_basis=()))
        )

    def test_rejects_ungrounded_position_atomically(self):
        substrate, proposal = fixture()
        self.assert_atomic_rejection(
            substrate, replace(proposal, position_groundings=())
        )

    def test_rejects_irrevisable_cut_atomically(self):
        substrate, proposal = fixture()
        self.assert_atomic_rejection(
            substrate,
            replace(proposal, cut=replace(proposal.cut, revision_conditions=())),
        )

    def test_rejects_ornamental_noticing_atomically(self):
        substrate, proposal = fixture()
        ornamental = replace(proposal.noticings[0], noticing_id="noticing-ornamental")
        self.assert_atomic_rejection(
            substrate,
            replace(proposal, noticings=proposal.noticings + (ornamental,)),
        )

    def test_rejects_ornamental_apparatus_atomically(self):
        substrate, proposal = fixture()
        ornamental = replace(
            proposal.apparatus_participations[0],
            participation_id="apparatus-ornamental",
        )
        self.assert_atomic_rejection(
            substrate,
            replace(
                proposal,
                apparatus_participations=proposal.apparatus_participations
                + (ornamental,),
            ),
        )

    def test_rejects_duplicate_grounding_link_atomically(self):
        substrate, proposal = fixture()
        duplicated = replace(
            proposal.position_groundings[0],
            noticing_ids=("noticing-1", "noticing-1"),
        )
        self.assert_atomic_rejection(
            substrate,
            replace(proposal, position_groundings=(duplicated,)),
        )

    def test_rejects_duplicate_evidence_link_atomically(self):
        substrate, proposal = fixture()
        duplicated = replace(
            proposal.noticings[0],
            evidence=(proposal.noticings[0].evidence[0],) * 2,
        )
        self.assert_atomic_rejection(
            substrate,
            replace(proposal, noticings=(duplicated,)),
        )

    def test_multiple_grounded_noticings_confer_no_order_authority(self):
        first_substrate, first = fixture()
        second_noticing = replace(
            first.noticings[0],
            noticing_id="noticing-2",
            became_perceptible="wording remains available under another local noticing",
        )
        grounding = replace(
            first.position_groundings[0],
            noticing_ids=("noticing-1", "noticing-2"),
        )
        first = replace(
            first,
            noticings=(first.noticings[0], second_noticing),
            position_groundings=(grounding,),
        )

        second_substrate, second = fixture()
        second = replace(
            second,
            noticings=(second_noticing, second.noticings[0]),
            position_groundings=(
                replace(grounding, noticing_ids=("noticing-2", "noticing-1")),
            ),
        )

        first_delta = SituatedFormationBoundary(first_substrate).enact(
            first, delta_id="formation-1"
        )
        second_delta = SituatedFormationBoundary(second_substrate).enact(
            second, delta_id="formation-1"
        )
        self.assertEqual(first_delta, second_delta)
        self.assertEqual(first_substrate.state, second_substrate.state)

    def assert_atomic_rejection(self, substrate, proposal):
        with self.assertRaises(InvalidReconfiguration):
            SituatedFormationBoundary(substrate).enact(
                proposal, delta_id="formation-1"
            )
        self.assertEqual((), substrate.state.active_cut_ids)
        self.assertEqual((), substrate.state.deltas)


class PluralSituatedFormationTests(unittest.TestCase):
    def test_materially_different_grounded_proposals_enter_concurrently(self):
        substrate, proposals = plural_fixture()
        delta = PluralSituatedFormationBoundary(substrate).enact(
            proposals, delta_id="plural-formation-1"
        )
        self.assertEqual(("cut-1", "cut-2"), delta.activated_cut_ids)
        self.assertEqual(("cut-1", "cut-2"), substrate.state.active_cut_ids)
        self.assertEqual(1, len(substrate.state.deltas))

    def test_proposal_order_confers_no_formation_authority(self):
        first_substrate, first = plural_fixture()
        second_substrate, second = plural_fixture()
        first_delta = PluralSituatedFormationBoundary(first_substrate).enact(
            first, delta_id="plural-formation-1"
        )
        second_delta = PluralSituatedFormationBoundary(second_substrate).enact(
            tuple(reversed(second)), delta_id="plural-formation-1"
        )
        self.assertEqual(first_delta, second_delta)
        self.assertEqual(first_substrate.state, second_substrate.state)

    def test_rejects_id_only_plurality_atomically(self):
        substrate, proposals = plural_fixture()
        duplicate = replace(
            proposals[0],
            proposal_id="proposal-2",
            formation=replace(proposals[0].formation, cut=replace(
                proposals[0].formation.cut, cut_id="cut-2"
            )),
        )
        self.assert_atomic_rejection(substrate, (proposals[0], duplicate))

    def test_rejects_cosmetically_reworded_plurality_atomically(self):
        substrate, proposals = plural_fixture()
        cosmetic_cut = replace(
            proposals[0].formation.cut,
            cut_id="cut-2",
            positions=(CutPosition("renamed", "different descriptive wording"),),
            exclusions=("different prose exclusion",),
            revision_conditions=("different prose revision condition",),
        )
        cosmetic = replace(
            proposals[0],
            proposal_id="proposal-2",
            formation=replace(
                proposals[0].formation,
                cut=cosmetic_cut,
                position_groundings=(
                    PositionGrounding("renamed", ("noticing-1",)),
                ),
            ),
        )
        self.assert_atomic_rejection(substrate, (proposals[0], cosmetic))

    def test_rejects_self_checking_proposal_atomically(self):
        substrate, proposals = plural_fixture()
        self_checked = replace(
            proposals[1], checking_participation_ids=("apparatus-1",)
        )
        self.assert_atomic_rejection(substrate, (proposals[0], self_checked))

    def test_rejects_unaccounted_checker_atomically(self):
        substrate, proposals = plural_fixture()
        unaccounted = replace(
            proposals[1], checking_participation_ids=("apparatus-hidden",)
        )
        self.assert_atomic_rejection(substrate, (proposals[0], unaccounted))

    def test_rejects_relabelled_self_checking_apparatus_atomically(self):
        substrate, proposals = plural_fixture()
        origin = proposals[1].formation.apparatus_participations[0]
        relabelled = replace(origin, participation_id="apparatus-check")
        formation = replace(
            proposals[1].formation,
            apparatus_participations=(origin, relabelled),
        )
        self.assert_atomic_rejection(
            substrate, (proposals[0], replace(proposals[1], formation=formation))
        )

    def test_one_invalid_proposal_leaves_no_partial_plurality(self):
        substrate, proposals = plural_fixture()
        invalid = replace(
            proposals[1],
            formation=replace(proposals[1].formation, noticings=()),
        )
        self.assert_atomic_rejection(substrate, (proposals[0], invalid))

    def test_concurrent_proposals_cannot_encode_hidden_stage_order(self):
        substrate, proposals = plural_fixture()
        dependent = replace(
            proposals[1],
            formation=replace(
                proposals[1].formation,
                cut=replace(proposals[1].formation.cut, dependency_ids=("cut-1",)),
            ),
        )
        self.assert_atomic_rejection(substrate, (proposals[0], dependent))

    def test_unrelated_arrival_cuts_cannot_simulate_plurality(self):
        substrate, proposals = plural_fixture()
        substrate.record_transport(
            TransportTrace("arrival-2", "text", "digest-2", b"elsewhere", "now")
        )
        second = proposals[1]
        participations = tuple(
            replace(item, trace_ids=("arrival-2",))
            for item in second.formation.apparatus_participations
        )
        noticing = replace(
            second.formation.noticings[0],
            evidence=(EvidenceSpan("arrival-2", 0, 9),),
        )
        unrelated = replace(
            second,
            formation=replace(
                second.formation,
                cut=replace(second.formation.cut, transport_basis=("arrival-2",)),
                apparatus_participations=participations,
                noticings=(noticing,),
            ),
        )
        self.assert_atomic_rejection(substrate, (proposals[0], unrelated))

    def test_plural_boundary_exposes_no_chooser_or_evaluator_state(self):
        forbidden = {
            "accepted", "canonical", "chosen", "confidence", "correct",
            "preferred", "primary", "rank", "score", "selected", "winner",
        }
        record_types = (
            AccountableSituatedProposal,
            PluralSituatedFormationBoundary,
        )
        for record_type in record_types:
            names = set(getattr(record_type, "__dataclass_fields__", ()))
            self.assertTrue(names.isdisjoint(forbidden))
        substrate, proposals = plural_fixture()
        delta = PluralSituatedFormationBoundary(substrate).enact(
            proposals, delta_id="plural-formation-1"
        )
        self.assertTrue(set(vars(delta)).isdisjoint(forbidden))

    def assert_atomic_rejection(self, substrate, proposals):
        with self.assertRaises(InvalidReconfiguration):
            PluralSituatedFormationBoundary(substrate).enact(
                proposals, delta_id="plural-formation-1"
            )
        self.assertEqual((), substrate.state.active_cut_ids)
        self.assertEqual((), substrate.state.deltas)


class InspectablePluralOriginationTests(unittest.TestCase):
    def test_distinct_origins_generate_concurrent_proposals(self):
        substrate, field, proposals = origination_fixture()
        delta = InspectablePluralOriginationBoundary(substrate).enact(
            field, proposals, delta_id="originated-plurality-1"
        )
        self.assertEqual(("cut-1", "cut-2"), delta.activated_cut_ids)

    def test_no_origin_may_control_complete_proposal_field(self):
        substrate, field, proposals = origination_fixture()
        controlled = replace(
            field,
            proposal_originations=tuple(
                replace(
                    origination,
                    originating_participation_ids=("apparatus-1",),
                )
                for origination in field.proposal_originations
            ),
        )
        second = replace(
            proposals[1],
            formation=replace(
                proposals[1].formation,
                apparatus_participations=(
                    proposals[0].formation.apparatus_participations[0],
                    proposals[1].formation.apparatus_participations[1],
                ),
                noticings=(replace(
                    proposals[1].formation.noticings[0],
                    apparatus_participation_ids=("apparatus-1", "apparatus-check"),
                ),),
            ),
            originating_participation_ids=("apparatus-1",),
        )
        self.assert_atomic_rejection(substrate, controlled, (proposals[0], second))

    def test_rejects_unaccounted_proposal_origination(self):
        substrate, field, proposals = origination_fixture()
        incomplete = replace(
            field, proposal_originations=(field.proposal_originations[0],)
        )
        self.assert_atomic_rejection(substrate, incomplete, proposals)

    def test_rejects_ornamental_originating_participation(self):
        substrate, field, proposals = origination_fixture()
        ornamental = replace(
            field.originating_participations[0],
            participation_id="apparatus-ornamental",
            condition="another materially described apparatus condition",
        )
        self.assert_atomic_rejection(
            substrate,
            replace(
                field,
                originating_participations=field.originating_participations
                + (ornamental,),
            ),
            proposals,
        )

    def test_rejects_relabelled_originating_participation(self):
        substrate, field, proposals = origination_fixture()
        relabelled = replace(
            field.originating_participations[0], participation_id="apparatus-2"
        )
        self.assert_atomic_rejection(
            substrate,
            replace(
                field,
                originating_participations=(
                    field.originating_participations[0],
                    relabelled,
                ),
            ),
            proposals,
        )

    def test_requires_inspectable_generative_difference(self):
        substrate, field, proposals = origination_fixture()
        originations = (
            replace(field.proposal_originations[0], generative_differences=()),
            field.proposal_originations[1],
        )
        self.assert_atomic_rejection(
            substrate,
            replace(field, proposal_originations=originations),
            proposals,
        )

    def test_field_origin_cannot_rebind_proposal_apparatus(self):
        substrate, field, proposals = origination_fixture()
        rebound = replace(
            field.originating_participations[0],
            condition="a field-only account not present in the proposal",
        )
        self.assert_atomic_rejection(
            substrate,
            replace(
                field,
                originating_participations=(
                    rebound,
                    field.originating_participations[1],
                ),
            ),
            proposals,
        )

    def test_requires_unavailable_possibilities_and_reopening_conditions(self):
        substrate, field, proposals = origination_fixture()
        self.assert_atomic_rejection(
            substrate, replace(field, unavailable_or_ungenerated=()), proposals
        )

    def test_origination_order_confers_no_authority(self):
        first_substrate, first_field, first_proposals = origination_fixture()
        second_substrate, second_field, second_proposals = origination_fixture()
        first_delta = InspectablePluralOriginationBoundary(first_substrate).enact(
            first_field, first_proposals, delta_id="originated-plurality-1"
        )
        second_delta = InspectablePluralOriginationBoundary(second_substrate).enact(
            replace(
                second_field,
                originating_participations=tuple(
                    reversed(second_field.originating_participations)
                ),
                proposal_originations=tuple(
                    reversed(second_field.proposal_originations)
                ),
            ),
            tuple(reversed(second_proposals)),
            delta_id="originated-plurality-1",
        )
        self.assertEqual(first_delta, second_delta)
        self.assertEqual(first_substrate.state, second_substrate.state)

    def test_origination_records_expose_no_coverage_or_chooser_authority(self):
        forbidden = {
            "accepted", "canonical", "chosen", "complete", "confidence",
            "correct", "coverage", "preferred", "rank", "score", "selected",
            "winner",
        }
        for record_type in (
            ProposalOrigination,
            InspectableOriginationField,
            InspectablePluralOriginationBoundary,
        ):
            names = set(getattr(record_type, "__dataclass_fields__", ()))
            self.assertTrue(names.isdisjoint(forbidden))

    def assert_atomic_rejection(self, substrate, field, proposals):
        with self.assertRaises(InvalidReconfiguration):
            InspectablePluralOriginationBoundary(substrate).enact(
                field, proposals, delta_id="originated-plurality-1"
            )
        self.assertEqual((), substrate.state.active_cut_ids)
        self.assertEqual((), substrate.state.deltas)


class RecordedPluralOriginationTests(unittest.TestCase):
    def test_enactment_derives_field_from_separate_recorded_emissions(self):
        substrate, assembly, contributions = recorded_origination_fixture()
        assembly.record(contributions[0])
        assembly.record(contributions[1])
        delta = assembly.enact(delta_id="recorded-plurality-1")
        self.assertEqual(("cut-1", "cut-2"), delta.activated_cut_ids)

    def test_final_enactment_accepts_no_caller_supplied_field(self):
        _, assembly, _ = recorded_origination_fixture()
        self.assertEqual(
            ("delta_id",),
            tuple(inspect.signature(assembly.enact).parameters),
        )

    def test_rejects_arrival_as_proposal_emission(self):
        substrate, assembly, contributions = recorded_origination_fixture()
        disguised = replace(
            contributions[0],
            emission_evidence=(EvidenceSpan("arrival-1", 0, 10),),
        )
        with self.assertRaises(InvalidReconfiguration):
            assembly.record(disguised)
        self.assertEqual((), substrate.state.active_cut_ids)

    def test_rejects_opaque_model_emission_provenance(self):
        substrate, assembly, contributions = recorded_origination_fixture()
        substrate.record_transport(TransportTrace(
            "opaque-emission", "model-output", "opaque-digest",
            b"opaque proposal", "now",
        ))
        opaque = replace(
            contributions[0],
            emission_evidence=(EvidenceSpan("opaque-emission", 0, 15),),
        )
        with self.assertRaises(InvalidReconfiguration):
            assembly.record(opaque)

    def test_rejects_one_emission_originating_multiple_proposals(self):
        substrate, assembly, contributions = recorded_origination_fixture()
        assembly.record(contributions[0])
        reused = replace(
            contributions[1],
            emission_evidence=contributions[0].emission_evidence,
        )
        with self.assertRaises(InvalidReconfiguration):
            assembly.record(reused)
        self.assertEqual((), substrate.state.active_cut_ids)

    def test_rejects_rebound_contribution_id(self):
        _, assembly, contributions = recorded_origination_fixture()
        assembly.record(contributions[0])
        with self.assertRaises(InvalidReconfiguration):
            assembly.record(replace(
                contributions[1], contribution_id="contribution-1"
            ))

    def test_invalid_proposal_is_not_retained_as_a_contribution(self):
        _, assembly, contributions = recorded_origination_fixture()
        invalid = replace(
            contributions[0],
            proposal=replace(
                contributions[0].proposal,
                formation=replace(
                    contributions[0].proposal.formation,
                    noticings=(),
                ),
            ),
        )
        with self.assertRaises(InvalidReconfiguration):
            assembly.record(invalid)
        assembly.record(contributions[0])

    def test_cannot_enact_one_recorded_contribution(self):
        substrate, assembly, contributions = recorded_origination_fixture()
        assembly.record(contributions[0])
        with self.assertRaises(InvalidReconfiguration):
            assembly.enact(delta_id="recorded-plurality-1")
        self.assertEqual((), substrate.state.active_cut_ids)

    def test_contribution_order_confers_no_authority(self):
        first_substrate, first_assembly, first = recorded_origination_fixture()
        second_substrate, second_assembly, second = recorded_origination_fixture()
        for contribution in first:
            first_assembly.record(contribution)
        for contribution in reversed(second):
            second_assembly.record(contribution)
        first_delta = first_assembly.enact(delta_id="recorded-plurality-1")
        second_delta = second_assembly.enact(delta_id="recorded-plurality-1")
        self.assertEqual(first_delta, second_delta)
        self.assertEqual(first_substrate.state, second_substrate.state)

    def test_record_shapes_expose_no_selection_or_certification(self):
        forbidden = {
            "accepted", "certified", "chosen", "complete", "confidence",
            "correct", "coverage", "preferred", "rank", "score", "selected",
            "winner",
        }
        for record_type in (
            RecordedProposalContribution,
            RecordedPluralOriginationAssembly,
        ):
            names = set(getattr(record_type, "__dataclass_fields__", ()))
            self.assertTrue(names.isdisjoint(forbidden))
        _, assembly, contributions = recorded_origination_fixture()
        assembly.record(contributions[0])
        self.assertTrue(set(vars(assembly)).isdisjoint(forbidden))


class DependencyActivatedOriginationTests(unittest.TestCase):
    @staticmethod
    def record_later_material(substrate, trace_id="later-material"):
        substrate.record_transport(TransportTrace(
            trace_id,
            "text",
            "later-digest-" + trace_id,
            b"later material changes the available relation",
            "later",
        ))

    def test_activation_trace_exposes_participation_without_evaluation(self):
        _, assembly, contributions, _ = activated_origination_fixture(
            include_unanswered=True
        )
        self.assertEqual(
            ("invitation-1", "invitation-2", "invitation-unanswered"),
            assembly.activation_trace.unanswered_invitation_ids,
        )
        assembly.record(invitation_id="invitation-2", contribution=contributions[1])
        self.assertEqual(
            ("invitation-2",),
            assembly.activation_trace.answered_invitation_ids,
        )
        self.assertEqual(
            ("invitation-1", "invitation-unanswered"),
            assembly.activation_trace.unanswered_invitation_ids,
        )

    def test_unresolved_relation_activates_distinct_proposal_participation(self):
        substrate, assembly, contributions, _ = activated_origination_fixture()
        assembly.record(invitation_id="invitation-1", contribution=contributions[0])
        assembly.record(invitation_id="invitation-2", contribution=contributions[1])
        delta = assembly.enact(delta_id="activated-plurality-1")
        self.assertEqual(("cut-1", "cut-2"), delta.activated_cut_ids)
        self.assertEqual(("cut-1", "cut-2"), substrate.state.active_cut_ids)

    def test_unanswered_invitation_does_not_create_fixed_stage_barrier(self):
        _, assembly, contributions, _ = activated_origination_fixture(
            include_unanswered=True
        )
        assembly.record(invitation_id="invitation-1", contribution=contributions[0])
        assembly.record(invitation_id="invitation-2", contribution=contributions[1])
        assembly.enact(delta_id="activated-plurality-1")
        self.assertEqual(
            ("invitation-unanswered",),
            assembly.activation_trace.unanswered_invitation_ids,
        )

    def test_one_invitation_answer_cannot_enact_semantic_field(self):
        substrate, assembly, contributions, _ = activated_origination_fixture()
        assembly.record(invitation_id="invitation-1", contribution=contributions[0])
        with self.assertRaises(InvalidReconfiguration):
            assembly.enact(delta_id="activated-plurality-1")
        self.assertEqual((), substrate.state.active_cut_ids)

    def test_one_emission_cannot_answer_multiple_invitations(self):
        substrate, assembly, contributions, _ = activated_origination_fixture()
        assembly.record(invitation_id="invitation-1", contribution=contributions[0])
        reused = replace(
            contributions[1], emission_evidence=contributions[0].emission_evidence
        )
        with self.assertRaises(InvalidReconfiguration):
            assembly.record(invitation_id="invitation-2", contribution=reused)
        self.assertEqual((), substrate.state.active_cut_ids)

    def test_contribution_id_cannot_be_rebound_across_invitations(self):
        substrate, assembly, contributions, _ = activated_origination_fixture()
        assembly.record(invitation_id="invitation-1", contribution=contributions[0])
        rebound = replace(
            contributions[1], contribution_id=contributions[0].contribution_id
        )
        with self.assertRaises(InvalidReconfiguration):
            assembly.record(invitation_id="invitation-2", contribution=rebound)
        self.assertEqual(
            ("invitation-1",), assembly.activation_trace.answered_invitation_ids
        )
        self.assertEqual((), substrate.state.active_cut_ids)

    def test_proposal_must_answer_its_invited_apparatus(self):
        substrate, assembly, contributions, _ = activated_origination_fixture()
        with self.assertRaises(InvalidReconfiguration):
            assembly.record(
                invitation_id="invitation-1", contribution=contributions[1]
            )
        self.assertEqual((), substrate.state.active_cut_ids)

    def test_rejects_invitation_detached_from_unresolved_evidence(self):
        substrate, _, contributions, invitations = activated_origination_fixture()
        detached = replace(
            invitations[1],
            participation=replace(
                invitations[1].participation, trace_ids=("emission-2",)
            ),
        )
        with self.assertRaises(InvalidReconfiguration):
            DependencyActivatedOriginationAssembly(
                substrate,
                field_id="activated-field-1",
                unresolved_relations=(UnresolvedArrivalRelation(
                    "relation-1",
                    (EvidenceSpan("arrival-1", 0, 27),),
                    "an unresolved local difference",
                    ("unavailable relations",),
                    ("later material revises the relation",),
                ),),
                invitations=(invitations[0], detached),
                unavailable_or_ungenerated=("other participation",),
                revision_conditions=("new material reopens activation",),
            )

    def test_rejects_materially_identical_invitations(self):
        substrate, _, _, invitations = activated_origination_fixture()
        duplicate = replace(
            invitations[0], invitation_id="invitation-2"
        )
        with self.assertRaises(InvalidReconfiguration):
            DependencyActivatedOriginationAssembly(
                substrate,
                field_id="activated-field-1",
                unresolved_relations=(UnresolvedArrivalRelation(
                    "relation-1",
                    (EvidenceSpan("arrival-1", 0, 27),),
                    "an unresolved local difference",
                    ("unavailable relations",),
                    ("later material revises the relation",),
                ),),
                invitations=(invitations[0], duplicate),
                unavailable_or_ungenerated=("other participation",),
                revision_conditions=("new material reopens activation",),
            )

    def test_activation_records_expose_no_priority_or_stage_authority(self):
        forbidden = {
            "accepted", "complete", "confidence", "correct", "next_stage",
            "preferred", "priority", "rank", "score", "selected", "winner",
        }
        for record_type in (
            UnresolvedArrivalRelation,
            ProposalParticipationInvitation,
            OriginationActivationTrace,
            FormationTransformationRequest,
            ProposedFormationMaterial,
            FormationChallengeMaterial,
            DependencyActivatedOriginationAssembly,
        ):
            names = set(getattr(record_type, "__dataclass_fields__", ()))
            self.assertTrue(names.isdisjoint(forbidden))

    def test_invitation_and_answer_order_confer_no_activation_authority(self):
        first_substrate, first_assembly, first, _ = activated_origination_fixture()
        second_substrate, second_assembly, second, _ = (
            activated_origination_fixture(
                reverse_invitations=True,
                reverse_invocations=True,
            )
        )
        first_assembly.record(invitation_id="invitation-1", contribution=first[0])
        first_assembly.record(invitation_id="invitation-2", contribution=first[1])
        second_assembly.record(invitation_id="invitation-2", contribution=second[1])
        second_assembly.record(invitation_id="invitation-1", contribution=second[0])
        first_delta = first_assembly.enact(delta_id="activated-plurality-1")
        second_delta = second_assembly.enact(delta_id="activated-plurality-1")
        self.assertEqual(first_delta, second_delta)
        self.assertEqual(first_substrate.state, second_substrate.state)

    def test_invocation_receives_exact_unresolved_material_and_limits(self):
        _, assembly, _, _ = activated_origination_fixture()
        participant = FixtureProposalParticipant(
            b"another provisional emission", "provider-c", "model-c"
        )
        assembly.invoke(
            invitation_id="invitation-1",
            participant=participant,
            trace_id="activated-emission-3",
            observed_at="later",
        )
        request = participant.requests[0]
        self.assertIsInstance(request, ProposalParticipationRequest)
        self.assertEqual(b"we need another arrangement", request.evidence[0].payload)
        self.assertEqual(("relation-1",), request.unresolved_relation_ids)
        self.assertEqual(("cannot establish a singular intention",), request.limits)

    def test_invocation_records_runtime_bound_transport_provenance(self):
        substrate, assembly, _, _ = activated_origination_fixture()
        span = assembly.invoke(
            invitation_id="invitation-1",
            participant=FixtureProposalParticipant(
                b"another provisional emission", "provider-c", "model-c"
            ),
            trace_id="activated-emission-3",
            observed_at="later",
        )
        trace = substrate.state.transports[span.trace_id]
        self.assertEqual("invitation-1", trace.provenance["invitation_id"])
        self.assertEqual(("relation-1",), trace.provenance["unresolved_relation_ids"])
        self.assertEqual(("arrival-1",), trace.provenance["arrival_trace_ids"])
        self.assertEqual(sha256(trace.payload).hexdigest(), trace.digest)

    def test_emission_cannot_cross_to_another_invitation(self):
        substrate, assembly, contributions, _ = activated_origination_fixture()
        crossed = replace(
            contributions[1],
            emission_evidence=contributions[0].emission_evidence,
        )
        with self.assertRaises(InvalidReconfiguration):
            assembly.record(invitation_id="invitation-2", contribution=crossed)
        self.assertEqual((), substrate.state.active_cut_ids)

    def test_failed_invocation_records_no_transport_or_answer(self):
        substrate, assembly, _, _ = activated_origination_fixture()
        before = substrate.state
        with self.assertRaises(RuntimeError):
            assembly.invoke(
                invitation_id="invitation-1",
                participant=FailingProposalParticipant(),
                trace_id="failed-emission",
                observed_at="later",
            )
        self.assertEqual(before, substrate.state)
        self.assertEqual((), assembly.activation_trace.answered_invitation_ids)

    def test_opaque_model_invocation_records_no_transport(self):
        substrate, assembly, _, _ = activated_origination_fixture()
        before = substrate.state
        with self.assertRaises(InvalidReconfiguration):
            assembly.invoke(
                invitation_id="invitation-1",
                participant=OpaqueModelParticipant(),
                trace_id="opaque-invocation",
                observed_at="later",
            )
        self.assertEqual(before, substrate.state)

    def test_participant_cannot_return_formed_semantic_contribution(self):
        substrate, assembly, contributions, _ = activated_origination_fixture()
        before = substrate.state
        with self.assertRaises(InvalidReconfiguration):
            assembly.invoke(
                invitation_id="invitation-1",
                participant=SemanticFormerParticipant(contributions[0]),
                trace_id="semantic-former-output",
                observed_at="later",
            )
        self.assertEqual(before, substrate.state)

    def test_runtime_transforms_and_records_provisional_contributions(self):
        substrate, assembly, contributions, _ = activated_origination_fixture()
        first = assembly.transform_and_record(
            invitation_id="invitation-1",
            emission_trace_id="activated-emission-1",
            transformer=FixtureFormationTransformer(contributions[0]),
            transformation_participation=transformation_participation(
                contributions[0], "activated-emission-1"
            ),
            counter_participant=FixtureFormationCounterParticipant(
                contributions[0].proposal.formation.apparatus_participations[1]
            ),
            proposal_id="cut-1",
            contribution_id="transformed-contribution-1",
        )
        second = assembly.transform_and_record(
            invitation_id="invitation-2",
            emission_trace_id="activated-emission-2",
            transformer=FixtureFormationTransformer(contributions[1]),
            transformation_participation=transformation_participation(
                contributions[1], "activated-emission-2"
            ),
            counter_participant=FixtureFormationCounterParticipant(
                contributions[1].proposal.formation.apparatus_participations[1]
            ),
            proposal_id="cut-2",
            contribution_id="transformed-contribution-2",
        )
        self.assertEqual("cut-1", first.proposal.formation.cut.cut_id)
        self.assertEqual("cut-2", second.proposal.formation.cut.cut_id)
        delta = assembly.enact(delta_id="transformed-plurality-1")
        self.assertEqual(("cut-1", "cut-2"), delta.activated_cut_ids)
        self.assertEqual(("cut-1", "cut-2"), substrate.state.active_cut_ids)

    def test_transformer_receives_exact_emission_and_arrival_material(self):
        _, assembly, contributions, _ = activated_origination_fixture()
        transformer = FixtureFormationTransformer(contributions[0])
        assembly.transform_and_record(
            invitation_id="invitation-1",
            emission_trace_id="activated-emission-1",
            transformer=transformer,
            transformation_participation=transformation_participation(
                contributions[0], "activated-emission-1"
            ),
            counter_participant=FixtureFormationCounterParticipant(
                contributions[0].proposal.formation.apparatus_participations[1]
            ),
            proposal_id="cut-1",
            contribution_id="transformed-contribution-1",
        )
        request = transformer.requests[0]
        self.assertIsInstance(request, FormationTransformationRequest)
        self.assertEqual(
            b"one locally addressable position",
            request.emission_evidence.payload,
        )
        self.assertEqual(
            b"we need another arrangement",
            request.arrival_evidence[0].payload,
        )

    def test_counter_participation_materially_reopens_provisional_cut(self):
        _, assembly, contributions, _ = activated_origination_fixture()
        counter = FixtureFormationCounterParticipant(
            contributions[0].proposal.formation.apparatus_participations[1]
        )
        contribution = assembly.transform_and_record(
            invitation_id="invitation-1",
            emission_trace_id="activated-emission-1",
            transformer=FixtureFormationTransformer(contributions[0]),
            transformation_participation=transformation_participation(
                contributions[0], "activated-emission-1"
            ),
            counter_participant=counter,
            proposal_id="cut-1",
            contribution_id="transformed-contribution-1",
        )
        cut = contribution.proposal.formation.cut
        self.assertIn("counter-utterance", {item.key for item in cut.positions})
        self.assertIn("complicates", {item.relation_type for item in cut.relations})
        self.assertIn(
            "relations exposed only by counter-participation", cut.exclusions
        )
        self.assertIn(
            "counter-material disturbs the proposed distinction",
            cut.revision_conditions,
        )
        self.assertIn(
            "the proposed distinction remains locally contestable",
            contribution.proposal.formation.noticings[0].unavailable_or_excluded,
        )

    def test_originating_apparatus_cannot_counter_check_its_formation(self):
        substrate, assembly, contributions, _ = activated_origination_fixture()
        with self.assertRaises(InvalidReconfiguration):
            assembly.transform_and_record(
                invitation_id="invitation-1",
                emission_trace_id="activated-emission-1",
                transformer=FixtureFormationTransformer(contributions[0]),
                transformation_participation=transformation_participation(
                    contributions[0], "activated-emission-1"
                ),
                counter_participant=FixtureFormationCounterParticipant(
                    contributions[0].originating_participation
                ),
                proposal_id="cut-1",
                contribution_id="transformed-contribution-1",
            )
        self.assertEqual((), assembly.activation_trace.answered_invitation_ids)
        self.assertEqual((), substrate.state.active_cut_ids)

    def test_invalid_transformation_cannot_answer_or_enact(self):
        substrate, assembly, contributions, _ = activated_origination_fixture()
        with self.assertRaises(InvalidReconfiguration):
            assembly.transform_and_record(
                invitation_id="invitation-1",
                emission_trace_id="activated-emission-1",
                transformer=InvalidFormationTransformer(),
                transformation_participation=transformation_participation(
                    contributions[0], "activated-emission-1"
                ),
                counter_participant=FixtureFormationCounterParticipant(
                    contributions[0].proposal.formation.apparatus_participations[1]
                ),
                proposal_id="cut-1",
                contribution_id="transformed-contribution-1",
            )
        self.assertEqual((), assembly.activation_trace.answered_invitation_ids)
        self.assertEqual((), substrate.state.active_cut_ids)

    def test_transformation_apparatus_is_retained_in_provisional_formation(self):
        _, assembly, contributions, _ = activated_origination_fixture()
        transformation = transformation_participation(
            contributions[0], "activated-emission-1"
        )
        contribution = assembly.transform_and_record(
            invitation_id="invitation-1",
            emission_trace_id="activated-emission-1",
            transformer=FixtureFormationTransformer(contributions[0]),
            transformation_participation=transformation,
            counter_participant=FixtureFormationCounterParticipant(
                contributions[0].proposal.formation.apparatus_participations[1]
            ),
            proposal_id="cut-1",
            contribution_id="transformed-contribution-1",
        )
        self.assertIn(
            transformation,
            contribution.proposal.formation.apparatus_participations,
        )
        self.assertIn(
            transformation.participation_id,
            contribution.proposal.formation.noticings[0].apparatus_participation_ids,
        )

    def test_prose_only_counter_participation_cannot_record_formation(self):
        substrate, assembly, contributions, _ = activated_origination_fixture()
        with self.assertRaises(InvalidReconfiguration):
            assembly.transform_and_record(
                invitation_id="invitation-1",
                emission_trace_id="activated-emission-1",
                transformer=FixtureFormationTransformer(contributions[0]),
                transformation_participation=transformation_participation(
                    contributions[0], "activated-emission-1"
                ),
                counter_participant=StringOnlyFormationCounterParticipant(
                    contributions[0].proposal.formation.apparatus_participations[1]
                ),
                proposal_id="cut-1",
                contribution_id="transformed-contribution-1",
            )
        self.assertEqual((), assembly.activation_trace.answered_invitation_ids)
        self.assertEqual((), substrate.state.active_cut_ids)

    def test_ungrounded_counter_structure_cannot_record_formation(self):
        substrate, assembly, contributions, _ = activated_origination_fixture()
        with self.assertRaises(InvalidReconfiguration):
            assembly.transform_and_record(
                invitation_id="invitation-1",
                emission_trace_id="activated-emission-1",
                transformer=FixtureFormationTransformer(contributions[0]),
                transformation_participation=transformation_participation(
                    contributions[0], "activated-emission-1"
                ),
                counter_participant=UngroundedFormationCounterParticipant(
                    contributions[0].proposal.formation.apparatus_participations[1]
                ),
                proposal_id="cut-1",
                contribution_id="transformed-contribution-1",
            )
        self.assertEqual((), assembly.activation_trace.answered_invitation_ids)
        self.assertEqual((), substrate.state.active_cut_ids)

    def test_later_material_reopens_enacted_formation(self):
        substrate, assembly, contributions, _ = activated_origination_fixture()
        transform_activated_contributions(assembly, contributions)
        assembly.enact(delta_id="transformed-plurality-1")
        self.record_later_material(substrate)
        trace = reopening_activation(assembly).enact(
            delta_id="formation-reopening-1"
        )
        self.assertIsInstance(trace, FormationReopeningTrace)
        self.assertEqual(("cut-1", "cut-2"), trace.invalidated_cut_ids)
        self.assertEqual((), substrate.state.active_cut_ids)
        self.assertEqual(
            ("invitation-1", "invitation-2"),
            assembly.activation_trace.invalidated_invitation_ids,
        )
        self.assertEqual(
            ("reopening-account-1", "reopening-account-2"),
            trace.activation_contribution_ids,
        )

    def test_relation_material_activation_requires_plural_contributions(self):
        substrate, assembly, _, _ = activated_origination_fixture()
        self.record_later_material(substrate)
        activation = reopening_activation(assembly, contribution_count=1)
        with self.assertRaises(InvalidReconfiguration):
            activation.enact(delta_id="formation-reopening-1")
        self.assertEqual((), assembly.reopening_traces)

    def test_pending_relation_material_activation_is_inspectable(self):
        substrate, assembly, _, _ = activated_origination_fixture()
        self.record_later_material(substrate)
        activation = reopening_activation(assembly)
        self.assertEqual(
            ("reopening-account-1", "reopening-account-2"),
            tuple(item.contribution_id for item in activation.contributions),
        )

    def test_final_reopening_accepts_no_caller_supplied_semantic_field(self):
        self.assertEqual(
            ("delta_id",),
            tuple(inspect.signature(
                InspectableReopeningActivationAssembly.enact
            ).parameters)[1:],
        )

    def test_executable_participants_form_plural_activation(self):
        substrate, assembly, _, _ = activated_origination_fixture()
        self.record_later_material(substrate)
        activation = executable_reopening_activation(substrate, assembly)
        trace = activation.enact(delta_id="executable-reopening-delta-1")
        self.assertEqual(
            (
                "executable-activation-contribution-1",
                "executable-activation-contribution-2",
            ),
            trace.activation_contribution_ids,
        )

    def test_raw_activation_emission_cannot_reopen_relation(self):
        substrate, assembly, _, _ = activated_origination_fixture()
        self.record_later_material(substrate)
        activation = ExecutableReopeningActivationAssembly(
            assembly,
            field_id="raw-activation-field",
            reopening_id="raw-reopening",
            later_material_evidence=(EvidenceSpan("later-material", 0, 45),),
            unavailable_or_ungenerated=("unformed activation",),
            revision_conditions=("formation remains open",),
        )
        origin = ApparatusParticipation(
            "raw-activation-origin", "raw activation condition",
            ("arrival-1", "later-material"), ("raw difference",), ("raw limit",),
            ("raw revision",),
        )
        activation.invoke(
            participation=origin,
            participant=FixtureActivationParticipant(
                b"raw activation", "provider-raw", "model-raw"
            ),
            trace_id="raw-activation-emission",
            observed_at="later",
        )
        self.assertEqual((), activation.contributions)
        self.assertEqual((), assembly.reopening_traces)

    def test_executable_activation_retains_emission_and_forming_apparatus(self):
        substrate, assembly, _, _ = activated_origination_fixture()
        self.record_later_material(substrate)
        activation = executable_reopening_activation(
            substrate, assembly, contribution_count=1
        )
        contribution = activation.contributions[0]
        self.assertEqual(("activation-emission-1",), tuple(
            span.trace_id for span in contribution.emission_evidence
        ))
        self.assertEqual(3, len(contribution.apparatus_participations))
        self.assertEqual(
            {"arrival-1", "later-material"},
            set(substrate.state.transports[
                "activation-emission-1"
            ].provenance["source_dependencies"]),
        )

    def test_one_executable_activation_cannot_reopen_complete_field(self):
        substrate, assembly, _, _ = activated_origination_fixture()
        self.record_later_material(substrate)
        activation = executable_reopening_activation(
            substrate, assembly, contribution_count=1
        )
        with self.assertRaises(InvalidReconfiguration):
            activation.enact(delta_id="incomplete-executable-reopening")
        self.assertEqual((), assembly.reopening_traces)

    def test_executable_reopening_enactment_accepts_only_delta(self):
        self.assertEqual(
            ("delta_id",),
            tuple(inspect.signature(
                ExecutableReopeningActivationAssembly.enact
            ).parameters)[1:],
        )

    def test_text_document_tool_and_material_arrivals_form_counter_grounded_cuts(self):
        substrate = ReconfigurationSubstrate()
        arrivals = (
            ("arrival-text", "text/plain", b"a direct textual request"),
            ("arrival-document", "application/pdf", b"document-extracted material"),
            ("arrival-tool", "tool-result", b"tool returned a bounded observation"),
            ("arrival-material", "material-state", b"the doorway is now locked"),
        )
        for trace_id, channel, payload in arrivals:
            substrate.record_transport(TransportTrace(
                trace_id, channel, sha256(payload).hexdigest(), payload, "now"
            ))
        evidence = tuple(
            EvidenceSpan(trace_id, 0, len(payload))
            for trace_id, _, payload in arrivals
        )
        trace_ids = tuple(sorted(trace_id for trace_id, _, _ in arrivals))
        relation = UnresolvedArrivalRelation(
            "mixed-arrival-relation",
            evidence,
            "the arrivals do not predeclare one semantic event",
            ("bodily and historical relations unavailable to transport",),
            ("another arrival changes the local relation",),
        )
        invitations = tuple(
            ProposalParticipationInvitation(
                f"mixed-invitation-{index}",
                ("mixed-arrival-relation",),
                ApparatusParticipation(
                    f"mixed-origin-{index}",
                    f"materially distinct mixed-arrival condition {index}",
                    trace_ids,
                    (f"mixed-arrival difference {index}",),
                    (f"mixed-arrival exclusion {index}",),
                    (f"mixed-arrival revision {index}",),
                ),
                f"mixed-arrival possibility {index}",
                (f"mixed invitation limit {index}",),
                (f"mixed invitation deactivation {index}",),
            )
            for index in (1, 2)
        )
        assembly = DependencyActivatedOriginationAssembly(
            substrate,
            field_id="mixed-arrival-field",
            unresolved_relations=(relation,),
            invitations=invitations,
            unavailable_or_ungenerated=("other mixed-arrival formations",),
            revision_conditions=("new mixed material reopens formation",),
        )
        for index, invitation in enumerate(invitations, start=1):
            emission_id = f"mixed-emission-{index}"
            assembly.invoke(
                invitation_id=invitation.invitation_id,
                participant=FixtureProposalParticipant(
                    f"opaque mixed proposal {index}".encode(),
                    f"mixed-provider-{index}",
                    f"mixed-model-{index}",
                ),
                trace_id=emission_id,
                observed_at="now",
            )
            transformer = ApparatusParticipation(
                f"mixed-transform-{index}",
                f"mixed transformation condition {index}",
                tuple(sorted(set(trace_ids).union({emission_id}))),
                (f"mixed transformation difference {index}",),
                (f"mixed transformation exclusion {index}",),
                (f"mixed transformation revision {index}",),
            )
            checker = ApparatusParticipation(
                f"mixed-check-{index}",
                f"mixed structural probe condition {index}",
                trace_ids,
                (f"counter-cut difference {index}",),
                (f"counter-cut exclusion {index}",),
                (f"counter-cut revision {index}",),
            )
            contribution = assembly.transform_and_record(
                invitation_id=invitation.invitation_id,
                emission_trace_id=emission_id,
                transformer=MixedArrivalFormationTransformer(
                    f"mixed-cut-{index}", index
                ),
                transformation_participation=transformer,
                counter_participant=FixtureFormationCounterParticipant(checker),
                proposal_id=f"mixed-cut-{index}",
                contribution_id=f"mixed-contribution-{index}",
            )
            self.assertTrue(any(
                position.key.startswith("counter-")
                for position in contribution.proposal.formation.cut.positions
            ))
        delta = assembly.enact(delta_id="mixed-arrival-formation")
        self.assertEqual(("mixed-cut-1", "mixed-cut-2"), delta.activated_cut_ids)
        self.assertEqual(set(trace_ids), set(delta.triggering_trace_ids))

    def test_reopening_revises_apparatus_descriptions_inside_relation_basis(self):
        substrate, assembly, _, invitations = activated_origination_fixture()
        self.record_later_material(substrate)
        executable_reopening_activation(substrate, assembly).enact(
            delta_id="apparatus-reopening-delta"
        )
        revisions = {}
        for index, invitation in enumerate(invitations, start=1):
            revisions[invitation.invitation_id] = ProposalParticipationInvitation(
                f"revised-invitation-{index}",
                invitation.unresolved_relation_ids,
                ApparatusParticipation(
                    f"revised-apparatus-{index}",
                    invitation.participation.condition + " changed by later material",
                    ("arrival-1", "later-material"),
                    invitation.participation.makes_perceptible
                    + ("the apparatus description is locally revisable",),
                    invitation.participation.obscures_or_excludes,
                    invitation.participation.revision_conditions,
                ),
                invitation.difference_opened,
                invitation.limits,
                invitation.deactivation_conditions,
            )
            assembly.record_apparatus_revision(
                reopening_id="executable-reopening-1",
                invalidated_invitation_id=invitation.invitation_id,
                revised_invitation=revisions[invitation.invitation_id],
            )
        revised = assembly.reconfigure_after_reopening(
            reopening_id="executable-reopening-1",
            new_field_id="revised-apparatus-field",
        )
        participant = FixtureProposalParticipant(
            b"proposal after apparatus revision", "provider-revised", "model-revised"
        )
        revised.invoke(
            invitation_id="revised-invitation-1",
            participant=participant,
            trace_id="revised-emission-1",
            observed_at="later",
        )
        self.assertEqual(
            {"arrival-1", "later-material"},
            {item.trace_id for item in participant.requests[0].evidence},
        )

    def test_reopening_rejects_cosmetic_apparatus_rebinding(self):
        substrate, assembly, _, invitations = activated_origination_fixture()
        self.record_later_material(substrate)
        executable_reopening_activation(substrate, assembly).enact(
            delta_id="apparatus-reopening-delta"
        )
        cosmetic = {
            invitation.invitation_id: replace(
                invitation,
                invitation_id="cosmetic-" + invitation.invitation_id,
                participation=replace(
                    invitation.participation,
                    participation_id="cosmetic-" + invitation.participation.participation_id,
                    trace_ids=("arrival-1", "later-material"),
                ),
            )
            for invitation in invitations
        }
        with self.assertRaises(InvalidReconfiguration):
            assembly.record_apparatus_revision(
                reopening_id="executable-reopening-1",
                invalidated_invitation_id="invitation-1",
                revised_invitation=cosmetic["invitation-1"],
            )

    def test_incomplete_apparatus_revisions_cannot_reform_field(self):
        substrate, assembly, _, invitations = activated_origination_fixture()
        self.record_later_material(substrate)
        executable_reopening_activation(substrate, assembly).enact(
            delta_id="apparatus-reopening-delta"
        )
        invitation = invitations[0]
        revised = replace(
            invitation,
            invitation_id="partial-revised-invitation",
            participation=replace(
                invitation.participation,
                participation_id="partial-revised-apparatus",
                condition="partial apparatus changed through later material",
                trace_ids=("arrival-1", "later-material"),
            ),
        )
        assembly.record_apparatus_revision(
            reopening_id="executable-reopening-1",
            invalidated_invitation_id=invitation.invitation_id,
            revised_invitation=revised,
        )
        with self.assertRaises(InvalidReconfiguration):
            assembly.reconfigure_after_reopening(
                reopening_id="executable-reopening-1",
                new_field_id="partial-revised-field",
            )

    def test_final_apparatus_reconfiguration_accepts_no_revision_field(self):
        self.assertEqual(
            ("reopening_id", "new_field_id"),
            tuple(inspect.signature(
                DependencyActivatedOriginationAssembly.reconfigure_after_reopening
            ).parameters)[1:],
        )

    def test_one_participation_cannot_supply_complete_activation_field(self):
        substrate, assembly, _, _ = activated_origination_fixture()
        self.record_later_material(substrate)
        activation = reopening_activation(assembly, contribution_count=1)
        template = reopening_activation(assembly).contributions[1]
        rebound = replace(
            template,
            participation=replace(
                template.participation,
                participation_id="reopening-apparatus-1",
            ),
        )
        with self.assertRaises(InvalidReconfiguration):
            activation.record(rebound)

    def test_reopening_activation_requires_exact_later_material_apparatus(self):
        substrate, assembly, _, _ = activated_origination_fixture()
        self.record_later_material(substrate)
        activation = InspectableReopeningActivationAssembly(
            assembly,
            field_id="reopening-activation-field-detached",
            reopening_id="reopening-detached",
            unavailable_or_ungenerated=("unavailable activation",),
            revision_conditions=("later activation reopens this field",),
        )
        first = reopening_activation(assembly, contribution_count=1).contributions[0]
        detached = replace(
            first,
            participation=replace(first.participation, trace_ids=("arrival-1",)),
        )
        with self.assertRaises(InvalidReconfiguration):
            activation.record(detached)

    def test_activation_order_confers_no_reopening_authority(self):
        first_substrate, first_assembly, _, _ = activated_origination_fixture()
        second_substrate, second_assembly, _, _ = activated_origination_fixture()
        self.record_later_material(first_substrate)
        self.record_later_material(second_substrate)
        first_activation = reopening_activation(first_assembly)
        second_activation = reopening_activation(second_assembly, reverse=True)
        first_trace = first_activation.enact(delta_id="formation-reopening-1")
        second_trace = second_activation.enact(delta_id="formation-reopening-1")
        self.assertEqual(first_trace, second_trace)

    def test_reopening_recursively_invalidates_dependent_cut(self):
        substrate, assembly, contributions, _ = activated_origination_fixture()
        transform_activated_contributions(assembly, contributions)
        assembly.enact(delta_id="transformed-plurality-1")
        substrate.enact_cut(
            CutEnactment(
                cut_id="dependent-cut",
                transport_basis=("arrival-1",),
                dependency_ids=("cut-1",),
                lineage_ids=(),
                positions=(CutPosition("dependent", "dependent local position"),),
                revision_conditions=("dependency disturbance reopens this cut",),
                exclusions=("relations outside this dependent cut",),
            ),
            delta_id="dependent-enactment",
        )
        self.record_later_material(substrate)
        trace = reopening_activation(assembly).enact(
            delta_id="formation-reopening-1"
        )
        self.assertEqual(
            {"cut-1", "cut-2", "dependent-cut"},
            set(trace.invalidated_cut_ids),
        )
        self.assertEqual((), substrate.state.active_cut_ids)

    def test_reopening_withdraws_provisional_answers_before_enactment(self):
        substrate, assembly, contributions, _ = activated_origination_fixture()
        transform_activated_contributions(assembly, contributions)
        self.record_later_material(substrate)
        trace = reopening_activation(assembly).enact(
            delta_id="formation-reopening-1"
        )
        self.assertEqual(("cut-1", "cut-2"), trace.invalidated_proposal_ids)
        self.assertEqual((), trace.invalidated_cut_ids)
        self.assertIsNone(trace.substrate_delta_id)
        self.assertEqual((), assembly.activation_trace.answered_invitation_ids)
        with self.assertRaises(InvalidReconfiguration):
            assembly.enact(delta_id="transformed-plurality-1")

    def test_reopening_preserves_arrival_and_emission_transport_history(self):
        substrate, assembly, contributions, _ = activated_origination_fixture()
        transform_activated_contributions(assembly, contributions)
        preserved_ids = set(substrate.state.transports)
        self.record_later_material(substrate)
        reopening_activation(assembly).enact(delta_id="formation-reopening-1")
        self.assertTrue(preserved_ids.issubset(substrate.state.transports))

    def test_invalidated_invitation_cannot_emit_or_transform_again(self):
        substrate, assembly, contributions, _ = activated_origination_fixture()
        self.record_later_material(substrate)
        reopening_activation(assembly).enact(delta_id="formation-reopening-1")
        with self.assertRaises(InvalidReconfiguration):
            assembly.invoke(
                invitation_id="invitation-1",
                participant=FixtureProposalParticipant(
                    b"stale emission", "provider-c", "model-c"
                ),
                trace_id="stale-emission",
                observed_at="later",
            )
        with self.assertRaises(InvalidReconfiguration):
            assembly.transform_and_record(
                invitation_id="invitation-1",
                emission_trace_id="activated-emission-1",
                transformer=FixtureFormationTransformer(contributions[0]),
                transformation_participation=transformation_participation(
                    contributions[0], "activated-emission-1"
                ),
                counter_participant=FixtureFormationCounterParticipant(
                    contributions[0].proposal.formation.apparatus_participations[1]
                ),
                proposal_id="cut-1",
                contribution_id="stale-contribution",
            )

    def test_original_arrival_cannot_masquerade_as_reopening_material(self):
        substrate, assembly, _, _ = activated_origination_fixture()
        before = substrate.state
        with self.assertRaises(InvalidReconfiguration):
            reopening_activation(assembly, trace_id="arrival-1")
        self.assertEqual(before, substrate.state)
        self.assertEqual((), assembly.reopening_traces)

    def test_reopening_trace_exposes_no_failure_or_maturity_authority(self):
        forbidden = {
            "accepted", "confidence", "correct", "failure", "maturity",
            "preferred", "rank", "score", "selected", "winner",
        }
        for record_type in (
            FormationReopeningTrace,
            RelationMaterialActivationContribution,
            RelationMaterialActivationRequest,
            RelationMaterialTransformationRequest,
            ProposedRelationMaterialActivation,
            RelationMaterialActivationChallenge,
        ):
            self.assertTrue(
                set(record_type.__dataclass_fields__).isdisjoint(forbidden)
            )

    def test_raw_emission_does_not_answer_invitation_or_enact_cut(self):
        substrate, assembly, _, _ = activated_origination_fixture()
        assembly.invoke(
            invitation_id="invitation-1",
            participant=FixtureProposalParticipant(
                b"unformed proposal material", "provider-c", "model-c"
            ),
            trace_id="activated-emission-3",
            observed_at="later",
        )
        self.assertEqual((), assembly.activation_trace.answered_invitation_ids)
        self.assertEqual((), substrate.state.active_cut_ids)


if __name__ == "__main__":
    unittest.main()
