from dataclasses import fields, replace
import unittest

from cbra.reconfiguration import (
    Allocation,
    ArrangementStateWitness,
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
    ResponsivenessFinding,
    Relation,
    StructuralDimension,
    TransportTrace,
    audit_structural_responsiveness,
    counter_cut_from_oscillation,
    disturb_through_arrangement_difference,
    reenter_recomputed_arrangement_difference,
    retain_competing_alternatives,
    revise_reopened_arrangement,
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


class CounterCutRevisionTests(unittest.TestCase):
    setUp = DiffractiveArrangementTests.setUp
    difference = DiffractiveArrangementTests.difference
    disturb = DiffractiveArrangementTests.disturb

    def counter_cut(self, **overrides):
        values = dict(
            cut_id="cut:counter-shared",
            transport_basis=("transport:disclosure",),
            dependency_ids=(self.source.cut_id,),
            lineage_ids=("cut:enable-shared",),
            positions=(
                CutPosition("availability", "revised shared availability"),
                CutPosition("support", "support participation"),
            ),
            allocations=(
                Allocation(
                    StructuralDimension.CAPACITY,
                    local("cut:counter-shared", "support"),
                    1,
                ),
            ),
        )
        values.update(overrides)
        return CutEnactment(**values)

    def revised_arrangement(self, **overrides):
        original = self.field.competing.alternatives[0].replacement
        cut_id = overrides.pop("cut_id", "cut:shared-recomputed")
        values = dict(
            cut_id=cut_id,
            transport_basis=original.transport_basis,
            dependency_ids=("cut:counter-shared",),
            lineage_ids=(original.cut_id,),
            positions=tuple(
                CutPosition(item.key, item.local_name) for item in original.positions
            ),
            relations=tuple(
                Relation(
                    item.relation_type,
                    local(cut_id, item.source.position_key),
                    local(cut_id, item.target.position_key),
                )
                for item in original.relations
            ),
            allocations=tuple(
                Allocation(item.dimension, local(cut_id, item.position.position_key), item.amount)
                for item in original.allocations
                if item.dimension != StructuralDimension.BURDEN
            )
            + (
                Allocation(StructuralDimension.BURDEN, local(cut_id, "disclosure"), 1.25),
                Allocation(StructuralDimension.BURDEN, local(cut_id, "coordination"), 1.5),
                Allocation(StructuralDimension.BURDEN, local(cut_id, "affected"), 1.25),
            ),
            revision_conditions=original.revision_conditions,
            exclusions=original.exclusions,
        )
        values.update(overrides)
        return CutEnactment(**values)

    def revise(self, **overrides):
        disturbed = self.disturb()
        values = dict(
            field=disturbed,
            substrate=self.substrate,
            disturbance_delta_id="delta:burden-diffraction",
            counter_cut=self.counter_cut(),
            counter_cut_delta_id="delta:counter-shared",
            revised_arrangement=self.revised_arrangement(),
        )
        values.update(overrides)
        return revise_reopened_arrangement(**values)

    def test_counter_cut_recomputes_trace_and_preserves_disturbance_history(self):
        revised = self.revise()
        revision = revised.revisions[0]
        self.assertEqual("cut:shared", revision.reopened_alternative_id)
        self.assertEqual("cut:shared-recomputed", revision.revised_alternative_id)
        self.assertEqual(2.0, revision.prior_trace.effects[0].maximum_after)
        self.assertEqual(1.5, revision.recomputed_trace.effects[0].maximum_after)
        self.assertEqual(
            "delta:burden-diffraction", revision.disturbance_delta_id
        )
        self.assertEqual(1, len(revised.field.disturbances))
        self.assertEqual(
            "delta:burden-diffraction",
            revised.field.disturbances[0].delta.delta_id,
        )

    def test_counter_cut_is_active_and_invalidated_formation_remains_recorded(self):
        self.revise()
        self.assertIn("cut:counter-shared", self.substrate.state.active_cut_ids)
        self.assertNotIn("cut:enable-shared", self.substrate.state.active_cut_ids)
        self.assertIn("cut:enable-shared", self.substrate.state.cuts)
        self.assertEqual(
            "delta:burden-diffraction",
            self.substrate.state.invalidated_by["cut:enable-shared"],
        )

    def test_revised_field_retains_ordinal_without_ranking_or_selection(self):
        revised = self.revise()
        self.assertEqual(
            ("cut:shared-recomputed", "cut:distributed"),
            tuple(
                item.replacement.cut_id
                for item in revised.field.competing.alternatives
            ),
        )
        names = {
            item.name
            for record in (revised, revised.revisions[0])
            for item in fields(record)
        }
        self.assertTrue(
            names.isdisjoint(
                {"score", "rank", "ranking", "selected", "preferred", "winner"}
            )
        )
        self.assertFalse(hasattr(revised, "choose"))

    def test_cosmetic_recomputation_fails_atomically(self):
        disturbed = self.disturb()
        before = self.substrate.state
        original = self.field.competing.alternatives[0].replacement
        cosmetic = replace(
            self.revised_arrangement(),
            allocations=tuple(
                Allocation(
                    item.dimension,
                    local("cut:shared-recomputed", item.position.position_key),
                    item.amount,
                )
                for item in original.allocations
            ),
        )
        with self.assertRaisesRegex(InvalidReconfiguration, "structurally changed"):
            revise_reopened_arrangement(
                field=disturbed,
                substrate=self.substrate,
                disturbance_delta_id="delta:burden-diffraction",
                counter_cut=self.counter_cut(),
                counter_cut_delta_id="delta:counter-shared",
                revised_arrangement=cosmetic,
            )
        self.assertEqual(before, self.substrate.state)


class RecursiveDiffractiveReentryTests(unittest.TestCase):
    setUp = DiffractiveArrangementTests.setUp
    difference = DiffractiveArrangementTests.difference
    disturb = DiffractiveArrangementTests.disturb
    counter_cut = CounterCutRevisionTests.counter_cut
    revised_arrangement = CounterCutRevisionTests.revised_arrangement
    revise = CounterCutRevisionTests.revise

    def first_revised_field(self):
        revised = self.revised_arrangement()
        revised = replace(
            revised,
            allocations=revised.allocations
            + (
                Allocation(
                    StructuralDimension.CAPACITY,
                    local(revised.cut_id, "coordination"),
                    1,
                ),
            ),
        )
        return self.revise(revised_arrangement=revised)

    @staticmethod
    def reentry_difference():
        return ConsequentialDifference(
            witness_alternative_id="cut:shared-recomputed",
            contrasted_alternative_id="cut:distributed",
            dimension=StructuralDimension.CAPACITY,
            measure=EffectMeasure.TOTAL,
        )

    def reenter(self, **overrides):
        revised = self.first_revised_field()
        values = dict(
            field=revised,
            substrate=self.substrate,
            difference=self.reentry_difference(),
            enabling_cut_id="cut:enable-distributed",
            delta_id="delta:recursive-reentry",
            triggering_trace_ids=("transport:disclosure",),
        )
        values.update(overrides)
        return reenter_recomputed_arrangement_difference(**values)

    def counter_distributed(self):
        return CutEnactment(
            cut_id="cut:counter-distributed",
            transport_basis=("transport:disclosure",),
            dependency_ids=(self.source.cut_id,),
            lineage_ids=("cut:enable-distributed",),
            positions=(
                CutPosition("availability", "revised distributed availability"),
                CutPosition("coordination", "coordination participation"),
            ),
            allocations=(
                Allocation(
                    StructuralDimension.POSSIBILITY,
                    local("cut:counter-distributed", "coordination"),
                    1,
                ),
            ),
        )

    def recomputed_distributed(self):
        original = self.field.competing.alternatives[1].replacement
        cut_id = "cut:distributed-recomputed"
        return CutEnactment(
            cut_id=cut_id,
            transport_basis=original.transport_basis,
            dependency_ids=("cut:counter-distributed",),
            lineage_ids=(original.cut_id,),
            positions=original.positions,
            relations=tuple(
                Relation(
                    item.relation_type,
                    local(cut_id, item.source.position_key),
                    local(cut_id, item.target.position_key),
                )
                for item in original.relations
            ),
            allocations=tuple(
                Allocation(
                    item.dimension,
                    local(cut_id, item.position.position_key),
                    3 if item.dimension == StructuralDimension.POWER else item.amount,
                )
                for item in original.allocations
            ),
        )

    def twice_revised_field(self):
        reentered = self.reenter()
        return revise_reopened_arrangement(
            field=reentered,
            substrate=self.substrate,
            disturbance_delta_id="delta:recursive-reentry",
            counter_cut=self.counter_distributed(),
            counter_cut_delta_id="delta:counter-distributed",
            revised_arrangement=self.recomputed_distributed(),
        )

    def test_recomputed_arrangement_reenters_as_current_structural_witness(self):
        reentered = self.reenter()
        trace = reentered.reentries[0]
        self.assertEqual("cut:shared-recomputed", trace.witness_alternative_id)
        self.assertEqual("cut:counter-shared", trace.witness_counter_cut_id)
        self.assertEqual("cut:enable-distributed", trace.target_enabling_cut_id)
        self.assertEqual((4.0, 3.0), (
            trace.disturbance.witness_value,
            trace.disturbance.reopened_value,
        ))
        self.assertNotIn("cut:enable-distributed", self.substrate.state.active_cut_ids)
        self.assertEqual(1, len(reentered.revisions))
        self.assertEqual(2, len(reentered.field.disturbances))

    def test_recomputed_arrangement_can_disturb_an_earlier_counter_cut(self):
        twice_revised = self.twice_revised_field()
        self.substrate.enact_cut(
            dependent_cut(
                "cut:counter-shared-dependent",
                "cut:counter-shared",
                "counter-cut dependent",
            ),
            delta_id="delta:counter-shared-dependent",
        )
        reordered = replace(
            twice_revised,
            revisions=tuple(reversed(twice_revised.revisions)),
        )
        final = reenter_recomputed_arrangement_difference(
            field=reordered,
            substrate=self.substrate,
            difference=ConsequentialDifference(
                witness_alternative_id="cut:distributed-recomputed",
                contrasted_alternative_id="cut:shared-recomputed",
                dimension=StructuralDimension.POWER,
                measure=EffectMeasure.TOTAL,
            ),
            enabling_cut_id="cut:counter-shared",
            delta_id="delta:counter-cut-reentry",
            triggering_trace_ids=("transport:disclosure",),
        )
        self.assertNotIn("cut:counter-shared", self.substrate.state.active_cut_ids)
        self.assertIn("cut:counter-distributed", self.substrate.state.active_cut_ids)
        self.assertEqual(2, len(final.revisions))
        self.assertEqual(2, len(final.reentries))
        self.assertEqual(
            {"cut:counter-shared", "cut:counter-shared-dependent"},
            set(final.reentries[-1].disturbance.invalidated_cut_ids),
        )

    def test_unrevised_alternative_has_no_recursive_reentry_authority(self):
        revised = self.first_revised_field()
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "exact recorded recomputation"):
            reenter_recomputed_arrangement_difference(
                field=revised,
                substrate=self.substrate,
                difference=ConsequentialDifference(
                    witness_alternative_id="cut:distributed",
                    contrasted_alternative_id="cut:shared-recomputed",
                    dimension=StructuralDimension.CAPACITY,
                    measure=EffectMeasure.TOTAL,
                ),
                enabling_cut_id="cut:counter-shared",
                delta_id="delta:unrevised-authority",
                triggering_trace_ids=("transport:disclosure",),
            )
        self.assertEqual(before, self.substrate.state)

    def test_repeated_revision_records_cannot_create_iteration_authority(self):
        revised = self.first_revised_field()
        inflated = replace(revised, revisions=revised.revisions * 2)
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "one exact recorded"):
            reenter_recomputed_arrangement_difference(
                field=inflated,
                substrate=self.substrate,
                difference=self.reentry_difference(),
                enabling_cut_id="cut:enable-distributed",
                delta_id="delta:iteration-authority",
                triggering_trace_ids=("transport:disclosure",),
            )
        self.assertEqual(before, self.substrate.state)

    def test_forged_revision_lineage_cannot_create_reentry_authority(self):
        revised = self.first_revised_field()
        forged_revision = replace(
            revised.revisions[0],
            disturbance_delta_id="delta:counter-shared",
        )
        forged = replace(revised, revisions=(forged_revision,))
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "invalidation history"):
            reenter_recomputed_arrangement_difference(
                field=forged,
                substrate=self.substrate,
                difference=self.reentry_difference(),
                enabling_cut_id="cut:enable-distributed",
                delta_id="delta:forged-reentry",
                triggering_trace_ids=("transport:disclosure",),
            )
        self.assertEqual(before, self.substrate.state)

    def test_inactive_witness_counter_cut_removes_reentry_authority(self):
        revised = self.first_revised_field()
        self.substrate.enact_cut(
            dependent_cut("cut:counter-dependent", "cut:counter-shared", "dependent"),
            delta_id="delta:counter-dependent",
        )
        self.substrate.disturb(
            delta_id="delta:invalidate-witness",
            triggering_trace_ids=("transport:disclosure",),
            invalidated_root_ids=("cut:counter-shared",),
            replacements=(),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "active enabling formation"):
            reenter_recomputed_arrangement_difference(
                field=revised,
                substrate=self.substrate,
                difference=self.reentry_difference(),
                enabling_cut_id="cut:enable-distributed",
                delta_id="delta:stale-reentry",
                triggering_trace_ids=("transport:disclosure",),
            )
        self.assertEqual(before, self.substrate.state)

    def test_reentry_records_expose_no_recency_depth_or_selection_authority(self):
        reentered = self.reenter()
        names = {
            item.name
            for record in (reentered, reentered.reentries[0])
            for item in fields(record)
        }
        self.assertTrue(names.isdisjoint({
            "score", "rank", "ranking", "selected", "preferred", "winner",
            "depth", "recency", "iteration", "generation",
        }))
        self.assertFalse(hasattr(reentered, "choose"))


class CounterCutRevisionValidationTests(unittest.TestCase):
    setUp = DiffractiveArrangementTests.setUp
    difference = DiffractiveArrangementTests.difference
    disturb = DiffractiveArrangementTests.disturb
    counter_cut = CounterCutRevisionTests.counter_cut
    revised_arrangement = CounterCutRevisionTests.revised_arrangement
    revise = CounterCutRevisionTests.revise

    def test_counter_cut_must_name_reopened_lineage(self):
        disturbed = self.disturb()
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "reopened enabling cut"):
            revise_reopened_arrangement(
                field=disturbed,
                substrate=self.substrate,
                disturbance_delta_id="delta:burden-diffraction",
                counter_cut=self.counter_cut(lineage_ids=(self.source.cut_id,)),
                counter_cut_delta_id="delta:counter-shared",
                revised_arrangement=self.revised_arrangement(),
            )
        self.assertEqual(before, self.substrate.state)


class StructuralResponsivenessTests(unittest.TestCase):
    setUp = DiffractiveArrangementTests.setUp
    difference = DiffractiveArrangementTests.difference
    disturb = DiffractiveArrangementTests.disturb
    counter_cut = CounterCutRevisionTests.counter_cut
    revised_arrangement = CounterCutRevisionTests.revised_arrangement
    revise = CounterCutRevisionTests.revise

    def traces(self):
        revised = self.revise()
        original = self.field.competing.alternatives[0]
        changed = revised.revisions[0].recomputed_trace
        return original, changed

    def witness(
        self,
        witness_id,
        trace,
        enabling,
        triggers=("transport:missed", "transport:disclosure"),
        deltas=("delta:source",),
    ):
        return ArrangementStateWitness(
            witness_id=witness_id,
            trace=trace,
            enabling_cut_ids=(enabling,),
            operative_delta_ids=deltas,
            triggering_trace_ids=triggers,
        )

    def test_structural_change_is_recorded_without_becoming_preference(self):
        original, changed = self.traces()
        audit = audit_structural_responsiveness((
            self.witness("state:a", original, "cut:enable-shared"),
            self.witness("state:b", changed, "cut:counter-shared"),
        ), substrate=self.substrate)
        self.assertEqual(ResponsivenessFinding.MATERIAL_CHANGE, audit.traces[0].finding)
        self.assertTrue(audit.traces[0].structural_change)

    def test_unsupported_return_to_prior_topology_is_oscillation(self):
        original, changed = self.traces()
        audit = audit_structural_responsiveness((
            self.witness("state:a", original, "cut:enable-shared"),
            self.witness("state:b", changed, "cut:enable-shared"),
            self.witness("state:a-return", original, "cut:enable-shared"),
        ), substrate=self.substrate)
        trace = audit.traces[-1]
        self.assertEqual(ResponsivenessFinding.STRUCTURAL_OSCILLATION, trace.finding)
        self.assertEqual("state:a", trace.recurring_witness_id)

    def test_recurrence_with_new_material_remains_responsive(self):
        original, changed = self.traces()
        self.substrate.record_transport(
            transport("transport:new-disturbance", "A new material disturbance.")
        )
        new_material = CutEnactment(
            cut_id="cut:new-material",
            transport_basis=("transport:new-disturbance",),
            dependency_ids=(self.source.cut_id,),
            lineage_ids=(),
            positions=(CutPosition("material", "new material participation"),),
        )
        self.substrate.enact_cut(new_material, delta_id="delta:new-material")
        audit = audit_structural_responsiveness((
            self.witness("state:a", original, "cut:enable-shared"),
            self.witness("state:b", changed, "cut:enable-shared"),
            self.witness(
                "state:a-return",
                original,
                "cut:counter-shared",
                ("transport:missed", "transport:disclosure", "transport:new-disturbance"),
                ("delta:source", "delta:new-material"),
            ),
        ), substrate=self.substrate)
        trace = audit.traces[-1]
        self.assertEqual(ResponsivenessFinding.MATERIAL_RECURRENCE, trace.finding)
        self.assertEqual(("transport:new-disturbance",), trace.new_triggering_trace_ids)
        self.assertTrue(trace.changed_enabling_formation)

    def test_persistence_is_not_convergence_or_preference(self):
        original, _ = self.traces()
        audit = audit_structural_responsiveness((
            self.witness("state:a", original, "cut:enable-shared"),
            self.witness("state:a-still", original, "cut:enable-shared"),
        ), substrate=self.substrate)
        self.assertEqual(
            ResponsivenessFinding.STRUCTURAL_PERSISTENCE,
            audit.traces[0].finding,
        )
        names = {
            item.name
            for record in (audit, audit.traces[0])
            for item in fields(record)
        }
        self.assertTrue(names.isdisjoint({
            "score", "rank", "selected", "preferred", "winner", "stable",
            "converged", "iteration", "limit", "terminal",
        }))
        self.assertFalse(hasattr(audit, "stop"))

    def test_unchanged_topology_can_remain_materially_responsive(self):
        original, _ = self.traces()
        self.substrate.record_transport(
            transport("transport:new-disturbance", "New material enters.")
        )
        new_material = CutEnactment(
            cut_id="cut:new-material",
            transport_basis=("transport:new-disturbance",),
            dependency_ids=(self.source.cut_id,),
            lineage_ids=(),
            positions=(CutPosition("material", "new material participation"),),
        )
        self.substrate.enact_cut(new_material, delta_id="delta:new-material")
        audit = audit_structural_responsiveness((
            self.witness("state:a", original, "cut:enable-shared"),
            self.witness(
                "state:a-responsive",
                original,
                "cut:enable-shared",
                ("transport:missed", "transport:disclosure", "transport:new-disturbance"),
                ("delta:source", "delta:new-material"),
            ),
        ), substrate=self.substrate)
        trace = audit.traces[0]
        self.assertEqual(ResponsivenessFinding.MATERIAL_RECURRENCE, trace.finding)
        self.assertFalse(trace.structural_change)

    def test_repetition_count_does_not_change_the_finding(self):
        original, changed = self.traces()
        prefix = (
            self.witness("state:a", original, "cut:enable-shared"),
            self.witness("state:b", changed, "cut:enable-shared"),
        )
        once = audit_structural_responsiveness(prefix + (
            self.witness("state:a-return", original, "cut:enable-shared"),
        ), substrate=self.substrate)
        many = audit_structural_responsiveness(prefix + (
            self.witness("state:a-return", original, "cut:enable-shared"),
            self.witness("state:b-return", changed, "cut:enable-shared"),
            self.witness("state:a-again", original, "cut:enable-shared"),
        ), substrate=self.substrate)
        self.assertEqual(once.traces[-1].finding, many.traces[-1].finding)

    def test_audit_requires_distinct_historical_witnesses(self):
        original, _ = self.traces()
        repeated = self.witness("state:a", original, "cut:enable-shared")
        with self.assertRaisesRegex(InvalidReconfiguration, "ids must be unique"):
            audit_structural_responsiveness(
                (repeated, repeated), substrate=self.substrate
            )

    def test_unrecorded_novelty_cannot_hide_oscillation(self):
        original, changed = self.traces()
        witnesses = (
            self.witness("state:a", original, "cut:enable-shared"),
            self.witness("state:b", changed, "cut:enable-shared"),
            self.witness(
                "state:a-return",
                original,
                "cut:enable-shared",
                ("transport:missed", "transport:disclosure", "transport:invented"),
            ),
        )
        with self.assertRaisesRegex(InvalidReconfiguration, "must match operative"):
            audit_structural_responsiveness(
                witnesses, substrate=self.substrate
            )


class OscillationCounterCutTests(unittest.TestCase):
    setUp = DiffractiveArrangementTests.setUp
    difference = DiffractiveArrangementTests.difference
    disturb = DiffractiveArrangementTests.disturb
    counter_cut = CounterCutRevisionTests.counter_cut
    revised_arrangement = CounterCutRevisionTests.revised_arrangement
    revise = CounterCutRevisionTests.revise
    traces = StructuralResponsivenessTests.traces
    witness = StructuralResponsivenessTests.witness

    def oscillation_audit(self):
        original, changed = self.traces()
        return audit_structural_responsiveness((
            self.witness("state:a", original, "cut:counter-shared"),
            self.witness("state:b", changed, "cut:counter-shared"),
            self.witness("state:a-return", original, "cut:counter-shared"),
        ), substrate=self.substrate)

    def proposed_counter_cut(self, **overrides):
        values = dict(
            cut_id="cut:oscillation-counter",
            transport_basis=("transport:disclosure",),
            dependency_ids=(self.source.cut_id,),
            lineage_ids=("cut:counter-shared",),
            positions=(
                CutPosition("availability", "oscillation-exposed availability"),
                CutPosition("feedback", "recurrence feedback participation"),
                CutPosition("dependency", "reproducing dependency"),
            ),
            allocations=(
                Allocation(
                    StructuralDimension.POSSIBILITY,
                    local("cut:oscillation-counter", "feedback"),
                    1,
                ),
            ),
        )
        values.update(overrides)
        return CutEnactment(**values)

    def enact(self, **overrides):
        audit = self.oscillation_audit()
        self.substrate.enact_cut(
            dependent_cut(
                "cut:oscillation-dependent",
                "cut:counter-shared",
                "formation reproduced through return",
            ),
            delta_id="delta:oscillation-dependent",
        )
        values = dict(
            audit=audit,
            returning_witness_id="state:a-return",
            reopened_enabling_cut_id="cut:counter-shared",
            counter_cut=self.proposed_counter_cut(),
            delta_id="delta:oscillation-counter",
            triggering_trace_ids=("transport:disclosure",),
            substrate=self.substrate,
        )
        values.update(overrides)
        return counter_cut_from_oscillation(**values)

    def test_oscillation_trace_can_materially_ground_a_local_counter_cut(self):
        trace = self.enact()
        self.assertEqual("state:a", trace.recurring_witness_id)
        self.assertEqual("state:b", trace.departing_witness_id)
        self.assertEqual("state:a-return", trace.returning_witness_id)
        self.assertEqual(
            ResponsivenessFinding.STRUCTURAL_OSCILLATION,
            trace.responsiveness_trace.finding,
        )
        self.assertEqual(
            {"cut:counter-shared", "cut:oscillation-dependent"},
            set(trace.disturbance_delta.invalidated_cut_ids),
        )
        self.assertIn("cut:oscillation-counter", self.substrate.state.active_cut_ids)

    def test_detection_alone_does_not_mutate_or_command(self):
        original, changed = self.traces()
        witnesses = (
            self.witness("state:a", original, "cut:counter-shared"),
            self.witness("state:b", changed, "cut:counter-shared"),
            self.witness("state:a-return", original, "cut:counter-shared"),
        )
        before = self.substrate.state
        audit = audit_structural_responsiveness(witnesses, substrate=self.substrate)
        self.assertEqual(before, self.substrate.state)
        names = {
            item.name
            for record in (audit, audit.traces[-1])
            for item in fields(record)
        }
        self.assertTrue(names.isdisjoint({
            "stop", "settle", "restore", "selected", "preferred", "winner",
            "score", "rank", "limit", "converged",
        }))

    def test_material_recurrence_cannot_be_used_as_oscillation(self):
        original, changed = self.traces()
        audit = audit_structural_responsiveness((
            self.witness("state:a", original, "cut:enable-distributed"),
            self.witness("state:b", changed, "cut:enable-distributed"),
            self.witness(
                "state:a-return",
                original,
                "cut:counter-shared",
                deltas=("delta:source", "delta:counter-shared"),
            ),
        ), substrate=self.substrate)
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "unsupported structural"):
            counter_cut_from_oscillation(
                audit=audit,
                returning_witness_id="state:a-return",
                reopened_enabling_cut_id="cut:counter-shared",
                counter_cut=self.proposed_counter_cut(),
                delta_id="delta:not-oscillation",
                triggering_trace_ids=("transport:disclosure",),
                substrate=self.substrate,
            )
        self.assertEqual(before, self.substrate.state)

    def test_target_must_participate_in_departure_and_return(self):
        audit = self.oscillation_audit()
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "unsupported return"):
            counter_cut_from_oscillation(
                audit=audit,
                returning_witness_id="state:a-return",
                reopened_enabling_cut_id="cut:enable-distributed",
                counter_cut=self.proposed_counter_cut(
                    lineage_ids=("cut:enable-distributed",)
                ),
                delta_id="delta:unbound-target",
                triggering_trace_ids=("transport:disclosure",),
                substrate=self.substrate,
            )
        self.assertEqual(before, self.substrate.state)

    def test_relabelled_target_is_not_a_counter_cut(self):
        audit = self.oscillation_audit()
        reopened = self.substrate.state.cuts["cut:counter-shared"]
        relabelled = CutEnactment(
            cut_id="cut:oscillation-counter",
            transport_basis=("transport:disclosure",),
            dependency_ids=reopened.dependency_ids,
            lineage_ids=("cut:counter-shared",),
            positions=tuple(
                CutPosition(item.key, "renamed " + item.local_name)
                for item in reopened.positions
            ),
            allocations=tuple(
                Allocation(
                    item.dimension,
                    local("cut:oscillation-counter", item.position.position_key),
                    item.amount,
                )
                for item in reopened.allocations
            ),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "structurally distinct"):
            counter_cut_from_oscillation(
                audit=audit,
                returning_witness_id="state:a-return",
                reopened_enabling_cut_id="cut:counter-shared",
                counter_cut=relabelled,
                delta_id="delta:relabelled",
                triggering_trace_ids=("transport:disclosure",),
                substrate=self.substrate,
            )
        self.assertEqual(before, self.substrate.state)

    def test_transport_evidence_must_be_operative_in_return(self):
        audit = self.oscillation_audit()
        self.substrate.record_transport(
            transport("transport:unrelated", "Unrelated later message.")
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "operative in the return"):
            counter_cut_from_oscillation(
                audit=audit,
                returning_witness_id="state:a-return",
                reopened_enabling_cut_id="cut:counter-shared",
                counter_cut=self.proposed_counter_cut(
                    transport_basis=("transport:unrelated",)
                ),
                delta_id="delta:unrelated-evidence",
                triggering_trace_ids=("transport:unrelated",),
                substrate=self.substrate,
            )
        self.assertEqual(before, self.substrate.state)

    def test_forged_oscillation_finding_has_no_counter_cut_authority(self):
        audit = self.oscillation_audit()
        forged_trace = replace(
            audit.traces[-1],
            prior_witness_id="state:a",
        )
        forged = replace(audit, traces=audit.traces[:-1] + (forged_trace,))
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "exact recorded audit"):
            counter_cut_from_oscillation(
                audit=forged,
                returning_witness_id="state:a-return",
                reopened_enabling_cut_id="cut:counter-shared",
                counter_cut=self.proposed_counter_cut(),
                delta_id="delta:forged-oscillation",
                triggering_trace_ids=("transport:disclosure",),
                substrate=self.substrate,
            )
        self.assertEqual(before, self.substrate.state)

    def test_unrelated_dependency_cannot_acquire_local_counter_cut_authority(self):
        audit = self.oscillation_audit()
        unrelated = CutEnactment(
            cut_id="cut:unrelated-active",
            transport_basis=("transport:disclosure",),
            dependency_ids=(),
            lineage_ids=(),
            positions=(CutPosition("unrelated", "unrelated availability"),),
        )
        self.substrate.enact_cut(unrelated, delta_id="delta:unrelated-active")
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "locally anchored"):
            counter_cut_from_oscillation(
                audit=audit,
                returning_witness_id="state:a-return",
                reopened_enabling_cut_id="cut:counter-shared",
                counter_cut=self.proposed_counter_cut(
                    dependency_ids=("cut:unrelated-active",)
                ),
                delta_id="delta:unrelated-anchor",
                triggering_trace_ids=("transport:disclosure",),
                substrate=self.substrate,
            )
        self.assertEqual(before, self.substrate.state)

    def test_same_trace_cannot_force_repeated_revision(self):
        audit = self.oscillation_audit()
        self.substrate.enact_cut(
            dependent_cut(
                "cut:oscillation-dependent",
                "cut:counter-shared",
                "formation reproduced through return",
            ),
            delta_id="delta:oscillation-dependent",
        )
        trace = counter_cut_from_oscillation(
            audit=audit,
            returning_witness_id="state:a-return",
            reopened_enabling_cut_id="cut:counter-shared",
            counter_cut=self.proposed_counter_cut(),
            delta_id="delta:oscillation-counter",
            triggering_trace_ids=("transport:disclosure",),
            substrate=self.substrate,
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "remain active"):
            counter_cut_from_oscillation(
                audit=audit,
                returning_witness_id=trace.returning_witness_id,
                reopened_enabling_cut_id=trace.reopened_enabling_cut_id,
                counter_cut=self.proposed_counter_cut(cut_id="cut:forced-again"),
                delta_id="delta:forced-again",
                triggering_trace_ids=("transport:disclosure",),
                substrate=self.substrate,
            )
        self.assertEqual(before, self.substrate.state)


class CounterCutRevisionAdditionalValidationTests(unittest.TestCase):
    setUp = DiffractiveArrangementTests.setUp
    difference = DiffractiveArrangementTests.difference
    disturb = DiffractiveArrangementTests.disturb
    counter_cut = CounterCutRevisionTests.counter_cut
    revised_arrangement = CounterCutRevisionTests.revised_arrangement
    revise = CounterCutRevisionTests.revise

    def test_recomputed_arrangement_must_depend_on_counter_cut(self):
        disturbed = self.disturb()
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "explicit counter-cut"):
            revise_reopened_arrangement(
                field=disturbed,
                substrate=self.substrate,
                disturbance_delta_id="delta:burden-diffraction",
                counter_cut=self.counter_cut(),
                counter_cut_delta_id="delta:counter-shared",
                revised_arrangement=self.revised_arrangement(
                    dependency_ids=(self.source.cut_id,)
                ),
            )
        self.assertEqual(before, self.substrate.state)

    def test_relabelled_enabling_cut_is_not_a_counter_cut(self):
        disturbed = self.disturb()
        before = self.substrate.state
        relabelled = CutEnactment(
            cut_id="cut:counter-shared",
            transport_basis=("transport:disclosure",),
            dependency_ids=(self.source.cut_id,),
            lineage_ids=("cut:enable-shared",),
            positions=(CutPosition("renamed", "compassionate availability"),),
        )
        with self.assertRaisesRegex(InvalidReconfiguration, "relabelled enabling"):
            revise_reopened_arrangement(
                field=disturbed,
                substrate=self.substrate,
                disturbance_delta_id="delta:burden-diffraction",
                counter_cut=relabelled,
                counter_cut_delta_id="delta:counter-shared",
                revised_arrangement=self.revised_arrangement(),
            )
        self.assertEqual(before, self.substrate.state)

    def test_same_disturbance_cannot_revise_twice(self):
        revised = self.revise()
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "already has a revision"):
            revise_reopened_arrangement(
                field=revised,
                substrate=self.substrate,
                disturbance_delta_id="delta:burden-diffraction",
                counter_cut=self.counter_cut(cut_id="cut:counter-again"),
                counter_cut_delta_id="delta:counter-again",
                revised_arrangement=self.revised_arrangement(
                    cut_id="cut:shared-again",
                    dependency_ids=("cut:counter-again",),
                ),
            )
        self.assertEqual(before, self.substrate.state)


if __name__ == "__main__":
    unittest.main()
