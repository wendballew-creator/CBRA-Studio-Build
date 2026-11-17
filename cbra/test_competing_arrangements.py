from dataclasses import fields, replace
import unittest

from cbra.reconfiguration import (
    Allocation,
    ArrangementExplorer,
    CutEnactment,
    CutPosition,
    EffectDirection,
    EffectMeasure,
    HarmConstraint,
    InvalidReconfiguration,
    LocalPositionRef,
    ProhibitedChange,
    ReconfigurationSubstrate,
    Relation,
    StructuralDimension,
    TransportTrace,
    retain_competing_alternatives,
)


def local(cut_id: str, key: str) -> LocalPositionRef:
    return LocalPositionRef(cut_id, key)


def transport(trace_id: str, payload: str) -> TransportTrace:
    return TransportTrace(
        trace_id=trace_id,
        channel="text/plain",
        digest=f"digest:{trace_id}",
        payload=payload.encode(),
        observed_at="2026-08-04T00:00:00Z",
        provenance={"technical_channel": "fixture"},
    )


def case2_source(cut_id: str = "cut:case2-open") -> CutEnactment:
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


class CompetingArrangementTests(unittest.TestCase):
    def setUp(self):
        self.substrate = ReconfigurationSubstrate()
        self.substrate.record_transport(transport("transport:missed", "Work did not arrive."))
        self.substrate.record_transport(
            transport("transport:disclosure", "I have too much to hold.")
        )
        self.source = case2_source()
        self.substrate.enact_cut(self.source, delta_id="delta:source")
        self.explorer = ArrangementExplorer(self.substrate)
        self.shared = self.explorer.redistribute_concentrated_burden(
            source_cut_id=self.source.cut_id,
            source_position_key="disclosure",
            support_position_keys=("coordination",),
            alternative_cut_id="cut:shared",
            retained_source_fraction=0.5,
        ).replacement
        self.distributed = self.explorer.redistribute_concentrated_burden(
            source_cut_id=self.source.cut_id,
            source_position_key="disclosure",
            support_position_keys=("coordination", "affected"),
            alternative_cut_id="cut:distributed",
            retained_source_fraction=0.25,
        ).replacement
        self.constraints = (
            HarmConstraint(
                "constraint:no-consequence-increase",
                StructuralDimension.CONSEQUENCE,
                EffectMeasure.TOTAL,
                ProhibitedChange.INCREASE,
            ),
            HarmConstraint(
                "constraint:no-further-burden-concentration",
                StructuralDimension.BURDEN,
                EffectMeasure.MAXIMUM_LOCAL_LOAD,
                ProhibitedChange.INCREASE,
            ),
            HarmConstraint(
                "constraint:keep-possibility-open",
                StructuralDimension.POSSIBILITY,
                EffectMeasure.TOTAL,
                ProhibitedChange.DECREASE,
            ),
        )

    def field(self, replacements=None, constraints=None):
        return retain_competing_alternatives(
            source=self.source,
            replacements=replacements or (self.shared, self.distributed),
            constraints=self.constraints if constraints is None else constraints,
        )

    def test_retains_multiple_case2_arrangements_without_a_winner(self):
        field = self.field()
        self.assertEqual(
            ("cut:shared", "cut:distributed"),
            tuple(item.replacement.cut_id for item in field.alternatives),
        )
        names = {item.name for item in fields(field)}
        self.assertTrue(
            names.isdisjoint({"score", "ranking", "selected", "preferred", "winner"})
        )
        self.assertFalse(hasattr(field, "choose"))
        self.assertFalse(hasattr(field, "best"))

    def test_each_alternative_traces_every_structural_dimension(self):
        field = self.field()
        for alternative in field.alternatives:
            self.assertEqual(tuple(StructuralDimension), tuple(x.dimension for x in alternative.effects))
        burden = field.alternatives[0].effects[0]
        self.assertEqual(EffectDirection.REDISTRIBUTED, burden.direction)
        self.assertEqual((4.0, 2.0), (burden.maximum_before, burden.maximum_after))

    def test_harm_increase_is_retained_as_trace_not_removed_or_scored(self):
        harmful = replace(
            self.distributed,
            cut_id="cut:harm-increase",
            allocations=self.distributed.allocations
            + (
                Allocation(
                    StructuralDimension.CONSEQUENCE,
                    local("cut:harm-increase", "affected"),
                    3,
                ),
            ),
            relations=tuple(
                Relation(item.relation_type, local("cut:harm-increase", item.source.position_key), local("cut:harm-increase", item.target.position_key))
                for item in self.distributed.relations
            ),
        )
        # Rebind every pre-existing allocation to the new local cut.
        harmful = replace(
            harmful,
            allocations=tuple(
                Allocation(item.dimension, local(harmful.cut_id, item.position.position_key), item.amount)
                for item in harmful.allocations
            ),
        )
        field = self.field(replacements=(self.shared, harmful))
        traced = field.alternatives[1]
        self.assertTrue(traced.crosses_harm_constraint)
        self.assertEqual(("constraint:no-consequence-increase",), tuple(x.constraint_id for x in traced.harm_increases))
        self.assertEqual((2.0, 5.0), (traced.harm_increases[0].before, traced.harm_increases[0].after))
        self.assertIn(traced, field.alternatives)

    def test_harm_is_not_inferred_without_an_explicit_constraint(self):
        reduced_possibility = replace(
            self.distributed,
            cut_id="cut:closed-possibility",
            relations=tuple(
                Relation(item.relation_type, local("cut:closed-possibility", item.source.position_key), local("cut:closed-possibility", item.target.position_key))
                for item in self.distributed.relations
            ),
            allocations=tuple(
                Allocation(item.dimension, local("cut:closed-possibility", item.position.position_key), 0 if item.dimension == StructuralDimension.POSSIBILITY else item.amount)
                for item in self.distributed.allocations
            ),
        )
        without = self.field(replacements=(self.shared, reduced_possibility), constraints=())
        with_boundary = self.field(replacements=(self.shared, reduced_possibility))
        self.assertFalse(without.alternatives[1].crosses_harm_constraint)
        self.assertEqual(
            ("constraint:keep-possibility-open",),
            tuple(x.constraint_id for x in with_boundary.alternatives[1].harm_increases),
        )

    def test_duplicate_topology_does_not_masquerade_as_competing(self):
        duplicate = replace(
            self.shared,
            cut_id="cut:compassionate-words",
            positions=tuple(CutPosition(x.key, "compassionate " + x.local_name) for x in self.shared.positions),
            relations=tuple(
                Relation("compassionate-support", local("cut:compassionate-words", x.source.position_key), local("cut:compassionate-words", x.target.position_key))
                for x in self.shared.relations
            ),
            allocations=tuple(
                Allocation(x.dimension, local("cut:compassionate-words", x.position.position_key), x.amount)
                for x in self.shared.allocations
            ),
        )
        with self.assertRaisesRegex(InvalidReconfiguration, "duplicated topology"):
            self.field(replacements=(self.shared, duplicate))

    def test_renamed_position_keys_cannot_evade_duplicate_detection(self):
        renamed = replace(
            self.distributed,
            cut_id="cut:renamed-keys",
            positions=tuple(
                CutPosition(f"renamed-{item.key}", item.local_name)
                for item in self.distributed.positions
            ),
            relations=tuple(
                Relation(
                    item.relation_type,
                    local("cut:renamed-keys", f"renamed-{item.source.position_key}"),
                    local("cut:renamed-keys", f"renamed-{item.target.position_key}"),
                )
                for item in self.distributed.relations
            ),
            allocations=tuple(
                Allocation(
                    item.dimension,
                    local("cut:renamed-keys", f"renamed-{item.position.position_key}"),
                    item.amount,
                )
                for item in self.distributed.allocations
            ),
        )
        with self.assertRaisesRegex(InvalidReconfiguration, "position correspondence"):
            self.field(replacements=(self.shared, renamed))

    def test_one_option_is_not_competing_variation(self):
        with self.assertRaisesRegex(InvalidReconfiguration, "at least two"):
            self.field(replacements=(self.shared,))

    def test_paraphrased_demands_cannot_enter_the_alternative_field(self):
        before = self.substrate.state
        for index, payload in enumerate(
            ("Send another date.", "When will it be ready?", "Flag slippage sooner."),
            start=1,
        ):
            self.substrate.record_transport(transport(f"transport:paraphrase:{index}", payload))
        field = self.field()
        self.assertEqual(2, len(field.alternatives))
        self.assertEqual(before.deltas, self.substrate.state.deltas)

    def test_constraints_are_independent_not_aggregated(self):
        field = self.field()
        self.assertEqual(self.constraints, field.constraints)
        names = {item.name for item in fields(field.alternatives[0])}
        self.assertTrue(names.isdisjoint({"score", "harm_score", "net_effect", "utility"}))

    def test_duplicate_constraint_cannot_create_implicit_weighting(self):
        duplicate = HarmConstraint(
            "constraint:same-boundary-again",
            StructuralDimension.CONSEQUENCE,
            EffectMeasure.TOTAL,
            ProhibitedChange.INCREASE,
        )
        with self.assertRaisesRegex(InvalidReconfiguration, "implicit weighting"):
            self.field(constraints=self.constraints + (duplicate,))

    def test_harm_trace_does_not_reorder_alternatives(self):
        closed = replace(
            self.distributed,
            cut_id="cut:closed-first",
            relations=tuple(
                Relation(item.relation_type, local("cut:closed-first", item.source.position_key), local("cut:closed-first", item.target.position_key))
                for item in self.distributed.relations
            ),
            allocations=tuple(
                Allocation(
                    item.dimension,
                    local("cut:closed-first", item.position.position_key),
                    0 if item.dimension == StructuralDimension.POSSIBILITY else item.amount,
                )
                for item in self.distributed.allocations
            ),
        )
        field = self.field(replacements=(closed, self.shared))
        self.assertTrue(field.alternatives[0].crosses_harm_constraint)
        self.assertEqual(
            ("cut:closed-first", "cut:shared"),
            tuple(item.replacement.cut_id for item in field.alternatives),
        )


if __name__ == "__main__":
    unittest.main()
