from dataclasses import fields, replace
import unittest

from cbra.reconfiguration import (
    Allocation,
    ArrangementExplorer,
    BurdenRedistributionCandidate,
    CutEnactment,
    CutPosition,
    InvalidReconfiguration,
    LocalPositionRef,
    ReconfigurationSubstrate,
    Relation,
    StructuralDimension,
    TransportTrace,
    compare_arrangements,
)


def local(cut_id: str, key: str) -> LocalPositionRef:
    return LocalPositionRef(cut_id, key)


def transport(trace_id: str, payload: str) -> TransportTrace:
    return TransportTrace(
        trace_id=trace_id,
        channel="text/plain",
        digest=f"digest:{trace_id}",
        payload=payload.encode(),
        observed_at="2026-08-03T00:00:00Z",
        provenance={"technical_channel": "fixture"},
    )


def concentrated_arrangement(cut_id: str = "cut:case2-open") -> CutEnactment:
    return CutEnactment(
        cut_id=cut_id,
        transport_basis=("transport:missed", "transport:disclosure"),
        dependency_ids=(),
        lineage_ids=(),
        positions=(
            CutPosition("disclosure", "disclosing position"),
            CutPosition("coordination", "coordination arrangement"),
            CutPosition("affected", "affected work"),
        ),
        relations=(
            Relation(
                "capacity-shapes-scale",
                local(cut_id, "disclosure"),
                local(cut_id, "coordination"),
            ),
        ),
        allocations=(
            Allocation(StructuralDimension.BURDEN, local(cut_id, "disclosure"), 4),
            Allocation(StructuralDimension.CAPACITY, local(cut_id, "disclosure"), 3),
            Allocation(StructuralDimension.CONSEQUENCE, local(cut_id, "affected"), 2),
            Allocation(StructuralDimension.POWER, local(cut_id, "affected"), 2),
            Allocation(StructuralDimension.POSSIBILITY, local(cut_id, "coordination"), 1),
        ),
        revision_conditions=("observed effect",),
        exclusions=("unobserved capacity",),
    )


class ArrangementVariationTests(unittest.TestCase):
    def setUp(self):
        self.substrate = ReconfigurationSubstrate()
        self.substrate.record_transport(transport("transport:missed", "Work did not arrive."))
        self.substrate.record_transport(
            transport("transport:disclosure", "I have too much to hold.")
        )
        self.source = concentrated_arrangement()
        self.substrate.enact_cut(self.source, delta_id="delta:source")
        self.explorer = ArrangementExplorer(self.substrate)

    def candidate(self, **overrides):
        arguments = {
            "source_cut_id": self.source.cut_id,
            "source_position_key": "disclosure",
            "support_position_keys": ("coordination",),
            "alternative_cut_id": "cut:shared",
        }
        arguments.update(overrides)
        return self.explorer.redistribute_concentrated_burden(**arguments)

    def test_candidate_is_evidence_not_a_care_claim(self):
        candidate = self.candidate()
        self.assertIsInstance(candidate, BurdenRedistributionCandidate)
        names = {item.name for item in fields(candidate)}
        self.assertTrue(names.isdisjoint({"care", "care_score", "care_claim"}))
        self.assertEqual(
            (StructuralDimension.BURDEN,),
            candidate.comparison.changed_dimensions,
        )

    def test_alternative_redistributes_burden_and_preserves_total(self):
        candidate = self.candidate()
        before = candidate.comparison.before_shapes[0][1]
        after = candidate.comparison.after_shapes[0][1]
        self.assertEqual((4.0,), before)
        self.assertEqual((2.0, 2.0), after)
        self.assertEqual(sum(before), sum(after))
        self.assertTrue(candidate.comparison.preserves_consequence)

    def test_multiple_support_positions_change_the_allocation_shape(self):
        candidate = self.candidate(
            support_position_keys=("coordination", "affected"),
            retained_source_fraction=0.25,
        )
        self.assertEqual(
            (1.0, 1.5, 1.5), candidate.comparison.after_shapes[0][1]
        )

    def test_full_transfer_is_detected_even_when_shape_is_unchanged(self):
        candidate = self.candidate(retained_source_fraction=0)
        self.assertEqual((4.0,), candidate.comparison.before_shapes[0][1])
        self.assertEqual((4.0,), candidate.comparison.after_shapes[0][1])
        self.assertIn(
            StructuralDimension.BURDEN, candidate.comparison.changed_dimensions
        )

    def test_enacted_alternative_invalidates_source_and_dependents(self):
        dependent = CutEnactment(
            cut_id="cut:prospective-demand",
            transport_basis=("transport:missed",),
            dependency_ids=(self.source.cut_id,),
            lineage_ids=(),
            positions=(CutPosition("demand", "prospective demand"),),
        )
        self.substrate.enact_cut(dependent, delta_id="delta:dependent")
        candidate = self.candidate()
        delta = self.substrate.disturb(
            delta_id="delta:redistribution",
            triggering_trace_ids=("transport:disclosure",),
            invalidated_root_ids=(self.source.cut_id,),
            replacements=(candidate.replacement,),
        )
        self.assertEqual(
            {self.source.cut_id, dependent.cut_id}, set(delta.invalidated_cut_ids)
        )
        self.assertEqual((StructuralDimension.BURDEN,), delta.changed_dimensions)

    def test_removing_alternative_removes_structural_variation(self):
        candidate = self.candidate()
        removed = compare_arrangements(self.source, self.source)
        self.assertTrue(candidate.comparison.is_material_variation)
        self.assertFalse(removed.is_material_variation)

    def test_relabeling_same_arrangement_is_not_variation(self):
        relabelled = replace(
            self.source,
            cut_id="cut:renamed",
            positions=tuple(
                CutPosition(position.key, "different words")
                for position in self.source.positions
            ),
            relations=(
                Relation(
                    "different words",
                    local("cut:renamed", "disclosure"),
                    local("cut:renamed", "coordination"),
                ),
            ),
            allocations=tuple(
                Allocation(
                    item.dimension,
                    local("cut:renamed", item.position.position_key),
                    item.amount,
                )
                for item in self.source.allocations
            ),
        )
        comparison = compare_arrangements(self.source, relabelled)
        self.assertFalse(comparison.is_material_variation)

    def test_relation_text_alone_is_not_material_variation(self):
        changed_relation = replace(
            self.source,
            cut_id="cut:relation-only",
            relations=(
                Relation(
                    "supportive-and-compassionate",
                    local("cut:relation-only", "disclosure"),
                    local("cut:relation-only", "coordination"),
                ),
            ),
            allocations=tuple(
                Allocation(
                    item.dimension,
                    local("cut:relation-only", item.position.position_key),
                    item.amount,
                )
                for item in self.source.allocations
            ),
        )
        self.assertFalse(
            compare_arrangements(self.source, changed_relation).is_material_variation
        )

    def test_paraphrase_transport_does_not_create_an_alternative(self):
        before = self.substrate.state
        self.substrate.record_transport(
            transport("transport:paraphrase", "Please name another deadline.")
        )
        self.assertEqual(before.deltas, self.substrate.state.deltas)

    def test_nonconcentrated_burden_cannot_be_called_redistribution_candidate(self):
        balanced = replace(
            concentrated_arrangement("cut:balanced"),
            allocations=(
                Allocation(StructuralDimension.BURDEN, local("cut:balanced", "disclosure"), 2),
                Allocation(StructuralDimension.BURDEN, local("cut:balanced", "coordination"), 2),
            ),
        )
        self.substrate.enact_cut(balanced, delta_id="delta:balanced")
        with self.assertRaisesRegex(InvalidReconfiguration, "not structurally concentrated"):
            self.explorer.redistribute_concentrated_burden(
                source_cut_id="cut:balanced",
                source_position_key="disclosure",
                support_position_keys=("coordination",),
                alternative_cut_id="cut:false-care",
            )

    def test_support_cannot_escape_local_cut(self):
        with self.assertRaisesRegex(InvalidReconfiguration, "local to the source cut"):
            self.candidate(support_position_keys=("outside",))

    def test_candidate_does_not_read_or_reclassify_transport_payload(self):
        payloads_before = {
            key: item.payload for key, item in self.substrate.state.transports.items()
        }
        self.candidate()
        payloads_after = {
            key: item.payload for key, item in self.substrate.state.transports.items()
        }
        self.assertEqual(payloads_before, payloads_after)

    def test_consequence_erasure_is_visible_not_mistaken_for_care(self):
        candidate = self.candidate()
        erased = replace(
            candidate.replacement,
            allocations=tuple(
                item
                for item in candidate.replacement.allocations
                if item.dimension != StructuralDimension.CONSEQUENCE
            ),
        )
        comparison = compare_arrangements(self.source, erased)
        self.assertFalse(comparison.preserves_consequence)


if __name__ == "__main__":
    unittest.main()
