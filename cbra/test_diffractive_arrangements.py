from dataclasses import fields, replace
import unittest

from cbra.reconfiguration import (
    Allocation,
    ArrangementDependency,
    ArrangementExplorer,
    ConsequentialDifference,
    CutEnactment,
    CutPosition,
    DiffractiveArrangementField,
    EffectMeasure,
    InvalidReconfiguration,
    LocalPositionRef,
    ReconfigurationSubstrate,
    Relation,
    StructuralDimension,
    TransportTrace,
    disturb_through_arrangement_difference,
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


def case2_source() -> CutEnactment:
    cut_id = "cut:case2-open"
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
    )


def dependent_cut(cut_id: str, dependency_id: str, name: str) -> CutEnactment:
    return CutEnactment(
        cut_id=cut_id,
        transport_basis=(),
        dependency_ids=(dependency_id,),
        lineage_ids=(),
        positions=(CutPosition("availability", name),),
    )


class DiffractiveArrangementTests(unittest.TestCase):
    def setUp(self):
        self.substrate = ReconfigurationSubstrate()
        self.substrate.record_transport(transport("transport:missed", "Work did not arrive."))
        self.substrate.record_transport(
            transport("transport:disclosure", "I have too much to hold.")
        )
        self.source = case2_source()
        self.substrate.enact_cut(self.source, delta_id="delta:source")
        explorer = ArrangementExplorer(self.substrate)
        shared = explorer.redistribute_concentrated_burden(
            source_cut_id=self.source.cut_id,
            source_position_key="disclosure",
            support_position_keys=("coordination",),
            alternative_cut_id="cut:shared",
            retained_source_fraction=0.5,
        ).replacement
        distributed = explorer.redistribute_concentrated_burden(
            source_cut_id=self.source.cut_id,
            source_position_key="disclosure",
            support_position_keys=("coordination", "affected"),
            alternative_cut_id="cut:distributed",
            retained_source_fraction=0.25,
        ).replacement
        competing = retain_competing_alternatives(
            source=self.source,
            replacements=(shared, distributed),
            constraints=(),
        )

        for cut, delta_id in (
            (dependent_cut("cut:enable-shared", self.source.cut_id, "shared availability"), "delta:enable-shared"),
            (dependent_cut("cut:shared-action", "cut:enable-shared", "shared actionability"), "delta:shared-action"),
            (dependent_cut("cut:shared-release", "cut:shared-action", "shared release condition"), "delta:shared-release"),
            (dependent_cut("cut:enable-distributed", self.source.cut_id, "distributed availability"), "delta:enable-distributed"),
            (dependent_cut("cut:distributed-action", "cut:enable-distributed", "distributed actionability"), "delta:distributed-action"),
        ):
            self.substrate.enact_cut(cut, delta_id=delta_id)

        self.field = DiffractiveArrangementField(
            competing=competing,
            dependencies=(
                ArrangementDependency("cut:shared", ("cut:enable-shared",)),
                ArrangementDependency("cut:distributed", ("cut:enable-distributed",)),
            ),
        )

    def difference(self, dimension=StructuralDimension.BURDEN, measure=EffectMeasure.MAXIMUM_LOCAL_LOAD):
        return ConsequentialDifference(
            witness_alternative_id="cut:distributed",
            contrasted_alternative_id="cut:shared",
            dimension=dimension,
            measure=measure,
        )

    def disturb(self, **overrides):
        values = dict(
            field=self.field,
            substrate=self.substrate,
            difference=self.difference(),
            enabling_cut_id="cut:enable-shared",
            delta_id="delta:burden-diffraction",
            triggering_trace_ids=("transport:disclosure",),
        )
        values.update(overrides)
        return disturb_through_arrangement_difference(**values)

    def test_difference_reopens_enabling_cut_and_recursive_dependents(self):
        revised = self.disturb()
        trace = revised.disturbances[0]
        self.assertEqual((1.5, 2.0), (trace.witness_value, trace.reopened_value))
        self.assertEqual(
            {"cut:enable-shared", "cut:shared-action", "cut:shared-release"},
            set(trace.invalidated_cut_ids),
        )
        self.assertNotIn("cut:enable-shared", self.substrate.state.active_cut_ids)
        self.assertIn("cut:enable-distributed", self.substrate.state.active_cut_ids)

    def test_reopened_alternative_is_retained_as_evidence_not_removed(self):
        revised = self.disturb()
        self.assertEqual(self.field.competing, revised.competing)
        self.assertEqual(
            ("cut:shared", "cut:distributed"),
            tuple(x.replacement.cut_id for x in revised.competing.alternatives),
        )
        self.assertEqual(("cut:distributed",), revised.disturbances[0].left_intact_alternative_ids)

    def test_equal_effects_cannot_masquerade_as_diffraction(self):
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "equal arrangement effects"):
            self.disturb(
                difference=self.difference(
                    StructuralDimension.CONSEQUENCE, EffectMeasure.TOTAL
                )
            )
        self.assertEqual(before, self.substrate.state)

    def test_prose_and_relation_relabeling_cannot_create_difference(self):
        original = self.field.competing.alternatives[1].replacement
        renamed = replace(
            original,
            cut_id="cut:renamed-distributed",
            positions=tuple(CutPosition(x.key, "gentle " + x.local_name) for x in original.positions),
            relations=tuple(
                Relation("caring-" + x.relation_type, local("cut:renamed-distributed", x.source.position_key), local("cut:renamed-distributed", x.target.position_key))
                for x in original.relations
            ),
            allocations=tuple(
                Allocation(x.dimension, local("cut:renamed-distributed", x.position.position_key), x.amount)
                for x in original.allocations
            ),
        )
        with self.assertRaisesRegex(InvalidReconfiguration, "duplicated topology"):
            retain_competing_alternatives(
                source=self.source,
                replacements=(original, renamed),
                constraints=(),
            )

    def test_unbound_cut_cannot_be_reopened_by_an_alternative(self):
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "explicit enabling cut"):
            self.disturb(enabling_cut_id="cut:enable-distributed")
        self.assertEqual(before, self.substrate.state)

    def test_unrelated_cut_cannot_gain_authority_through_a_dependency_label(self):
        unrelated = CutEnactment(
            cut_id="cut:unrelated",
            transport_basis=("transport:missed",),
            dependency_ids=(),
            lineage_ids=(),
            positions=(CutPosition("unrelated", "unrelated availability"),),
        )
        self.substrate.enact_cut(unrelated, delta_id="delta:unrelated")
        self.substrate.enact_cut(
            dependent_cut("cut:unrelated-dependent", unrelated.cut_id, "dependent"),
            delta_id="delta:unrelated-dependent",
        )
        labelled_field = DiffractiveArrangementField(
            self.field.competing,
            (
                ArrangementDependency("cut:shared", (unrelated.cut_id,)),
                ArrangementDependency("cut:distributed", ("cut:enable-distributed",)),
            ),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "competing source cut"):
            self.disturb(field=labelled_field, enabling_cut_id=unrelated.cut_id)
        self.assertEqual(before, self.substrate.state)

    def test_single_part_change_cannot_be_called_diffractive(self):
        isolated = dependent_cut("cut:isolated-enabler", self.source.cut_id, "isolated")
        self.substrate.enact_cut(isolated, delta_id="delta:isolated")
        dependencies = (
            ArrangementDependency("cut:shared", ("cut:isolated-enabler",)),
            ArrangementDependency("cut:distributed", ("cut:enable-distributed",)),
        )
        isolated_field = DiffractiveArrangementField(self.field.competing, dependencies)
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "at least two dependent"):
            self.disturb(field=isolated_field, enabling_cut_id="cut:isolated-enabler")
        self.assertEqual(before, self.substrate.state)

    def test_every_alternative_requires_one_dependency_record(self):
        with self.assertRaisesRegex(InvalidReconfiguration, "every retained alternative"):
            DiffractiveArrangementField(
                self.field.competing,
                (ArrangementDependency("cut:shared", ("cut:enable-shared",)),),
            )

    def test_trace_contains_no_selection_or_scoring_authority(self):
        revised = self.disturb()
        names = {
            item.name
            for record in (revised, revised.disturbances[0])
            for item in fields(record)
        }
        self.assertTrue(
            names.isdisjoint(
                {"score", "rank", "ranking", "selected", "preferred", "winner"}
            )
        )
        self.assertFalse(hasattr(revised, "choose"))

    def test_reopened_arrangement_cannot_become_a_stale_witness(self):
        revised = self.disturb()
        reverse = ConsequentialDifference(
            witness_alternative_id="cut:shared",
            contrasted_alternative_id="cut:distributed",
            dimension=StructuralDimension.BURDEN,
            measure=EffectMeasure.MAXIMUM_LOCAL_LOAD,
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "before revision"):
            disturb_through_arrangement_difference(
                field=revised,
                substrate=self.substrate,
                difference=reverse,
                enabling_cut_id="cut:enable-distributed",
                delta_id="delta:stale-witness",
                triggering_trace_ids=("transport:disclosure",),
            )
        self.assertEqual(before, self.substrate.state)

    def test_transport_text_alone_cannot_reopen_an_arrangement(self):
        before = self.substrate.state
        self.substrate.record_transport(
            transport("transport:paraphrase", "Please send a revised date.")
        )
        self.assertEqual(before.deltas, self.substrate.state.deltas)
        self.assertEqual((), self.field.disturbances)


if __name__ == "__main__":
    unittest.main()
