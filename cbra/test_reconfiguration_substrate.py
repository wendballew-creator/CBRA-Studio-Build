from dataclasses import fields, replace
import unittest

from cbra.reconfiguration import (
    Allocation,
    ConfigurationTrace,
    CutEnactment,
    CutPosition,
    InvalidReconfiguration,
    LocalPositionRef,
    ReconfigurationSubstrate,
    Relation,
    StorageOntologyViolation,
    StructuralDimension,
    TransportTrace,
)


def trace(trace_id: str, text: str) -> TransportTrace:
    return TransportTrace(
        trace_id=trace_id,
        channel="text/plain",
        digest=f"digest:{trace_id}",
        payload=text.encode(),
        observed_at="2026-07-27T00:00:00Z",
        provenance={"technical_channel": "fixture"},
    )


def local(cut_id: str, key: str) -> LocalPositionRef:
    return LocalPositionRef(cut_id=cut_id, position_key=key)


def case2_initial_cut(cut_id: str = "cut:initial") -> CutEnactment:
    return CutEnactment(
        cut_id=cut_id,
        transport_basis=("transport:missed",),
        dependency_ids=(),
        lineage_ids=(),
        positions=(
            CutPosition("participant", "commitment-bearing position"),
            CutPosition("arrangement", "work arrangement"),
        ),
        relations=(
            Relation(
                "individualized-cause",
                local(cut_id, "participant"),
                local(cut_id, "arrangement"),
            ),
        ),
        allocations=(
            Allocation(StructuralDimension.BURDEN, local(cut_id, "participant"), 4),
            Allocation(StructuralDimension.CAPACITY, local(cut_id, "participant"), 3),
            Allocation(StructuralDimension.CONSEQUENCE, local(cut_id, "participant"), 2),
            Allocation(StructuralDimension.POWER, local(cut_id, "participant"), 3),
            Allocation(StructuralDimension.POSSIBILITY, local(cut_id, "arrangement"), 1),
        ),
        revision_conditions=("later capacity evidence",),
        exclusions=("unobserved material conditions",),
    )


def dependent_accountability_cut(cut_id: str = "cut:accountability") -> CutEnactment:
    return CutEnactment(
        cut_id=cut_id,
        transport_basis=("transport:missed",),
        dependency_ids=("cut:initial",),
        lineage_ids=(),
        positions=(
            CutPosition("same-position", "repair and warning bearer"),
            CutPosition("unchanged-work", "unchanged work arrangement"),
        ),
        allocations=(
            Allocation(StructuralDimension.BURDEN, local(cut_id, "same-position"), 4),
            Allocation(StructuralDimension.CAPACITY, local(cut_id, "same-position"), 2),
            Allocation(StructuralDimension.CONSEQUENCE, local(cut_id, "same-position"), 2),
            Allocation(StructuralDimension.POWER, local(cut_id, "same-position"), 2),
        ),
    )


def reconfigured_case2_cut(cut_id: str = "cut:reconfigured") -> CutEnactment:
    return CutEnactment(
        cut_id=cut_id,
        transport_basis=("transport:missed", "transport:disclosure"),
        dependency_ids=(),
        lineage_ids=("cut:initial", "cut:accountability"),
        positions=(
            CutPosition("disclosing-position", "locally addressable disclosure"),
            CutPosition("coordination", "coordination arrangement"),
            CutPosition("affected-work", "effects across work"),
        ),
        relations=(
            Relation(
                "capacity-shapes-next-scale",
                local(cut_id, "disclosing-position"),
                local(cut_id, "coordination"),
            ),
            Relation(
                "delay-has-distributed-effects",
                local(cut_id, "affected-work"),
                local(cut_id, "coordination"),
            ),
        ),
        allocations=(
            Allocation(StructuralDimension.BURDEN, local(cut_id, "disclosing-position"), 1),
            Allocation(StructuralDimension.BURDEN, local(cut_id, "coordination"), 2),
            Allocation(StructuralDimension.CAPACITY, local(cut_id, "coordination"), 1),
            Allocation(StructuralDimension.CONSEQUENCE, local(cut_id, "affected-work"), 2),
            Allocation(StructuralDimension.POWER, local(cut_id, "coordination"), 1),
            Allocation(StructuralDimension.POWER, local(cut_id, "affected-work"), 1),
            Allocation(StructuralDimension.POSSIBILITY, local(cut_id, "coordination"), 4),
        ),
        revision_conditions=("observed response effect", "new capacity evidence"),
        exclusions=("private cause", "total available capacity"),
    )


class StorageOntologyBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.runtime = ReconfigurationSubstrate()
        self.runtime.record_transport(trace("transport:missed", "Work was not delivered."))

    def test_transport_schema_has_no_semantic_role_fields(self):
        names = {item.name for item in fields(TransportTrace)}
        self.assertTrue(
            names.isdisjoint(
                {"user", "actor", "event", "failure", "explanation", "intent", "role"}
            )
        )

    def test_transport_provenance_cannot_smuggle_a_semantic_role(self):
        with self.assertRaisesRegex(ValueError, "semantic roles"):
            TransportTrace(
                trace_id="transport:bad",
                channel="text/plain",
                digest="digest:bad",
                payload=b"opaque",
                observed_at="2026-07-27T00:00:00Z",
                provenance={"role": "user"},
            )

        with self.assertRaisesRegex(ValueError, "semantic roles"):
            TransportTrace(
                trace_id="transport:nested-bad",
                channel="text/plain",
                digest="digest:nested-bad",
                payload=b"opaque",
                observed_at="2026-07-27T00:00:00Z",
                provenance={"headers": {"role": "user"}},
            )

    def test_nested_transport_provenance_is_immutable(self):
        item = TransportTrace(
            trace_id="transport:nested",
            channel="text/plain",
            digest="digest:nested",
            payload=b"opaque",
            observed_at="2026-07-27T00:00:00Z",
            provenance={"headers": {"content-type": "text/plain"}},
        )
        with self.assertRaises(TypeError):
            item.provenance["headers"]["content-type"] = "changed"

    def test_transport_payload_is_opaque_and_history_is_not_rewritten(self):
        before = self.runtime.state.transports["transport:missed"]
        self.runtime.enact_cut(case2_initial_cut(), delta_id="delta:initial")
        self.assertEqual(before, self.runtime.state.transports["transport:missed"])
        self.assertIsInstance(before.payload, bytes)

    def test_transport_id_cannot_become_a_semantic_position(self):
        bad = replace(
            case2_initial_cut(),
            positions=(CutPosition("transport:missed", "person"),),
            relations=(),
            allocations=(),
        )
        with self.assertRaises(StorageOntologyViolation):
            self.runtime.enact_cut(bad, delta_id="delta:bad")

    def test_semantic_positions_cannot_cross_their_local_cut(self):
        bad = replace(
            case2_initial_cut(),
            allocations=(
                Allocation(
                    StructuralDimension.BURDEN,
                    local("some-global-cut", "participant"),
                    1,
                ),
            ),
        )
        with self.assertRaises(InvalidReconfiguration):
            self.runtime.enact_cut(bad, delta_id="delta:bad-ref")

    def test_same_transport_supports_different_local_positions_without_identity(self):
        first = case2_initial_cut()
        self.runtime.enact_cut(first, delta_id="delta:first")
        second = CutEnactment(
            cut_id="cut:counter",
            transport_basis=("transport:missed",),
            dependency_ids=(),
            lineage_ids=(),
            positions=(CutPosition("coordination-signal", "coordination disturbance"),),
        )
        self.runtime.enact_cut(second, delta_id="delta:second")
        self.assertNotEqual(first.positions, second.positions)
        self.assertEqual(first.transport_basis, second.transport_basis)

    def test_matching_local_names_across_cuts_do_not_create_shared_refs(self):
        first = case2_initial_cut()
        self.runtime.enact_cut(first, delta_id="delta:first")
        second = CutEnactment(
            cut_id="cut:second",
            transport_basis=("transport:missed",),
            dependency_ids=(),
            lineage_ids=(),
            positions=(CutPosition("participant", "commitment-bearing position"),),
        )
        self.runtime.enact_cut(second, delta_id="delta:second")
        self.assertNotEqual(
            local("cut:initial", "participant"),
            local("cut:second", "participant"),
        )

    def test_continuity_requires_explicit_lineage_not_matching_transport(self):
        self.runtime.enact_cut(case2_initial_cut(), delta_id="delta:first")
        independent = CutEnactment(
            cut_id="cut:later",
            transport_basis=("transport:missed",),
            dependency_ids=(),
            lineage_ids=(),
            positions=(CutPosition("later", "later local position"),),
        )
        self.runtime.enact_cut(independent, delta_id="delta:later")
        self.assertEqual((), self.runtime.state.cuts["cut:later"].lineage_ids)


class DependencyInvalidationTests(unittest.TestCase):
    def setUp(self):
        self.runtime = ReconfigurationSubstrate()
        self.runtime.record_transport(trace("transport:missed", "Work was not delivered."))
        self.runtime.record_transport(trace("transport:disclosure", "I have had too much to hold."))
        self.runtime.enact_cut(case2_initial_cut(), delta_id="delta:initial")
        self.runtime.enact_cut(
            dependent_accountability_cut(), delta_id="delta:accountability"
        )
        downstream = CutEnactment(
            cut_id="cut:downstream",
            transport_basis=("transport:missed",),
            dependency_ids=("cut:accountability",),
            lineage_ids=(),
            positions=(CutPosition("release", "prospective intervention"),),
        )
        self.runtime.enact_cut(downstream, delta_id="delta:downstream")

    def test_disturbance_recursively_invalidates_all_dependents(self):
        delta = self.runtime.disturb(
            delta_id="delta:disclosure",
            triggering_trace_ids=("transport:disclosure",),
            invalidated_root_ids=("cut:initial",),
            replacements=(reconfigured_case2_cut(),),
        )
        self.assertEqual(
            {"cut:initial", "cut:accountability", "cut:downstream"},
            set(delta.invalidated_cut_ids),
        )
        self.assertEqual(("cut:reconfigured",), self.runtime.state.active_cut_ids)
        self.assertEqual(
            {"cut:initial", "cut:accountability", "cut:downstream"},
            set(self.runtime.state.invalidated_by),
        )

    def test_unrelated_cut_remains_active(self):
        unrelated = CutEnactment(
            cut_id="cut:unrelated",
            transport_basis=("transport:missed",),
            dependency_ids=(),
            lineage_ids=(),
            positions=(CutPosition("technical", "unrelated technical constraint"),),
        )
        self.runtime.enact_cut(unrelated, delta_id="delta:unrelated")
        self.runtime.disturb(
            delta_id="delta:disclosure",
            triggering_trace_ids=("transport:disclosure",),
            invalidated_root_ids=("cut:initial",),
            replacements=(reconfigured_case2_cut(),),
        )
        self.assertIn("cut:unrelated", self.runtime.state.active_cut_ids)

    def test_replacement_cannot_depend_on_invalidated_cut(self):
        bad = replace(
            reconfigured_case2_cut(), dependency_ids=("cut:accountability",)
        )
        before = self.runtime.state
        with self.assertRaises(InvalidReconfiguration):
            self.runtime.disturb(
                delta_id="delta:bad",
                triggering_trace_ids=("transport:disclosure",),
                invalidated_root_ids=("cut:initial",),
                replacements=(bad,),
            )
        self.assertIs(before, self.runtime.state)

    def test_atomic_replacements_cannot_hide_a_new_pipeline(self):
        one = reconfigured_case2_cut("cut:one")
        two = replace(
            reconfigured_case2_cut("cut:two"), dependency_ids=("cut:one",)
        )
        with self.assertRaisesRegex(InvalidReconfiguration, "stage order"):
            self.runtime.disturb(
                delta_id="delta:pipeline",
                triggering_trace_ids=("transport:disclosure",),
                invalidated_root_ids=("cut:initial",),
                replacements=(one, two),
            )


class StructuralDeltaAndCase2Tests(unittest.TestCase):
    def make_runtime(self) -> ReconfigurationSubstrate:
        runtime = ReconfigurationSubstrate()
        runtime.record_transport(trace("transport:missed", "Work was not delivered."))
        runtime.record_transport(trace("transport:disclosure", "I am overwhelmed."))
        runtime.enact_cut(case2_initial_cut(), delta_id="delta:initial")
        runtime.enact_cut(
            dependent_accountability_cut(), delta_id="delta:accountability"
        )
        return runtime

    def test_case2_disclosure_changes_all_required_structural_dimensions(self):
        runtime = self.make_runtime()
        delta = runtime.disturb(
            delta_id="delta:case2",
            triggering_trace_ids=("transport:disclosure",),
            invalidated_root_ids=("cut:initial",),
            replacements=(reconfigured_case2_cut(),),
        )
        self.assertEqual(set(StructuralDimension), set(delta.changed_dimensions))
        self.assertTrue(delta.has_structural_change)
        self.assertEqual(("transport:disclosure",), delta.triggering_trace_ids)

    def test_delta_is_derived_not_caller_asserted(self):
        names = {item.name for item in fields(type(self.make_runtime().state.deltas[-1]))}
        self.assertNotIn("care_claim", names)
        self.assertNotIn("reconfigured", names)
        self.assertNotIn("rationale", names)

    def test_textual_paraphrase_cannot_change_burden_topology(self):
        versions = (
            "Please send a revised completion date and flag delays earlier.",
            "Name a new delivery point and give notice sooner next time.",
            "Choose when the work will arrive and alert the group before it slips.",
        )
        snapshots = []
        for index, wording in enumerate(versions):
            runtime = self.make_runtime()
            runtime.record_transport(trace(f"transport:wording:{index}", wording))
            snapshots.append(
                tuple(
                    (item.dimension, item.position.position_key, item.amount)
                    for item in runtime.state.deltas[-1].allocation_after
                )
            )
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertEqual(snapshots[1], snapshots[2])

    def test_payload_only_change_is_storage_not_reconfiguration(self):
        runtime = self.make_runtime()
        delta_count = len(runtime.state.deltas)
        runtime.record_transport(
            trace("transport:empathy", "I hear that things have been difficult.")
        )
        self.assertEqual(delta_count, len(runtime.state.deltas))

    def test_relabelled_same_topology_does_not_claim_distribution_change(self):
        runtime = ReconfigurationSubstrate()
        runtime.record_transport(trace("transport:missed", "Work was not delivered."))
        runtime.record_transport(trace("transport:disclosure", "I am overwhelmed."))
        initial = case2_initial_cut()
        runtime.enact_cut(initial, delta_id="delta:initial")
        relabelled = CutEnactment(
            cut_id="cut:renamed",
            transport_basis=("transport:missed", "transport:disclosure"),
            dependency_ids=(),
            lineage_ids=("cut:initial",),
            positions=(
                CutPosition("different-a", "new words"),
                CutPosition("different-b", "more new words"),
            ),
            relations=(
                Relation(
                    "new-relation-label",
                    local("cut:renamed", "different-a"),
                    local("cut:renamed", "different-b"),
                ),
            ),
            allocations=(
                Allocation(StructuralDimension.BURDEN, local("cut:renamed", "different-a"), 4),
                Allocation(StructuralDimension.CAPACITY, local("cut:renamed", "different-a"), 3),
                Allocation(StructuralDimension.CONSEQUENCE, local("cut:renamed", "different-a"), 2),
                Allocation(StructuralDimension.POWER, local("cut:renamed", "different-a"), 3),
                Allocation(StructuralDimension.POSSIBILITY, local("cut:renamed", "different-b"), 1),
            ),
        )
        delta = runtime.disturb(
            delta_id="delta:relabel",
            triggering_trace_ids=("transport:disclosure",),
            invalidated_root_ids=("cut:initial",),
            replacements=(relabelled,),
        )
        self.assertEqual((), delta.changed_dimensions)
        self.assertTrue(delta.has_structural_change)

    def test_disturbance_without_replacement_still_records_real_invalidation(self):
        runtime = self.make_runtime()
        delta = runtime.disturb(
            delta_id="delta:withhold",
            triggering_trace_ids=("transport:disclosure",),
            invalidated_root_ids=("cut:initial",),
            replacements=(),
        )
        self.assertTrue(delta.has_structural_change)
        self.assertEqual((), runtime.state.active_cut_ids)

    def test_configuration_rejects_restored_active_cut_with_missing_dependency(self):
        runtime = self.make_runtime()
        corrupted = ConfigurationTrace(
            version=runtime.state.version,
            transports=runtime.state.transports,
            cuts=runtime.state.cuts,
            active_cut_ids=("cut:accountability",),
            invalidated_by={},
            deltas=runtime.state.deltas,
        )
        with self.assertRaises(InvalidReconfiguration):
            ReconfigurationSubstrate(corrupted)

    def test_configuration_rejects_restored_dependency_cycle(self):
        runtime = self.make_runtime()
        one = replace(
            runtime.state.cuts["cut:initial"], dependency_ids=("cut:accountability",)
        )
        cuts = dict(runtime.state.cuts)
        cuts["cut:initial"] = one
        corrupted = ConfigurationTrace(
            version=runtime.state.version,
            transports=runtime.state.transports,
            cuts=cuts,
            active_cut_ids=runtime.state.active_cut_ids,
            invalidated_by={},
            deltas=runtime.state.deltas,
        )
        with self.assertRaisesRegex(InvalidReconfiguration, "cycle"):
            ReconfigurationSubstrate(corrupted)


if __name__ == "__main__":
    unittest.main()
