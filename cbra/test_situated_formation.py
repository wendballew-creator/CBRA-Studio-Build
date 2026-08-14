from dataclasses import replace
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
    SituatedCutProposal,
    SituatedFormationBoundary,
    SituatedNoticing,
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


if __name__ == "__main__":
    unittest.main()
