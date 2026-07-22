from copy import deepcopy
import unittest

from cbra.native import (
    Apparatus,
    DriftKind,
    DriftSignal,
    RuntimeHypotheses,
    Stream,
    articulate,
    form_provisional_cut,
    initialize_field,
    reinsert_articulation,
    reintegrate_field,
    run_until_articulation,
    update_field,
)
from cbra.native.models import ProvisionalCut
from cbra.native.operators import (
    propose_coactive_updates,
    propose_play,
    relation_for_pair,
)


class NativeRuntimeArchitectureTests(unittest.TestCase):
    def make_field(self):
        return initialize_field(
            [
                Stream(
                    stream_id="user:1",
                    kind="user_input",
                    payload={
                        "text": "How can creative becoming stay open under pressure?"
                    },
                    participation=0.82,
                    persistence=0.80,
                ),
                Stream(
                    stream_id="memory:1",
                    kind="memory",
                    payload={
                        "text": "Pressure has previously narrowed what could be noticed."
                    },
                    participation=0.64,
                    persistence=0.75,
                ),
                Stream(
                    stream_id="environment:1",
                    kind="environment",
                    payload={
                        "text": "The deadline and interface are participating."
                    },
                    participation=0.58,
                    persistence=0.70,
                ),
            ],
            apparatus=Apparatus(
                apparatus_id="apparatus:test",
                framing="architecture-first inquiry",
                medium="text_chat",
                constraints=["non-coercive closure"],
                institutions=["ChatGPT"],
            ),
            field_id="field:test",
        )

    def test_every_operator_proposes_from_one_shared_field_state(self):
        state = self.make_field()
        untouched = deepcopy(state)
        proposals, _ = propose_coactive_updates(
            state,
            RuntimeHypotheses(),
        )
        self.assertEqual(state, untouched)
        self.assertEqual(
            {delta.basis_timestep for delta in proposals},
            {0},
        )

        trace = update_field(state)

        self.assertTrue(trace.coactive)
        self.assertEqual(
            trace.operator_order,
            [
                "intra_action",
                "play",
                "diffraction",
                "creative_becoming",
                "care",
            ],
        )
        self.assertEqual(trace.calculation_basis_timestep, 0)
        self.assertEqual(
            {delta.basis_timestep for delta in trace.deltas},
            {0},
        )
        self.assertEqual(state.timestep, 1)
        self.assertTrue(any(delta.patterns for delta in trace.deltas))
        play_delta = next(
            item for item in trace.deltas if item.operator_name == "play"
        )
        self.assertFalse(play_delta.proposed_streams)
        self.assertIn(
            "regulatory coherence",
            play_delta.traces[0],
        )
        self.assertTrue(state.current_phenomenon_ids)
        self.assertTrue(
            all(
                state.phenomenon(item_id).timestep == state.timestep
                for item_id in state.current_phenomenon_ids
            )
        )
        self.assertIn("care_max_stream_shift", trace.hypotheses)

    def test_apparatus_is_materialized_and_modulates_relations(self):
        state = self.make_field()
        apparatus_ids = {
            item.stream_id
            for item in state.streams
            if item.kind == "apparatus"
        }
        self.assertGreaterEqual(len(apparatus_ids), 4)

        update_field(state)
        self.assertTrue(
            any(item.apparatus_effect > 0.0 for item in state.relations)
        )
        self.assertTrue(
            all(item.co_presence > 0.0 for item in state.relations)
        )

    def test_care_changes_the_field_and_constrains_other_operators(self):
        state = self.make_field()
        state.field_values.cut_pressure = 0.90
        state.field_values.cut_permeability = 0.20
        before_permeability = state.field_values.cut_permeability

        trace = update_field(state)

        care_delta = next(
            item for item in trace.deltas if item.operator_name == "care"
        )
        self.assertIn("cut_permeability", care_delta.field_value_changes)
        self.assertGreater(
            state.field_values.cut_permeability,
            before_permeability,
        )
        self.assertTrue(
            any(
                item.target == "field:cut_pressure"
                for item in trace.care_constraints
            )
        )
        self.assertGreaterEqual(
            state.field_values.multiplicity,
            RuntimeHypotheses().care_min_multiplicity,
        )

    def test_provisional_cut_uses_relational_components_and_holds_open_the_rest(self):
        state = self.make_field()
        state.streams.append(
            Stream(
                stream_id="quiet:1",
                kind="other",
                payload={"text": "A quiet strand remains available."},
                participation=0.44,
                persistence=0.90,
            )
        )
        hypotheses = RuntimeHypotheses(
            articulation_emergence_floor=0.10,
            articulation_coherence_floor=0.08,
        )
        update_field(state, hypotheses)
        cut = form_provisional_cut(state, hypotheses)

        self.assertIsNotNone(cut)
        self.assertIn("quiet:1", cut.held_open_stream_ids)
        self.assertNotIn("quiet:1", cut.included_stream_ids)
        self.assertEqual(cut.excluded_stream_ids, [])
        self.assertEqual(
            cut.basis,
            "relational_participation_without_ranking",
        )
        self.assertTrue(set(cut.included_stream_ids).isdisjoint(cut.held_open_stream_ids))

        cut_fields = set(ProvisionalCut.__dataclass_fields__)
        self.assertNotIn("selected_elements", cut_fields)
        self.assertNotIn("foregrounded", cut_fields)
        self.assertNotIn("ranked_streams", cut_fields)

    def test_articulation_comes_from_the_cut_and_reenters_as_a_stream(self):
        state = self.make_field()
        hypotheses = RuntimeHypotheses(
            articulation_emergence_floor=0.10,
            articulation_coherence_floor=0.08,
        )
        update_field(state, hypotheses)
        cut = form_provisional_cut(state, hypotheses)
        result = articulate(state, cut)

        self.assertIsNotNone(result)
        self.assertIn(
            "How can creative becoming stay open under pressure?",
            result.text,
        )
        self.assertEqual(result.cut_id, cut.cut_id)
        self.assertEqual(result.included_stream_ids, cut.included_stream_ids)
        self.assertTrue(result.provisional)

        stream_id = reinsert_articulation(state, result)
        inserted = state.stream(stream_id)
        self.assertIsNotNone(inserted)
        self.assertEqual(inserted.kind, "articulation")
        self.assertEqual(inserted.payload["text"], result.text)
        self.assertEqual(inserted.payload["cut_id"], cut.cut_id)

        update_field(state, hypotheses)
        self.assertTrue(
            any(
                item.left_id == stream_id or item.right_id == stream_id
                for item in state.relations
            )
        )

    def test_each_drift_form_has_a_distinct_reintegration(self):
        traces = {}
        for kind in DriftKind:
            state = self.make_field()
            update_field(state)
            user = state.stream("user:1")
            memory = state.stream("memory:1")
            user.participation = 0.98
            memory.participation = 0.08
            state.field_values.cut_pressure = 0.90
            state.field_values.cut_permeability = 0.10
            state.field_values.care_capacity = 0.10
            state.field_values.care_tension = 0.90

            before_gap = abs(user.participation - memory.participation)
            before_capacity = state.field_values.care_capacity
            before_permeability = state.field_values.cut_permeability
            before_relation_total = sum(
                item.mutuality for item in state.relations
            )
            before_participation_total = sum(
                item.participation for item in state.streams
            )

            signal = DriftSignal(
                kind=kind,
                intensity=1.0,
                evidence=["test signal"],
                detected_at=state.timestep,
                source="test",
            )
            trace = reintegrate_field(state, [signal])[0]
            traces[kind] = trace.trace

            if kind == DriftKind.COMPRESSION:
                self.assertGreater(
                    state.field_values.cut_permeability,
                    before_permeability,
                )
            elif kind == DriftKind.NARRATIVE_DOMINANCE:
                self.assertLess(
                    abs(user.participation - memory.participation),
                    before_gap,
                )
            elif kind == DriftKind.MORALIZATION:
                self.assertGreater(state.field_values.openness, 0.55)
            elif kind == DriftKind.CAPACITY_COLLAPSE:
                self.assertGreater(
                    state.field_values.care_capacity,
                    before_capacity,
                )
                self.assertLess(
                    sum(item.participation for item in state.streams),
                    before_participation_total,
                )
            elif kind == DriftKind.ONTOLOGICAL_DRIFT:
                self.assertGreater(
                    sum(item.mutuality for item in state.relations),
                    before_relation_total,
                )
            elif kind == DriftKind.PROCEDURAL_BYPASS:
                self.assertFalse(trace.stream_participation_changes)
                self.assertFalse(trace.relation_changes)

        self.assertEqual(len(set(traces.values())), len(DriftKind))

    def test_complete_movement_records_history_and_reinsertion(self):
        state = self.make_field()
        result, cycles = run_until_articulation(state, max_cycles=5)

        self.assertIsNotNone(result)
        self.assertGreaterEqual(len(cycles), 1)
        self.assertEqual(len(state.history), len(cycles))
        self.assertEqual(
            state.history[-1].articulation_id,
            result.articulation_id,
        )
        self.assertEqual(
            state.history[-1].before.timestep + 1,
            state.history[-1].after.timestep,
        )
        inserted_id = "stream:{0}".format(result.articulation_id)
        self.assertIsNotNone(state.stream(inserted_id))
        self.assertEqual(
            state.stream(inserted_id).provenance["movement"],
            "articulation_reinsertion",
        )
        self.assertFalse(
            any(cycle.trace.drift_signals for cycle in cycles)
        )

    def test_difference_and_co_presence_do_not_manufacture_a_relation(self):
        hypotheses = RuntimeHypotheses()
        left = Stream(
            stream_id="cedar:1",
            kind="memory",
            payload={"text": "cedar roots"},
            participation=0.72,
            persistence=0.80,
        )
        right = Stream(
            stream_id="river:1",
            kind="environment",
            payload={"text": "river current"},
            participation=0.75,
            persistence=0.80,
        )

        evidence = relation_for_pair(left, right, hypotheses)

        self.assertGreater(evidence.co_presence, 0.0)
        self.assertEqual(evidence.difference, 1.0)
        self.assertEqual(evidence.interference, 0.0)
        self.assertEqual(evidence.mutuality, 0.0)
        self.assertGreater(evidence.apparatus_effect, 0.0)

        state = initialize_field([left, right], field_id="field:sparse")
        update_field(state, hypotheses)
        self.assertFalse(state.relations)
        self.assertFalse(state.current_phenomenon_ids)
        self.assertTrue(all(item.active for item in state.streams))

    def test_apparatus_can_attach_without_collapsing_constellations(self):
        state, hypotheses = self.make_two_constellation_field(
            framing="cedar river"
        )

        update_field(state, hypotheses)
        phenomena = [
            state.phenomenon(item_id)
            for item_id in state.current_phenomenon_ids
        ]

        self.assertEqual(len(phenomena), 2)
        self.assertEqual(
            {
                frozenset(
                    item_id
                    for item_id in phenomenon.stream_ids
                    if not item_id.startswith("apparatus:topology")
                )
                for phenomenon in phenomena
            },
            {
                frozenset({"a:1", "a:2"}),
                frozenset({"b:1", "b:2"}),
            },
        )
        self.assertTrue(
            all(
                "apparatus:topology:framing" in phenomenon.stream_ids
                for phenomenon in phenomena
            )
        )

    def test_play_waits_for_capacity_and_varies_only_enacted_patterns(self):
        state, hypotheses = self.make_two_constellation_field()

        initial = propose_play(state, hypotheses)
        self.assertFalse(initial.proposed_streams)

        state.field_values.coherence = hypotheses.play_coherence_floor
        ready = propose_play(state, hypotheses)
        source_pairs = {
            frozenset(item.payload["source_stream_ids"])
            for item in ready.proposed_streams
        }
        self.assertEqual(
            source_pairs,
            {
                frozenset({"a:1", "a:2"}),
                frozenset({"b:1", "b:2"}),
            },
        )
        self.assertTrue(
            all("quiet:1" not in pair for pair in source_pairs)
        )

        state.field_values.care_capacity = (
            hypotheses.play_care_capacity_floor - 0.01
        )
        constrained = propose_play(state, hypotheses)
        self.assertFalse(constrained.proposed_streams)

    def test_composite_cut_preserves_distinct_forms_and_active_held_open_material(self):
        state, hypotheses = self.make_two_constellation_field()

        update_field(state, hypotheses)
        cut = form_provisional_cut(state, hypotheses)

        self.assertIsNotNone(cut)
        self.assertEqual(len(cut.phenomenon_ids), 2)
        self.assertEqual(
            set(cut.included_stream_ids),
            {"a:1", "a:2", "b:1", "b:2"},
        )
        self.assertIn("quiet:1", cut.held_open_stream_ids)
        self.assertGreater(state.stream("quiet:1").participation, 0.0)
        self.assertEqual(cut.excluded_stream_ids, [])

    def test_relation_growth_follows_enactment_not_a_complete_graph(self):
        state, hypotheses = self.make_two_constellation_field()

        update_field(state, hypotheses)
        first_relation_ids = {item.relation_id for item in state.relations}
        update_field(state, hypotheses)

        stream_count = len([item for item in state.streams if item.active])
        complete_graph_size = stream_count * (stream_count - 1) // 2
        self.assertEqual(len(first_relation_ids), 2)
        self.assertEqual(
            {item.relation_id for item in state.relations},
            first_relation_ids,
        )
        self.assertLess(len(state.relations), complete_graph_size)
        self.assertTrue(all(item.active for item in state.relations))

    def test_reinserted_articulation_participates_without_collapsing_forms(self):
        state, hypotheses = self.make_two_constellation_field()
        update_field(state, hypotheses)
        cut = form_provisional_cut(state, hypotheses)
        result = articulate(state, cut)
        inserted_id = reinsert_articulation(state, result, hypotheses)

        update_field(state, hypotheses)
        phenomena = [
            state.phenomenon(item_id)
            for item_id in state.current_phenomenon_ids
        ]

        self.assertEqual(len(phenomena), 2)
        self.assertTrue(
            all(inserted_id in item.stream_ids for item in phenomena)
        )
        self.assertTrue(
            all("quiet:1" not in item.stream_ids for item in phenomena)
        )

    def make_two_constellation_field(self, framing="shared inquiry"):
        hypotheses = RuntimeHypotheses(
            articulation_emergence_floor=0.05,
            articulation_coherence_floor=0.05,
        )
        state = initialize_field(
            [
                Stream(
                    stream_id="a:1",
                    kind="memory",
                    payload={"text": "cedar roots shelter soil"},
                    participation=0.72,
                    persistence=0.80,
                ),
                Stream(
                    stream_id="a:2",
                    kind="user_input",
                    payload={"text": "cedar soil holds moisture"},
                    participation=0.74,
                    persistence=0.80,
                ),
                Stream(
                    stream_id="b:1",
                    kind="environment",
                    payload={"text": "river currents shape stone"},
                    participation=0.70,
                    persistence=0.80,
                ),
                Stream(
                    stream_id="b:2",
                    kind="document",
                    payload={"text": "river stone carries silt"},
                    participation=0.75,
                    persistence=0.80,
                ),
                Stream(
                    stream_id="quiet:1",
                    kind="other",
                    payload={"text": "lantern ember waits"},
                    participation=0.61,
                    persistence=0.80,
                ),
            ],
            apparatus=Apparatus(
                apparatus_id="apparatus:topology",
                framing=framing,
                medium="text chat",
                institutions=["ChatGPT"],
            ),
            field_id="field:topology",
            hypotheses=hypotheses,
        )
        return state, hypotheses


if __name__ == "__main__":
    unittest.main()
