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
    FeedbackDisposition,
    ObservedDimensionEffect,
    revise_field_from_feedback,
    return_effects_as_feedback,
    disturb_through_arrangement_difference,
    reenter_recomputed_arrangement_difference,
    retain_competing_alternatives,
    return_oscillation_counter_cut_to_field,
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


class OscillationFieldReturnTests(unittest.TestCase):
    setUp = DiffractiveArrangementTests.setUp
    difference = DiffractiveArrangementTests.difference
    disturb = DiffractiveArrangementTests.disturb
    counter_cut = CounterCutRevisionTests.counter_cut
    revised_arrangement = CounterCutRevisionTests.revised_arrangement
    revise = CounterCutRevisionTests.revise
    witness = StructuralResponsivenessTests.witness
    proposed_counter_cut = OscillationCounterCutTests.proposed_counter_cut

    def prepared(self):
        revised = self.revise()
        original = self.field.competing.alternatives[0]
        changed = revised.revisions[0].recomputed_trace
        audit = audit_structural_responsiveness((
            self.witness("state:a", original, "cut:counter-shared"),
            self.witness("state:b", changed, "cut:counter-shared"),
            self.witness("state:a-return", original, "cut:counter-shared"),
        ), substrate=self.substrate)
        self.substrate.enact_cut(
            dependent_cut(
                "cut:oscillation-dependent",
                "cut:counter-shared",
                "formation reproduced through return",
            ),
            delta_id="delta:oscillation-dependent",
        )
        oscillation = counter_cut_from_oscillation(
            audit=audit,
            returning_witness_id="state:a-return",
            reopened_enabling_cut_id="cut:counter-shared",
            counter_cut=self.proposed_counter_cut(),
            delta_id="delta:oscillation-counter",
            triggering_trace_ids=("transport:disclosure",),
            substrate=self.substrate,
        )
        return revised, oscillation

    def recomputed(self, **overrides):
        original = self.revised_arrangement()
        cut_id = overrides.pop("cut_id", "cut:shared-after-oscillation")
        values = dict(
            cut_id=cut_id,
            transport_basis=original.transport_basis,
            dependency_ids=("cut:oscillation-counter",),
            lineage_ids=("cut:shared-recomputed",),
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
                    item.amount,
                )
                for item in original.allocations
                if item.dimension != StructuralDimension.BURDEN
            ) + (
                Allocation(StructuralDimension.BURDEN, local(cut_id, "disclosure"), 1),
                Allocation(StructuralDimension.BURDEN, local(cut_id, "coordination"), 1),
                Allocation(StructuralDimension.BURDEN, local(cut_id, "affected"), 2),
            ),
        )
        values.update(overrides)
        return CutEnactment(**values)

    def return_to_field(self, **overrides):
        revised, oscillation = self.prepared()
        values = dict(
            field=revised,
            substrate=self.substrate,
            oscillation_counter_cut=oscillation,
            recomputed_arrangements=(self.recomputed(),),
        )
        values.update(overrides)
        return return_oscillation_counter_cut_to_field(**values)

    def test_counter_cut_returns_to_field_and_recomputes_cycle_dependent_trace(self):
        returned = self.return_to_field()
        trace = returned.oscillation_revisions[0]
        self.assertEqual("cut:oscillation-counter", trace.counter_cut_id)
        self.assertEqual(1, len(trace.affected))
        affected = trace.affected[0]
        self.assertEqual("cut:shared-recomputed", affected.prior_alternative_id)
        self.assertEqual(
            "cut:shared-after-oscillation", affected.recomputed_alternative_id
        )
        self.assertEqual(1.5, affected.prior_trace.effects[0].maximum_after)
        self.assertEqual(2.0, affected.recomputed_trace.effects[0].maximum_after)

    def test_unaffected_competing_arrangement_and_full_history_remain_present(self):
        returned = self.return_to_field()
        self.assertEqual(
            ("cut:shared-after-oscillation", "cut:distributed"),
            tuple(
                item.replacement.cut_id
                for item in returned.field.competing.alternatives
            ),
        )
        self.assertEqual(1, len(returned.revisions))
        self.assertEqual(1, len(returned.field.disturbances))
        self.assertEqual(
            "delta:oscillation-counter",
            returned.oscillation_revisions[0]
            .oscillation_counter_cut.disturbance_delta.delta_id,
        )

    def test_every_cycle_dependent_formation_must_be_recomputed(self):
        revised, oscillation = self.prepared()
        duplicated_dependency = replace(
            revised,
            field=replace(
                revised.field,
                dependencies=(
                    revised.field.dependencies[0],
                    ArrangementDependency(
                        "cut:distributed", ("cut:counter-shared",)
                    ),
                ),
            ),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "all cycle-dependent"):
            return_oscillation_counter_cut_to_field(
                field=duplicated_dependency,
                substrate=self.substrate,
                oscillation_counter_cut=oscillation,
                recomputed_arrangements=(self.recomputed(),),
            )
        self.assertEqual(before, self.substrate.state)

    def test_cosmetic_recomputation_cannot_reenter_the_field(self):
        revised, oscillation = self.prepared()
        current = revised.field.competing.alternatives[0].replacement
        cosmetic = replace(
            self.recomputed(),
            allocations=tuple(
                Allocation(
                    item.dimension,
                    local("cut:shared-after-oscillation", item.position.position_key),
                    item.amount,
                )
                for item in current.allocations
            ),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "freshly change"):
            return_oscillation_counter_cut_to_field(
                field=revised,
                substrate=self.substrate,
                oscillation_counter_cut=oscillation,
                recomputed_arrangements=(cosmetic,),
            )
        self.assertEqual(before, self.substrate.state)

    def test_exact_recorded_oscillation_delta_is_required(self):
        revised, oscillation = self.prepared()
        forged = replace(
            oscillation,
            disturbance_delta=replace(
                oscillation.disturbance_delta,
                triggering_trace_ids=("transport:missed",),
            ),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "exact recorded"):
            return_oscillation_counter_cut_to_field(
                field=revised,
                substrate=self.substrate,
                oscillation_counter_cut=forged,
                recomputed_arrangements=(self.recomputed(),),
            )
        self.assertEqual(before, self.substrate.state)

    def test_internally_forged_audit_lineage_cannot_return_to_field(self):
        revised, oscillation = self.prepared()
        forged = replace(oscillation, departing_witness_id="state:invented")
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "audit lineage"):
            return_oscillation_counter_cut_to_field(
                field=revised,
                substrate=self.substrate,
                oscillation_counter_cut=forged,
                recomputed_arrangements=(self.recomputed(),),
            )
        self.assertEqual(before, self.substrate.state)

    def test_same_oscillation_cannot_manufacture_repeated_field_revision(self):
        returned = self.return_to_field()
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "cannot be returned"):
            return_oscillation_counter_cut_to_field(
                field=returned,
                substrate=self.substrate,
                oscillation_counter_cut=returned.oscillation_revisions[0].oscillation_counter_cut,
                recomputed_arrangements=(
                    self.recomputed(
                        cut_id="cut:shared-after-oscillation-again",
                        lineage_ids=("cut:shared-after-oscillation",),
                    ),
                ),
            )
        self.assertEqual(before, self.substrate.state)

    def test_oscillation_counter_cut_remains_open_to_later_disturbance(self):
        returned = self.return_to_field()
        self.substrate.enact_cut(
            dependent_cut(
                "cut:oscillation-field-dependent",
                "cut:oscillation-counter",
                "field projection dependency",
            ),
            delta_id="delta:oscillation-field-dependent",
        )
        disturbed = disturb_through_arrangement_difference(
            field=returned.field,
            substrate=self.substrate,
            difference=ConsequentialDifference(
                witness_alternative_id="cut:distributed",
                contrasted_alternative_id="cut:shared-after-oscillation",
                dimension=StructuralDimension.BURDEN,
                measure=EffectMeasure.MAXIMUM_LOCAL_LOAD,
            ),
            enabling_cut_id="cut:oscillation-counter",
            delta_id="delta:disturb-oscillation-counter",
            triggering_trace_ids=("transport:disclosure",),
        )
        self.assertNotIn("cut:oscillation-counter", self.substrate.state.active_cut_ids)
        self.assertEqual(
            "cut:oscillation-counter", disturbed.disturbances[-1].enabling_cut_id
        )

    def test_returned_recomputation_can_act_as_a_fresh_witness(self):
        returned = self.return_to_field()
        reentered = reenter_recomputed_arrangement_difference(
            field=returned,
            substrate=self.substrate,
            difference=ConsequentialDifference(
                witness_alternative_id="cut:shared-after-oscillation",
                contrasted_alternative_id="cut:distributed",
                dimension=StructuralDimension.BURDEN,
                measure=EffectMeasure.MAXIMUM_LOCAL_LOAD,
            ),
            enabling_cut_id="cut:enable-distributed",
            delta_id="delta:oscillation-recomputed-reentry",
            triggering_trace_ids=("transport:disclosure",),
        )
        self.assertEqual(
            "cut:oscillation-counter",
            reentered.reentries[-1].witness_counter_cut_id,
        )
        self.assertNotIn("cut:enable-distributed", self.substrate.state.active_cut_ids)

    def test_forged_return_lineage_cannot_create_witness_authority(self):
        returned = self.return_to_field()
        affected = returned.oscillation_revisions[0].affected[0]
        forged_affected = replace(
            affected,
            prior_alternative_id="cut:invented-prior",
        )
        forged_field_revision = replace(
            returned.oscillation_revisions[0],
            affected=(forged_affected,),
        )
        forged = replace(returned, oscillation_revisions=(forged_field_revision,))
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "proposal lineage"):
            reenter_recomputed_arrangement_difference(
                field=forged,
                substrate=self.substrate,
                difference=ConsequentialDifference(
                    witness_alternative_id="cut:shared-after-oscillation",
                    contrasted_alternative_id="cut:distributed",
                    dimension=StructuralDimension.BURDEN,
                    measure=EffectMeasure.MAXIMUM_LOCAL_LOAD,
                ),
                enabling_cut_id="cut:enable-distributed",
                delta_id="delta:forged-return-reentry",
                triggering_trace_ids=("transport:disclosure",),
            )
        self.assertEqual(before, self.substrate.state)

    def test_field_return_contains_no_ranking_or_protection_authority(self):
        returned = self.return_to_field()
        names = {
            item.name
            for record in (
                returned,
                returned.oscillation_revisions[0],
                returned.oscillation_revisions[0].affected[0],
            )
            for item in fields(record)
        }
        self.assertTrue(names.isdisjoint({
            "score", "rank", "ranking", "selected", "preferred", "winner",
            "protected", "final", "settled", "iteration", "depth", "recency",
        }))
        self.assertFalse(hasattr(returned, "choose"))


class PostReturnFeedbackTests(unittest.TestCase):
    setUp = DiffractiveArrangementTests.setUp
    difference = DiffractiveArrangementTests.difference
    disturb = DiffractiveArrangementTests.disturb
    counter_cut = CounterCutRevisionTests.counter_cut
    revised_arrangement = CounterCutRevisionTests.revised_arrangement
    revise = CounterCutRevisionTests.revise
    witness = StructuralResponsivenessTests.witness
    proposed_counter_cut = OscillationCounterCutTests.proposed_counter_cut
    prepared = OscillationFieldReturnTests.prepared
    recomputed = OscillationFieldReturnTests.recomputed
    return_to_field = OscillationFieldReturnTests.return_to_field
    def returned_with_observation(self):
        returned = self.return_to_field()
        self.substrate.record_transport(
            transport("transport:post-return-effect", "Observed effects after field return.")
        )
        return returned

    @staticmethod
    def observed(trace, *, burden_maximum=None):
        values = []
        for effect in trace.effects:
            values.append(ObservedDimensionEffect(
                dimension=effect.dimension,
                total=effect.total_after,
                maximum_local_load=(
                    burden_maximum
                    if effect.dimension == StructuralDimension.BURDEN
                    and burden_maximum is not None
                    else effect.maximum_after
                ),
                occupied_positions=effect.occupied_positions_after,
            ))
        return tuple(values)

    def feedback(self, returned, **overrides):
        trace = returned.field.competing.alternatives[0]
        values = dict(
            field=returned,
            substrate=self.substrate,
            observation_trace_id="transport:post-return-effect",
            alternative_id="cut:shared-after-oscillation",
            observed_effects=self.observed(trace),
            disposition=FeedbackDisposition.CONFIRMS,
        )
        values.update(overrides)
        return return_effects_as_feedback(**values)

    def test_corresponding_effects_confirm_without_finalizing_or_mutating(self):
        returned = self.returned_with_observation()
        before = self.substrate.state
        updated = self.feedback(returned)
        result = updated.feedback[-1]
        self.assertEqual(FeedbackDisposition.CONFIRMS, result.disposition)
        self.assertEqual((), result.differing_dimensions)
        self.assertIsNone(result.disturbance_delta)
        self.assertEqual(before, self.substrate.state)
        self.assertIn("cut:oscillation-counter", self.substrate.state.active_cut_ids)

    def test_confirmation_cannot_carry_mutation_or_protection_authority(self):
        returned = self.returned_with_observation()
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "cannot mutate"):
            self.feedback(
                returned,
                affected_cut_id="cut:oscillation-counter",
                delta_id="delta:confirmation-finality",
            )
        self.assertEqual(before, self.substrate.state)

    def test_difference_can_complicate_one_explicit_dependent_formation(self):
        returned = self.returned_with_observation()
        self.substrate.enact_cut(
            dependent_cut(
                "cut:feedback-dependent",
                "cut:oscillation-counter",
                "post-return consequence uptake",
            ),
            delta_id="delta:feedback-dependent",
        )
        updated = self.feedback(
            returned,
            observed_effects=self.observed(
                returned.field.competing.alternatives[0], burden_maximum=3.0
            ),
            disposition=FeedbackDisposition.COMPLICATES,
            affected_cut_id="cut:feedback-dependent",
            delta_id="delta:feedback-complication",
        )
        result = updated.feedback[-1]
        self.assertEqual((StructuralDimension.BURDEN,), result.differing_dimensions)
        self.assertNotIn("cut:feedback-dependent", self.substrate.state.active_cut_ids)
        self.assertIn("cut:oscillation-counter", self.substrate.state.active_cut_ids)

    def test_difference_can_invalidate_enabling_formation_without_becoming_failure(self):
        returned = self.returned_with_observation()
        updated = self.feedback(
            returned,
            observed_effects=self.observed(
                returned.field.competing.alternatives[0], burden_maximum=3.0
            ),
            disposition=FeedbackDisposition.INVALIDATES,
            affected_cut_id="cut:oscillation-counter",
            delta_id="delta:feedback-invalidation",
        )
        result = updated.feedback[-1]
        self.assertEqual(FeedbackDisposition.INVALIDATES, result.disposition)
        self.assertNotIn("cut:oscillation-counter", self.substrate.state.active_cut_ids)
        self.assertFalse(hasattr(result, "failure"))

    def test_mismatch_does_not_automatically_choose_its_scope(self):
        returned = self.returned_with_observation()
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "explicit affected"):
            self.feedback(
                returned,
                observed_effects=self.observed(
                    returned.field.competing.alternatives[0], burden_maximum=3.0
                ),
                disposition=FeedbackDisposition.INVALIDATES,
            )
        self.assertEqual(before, self.substrate.state)

    def test_forged_or_stale_field_recomputation_has_no_feedback_authority(self):
        returned = self.returned_with_observation()
        affected = returned.oscillation_revisions[0].affected[0]
        forged = replace(
            returned,
            oscillation_revisions=(replace(
                returned.oscillation_revisions[0],
                affected=(replace(affected, prior_alternative_id="cut:forged"),),
            ),),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "proposal lineage"):
            self.feedback(forged)
        self.assertEqual(before, self.substrate.state)

    def test_feedback_record_contains_no_finality_ranking_or_failure_authority(self):
        returned = self.returned_with_observation()
        result = self.feedback(returned).feedback[-1]
        names = {item.name for item in fields(result)}
        self.assertTrue(names.isdisjoint({
            "score", "rank", "selected", "preferred", "winner", "final",
            "settled", "success", "failure", "iteration", "confidence",
        }))

    def test_same_observation_cannot_manufacture_repeated_feedback(self):
        returned = self.returned_with_observation()
        updated = self.feedback(returned)
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "repeated feedback"):
            self.feedback(updated)
        self.assertEqual(before, self.substrate.state)

    def test_feedback_history_survives_later_recursive_reentry(self):
        returned = self.returned_with_observation()
        updated = self.feedback(returned)
        reentered = reenter_recomputed_arrangement_difference(
            field=updated,
            substrate=self.substrate,
            difference=ConsequentialDifference(
                witness_alternative_id="cut:shared-after-oscillation",
                contrasted_alternative_id="cut:distributed",
                dimension=StructuralDimension.BURDEN,
                measure=EffectMeasure.MAXIMUM_LOCAL_LOAD,
            ),
            enabling_cut_id="cut:enable-distributed",
            delta_id="delta:feedback-preserving-reentry",
            triggering_trace_ids=("transport:disclosure",),
        )
        self.assertEqual(updated.feedback, reentered.feedback)


class FeedbackGroundedFieldRevisionTests(unittest.TestCase):
    setUp = DiffractiveArrangementTests.setUp
    difference = DiffractiveArrangementTests.difference
    disturb = DiffractiveArrangementTests.disturb
    counter_cut = CounterCutRevisionTests.counter_cut
    revised_arrangement = CounterCutRevisionTests.revised_arrangement
    revise = CounterCutRevisionTests.revise
    witness = StructuralResponsivenessTests.witness
    proposed_counter_cut = OscillationCounterCutTests.proposed_counter_cut
    prepared = OscillationFieldReturnTests.prepared
    recomputed = OscillationFieldReturnTests.recomputed
    return_to_field = OscillationFieldReturnTests.return_to_field
    observed = staticmethod(PostReturnFeedbackTests.observed)

    def feedback_counter_cut(self, reopened_cut_id, **overrides):
        cut_id = overrides.pop("cut_id", "cut:feedback-counter")
        values = dict(
            cut_id=cut_id,
            transport_basis=("transport:feedback-revision",),
            dependency_ids=(self.source.cut_id,),
            lineage_ids=(reopened_cut_id,),
            positions=(
                CutPosition("availability", "feedback-reopened availability"),
                CutPosition("uptake", "observed-effect uptake"),
            ),
            relations=(Relation(
                "feedback-revises-availability",
                local(cut_id, "uptake"),
                local(cut_id, "availability"),
            ),),
        )
        values.update(overrides)
        return CutEnactment(**values)

    def feedback_recomputed(self, **overrides):
        prior = self.recomputed()
        cut_id = overrides.pop("cut_id", "cut:shared-after-feedback")
        values = dict(
            cut_id=cut_id,
            transport_basis=("transport:feedback-revision",),
            dependency_ids=("cut:feedback-counter",),
            lineage_ids=("cut:shared-after-oscillation",),
            positions=prior.positions,
            relations=tuple(
                Relation(
                    item.relation_type,
                    local(cut_id, item.source.position_key),
                    local(cut_id, item.target.position_key),
                )
                for item in prior.relations
            ),
            allocations=tuple(
                Allocation(
                    item.dimension,
                    local(cut_id, item.position.position_key),
                    item.amount,
                )
                for item in prior.allocations
                if item.dimension != StructuralDimension.BURDEN
            ) + (
                Allocation(StructuralDimension.BURDEN, local(cut_id, "disclosure"), 1.5),
                Allocation(StructuralDimension.BURDEN, local(cut_id, "coordination"), 1.25),
                Allocation(StructuralDimension.BURDEN, local(cut_id, "affected"), 1.25),
            ),
        )
        values.update(overrides)
        return CutEnactment(**values)

    def with_feedback(self, disposition=FeedbackDisposition.INVALIDATES):
        returned = self.return_to_field()
        self.substrate.record_transport(transport(
            "transport:feedback-revision", "Observed consequences complicate the return."
        ))
        affected_cut_id = "cut:oscillation-counter"
        if disposition == FeedbackDisposition.COMPLICATES:
            affected_cut_id = "cut:feedback-dependent"
            self.substrate.enact_cut(
                dependent_cut(
                    affected_cut_id,
                    "cut:oscillation-counter",
                    "feedback-local dependent",
                ),
                delta_id="delta:feedback-dependent-local",
            )
        trace = returned.field.competing.alternatives[0]
        return return_effects_as_feedback(
            field=returned,
            substrate=self.substrate,
            observation_trace_id="transport:feedback-revision",
            alternative_id="cut:shared-after-oscillation",
            observed_effects=self.observed(trace, burden_maximum=3.0),
            disposition=disposition,
            affected_cut_id=affected_cut_id,
            delta_id="delta:feedback-revision-disturbance",
        )

    def apply_revision(self, disposition=FeedbackDisposition.INVALIDATES, **overrides):
        field = overrides.pop("field", None)
        if field is None:
            field = self.with_feedback(disposition)
        feedback = field.feedback[-1]
        values = dict(
            field=field,
            substrate=self.substrate,
            observation_trace_id="transport:feedback-revision",
            counter_cut=self.feedback_counter_cut(feedback.affected_cut_id),
            counter_cut_delta_id="delta:feedback-counter",
            recomputed_arrangement=self.feedback_recomputed(),
        )
        values.update(overrides)
        return revise_field_from_feedback(**values)

    def test_invalidating_feedback_grounds_counter_cut_and_fresh_recomputation(self):
        revised = self.apply_revision()
        trace = revised.feedback_revisions[-1]
        self.assertEqual("cut:oscillation-counter", trace.reopened_cut_id)
        self.assertEqual("cut:feedback-counter", trace.counter_cut_id)
        self.assertEqual("cut:shared-after-feedback", trace.recomputed_alternative_id)
        self.assertEqual(2.0, trace.prior_trace.effects[0].maximum_after)
        self.assertEqual(1.5, trace.recomputed_trace.effects[0].maximum_after)
        self.assertIn("cut:feedback-counter", self.substrate.state.active_cut_ids)

    def test_complicating_feedback_can_ground_its_own_local_counter_cut(self):
        revised = self.apply_revision(FeedbackDisposition.COMPLICATES)
        trace = revised.feedback_revisions[-1]
        self.assertEqual("cut:feedback-dependent", trace.reopened_cut_id)
        self.assertIn("cut:oscillation-counter", self.substrate.state.active_cut_ids)
        self.assertIn("cut:feedback-counter", self.substrate.state.active_cut_ids)

    def test_confirming_feedback_remains_evidence_without_revision_authority(self):
        returned = self.return_to_field()
        self.substrate.record_transport(transport(
            "transport:feedback-revision", "Observed effects correspond."
        ))
        trace = returned.field.competing.alternatives[0]
        confirmed = return_effects_as_feedback(
            field=returned,
            substrate=self.substrate,
            observation_trace_id="transport:feedback-revision",
            alternative_id="cut:shared-after-oscillation",
            observed_effects=self.observed(trace),
            disposition=FeedbackDisposition.CONFIRMS,
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "cannot authorize"):
            revise_field_from_feedback(
                field=confirmed,
                substrate=self.substrate,
                observation_trace_id="transport:feedback-revision",
                counter_cut=self.feedback_counter_cut("cut:oscillation-counter"),
                counter_cut_delta_id="delta:confirmation-counter",
                recomputed_arrangement=self.feedback_recomputed(),
            )
        self.assertEqual(before, self.substrate.state)
        self.assertEqual(FeedbackDisposition.CONFIRMS, confirmed.feedback[-1].disposition)

    def test_prior_confirmation_is_preserved_but_does_not_accumulate_weight(self):
        returned = self.return_to_field()
        self.substrate.record_transport(transport("transport:confirm-first", "Correspondence."))
        current = returned.field.competing.alternatives[0]
        confirmed = return_effects_as_feedback(
            field=returned,
            substrate=self.substrate,
            observation_trace_id="transport:confirm-first",
            alternative_id="cut:shared-after-oscillation",
            observed_effects=self.observed(current),
            disposition=FeedbackDisposition.CONFIRMS,
        )
        self.substrate.record_transport(transport(
            "transport:feedback-revision", "Later effects complicate correspondence."
        ))
        disturbed = return_effects_as_feedback(
            field=confirmed,
            substrate=self.substrate,
            observation_trace_id="transport:feedback-revision",
            alternative_id="cut:shared-after-oscillation",
            observed_effects=self.observed(current, burden_maximum=3.0),
            disposition=FeedbackDisposition.INVALIDATES,
            affected_cut_id="cut:oscillation-counter",
            delta_id="delta:feedback-revision-disturbance",
        )
        revised = self.apply_revision(field=disturbed)
        self.assertEqual(2, len(revised.feedback))
        self.assertEqual(FeedbackDisposition.CONFIRMS, revised.feedback[0].disposition)
        names = {item.name for item in fields(revised.feedback_revisions[-1])}
        self.assertTrue(names.isdisjoint({"confidence", "weight", "count"}))

    def test_forged_feedback_delta_has_no_revision_authority(self):
        field = self.with_feedback()
        forged_feedback = replace(
            field.feedback[-1],
            disturbance_delta=replace(
                field.feedback[-1].disturbance_delta,
                triggering_trace_ids=("transport:disclosure",),
            ),
        )
        forged = replace(field, feedback=(forged_feedback,))
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "exact recorded"):
            self.apply_revision(field=forged)
        self.assertEqual(before, self.substrate.state)

    def test_relabelled_reopened_formation_is_not_a_counter_cut(self):
        field = self.with_feedback()
        reopened = self.substrate.state.cuts["cut:oscillation-counter"]
        cut_id = "cut:feedback-counter"
        relabelled = replace(
            reopened,
            cut_id=cut_id,
            transport_basis=("transport:feedback-revision",),
            lineage_ids=("cut:oscillation-counter",),
            relations=tuple(
                Relation(
                    item.relation_type,
                    local(cut_id, item.source.position_key),
                    local(cut_id, item.target.position_key),
                ) for item in reopened.relations
            ),
            allocations=tuple(
                Allocation(item.dimension, local(cut_id, item.position.position_key), item.amount)
                for item in reopened.allocations
            ),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "relabelled feedback"):
            self.apply_revision(field=field, counter_cut=relabelled)
        self.assertEqual(before, self.substrate.state)

    def test_cosmetic_recomputation_fails_atomically(self):
        field = self.with_feedback()
        prior = field.field.competing.alternatives[0].replacement
        cosmetic = replace(
            self.feedback_recomputed(),
            allocations=tuple(
                Allocation(item.dimension, local("cut:shared-after-feedback", item.position.position_key), item.amount)
                for item in prior.allocations
            ),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "freshly change"):
            self.apply_revision(field=field, recomputed_arrangement=cosmetic)
        self.assertEqual(before, self.substrate.state)

    def test_duplicate_topology_fails_before_counter_cut_enactment(self):
        field = self.with_feedback()
        other = field.field.competing.alternatives[1].replacement
        duplicate = replace(
            self.feedback_recomputed(),
            allocations=tuple(
                Allocation(item.dimension, local("cut:shared-after-feedback", item.position.position_key), item.amount)
                for item in other.allocations
            ),
            relations=tuple(
                Relation(item.relation_type, local("cut:shared-after-feedback", item.source.position_key), local("cut:shared-after-feedback", item.target.position_key))
                for item in other.relations
            ),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "duplicated topology"):
            self.apply_revision(field=field, recomputed_arrangement=duplicate)
        self.assertEqual(before, self.substrate.state)

    def test_same_feedback_cannot_authorize_serial_revisions(self):
        revised = self.apply_revision()
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "repeated revision"):
            revise_field_from_feedback(
                field=revised,
                substrate=self.substrate,
                observation_trace_id="transport:feedback-revision",
                counter_cut=self.feedback_counter_cut(
                    "cut:oscillation-counter", cut_id="cut:feedback-counter-again"
                ),
                counter_cut_delta_id="delta:feedback-counter-again",
                recomputed_arrangement=self.feedback_recomputed(
                    cut_id="cut:shared-after-feedback-again",
                    dependency_ids=("cut:feedback-counter-again",),
                ),
            )
        self.assertEqual(before, self.substrate.state)

    def test_feedback_revision_contains_no_confidence_ranking_or_finality_authority(self):
        revised = self.apply_revision()
        names = {
            item.name
            for record in (revised, revised.feedback_revisions[-1])
            for item in fields(record)
        }
        self.assertTrue(names.isdisjoint({
            "confidence", "weight", "score", "rank", "selected", "preferred",
            "winner", "final", "settled", "success", "failure", "iteration",
        }))
        self.assertFalse(hasattr(revised, "choose"))


class FeedbackRecomputedProjectionTests(unittest.TestCase):
    """Feedback revision remains recursively observable, never authoritative by age."""

    setUp = DiffractiveArrangementTests.setUp
    difference = DiffractiveArrangementTests.difference
    disturb = DiffractiveArrangementTests.disturb
    counter_cut = CounterCutRevisionTests.counter_cut
    revised_arrangement = CounterCutRevisionTests.revised_arrangement
    revise = CounterCutRevisionTests.revise
    witness = StructuralResponsivenessTests.witness
    proposed_counter_cut = OscillationCounterCutTests.proposed_counter_cut
    prepared = OscillationFieldReturnTests.prepared
    recomputed = OscillationFieldReturnTests.recomputed
    return_to_field = OscillationFieldReturnTests.return_to_field
    observed = staticmethod(PostReturnFeedbackTests.observed)
    feedback_counter_cut = FeedbackGroundedFieldRevisionTests.feedback_counter_cut
    feedback_recomputed = FeedbackGroundedFieldRevisionTests.feedback_recomputed
    with_feedback = FeedbackGroundedFieldRevisionTests.with_feedback
    apply_revision = FeedbackGroundedFieldRevisionTests.apply_revision

    def test_feedback_recomputed_projection_reenters_as_current_witness(self):
        proposed = self.feedback_recomputed()
        proposed = replace(
            proposed,
            allocations=tuple(
                item for item in proposed.allocations
                if item.dimension != StructuralDimension.BURDEN
            ) + (
                Allocation(StructuralDimension.BURDEN, local(proposed.cut_id, "disclosure"), 1.75),
                Allocation(StructuralDimension.BURDEN, local(proposed.cut_id, "coordination"), 1.25),
                Allocation(StructuralDimension.BURDEN, local(proposed.cut_id, "affected"), 1.0),
            ),
        )
        revised = self.apply_revision(recomputed_arrangement=proposed)
        reentered = reenter_recomputed_arrangement_difference(
            field=revised,
            substrate=self.substrate,
            difference=ConsequentialDifference(
                witness_alternative_id="cut:shared-after-feedback",
                contrasted_alternative_id="cut:distributed",
                dimension=StructuralDimension.BURDEN,
                measure=EffectMeasure.MAXIMUM_LOCAL_LOAD,
            ),
            enabling_cut_id="cut:enable-distributed",
            delta_id="delta:feedback-recomputed-reentry",
            triggering_trace_ids=("transport:feedback-revision",),
        )
        trace = reentered.reentries[-1]
        self.assertEqual("cut:shared-after-feedback", trace.witness_alternative_id)
        self.assertEqual("cut:feedback-counter", trace.witness_counter_cut_id)
        self.assertNotIn("cut:enable-distributed", self.substrate.state.active_cut_ids)

    def test_feedback_recomputed_projection_can_receive_confirming_effects(self):
        revised = self.apply_revision()
        self.substrate.record_transport(transport(
            "transport:feedback-recomputed-confirmation",
            "Observed effects correspond with the feedback recomputation.",
        ))
        current = revised.field.competing.alternatives[0]
        updated = return_effects_as_feedback(
            field=revised,
            substrate=self.substrate,
            observation_trace_id="transport:feedback-recomputed-confirmation",
            alternative_id="cut:shared-after-feedback",
            observed_effects=self.observed(current),
            disposition=FeedbackDisposition.CONFIRMS,
        )
        self.assertEqual(FeedbackDisposition.CONFIRMS, updated.feedback[-1].disposition)
        self.assertIn("cut:feedback-counter", self.substrate.state.active_cut_ids)

    def test_later_effect_can_complicate_earlier_confirmation_without_rewriting_it(self):
        revised = self.apply_revision()
        current = revised.field.competing.alternatives[0]
        self.substrate.record_transport(transport(
            "transport:feedback-recomputed-confirmation", "Correspondence observed."
        ))
        confirmed = return_effects_as_feedback(
            field=revised,
            substrate=self.substrate,
            observation_trace_id="transport:feedback-recomputed-confirmation",
            alternative_id="cut:shared-after-feedback",
            observed_effects=self.observed(current),
            disposition=FeedbackDisposition.CONFIRMS,
        )
        self.substrate.enact_cut(
            dependent_cut(
                "cut:later-feedback-dependent",
                "cut:feedback-counter",
                "later observed consequence",
            ),
            delta_id="delta:later-feedback-dependent",
        )
        self.substrate.record_transport(transport(
            "transport:feedback-recomputed-complication",
            "Later effects complicate the earlier correspondence.",
        ))
        complicated = return_effects_as_feedback(
            field=confirmed,
            substrate=self.substrate,
            observation_trace_id="transport:feedback-recomputed-complication",
            alternative_id="cut:shared-after-feedback",
            observed_effects=self.observed(current, burden_maximum=2.5),
            disposition=FeedbackDisposition.COMPLICATES,
            affected_cut_id="cut:later-feedback-dependent",
            delta_id="delta:feedback-recomputed-complication",
        )
        self.assertEqual(FeedbackDisposition.CONFIRMS, complicated.feedback[-2].disposition)
        self.assertEqual(FeedbackDisposition.COMPLICATES, complicated.feedback[-1].disposition)
        self.assertEqual(
            "cut:shared-after-feedback", complicated.feedback[-2].alternative_id
        )
        self.assertFalse(hasattr(complicated.feedback[-1], "failure"))

    def test_later_effect_can_invalidate_recomputed_formation_without_retroactive_failure(self):
        revised = self.apply_revision()
        current = revised.field.competing.alternatives[0]
        self.substrate.record_transport(transport(
            "transport:feedback-recomputed-confirmation", "Correspondence observed."
        ))
        confirmed = return_effects_as_feedback(
            field=revised,
            substrate=self.substrate,
            observation_trace_id="transport:feedback-recomputed-confirmation",
            alternative_id="cut:shared-after-feedback",
            observed_effects=self.observed(current),
            disposition=FeedbackDisposition.CONFIRMS,
        )
        self.substrate.record_transport(transport(
            "transport:feedback-recomputed-invalidation",
            "Later effects reopen the feedback-grounded formation.",
        ))
        invalidated = return_effects_as_feedback(
            field=confirmed,
            substrate=self.substrate,
            observation_trace_id="transport:feedback-recomputed-invalidation",
            alternative_id="cut:shared-after-feedback",
            observed_effects=self.observed(current, burden_maximum=2.75),
            disposition=FeedbackDisposition.INVALIDATES,
            affected_cut_id="cut:feedback-counter",
            delta_id="delta:feedback-recomputed-invalidation",
        )
        self.assertEqual(FeedbackDisposition.CONFIRMS, invalidated.feedback[-2].disposition)
        self.assertEqual(FeedbackDisposition.INVALIDATES, invalidated.feedback[-1].disposition)
        self.assertNotIn("cut:feedback-counter", self.substrate.state.active_cut_ids)
        self.assertFalse(hasattr(invalidated.feedback[-1], "failure"))

    def test_confirmation_count_does_not_create_reentry_authority(self):
        revised = self.apply_revision()
        forged = replace(revised, feedback_revisions=())
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "recorded recomputation"):
            reenter_recomputed_arrangement_difference(
                field=forged,
                substrate=self.substrate,
                difference=ConsequentialDifference(
                    witness_alternative_id="cut:shared-after-feedback",
                    contrasted_alternative_id="cut:distributed",
                    dimension=StructuralDimension.BURDEN,
                    measure=EffectMeasure.MAXIMUM_LOCAL_LOAD,
                ),
                enabling_cut_id="cut:enable-distributed",
                delta_id="delta:confidence-cannot-reenter",
                triggering_trace_ids=("transport:feedback-revision",),
            )
        self.assertEqual(before, self.substrate.state)

    def test_forged_feedback_revision_lineage_cannot_reenter(self):
        revised = self.apply_revision()
        forged_revision = replace(
            revised.feedback_revisions[-1], reopened_cut_id="cut:enable-distributed"
        )
        forged = replace(revised, feedback_revisions=(forged_revision,))
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "reopened lineage"):
            reenter_recomputed_arrangement_difference(
                field=forged,
                substrate=self.substrate,
                difference=ConsequentialDifference(
                    witness_alternative_id="cut:shared-after-feedback",
                    contrasted_alternative_id="cut:distributed",
                    dimension=StructuralDimension.BURDEN,
                    measure=EffectMeasure.MAXIMUM_LOCAL_LOAD,
                ),
                enabling_cut_id="cut:enable-distributed",
                delta_id="delta:forged-feedback-reentry",
                triggering_trace_ids=("transport:feedback-revision",),
            )
        self.assertEqual(before, self.substrate.state)

    def test_inactive_feedback_counter_cut_removes_witness_authority(self):
        revised = self.apply_revision()
        self.substrate.record_transport(transport(
            "transport:later-invalidation", "A later effect reopens the formation."
        ))
        self.substrate.disturb(
            delta_id="delta:later-counter-invalidation",
            triggering_trace_ids=("transport:later-invalidation",),
            invalidated_root_ids=("cut:feedback-counter",),
            replacements=(),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "active enabling"):
            reenter_recomputed_arrangement_difference(
                field=revised,
                substrate=self.substrate,
                difference=ConsequentialDifference(
                    witness_alternative_id="cut:shared-after-feedback",
                    contrasted_alternative_id="cut:distributed",
                    dimension=StructuralDimension.BURDEN,
                    measure=EffectMeasure.MAXIMUM_LOCAL_LOAD,
                ),
                enabling_cut_id="cut:enable-distributed",
                delta_id="delta:inactive-feedback-witness",
                triggering_trace_ids=("transport:feedback-revision",),
            )
        self.assertEqual(before, self.substrate.state)

    def test_records_contain_no_confidence_or_retroactive_failure_authority(self):
        revised = self.apply_revision()
        names = {
            item.name
            for record in (revised, revised.feedback_revisions[-1])
            for item in fields(record)
        }
        self.assertTrue(names.isdisjoint({
            "confidence", "weight", "count", "score", "rank", "preferred",
            "winner", "final", "success", "failure", "retroactive_failure",
        }))


class RecursiveFeedbackGroundedRevisionTests(unittest.TestCase):
    """Later effects may revise locally; feedback depth supplies no authority."""

    setUp = DiffractiveArrangementTests.setUp
    difference = DiffractiveArrangementTests.difference
    disturb = DiffractiveArrangementTests.disturb
    counter_cut = CounterCutRevisionTests.counter_cut
    revised_arrangement = CounterCutRevisionTests.revised_arrangement
    revise = CounterCutRevisionTests.revise
    witness = StructuralResponsivenessTests.witness
    proposed_counter_cut = OscillationCounterCutTests.proposed_counter_cut
    prepared = OscillationFieldReturnTests.prepared
    recomputed = OscillationFieldReturnTests.recomputed
    return_to_field = OscillationFieldReturnTests.return_to_field
    observed = staticmethod(PostReturnFeedbackTests.observed)
    feedback_counter_cut = FeedbackGroundedFieldRevisionTests.feedback_counter_cut
    feedback_recomputed = FeedbackGroundedFieldRevisionTests.feedback_recomputed
    with_feedback = FeedbackGroundedFieldRevisionTests.with_feedback
    apply_revision = FeedbackGroundedFieldRevisionTests.apply_revision

    def later_counter_cut(self, reopened_cut_id, **overrides):
        cut_id = overrides.pop("cut_id", "cut:later-feedback-counter")
        values = dict(
            cut_id=cut_id,
            transport_basis=("transport:later-feedback",),
            dependency_ids=(self.source.cut_id,),
            lineage_ids=(reopened_cut_id,),
            positions=(
                CutPosition("later-observation", "later observed effect"),
                CutPosition("local-uptake", "locally revised uptake"),
            ),
            relations=(Relation(
                "later-effect-revises-uptake",
                local(cut_id, "later-observation"),
                local(cut_id, "local-uptake"),
            ),),
        )
        values.update(overrides)
        return CutEnactment(**values)

    def later_recomputed(self, **overrides):
        prior = self.feedback_recomputed()
        cut_id = overrides.pop("cut_id", "cut:shared-after-later-feedback")
        values = dict(
            cut_id=cut_id,
            transport_basis=("transport:later-feedback",),
            dependency_ids=("cut:later-feedback-counter",),
            lineage_ids=("cut:shared-after-feedback",),
            positions=prior.positions,
            relations=tuple(
                Relation(
                    item.relation_type,
                    local(cut_id, item.source.position_key),
                    local(cut_id, item.target.position_key),
                )
                for item in prior.relations
            ),
            allocations=tuple(
                Allocation(
                    item.dimension,
                    local(cut_id, item.position.position_key),
                    item.amount,
                )
                for item in prior.allocations
                if item.dimension != StructuralDimension.BURDEN
            ) + (
                Allocation(StructuralDimension.BURDEN, local(cut_id, "disclosure"), 1.4),
                Allocation(StructuralDimension.BURDEN, local(cut_id, "coordination"), 1.4),
                Allocation(StructuralDimension.BURDEN, local(cut_id, "affected"), 1.2),
            ),
        )
        values.update(overrides)
        return CutEnactment(**values)

    def later_feedback(self, disposition=FeedbackDisposition.INVALIDATES, *, confirm=False):
        revised = self.apply_revision()
        current = revised.field.competing.alternatives[0]
        if confirm:
            self.substrate.record_transport(transport(
                "transport:later-confirmation", "Situated correspondence observed."
            ))
            revised = return_effects_as_feedback(
                field=revised,
                substrate=self.substrate,
                observation_trace_id="transport:later-confirmation",
                alternative_id="cut:shared-after-feedback",
                observed_effects=self.observed(current),
                disposition=FeedbackDisposition.CONFIRMS,
            )
        affected_cut_id = "cut:feedback-counter"
        if disposition == FeedbackDisposition.COMPLICATES:
            affected_cut_id = "cut:later-feedback-dependent"
            self.substrate.enact_cut(
                dependent_cut(
                    affected_cut_id,
                    "cut:feedback-counter",
                    "later feedback-local dependent",
                ),
                delta_id="delta:later-feedback-dependent",
            )
        self.substrate.record_transport(transport(
            "transport:later-feedback", "Later effects materially reopen the formation."
        ))
        return return_effects_as_feedback(
            field=revised,
            substrate=self.substrate,
            observation_trace_id="transport:later-feedback",
            alternative_id="cut:shared-after-feedback",
            observed_effects=self.observed(current, burden_maximum=2.75),
            disposition=disposition,
            affected_cut_id=affected_cut_id,
            delta_id="delta:later-feedback-disturbance",
        )

    def revise_again(self, disposition=FeedbackDisposition.INVALIDATES, **overrides):
        field = overrides.pop("field", None)
        if field is None:
            field = self.later_feedback(disposition)
        feedback = next(
            item for item in field.feedback
            if item.observation_trace_id == "transport:later-feedback"
        )
        values = dict(
            field=field,
            substrate=self.substrate,
            observation_trace_id="transport:later-feedback",
            counter_cut=self.later_counter_cut(feedback.affected_cut_id),
            counter_cut_delta_id="delta:later-feedback-counter",
            recomputed_arrangement=self.later_recomputed(),
        )
        values.update(overrides)
        return revise_field_from_feedback(**values)

    def test_later_invalidation_grounds_fresh_counter_cut_and_recomputation(self):
        revised = self.revise_again()
        latest = revised.feedback_revisions[-1]
        self.assertEqual("cut:feedback-counter", latest.reopened_cut_id)
        self.assertEqual("cut:later-feedback-counter", latest.counter_cut_id)
        self.assertEqual("cut:shared-after-later-feedback", latest.recomputed_alternative_id)
        self.assertEqual(2, len(revised.feedback_revisions))
        self.assertIn("cut:later-feedback-counter", self.substrate.state.active_cut_ids)

    def test_later_complication_remains_scoped_to_reopened_dependent(self):
        revised = self.revise_again(FeedbackDisposition.COMPLICATES)
        latest = revised.feedback_revisions[-1]
        self.assertEqual("cut:later-feedback-dependent", latest.reopened_cut_id)
        self.assertIn("cut:feedback-counter", self.substrate.state.active_cut_ids)
        self.assertIn("cut:later-feedback-counter", self.substrate.state.active_cut_ids)

    def test_confirmation_and_both_disturbances_remain_in_history(self):
        field = self.later_feedback(confirm=True)
        revised = self.revise_again(field=field)
        self.assertEqual(3, len(revised.feedback))
        self.assertEqual(
            (
                FeedbackDisposition.INVALIDATES,
                FeedbackDisposition.CONFIRMS,
                FeedbackDisposition.INVALIDATES,
            ),
            tuple(item.disposition for item in revised.feedback),
        )
        self.assertEqual(2, len(revised.feedback_revisions))
        self.assertEqual(
            "cut:shared-after-feedback",
            revised.feedback_revisions[-1].prior_alternative_id,
        )

    def test_confirmation_cannot_substitute_for_later_disturbance(self):
        revised = self.apply_revision()
        current = revised.field.competing.alternatives[0]
        self.substrate.record_transport(transport(
            "transport:later-feedback", "Correspondence alone."
        ))
        confirmed = return_effects_as_feedback(
            field=revised,
            substrate=self.substrate,
            observation_trace_id="transport:later-feedback",
            alternative_id="cut:shared-after-feedback",
            observed_effects=self.observed(current),
            disposition=FeedbackDisposition.CONFIRMS,
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "cannot authorize"):
            self.revise_again(field=confirmed)
        self.assertEqual(before, self.substrate.state)

    def test_missing_prior_feedback_revision_cannot_be_replaced_by_history_depth(self):
        field = self.later_feedback(confirm=True)
        forged = replace(field, feedback_revisions=())
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "originating recomputation"):
            self.revise_again(field=forged)
        self.assertEqual(before, self.substrate.state)

    def test_forged_prior_revision_lineage_cannot_ground_another_counter_cut(self):
        field = self.later_feedback()
        forged_prior = replace(
            field.feedback_revisions[-1],
            reopened_cut_id="cut:enable-distributed",
        )
        forged = replace(field, feedback_revisions=(forged_prior,))
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "provenance closure"):
            self.revise_again(field=forged)
        self.assertEqual(before, self.substrate.state)

    def test_later_cosmetic_recomputation_fails_atomically(self):
        field = self.later_feedback()
        prior = field.field.competing.alternatives[0].replacement
        cosmetic = replace(
            self.later_recomputed(),
            allocations=tuple(
                Allocation(
                    item.dimension,
                    local("cut:shared-after-later-feedback", item.position.position_key),
                    item.amount,
                )
                for item in prior.allocations
            ),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "freshly change"):
            self.revise_again(field=field, recomputed_arrangement=cosmetic)
        self.assertEqual(before, self.substrate.state)

    def test_recursive_feedback_records_contain_no_depth_or_ranking_authority(self):
        revised = self.revise_again()
        names = {
            item.name
            for record in (revised, *revised.feedback_revisions, *revised.feedback)
            for item in fields(record)
        }
        self.assertTrue(names.isdisjoint({
            "depth", "generation", "iteration", "confidence", "weight", "count",
            "score", "rank", "selected", "preferred", "winner", "final",
            "success", "failure",
        }))
        self.assertFalse(hasattr(revised, "choose"))


class RecursiveFeedbackReentryAndEffectsTests(unittest.TestCase):
    """Recursive recomputations remain answerable without gaining seniority."""

    setUp = DiffractiveArrangementTests.setUp
    difference = DiffractiveArrangementTests.difference
    disturb = DiffractiveArrangementTests.disturb
    counter_cut = CounterCutRevisionTests.counter_cut
    revised_arrangement = CounterCutRevisionTests.revised_arrangement
    revise = CounterCutRevisionTests.revise
    witness = StructuralResponsivenessTests.witness
    proposed_counter_cut = OscillationCounterCutTests.proposed_counter_cut
    prepared = OscillationFieldReturnTests.prepared
    recomputed = OscillationFieldReturnTests.recomputed
    return_to_field = OscillationFieldReturnTests.return_to_field
    observed = staticmethod(PostReturnFeedbackTests.observed)
    feedback_counter_cut = FeedbackGroundedFieldRevisionTests.feedback_counter_cut
    feedback_recomputed = FeedbackGroundedFieldRevisionTests.feedback_recomputed
    with_feedback = FeedbackGroundedFieldRevisionTests.with_feedback
    apply_revision = FeedbackGroundedFieldRevisionTests.apply_revision
    later_counter_cut = RecursiveFeedbackGroundedRevisionTests.later_counter_cut
    later_recomputed = RecursiveFeedbackGroundedRevisionTests.later_recomputed
    later_feedback = RecursiveFeedbackGroundedRevisionTests.later_feedback
    revise_again = RecursiveFeedbackGroundedRevisionTests.revise_again

    def reenter_latest(self, field=None, **overrides):
        if field is None:
            field = self.revise_again()
        values = dict(
            field=field,
            substrate=self.substrate,
            difference=ConsequentialDifference(
                witness_alternative_id="cut:shared-after-later-feedback",
                contrasted_alternative_id="cut:distributed",
                dimension=StructuralDimension.BURDEN,
                measure=EffectMeasure.MAXIMUM_LOCAL_LOAD,
            ),
            enabling_cut_id="cut:enable-distributed",
            delta_id="delta:recursive-feedback-reentry",
            triggering_trace_ids=("transport:later-feedback",),
        )
        values.update(overrides)
        return reenter_recomputed_arrangement_difference(**values)

    def test_latest_recomputation_reenters_through_its_active_counter_cut(self):
        reentered = self.reenter_latest()
        trace = reentered.reentries[-1]
        self.assertEqual("cut:shared-after-later-feedback", trace.witness_alternative_id)
        self.assertEqual("cut:later-feedback-counter", trace.witness_counter_cut_id)
        self.assertNotIn("cut:enable-distributed", self.substrate.state.active_cut_ids)

    def test_latest_recomputation_receives_later_confirming_effects(self):
        revised = self.revise_again()
        current = revised.field.competing.alternatives[0]
        self.substrate.record_transport(transport(
            "transport:recursive-confirmation", "Situated correspondence observed."
        ))
        updated = return_effects_as_feedback(
            field=revised,
            substrate=self.substrate,
            observation_trace_id="transport:recursive-confirmation",
            alternative_id="cut:shared-after-later-feedback",
            observed_effects=self.observed(current),
            disposition=FeedbackDisposition.CONFIRMS,
        )
        self.assertEqual(FeedbackDisposition.CONFIRMS, updated.feedback[-1].disposition)
        self.assertIn("cut:later-feedback-counter", self.substrate.state.active_cut_ids)

    def test_later_complication_preserves_confirmation_and_recursive_history(self):
        revised = self.revise_again()
        current = revised.field.competing.alternatives[0]
        self.substrate.record_transport(transport(
            "transport:recursive-confirmation", "Situated correspondence observed."
        ))
        confirmed = return_effects_as_feedback(
            field=revised,
            substrate=self.substrate,
            observation_trace_id="transport:recursive-confirmation",
            alternative_id="cut:shared-after-later-feedback",
            observed_effects=self.observed(current),
            disposition=FeedbackDisposition.CONFIRMS,
        )
        self.substrate.enact_cut(
            dependent_cut(
                "cut:recursive-effect-dependent",
                "cut:later-feedback-counter",
                "recursive effect-local dependent",
            ),
            delta_id="delta:recursive-effect-dependent",
        )
        self.substrate.record_transport(transport(
            "transport:recursive-complication", "Later effects complicate correspondence."
        ))
        complicated = return_effects_as_feedback(
            field=confirmed,
            substrate=self.substrate,
            observation_trace_id="transport:recursive-complication",
            alternative_id="cut:shared-after-later-feedback",
            observed_effects=self.observed(current, burden_maximum=2.6),
            disposition=FeedbackDisposition.COMPLICATES,
            affected_cut_id="cut:recursive-effect-dependent",
            delta_id="delta:recursive-complication",
        )
        self.assertEqual(FeedbackDisposition.CONFIRMS, complicated.feedback[-2].disposition)
        self.assertEqual(FeedbackDisposition.COMPLICATES, complicated.feedback[-1].disposition)
        self.assertEqual(2, len(complicated.feedback_revisions))
        self.assertIn("cut:later-feedback-counter", self.substrate.state.active_cut_ids)

    def test_later_invalidation_reopens_latest_counter_cut_without_failure(self):
        revised = self.revise_again()
        current = revised.field.competing.alternatives[0]
        self.substrate.record_transport(transport(
            "transport:recursive-invalidation", "Further effects reopen the formation."
        ))
        invalidated = return_effects_as_feedback(
            field=revised,
            substrate=self.substrate,
            observation_trace_id="transport:recursive-invalidation",
            alternative_id="cut:shared-after-later-feedback",
            observed_effects=self.observed(current, burden_maximum=2.8),
            disposition=FeedbackDisposition.INVALIDATES,
            affected_cut_id="cut:later-feedback-counter",
            delta_id="delta:recursive-invalidation",
        )
        self.assertEqual(FeedbackDisposition.INVALIDATES, invalidated.feedback[-1].disposition)
        self.assertNotIn("cut:later-feedback-counter", self.substrate.state.active_cut_ids)
        self.assertEqual(2, len(invalidated.feedback_revisions))
        self.assertFalse(hasattr(invalidated.feedback[-1], "failure"))

    def test_missing_predecessor_closure_cannot_be_replaced_by_history_length(self):
        revised = self.revise_again()
        forged = replace(revised, provenance_closures=(revised.provenance_closures[-1],))
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "retained predecessor"):
            self.reenter_latest(field=forged)
        self.assertEqual(before, self.substrate.state)

    def test_revision_tuple_order_does_not_confer_reentry_authority(self):
        revised = self.revise_again()
        reordered = replace(
            revised,
            feedback_revisions=tuple(reversed(revised.feedback_revisions)),
        )
        reentered = self.reenter_latest(field=reordered)
        self.assertEqual(
            "cut:later-feedback-counter",
            reentered.reentries[-1].witness_counter_cut_id,
        )

    def test_recursive_records_expose_no_maturity_or_authority_accumulator(self):
        revised = self.revise_again()
        names = {
            item.name
            for record in (revised, *revised.feedback_revisions, *revised.feedback)
            for item in fields(record)
        }
        self.assertTrue(names.isdisjoint({
            "maturity", "seniority", "depth", "generation", "iteration",
            "confidence", "weight", "count", "score", "rank", "authority",
            "selected", "preferred", "winner", "final", "success", "failure",
        }))


class BoundedRecursiveFeedbackRevisionTests(unittest.TestCase):
    """Further revision uses local closure, never ancestry length."""

    setUp = DiffractiveArrangementTests.setUp
    difference = DiffractiveArrangementTests.difference
    disturb = DiffractiveArrangementTests.disturb
    counter_cut = CounterCutRevisionTests.counter_cut
    revised_arrangement = CounterCutRevisionTests.revised_arrangement
    revise = CounterCutRevisionTests.revise
    witness = StructuralResponsivenessTests.witness
    proposed_counter_cut = OscillationCounterCutTests.proposed_counter_cut
    prepared = OscillationFieldReturnTests.prepared
    recomputed = OscillationFieldReturnTests.recomputed
    return_to_field = OscillationFieldReturnTests.return_to_field
    observed = staticmethod(PostReturnFeedbackTests.observed)
    feedback_counter_cut = FeedbackGroundedFieldRevisionTests.feedback_counter_cut
    feedback_recomputed = FeedbackGroundedFieldRevisionTests.feedback_recomputed
    with_feedback = FeedbackGroundedFieldRevisionTests.with_feedback
    apply_revision = FeedbackGroundedFieldRevisionTests.apply_revision
    later_counter_cut = RecursiveFeedbackGroundedRevisionTests.later_counter_cut
    later_recomputed = RecursiveFeedbackGroundedRevisionTests.later_recomputed
    later_feedback = RecursiveFeedbackGroundedRevisionTests.later_feedback
    revise_again = RecursiveFeedbackGroundedRevisionTests.revise_again
    reenter_latest = RecursiveFeedbackReentryAndEffectsTests.reenter_latest

    def further_counter_cut(self, reopened_cut_id, **overrides):
        cut_id = overrides.pop("cut_id", "cut:further-feedback-counter")
        values = dict(
            cut_id=cut_id,
            transport_basis=("transport:further-feedback",),
            dependency_ids=(self.source.cut_id,),
            lineage_ids=(reopened_cut_id,),
            positions=(
                CutPosition("effect", "further material effect"),
                CutPosition("relation", "reopened local relation"),
                CutPosition("uptake", "fresh local uptake"),
            ),
            relations=(
                Relation("effect-reopens-relation", local(cut_id, "effect"), local(cut_id, "relation")),
                Relation("relation-shapes-uptake", local(cut_id, "relation"), local(cut_id, "uptake")),
            ),
        )
        values.update(overrides)
        return CutEnactment(**values)

    def further_recomputed(self, **overrides):
        prior = self.later_recomputed()
        cut_id = overrides.pop("cut_id", "cut:shared-after-further-feedback")
        values = dict(
            cut_id=cut_id,
            transport_basis=("transport:further-feedback",),
            dependency_ids=("cut:further-feedback-counter",),
            lineage_ids=("cut:shared-after-later-feedback",),
            positions=prior.positions,
            relations=tuple(
                Relation(
                    item.relation_type,
                    local(cut_id, item.source.position_key),
                    local(cut_id, item.target.position_key),
                ) for item in prior.relations
            ),
            allocations=tuple(
                Allocation(item.dimension, local(cut_id, item.position.position_key), item.amount)
                for item in prior.allocations
                if item.dimension != StructuralDimension.BURDEN
            ) + (
                Allocation(StructuralDimension.BURDEN, local(cut_id, "disclosure"), 1.35),
                Allocation(StructuralDimension.BURDEN, local(cut_id, "coordination"), 1.35),
                Allocation(StructuralDimension.BURDEN, local(cut_id, "affected"), 1.30),
            ),
        )
        values.update(overrides)
        return CutEnactment(**values)

    def further_feedback(self, disposition=FeedbackDisposition.INVALIDATES):
        revised = self.revise_again()
        current = revised.field.competing.alternatives[0]
        affected_cut_id = "cut:later-feedback-counter"
        if disposition == FeedbackDisposition.COMPLICATES:
            affected_cut_id = "cut:further-feedback-dependent"
            self.substrate.enact_cut(
                dependent_cut(
                    affected_cut_id,
                    "cut:later-feedback-counter",
                    "further effect-local dependent",
                ),
                delta_id="delta:further-feedback-dependent",
            )
        self.substrate.record_transport(transport(
            "transport:further-feedback",
            "Further material effects reopen the current formation.",
        ))
        return return_effects_as_feedback(
            field=revised,
            substrate=self.substrate,
            observation_trace_id="transport:further-feedback",
            alternative_id="cut:shared-after-later-feedback",
            observed_effects=self.observed(current, burden_maximum=2.9),
            disposition=disposition,
            affected_cut_id=affected_cut_id,
            delta_id="delta:further-feedback-disturbance",
        )

    def revise_further(self, disposition=FeedbackDisposition.INVALIDATES, **overrides):
        field = overrides.pop("field", None)
        if field is None:
            field = self.further_feedback(disposition)
        feedback = next(
            item for item in field.feedback
            if item.observation_trace_id == "transport:further-feedback"
        )
        values = dict(
            field=field,
            substrate=self.substrate,
            observation_trace_id="transport:further-feedback",
            counter_cut=self.further_counter_cut(feedback.affected_cut_id),
            counter_cut_delta_id="delta:further-feedback-counter",
            recomputed_arrangement=self.further_recomputed(),
        )
        values.update(overrides)
        return revise_field_from_feedback(**values)

    def test_further_invalidation_grounds_bounded_counter_cut_and_recomputation(self):
        revised = self.revise_further()
        latest = revised.feedback_revisions[-1]
        self.assertEqual("cut:later-feedback-counter", latest.reopened_cut_id)
        self.assertEqual("cut:further-feedback-counter", latest.counter_cut_id)
        self.assertEqual("cut:shared-after-further-feedback", latest.recomputed_alternative_id)
        self.assertEqual(3, len(revised.feedback_revisions))
        self.assertEqual(3, len(revised.provenance_closures))

    def test_further_complication_remains_local(self):
        revised = self.revise_further(FeedbackDisposition.COMPLICATES)
        self.assertEqual(
            "cut:further-feedback-dependent",
            revised.feedback_revisions[-1].reopened_cut_id,
        )
        self.assertIn("cut:later-feedback-counter", self.substrate.state.active_cut_ids)

    def test_complete_history_is_preserved_beside_bounded_closures(self):
        revised = self.revise_further()
        self.assertEqual(3, len(revised.feedback))
        self.assertEqual(3, len(revised.feedback_revisions))
        self.assertEqual(
            tuple(item.feedback for item in revised.feedback_revisions),
            revised.feedback,
        )

    def test_forged_current_closure_fails_without_mutation(self):
        field = self.further_feedback()
        closure = field.provenance_closures[-1]
        forged = replace(
            field,
            provenance_closures=field.provenance_closures[:-1] + (
                replace(closure, observation_trace_id="transport:invented"),
            ),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "closure is inconsistent"):
            self.revise_further(field=forged)
        self.assertEqual(before, self.substrate.state)

    def test_closure_tuple_order_does_not_confer_authority(self):
        revised = self.revise_again()
        reordered = replace(
            revised,
            provenance_closures=tuple(reversed(revised.provenance_closures)),
        )
        reentered = self.reenter_latest(field=reordered)
        self.assertEqual(
            "cut:later-feedback-counter",
            reentered.reentries[-1].witness_counter_cut_id,
        )

    def test_further_cosmetic_recomputation_fails_atomically(self):
        field = self.further_feedback()
        prior = field.field.competing.alternatives[0].replacement
        cosmetic = replace(
            self.further_recomputed(),
            allocations=tuple(
                Allocation(
                    item.dimension,
                    local("cut:shared-after-further-feedback", item.position.position_key),
                    item.amount,
                ) for item in prior.allocations
            ),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "freshly change"):
            self.revise_further(field=field, recomputed_arrangement=cosmetic)
        self.assertEqual(before, self.substrate.state)

    def test_closure_contains_no_depth_maturity_or_selection_authority(self):
        revised = self.revise_further()
        names = {
            item.name
            for record in (*revised.provenance_closures, revised)
            for item in fields(record)
        }
        self.assertTrue(names.isdisjoint({
            "depth", "generation", "iteration", "maturity", "authority",
            "confidence", "weight", "score", "rank", "selected", "preferred",
            "winner", "final", "success", "failure",
        }))


class ClosureGroundedReentryAndEffectsTests(unittest.TestCase):
    """A bounded closure preserves continuity but never answers for materiality."""

    setUp = DiffractiveArrangementTests.setUp
    difference = DiffractiveArrangementTests.difference
    disturb = DiffractiveArrangementTests.disturb
    counter_cut = CounterCutRevisionTests.counter_cut
    revised_arrangement = CounterCutRevisionTests.revised_arrangement
    revise = CounterCutRevisionTests.revise
    witness = StructuralResponsivenessTests.witness
    proposed_counter_cut = OscillationCounterCutTests.proposed_counter_cut
    prepared = OscillationFieldReturnTests.prepared
    recomputed = OscillationFieldReturnTests.recomputed
    return_to_field = OscillationFieldReturnTests.return_to_field
    observed = staticmethod(PostReturnFeedbackTests.observed)
    feedback_counter_cut = FeedbackGroundedFieldRevisionTests.feedback_counter_cut
    feedback_recomputed = FeedbackGroundedFieldRevisionTests.feedback_recomputed
    with_feedback = FeedbackGroundedFieldRevisionTests.with_feedback
    apply_revision = FeedbackGroundedFieldRevisionTests.apply_revision
    later_counter_cut = RecursiveFeedbackGroundedRevisionTests.later_counter_cut
    later_recomputed = RecursiveFeedbackGroundedRevisionTests.later_recomputed
    later_feedback = RecursiveFeedbackGroundedRevisionTests.later_feedback
    revise_again = RecursiveFeedbackGroundedRevisionTests.revise_again
    further_counter_cut = BoundedRecursiveFeedbackRevisionTests.further_counter_cut
    further_recomputed = BoundedRecursiveFeedbackRevisionTests.further_recomputed
    further_feedback = BoundedRecursiveFeedbackRevisionTests.further_feedback
    revise_further = BoundedRecursiveFeedbackRevisionTests.revise_further

    def reenter_closure_grounded(self, field=None, **overrides):
        if field is None:
            field = self.revise_further()
        values = dict(
            field=field,
            substrate=self.substrate,
            difference=ConsequentialDifference(
                witness_alternative_id="cut:shared-after-further-feedback",
                contrasted_alternative_id="cut:distributed",
                dimension=StructuralDimension.BURDEN,
                measure=EffectMeasure.MAXIMUM_LOCAL_LOAD,
            ),
            enabling_cut_id="cut:enable-distributed",
            delta_id="delta:closure-grounded-reentry",
            triggering_trace_ids=("transport:further-feedback",),
        )
        values.update(overrides)
        return reenter_recomputed_arrangement_difference(**values)

    def test_closure_grounded_recomputation_reenters_through_present_materiality(self):
        reentered = self.reenter_closure_grounded()
        trace = reentered.reentries[-1]
        self.assertEqual(
            "cut:shared-after-further-feedback", trace.witness_alternative_id
        )
        self.assertEqual("cut:further-feedback-counter", trace.witness_counter_cut_id)
        self.assertEqual(
            "cut:enable-distributed", trace.target_enabling_cut_id
        )

    def test_valid_closure_cannot_substitute_for_active_counter_cut(self):
        revised = self.revise_further()
        self.substrate.disturb(
            delta_id="delta:reopen-closure-counter",
            triggering_trace_ids=("transport:further-feedback",),
            invalidated_root_ids=("cut:further-feedback-counter",),
            replacements=(),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "active enabling formation"):
            self.reenter_closure_grounded(field=revised)
        self.assertEqual(before, self.substrate.state)

    def test_valid_closure_cannot_substitute_for_current_field_dependency(self):
        revised = self.revise_further()
        dependencies = tuple(
            ArrangementDependency(
                item.alternative_cut_id,
                ("cut:enable-shared",),
            )
            if item.alternative_cut_id == "cut:shared-after-further-feedback"
            else item
            for item in revised.field.dependencies
        )
        forged = replace(
            revised,
            field=replace(revised.field, dependencies=dependencies),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "recorded counter-cut"):
            self.reenter_closure_grounded(field=forged)
        self.assertEqual(before, self.substrate.state)

    def test_valid_closure_cannot_substitute_for_exact_current_trace(self):
        revised = self.revise_further()
        latest = revised.feedback_revisions[-1]
        alternatives = tuple(
            latest.prior_trace
            if item.replacement.cut_id == "cut:shared-after-further-feedback"
            else item
            for item in revised.field.competing.alternatives
        )
        forged = replace(
            revised,
            field=replace(
                revised.field,
                competing=replace(
                    revised.field.competing,
                    alternatives=alternatives,
                ),
                dependencies=tuple(
                    ArrangementDependency(
                        latest.prior_alternative_id,
                        item.enabling_cut_ids,
                    )
                    if item.alternative_cut_id
                    == "cut:shared-after-further-feedback"
                    else item
                    for item in revised.field.dependencies
                ),
            ),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "currently retained"):
            self.reenter_closure_grounded(field=forged)
        self.assertEqual(before, self.substrate.state)

    def test_valid_closure_cannot_turn_equal_effects_into_difference(self):
        revised = self.revise_further()
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "equal arrangement effects"):
            self.reenter_closure_grounded(
                field=revised,
                difference=ConsequentialDifference(
                    witness_alternative_id="cut:shared-after-further-feedback",
                    contrasted_alternative_id="cut:distributed",
                    dimension=StructuralDimension.BURDEN,
                    measure=EffectMeasure.TOTAL,
                ),
            )
        self.assertEqual(before, self.substrate.state)

    def test_closure_grounded_recomputation_receives_later_effects(self):
        revised = self.revise_further()
        current = revised.field.competing.alternatives[0]
        self.substrate.record_transport(transport(
            "transport:closure-confirmation",
            "Present effects correspond with the current formation.",
        ))
        confirmed = return_effects_as_feedback(
            field=revised,
            substrate=self.substrate,
            observation_trace_id="transport:closure-confirmation",
            alternative_id="cut:shared-after-further-feedback",
            observed_effects=self.observed(current),
            disposition=FeedbackDisposition.CONFIRMS,
        )
        self.assertEqual(FeedbackDisposition.CONFIRMS, confirmed.feedback[-1].disposition)
        self.assertIn("cut:further-feedback-counter", self.substrate.state.active_cut_ids)

    def test_confirmation_does_not_protect_closure_grounded_counter_cut(self):
        revised = self.revise_further()
        current = revised.field.competing.alternatives[0]
        self.substrate.record_transport(transport(
            "transport:closure-confirmation",
            "Present effects correspond with the current formation.",
        ))
        confirmed = return_effects_as_feedback(
            field=revised,
            substrate=self.substrate,
            observation_trace_id="transport:closure-confirmation",
            alternative_id="cut:shared-after-further-feedback",
            observed_effects=self.observed(current),
            disposition=FeedbackDisposition.CONFIRMS,
        )
        self.substrate.record_transport(transport(
            "transport:closure-invalidation",
            "Further effects materially reopen the current formation.",
        ))
        invalidated = return_effects_as_feedback(
            field=confirmed,
            substrate=self.substrate,
            observation_trace_id="transport:closure-invalidation",
            alternative_id="cut:shared-after-further-feedback",
            observed_effects=self.observed(current, burden_maximum=3.1),
            disposition=FeedbackDisposition.INVALIDATES,
            affected_cut_id="cut:further-feedback-counter",
            delta_id="delta:closure-invalidation",
        )
        self.assertEqual(FeedbackDisposition.CONFIRMS, invalidated.feedback[-2].disposition)
        self.assertEqual(FeedbackDisposition.INVALIDATES, invalidated.feedback[-1].disposition)
        self.assertNotIn("cut:further-feedback-counter", self.substrate.state.active_cut_ids)
        self.assertFalse(hasattr(invalidated.feedback[-1], "failure"))


class PostClosureGroundedFeedbackRevisionTests(unittest.TestCase):
    """Continuity closures cannot transmit protection into later revisions."""

    setUp = DiffractiveArrangementTests.setUp
    difference = DiffractiveArrangementTests.difference
    disturb = DiffractiveArrangementTests.disturb
    counter_cut = CounterCutRevisionTests.counter_cut
    revised_arrangement = CounterCutRevisionTests.revised_arrangement
    revise = CounterCutRevisionTests.revise
    witness = StructuralResponsivenessTests.witness
    proposed_counter_cut = OscillationCounterCutTests.proposed_counter_cut
    prepared = OscillationFieldReturnTests.prepared
    recomputed = OscillationFieldReturnTests.recomputed
    return_to_field = OscillationFieldReturnTests.return_to_field
    observed = staticmethod(PostReturnFeedbackTests.observed)
    feedback_counter_cut = FeedbackGroundedFieldRevisionTests.feedback_counter_cut
    feedback_recomputed = FeedbackGroundedFieldRevisionTests.feedback_recomputed
    with_feedback = FeedbackGroundedFieldRevisionTests.with_feedback
    apply_revision = FeedbackGroundedFieldRevisionTests.apply_revision
    later_counter_cut = RecursiveFeedbackGroundedRevisionTests.later_counter_cut
    later_recomputed = RecursiveFeedbackGroundedRevisionTests.later_recomputed
    later_feedback = RecursiveFeedbackGroundedRevisionTests.later_feedback
    revise_again = RecursiveFeedbackGroundedRevisionTests.revise_again
    further_counter_cut = BoundedRecursiveFeedbackRevisionTests.further_counter_cut
    further_recomputed = BoundedRecursiveFeedbackRevisionTests.further_recomputed
    further_feedback = BoundedRecursiveFeedbackRevisionTests.further_feedback
    revise_further = BoundedRecursiveFeedbackRevisionTests.revise_further

    def post_closure_feedback(
        self,
        disposition=FeedbackDisposition.INVALIDATES,
        *,
        confirm=False,
    ):
        revised = self.revise_further()
        current = revised.field.competing.alternatives[0]
        if confirm:
            self.substrate.record_transport(transport(
                "transport:post-closure-confirmation",
                "Situated effects correspond before later disturbance.",
            ))
            revised = return_effects_as_feedback(
                field=revised,
                substrate=self.substrate,
                observation_trace_id="transport:post-closure-confirmation",
                alternative_id="cut:shared-after-further-feedback",
                observed_effects=self.observed(current),
                disposition=FeedbackDisposition.CONFIRMS,
            )
        affected_cut_id = "cut:further-feedback-counter"
        if disposition == FeedbackDisposition.COMPLICATES:
            affected_cut_id = "cut:post-closure-dependent"
            self.substrate.enact_cut(
                dependent_cut(
                    affected_cut_id,
                    "cut:further-feedback-counter",
                    "post-closure effect-local dependent",
                ),
                delta_id="delta:post-closure-dependent",
            )
        self.substrate.record_transport(transport(
            "transport:post-closure-disturbance",
            "Effects after closure-grounded re-entry reopen a local formation.",
        ))
        return return_effects_as_feedback(
            field=revised,
            substrate=self.substrate,
            observation_trace_id="transport:post-closure-disturbance",
            alternative_id="cut:shared-after-further-feedback",
            observed_effects=self.observed(current, burden_maximum=3.2),
            disposition=disposition,
            affected_cut_id=affected_cut_id,
            delta_id="delta:post-closure-disturbance",
        )

    def successor_counter_cut(self, reopened_cut_id, **overrides):
        cut_id = overrides.pop("cut_id", "cut:post-closure-counter")
        values = dict(
            cut_id=cut_id,
            transport_basis=("transport:post-closure-disturbance",),
            dependency_ids=(self.source.cut_id,),
            lineage_ids=(reopened_cut_id,),
            positions=(
                CutPosition("effect", "post-closure material effect"),
                CutPosition("relation", "locally reopened relation"),
                CutPosition("continuity", "retained but non-protective continuity"),
                CutPosition("uptake", "successor local uptake"),
            ),
            relations=(
                Relation(
                    "effect-reopens-relation",
                    local(cut_id, "effect"),
                    local(cut_id, "relation"),
                ),
                Relation(
                    "relation-meets-continuity",
                    local(cut_id, "relation"),
                    local(cut_id, "continuity"),
                ),
                Relation(
                    "continuity-remains-answerable-in-uptake",
                    local(cut_id, "continuity"),
                    local(cut_id, "uptake"),
                ),
            ),
        )
        values.update(overrides)
        return CutEnactment(**values)

    def successor_recomputed(self, **overrides):
        prior = self.further_recomputed()
        cut_id = overrides.pop("cut_id", "cut:shared-after-post-closure")
        values = dict(
            cut_id=cut_id,
            transport_basis=("transport:post-closure-disturbance",),
            dependency_ids=("cut:post-closure-counter",),
            lineage_ids=("cut:shared-after-further-feedback",),
            positions=prior.positions,
            relations=tuple(
                Relation(
                    item.relation_type,
                    local(cut_id, item.source.position_key),
                    local(cut_id, item.target.position_key),
                ) for item in prior.relations
            ),
            allocations=tuple(
                Allocation(
                    item.dimension,
                    local(cut_id, item.position.position_key),
                    item.amount,
                )
                for item in prior.allocations
                if item.dimension != StructuralDimension.BURDEN
            ) + (
                Allocation(StructuralDimension.BURDEN, local(cut_id, "disclosure"), 1.1),
                Allocation(StructuralDimension.BURDEN, local(cut_id, "coordination"), 1.1),
                Allocation(StructuralDimension.BURDEN, local(cut_id, "affected"), 1.8),
            ),
        )
        values.update(overrides)
        return CutEnactment(**values)

    def revise_post_closure(
        self,
        disposition=FeedbackDisposition.INVALIDATES,
        *,
        confirm=False,
        **overrides,
    ):
        field = overrides.pop("field", None)
        if field is None:
            field = self.post_closure_feedback(disposition, confirm=confirm)
        feedback = next(
            item for item in field.feedback
            if item.observation_trace_id == "transport:post-closure-disturbance"
        )
        values = dict(
            field=field,
            substrate=self.substrate,
            observation_trace_id="transport:post-closure-disturbance",
            counter_cut=self.successor_counter_cut(feedback.affected_cut_id),
            counter_cut_delta_id="delta:post-closure-counter",
            recomputed_arrangement=self.successor_recomputed(),
        )
        values.update(overrides)
        return revise_field_from_feedback(**values)

    def test_post_closure_invalidation_grounds_successor_revision(self):
        revised = self.revise_post_closure()
        latest = revised.feedback_revisions[-1]
        self.assertEqual("cut:further-feedback-counter", latest.reopened_cut_id)
        self.assertEqual("cut:post-closure-counter", latest.counter_cut_id)
        self.assertEqual(
            "cut:shared-after-post-closure", latest.recomputed_alternative_id
        )
        self.assertEqual(4, len(revised.feedback_revisions))
        self.assertEqual(4, len(revised.provenance_closures))

    def test_post_closure_complication_remains_local(self):
        revised = self.revise_post_closure(FeedbackDisposition.COMPLICATES)
        self.assertEqual(
            "cut:post-closure-dependent",
            revised.feedback_revisions[-1].reopened_cut_id,
        )
        self.assertIn("cut:further-feedback-counter", self.substrate.state.active_cut_ids)

    def test_prior_confirmation_and_closure_cannot_protect_formation(self):
        revised = self.revise_post_closure(confirm=True)
        self.assertEqual(
            FeedbackDisposition.CONFIRMS,
            revised.feedback[-2].disposition,
        )
        self.assertEqual(
            FeedbackDisposition.INVALIDATES,
            revised.feedback[-1].disposition,
        )
        self.assertIn("cut:post-closure-counter", self.substrate.state.active_cut_ids)

    def test_successor_closure_cannot_protect_fresh_counter_cut(self):
        revised = self.revise_post_closure()
        current = revised.field.competing.alternatives[0]
        self.substrate.record_transport(transport(
            "transport:successor-invalidation",
            "The successor formation remains materially answerable.",
        ))
        invalidated = return_effects_as_feedback(
            field=revised,
            substrate=self.substrate,
            observation_trace_id="transport:successor-invalidation",
            alternative_id="cut:shared-after-post-closure",
            observed_effects=self.observed(current, burden_maximum=3.3),
            disposition=FeedbackDisposition.INVALIDATES,
            affected_cut_id="cut:post-closure-counter",
            delta_id="delta:successor-invalidation",
        )
        self.assertEqual(
            FeedbackDisposition.INVALIDATES,
            invalidated.feedback[-1].disposition,
        )
        self.assertNotIn("cut:post-closure-counter", self.substrate.state.active_cut_ids)
        self.assertEqual(4, len(invalidated.provenance_closures))

    def test_forged_predecessor_closure_cannot_authorize_successor(self):
        field = self.post_closure_feedback()
        predecessor = field.provenance_closures[-1]
        forged = replace(
            field,
            provenance_closures=field.provenance_closures[:-1] + (
                replace(predecessor, counter_cut_id="cut:invented-protection"),
            ),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "exact provenance closure"):
            self.revise_post_closure(field=forged)
        self.assertEqual(before, self.substrate.state)

    def test_successor_closure_contains_no_protection_authority(self):
        revised = self.revise_post_closure(confirm=True)
        names = {
            item.name
            for record in (*revised.provenance_closures, revised)
            for item in fields(record)
        }
        self.assertTrue(names.isdisjoint({
            "certificate", "checkpoint", "protected", "protection", "immune",
            "immunity", "adequate", "authority", "confidence", "weight",
            "score", "rank", "selected", "preferred", "final", "success",
            "failure",
        }))


class SuccessorClosureRenewalAndEffectsTests(unittest.TestCase):
    """Renewed continuity never accumulates authority for a successor."""

    setUp = DiffractiveArrangementTests.setUp
    difference = DiffractiveArrangementTests.difference
    disturb = DiffractiveArrangementTests.disturb
    counter_cut = CounterCutRevisionTests.counter_cut
    revised_arrangement = CounterCutRevisionTests.revised_arrangement
    revise = CounterCutRevisionTests.revise
    witness = StructuralResponsivenessTests.witness
    proposed_counter_cut = OscillationCounterCutTests.proposed_counter_cut
    prepared = OscillationFieldReturnTests.prepared
    recomputed = OscillationFieldReturnTests.recomputed
    return_to_field = OscillationFieldReturnTests.return_to_field
    observed = staticmethod(PostReturnFeedbackTests.observed)
    feedback_counter_cut = FeedbackGroundedFieldRevisionTests.feedback_counter_cut
    feedback_recomputed = FeedbackGroundedFieldRevisionTests.feedback_recomputed
    with_feedback = FeedbackGroundedFieldRevisionTests.with_feedback
    apply_revision = FeedbackGroundedFieldRevisionTests.apply_revision
    later_counter_cut = RecursiveFeedbackGroundedRevisionTests.later_counter_cut
    later_recomputed = RecursiveFeedbackGroundedRevisionTests.later_recomputed
    later_feedback = RecursiveFeedbackGroundedRevisionTests.later_feedback
    revise_again = RecursiveFeedbackGroundedRevisionTests.revise_again
    further_counter_cut = BoundedRecursiveFeedbackRevisionTests.further_counter_cut
    further_recomputed = BoundedRecursiveFeedbackRevisionTests.further_recomputed
    further_feedback = BoundedRecursiveFeedbackRevisionTests.further_feedback
    revise_further = BoundedRecursiveFeedbackRevisionTests.revise_further
    post_closure_feedback = PostClosureGroundedFeedbackRevisionTests.post_closure_feedback
    successor_counter_cut = PostClosureGroundedFeedbackRevisionTests.successor_counter_cut
    successor_recomputed = PostClosureGroundedFeedbackRevisionTests.successor_recomputed
    revise_post_closure = PostClosureGroundedFeedbackRevisionTests.revise_post_closure

    def reenter_successor(self, field=None, **overrides):
        if field is None:
            field = self.revise_post_closure()
        values = dict(
            field=field,
            substrate=self.substrate,
            difference=ConsequentialDifference(
                witness_alternative_id="cut:shared-after-post-closure",
                contrasted_alternative_id="cut:distributed",
                dimension=StructuralDimension.BURDEN,
                measure=EffectMeasure.MAXIMUM_LOCAL_LOAD,
            ),
            enabling_cut_id="cut:enable-distributed",
            delta_id="delta:successor-reentry",
            triggering_trace_ids=("transport:post-closure-disturbance",),
        )
        values.update(overrides)
        return reenter_recomputed_arrangement_difference(**values)

    def test_successor_recomputation_renews_continuity_through_material_reentry(self):
        reentered = self.reenter_successor()
        trace = reentered.reentries[-1]
        self.assertEqual("cut:shared-after-post-closure", trace.witness_alternative_id)
        self.assertEqual("cut:post-closure-counter", trace.witness_counter_cut_id)
        self.assertEqual(4, len(reentered.provenance_closures))

    def test_reordered_closures_do_not_change_successor_reentry_authority(self):
        revised = self.revise_post_closure()
        reordered = replace(
            revised,
            provenance_closures=tuple(reversed(revised.provenance_closures)),
        )
        reentered = self.reenter_successor(field=reordered)
        self.assertEqual(
            "cut:post-closure-counter",
            reentered.reentries[-1].witness_counter_cut_id,
        )

    def test_valid_renewed_continuity_cannot_replace_active_successor_cut(self):
        revised = self.revise_post_closure()
        self.substrate.disturb(
            delta_id="delta:reopen-successor-counter",
            triggering_trace_ids=("transport:post-closure-disturbance",),
            invalidated_root_ids=("cut:post-closure-counter",),
            replacements=(),
        )
        before = self.substrate.state
        with self.assertRaisesRegex(InvalidReconfiguration, "active enabling formation"):
            self.reenter_successor(field=revised)
        self.assertEqual(before, self.substrate.state)

    def test_successor_receives_confirmation_without_accumulated_authority(self):
        revised = self.revise_post_closure(confirm=True)
        current = revised.field.competing.alternatives[0]
        self.substrate.record_transport(transport(
            "transport:renewed-successor-confirmation",
            "The successor presently corresponds without becoming authoritative.",
        ))
        confirmed = return_effects_as_feedback(
            field=revised,
            substrate=self.substrate,
            observation_trace_id="transport:renewed-successor-confirmation",
            alternative_id="cut:shared-after-post-closure",
            observed_effects=self.observed(current),
            disposition=FeedbackDisposition.CONFIRMS,
        )
        confirmations = tuple(
            item for item in confirmed.feedback
            if item.disposition == FeedbackDisposition.CONFIRMS
        )
        self.assertEqual(2, len(confirmations))
        self.assertIn("cut:post-closure-counter", self.substrate.state.active_cut_ids)
        self.assertFalse(hasattr(confirmed, "confidence"))

    def test_renewed_successor_remains_immediately_open_to_complication(self):
        revised = self.revise_post_closure()
        current = revised.field.competing.alternatives[0]
        self.substrate.enact_cut(
            dependent_cut(
                "cut:renewed-successor-dependent",
                "cut:post-closure-counter",
                "renewed successor effect-local dependent",
            ),
            delta_id="delta:renewed-successor-dependent",
        )
        self.substrate.record_transport(transport(
            "transport:renewed-successor-complication",
            "Further effects complicate one local successor relation.",
        ))
        complicated = return_effects_as_feedback(
            field=revised,
            substrate=self.substrate,
            observation_trace_id="transport:renewed-successor-complication",
            alternative_id="cut:shared-after-post-closure",
            observed_effects=self.observed(current, burden_maximum=3.4),
            disposition=FeedbackDisposition.COMPLICATES,
            affected_cut_id="cut:renewed-successor-dependent",
            delta_id="delta:renewed-successor-complication",
        )
        self.assertEqual(FeedbackDisposition.COMPLICATES, complicated.feedback[-1].disposition)
        self.assertIn("cut:post-closure-counter", self.substrate.state.active_cut_ids)
        self.assertEqual(4, len(complicated.provenance_closures))

    def test_renewed_successor_remains_immediately_open_to_invalidation(self):
        revised = self.revise_post_closure(confirm=True)
        current = revised.field.competing.alternatives[0]
        self.substrate.record_transport(transport(
            "transport:renewed-successor-invalidation",
            "Further effects reopen the successor formation.",
        ))
        invalidated = return_effects_as_feedback(
            field=revised,
            substrate=self.substrate,
            observation_trace_id="transport:renewed-successor-invalidation",
            alternative_id="cut:shared-after-post-closure",
            observed_effects=self.observed(current, burden_maximum=3.5),
            disposition=FeedbackDisposition.INVALIDATES,
            affected_cut_id="cut:post-closure-counter",
            delta_id="delta:renewed-successor-invalidation",
        )
        prior_confirmation = next(
            item for item in invalidated.feedback
            if item.observation_trace_id == "transport:post-closure-confirmation"
        )
        self.assertEqual(FeedbackDisposition.CONFIRMS, prior_confirmation.disposition)
        self.assertEqual(FeedbackDisposition.INVALIDATES, invalidated.feedback[-1].disposition)
        self.assertNotIn("cut:post-closure-counter", self.substrate.state.active_cut_ids)
        self.assertFalse(hasattr(invalidated.feedback[-1], "failure"))

    def test_renewal_records_contain_no_cumulative_authority(self):
        revised = self.revise_post_closure(confirm=True)
        names = {
            item.name
            for record in (*revised.provenance_closures, revised)
            for item in fields(record)
        }
        self.assertTrue(names.isdisjoint({
            "renewals", "renewal_count", "depth", "generation", "maturity",
            "authority", "confidence", "weight", "score", "rank",
            "selected", "preferred", "protected", "certificate", "final",
            "success", "failure",
        }))


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
