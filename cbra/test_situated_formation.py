from dataclasses import replace
import unittest

from cbra.reconfiguration.formation import (
    ApparatusParticipation,
    EvidenceSpan,
    PositionGrounding,
    SituatedCutProposal,
    SituatedFormationBoundary,
    SituatedNoticing,
)
from cbra.reconfiguration.models import CutEnactment, CutPosition, TransportTrace
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


if __name__ == "__main__":
    unittest.main()
