from copy import deepcopy
from dataclasses import replace
import unittest
from unittest.mock import patch

from cbra.native import (
    Apparatus,
    CyclePhase,
    DRIFT_REENTRY_TARGETS,
    DriftKind,
    DriftSignal,
    ReentryTarget,
    RuntimeHypotheses,
    Stream,
    articulate,
    form_articulation_candidate,
    form_provisional_cut,
    initialize_field,
    reinsert_articulation,
    reintegrate_field,
    run_cycle,
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
        self.assertNotIn(
            "How can creative becoming stay open under pressure?",
            result.text,
        )
        self.assertIn(
            "creative becoming stay open under pressure",
            result.text,
        )
        self.assertEqual(result.cut_id, cut.cut_id)
        self.assertEqual(result.included_stream_ids, cut.included_stream_ids)
        self.assertTrue(result.provisional)
        evaluation = state.current_evaluation()
        self.assertIsNotNone(evaluation)
        self.assertTrue(evaluation.accepted)
        self.assertEqual(result.evaluation_id, evaluation.evaluation_id)

        stream_id = reinsert_articulation(state, result)
        inserted = state.stream(stream_id)
        self.assertIsNotNone(inserted)
        self.assertEqual(inserted.kind, "articulation")
        self.assertNotIn("text", inserted.payload)
        self.assertEqual(inserted.payload["cut_id"], cut.cut_id)
        self.assertEqual(
            inserted.payload["included_stream_ids"],
            cut.included_stream_ids,
        )
        self.assertEqual(reinsert_articulation(state, result), stream_id)
        self.assertEqual(
            len(
                [
                    item
                    for item in state.streams
                    if item.stream_id == stream_id
                ]
            ),
            1,
        )

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

    def test_reintegration_traces_canonical_target_and_signal_evidence(self):
        expected = {
            DriftKind.ONTOLOGICAL_DRIFT: ReentryTarget.FIELD_ENTRY,
            DriftKind.COMPRESSION: ReentryTarget.NOTICING,
            DriftKind.CAPACITY_COLLAPSE: ReentryTarget.RELATIONAL_FRAMING,
            DriftKind.NARRATIVE_DOMINANCE: ReentryTarget.DIFFRACTIVE_MAPPING,
            DriftKind.MORALIZATION: ReentryTarget.ARTICULATION,
            DriftKind.PROCEDURAL_BYPASS: ReentryTarget.FIELD_ENTRY,
        }
        self.assertEqual(DRIFT_REENTRY_TARGETS, expected)

        for kind, target in expected.items():
            state = self.make_field()
            update_field(state)
            signal = DriftSignal(
                kind=kind,
                intensity=0.63,
                evidence=["canonical mapping test"],
                detected_at=state.timestep,
                source="architecture_test",
            )

            trace = reintegrate_field(state, [signal])[0]

            self.assertEqual(trace.reentry_target, target)
            self.assertEqual(trace.signal_intensity, 0.63)
            self.assertEqual(
                trace.signal_evidence,
                ["canonical mapping test"],
            )
            self.assertEqual(trace.signal_source, "architecture_test")
            self.assertEqual(trace.signal_detected_at, state.timestep)
            self.assertIn(target.value, trace.target_enactment)
            self.assertIn(target, state.pending_reentry_targets)

    def test_history_records_complete_immutable_lifecycle_phases(self):
        state = self.make_field()
        state.pending_drifts.append(
            DriftSignal(
                kind=DriftKind.MORALIZATION,
                intensity=0.75,
                evidence=["corrective closure appeared"],
                detected_at=state.timestep,
                source="test",
            )
        )

        run_cycle(state)
        entry = state.history[-1]

        self.assertEqual(
            [item.phase for item in entry.phases],
            [
                CyclePhase.BEFORE_UPDATE,
                CyclePhase.AFTER_UPDATE_AND_EMERGENCE,
                CyclePhase.AFTER_DRIFT_DETECTION,
                CyclePhase.AFTER_ARTICULATION_EVALUATION,
                CyclePhase.AFTER_REINTEGRATION_OR_ARTICULATION,
            ],
        )
        after_detection = entry.after_drift_detection
        self.assertEqual(
            after_detection.apparatus.apparatus_id,
            "apparatus:test",
        )
        self.assertTrue(after_detection.streams)
        self.assertTrue(after_detection.relations)
        self.assertTrue(after_detection.patterns)
        self.assertTrue(after_detection.phenomena)
        self.assertTrue(after_detection.active_drifts)
        self.assertFalse(
            entry.after_update_and_emergence.active_drifts
        )
        self.assertFalse(entry.after.active_drifts)
        self.assertEqual(
            entry.after.pending_reentry_targets,
            (ReentryTarget.ARTICULATION,),
        )
        self.assertFalse(hasattr(after_detection, "history"))
        user_snapshot = next(
            item
            for item in after_detection.streams
            if item.stream_id == "user:1"
        )
        self.assertIn("text", user_snapshot.payload)
        self.assertEqual(user_snapshot.provenance, {})

        preserved = deepcopy(after_detection)
        state.apparatus.framing = "later mutation"
        state.stream("user:1").payload["text"] = "later mutation"
        state.field_values.openness = 0.0
        self.assertEqual(after_detection, preserved)

    def test_reintegration_invalidates_current_formations_not_records(self):
        state = self.make_field()
        hypotheses = RuntimeHypotheses(
            articulation_emergence_floor=0.10,
            articulation_coherence_floor=0.08,
        )
        update_field(state, hypotheses)
        old_pattern_ids = set(state.current_pattern_ids)
        old_phenomenon_ids = set(state.current_phenomenon_ids)
        old_cut = form_provisional_cut(state, hypotheses)
        old_articulation = articulate(state, old_cut)
        reinsert_articulation(state, old_articulation, hypotheses)
        state.pending_drifts.append(
            DriftSignal(
                kind=DriftKind.MORALIZATION,
                intensity=0.80,
                evidence=["evaluative hierarchy"],
                detected_at=state.timestep,
                source="test",
            )
        )

        result = run_cycle(state, hypotheses)
        entry = state.history[-1]
        reintegration = result.reintegrations[0]

        self.assertTrue(entry.after_drift_detection.current_phenomenon_ids)
        self.assertFalse(state.current_pattern_ids)
        self.assertFalse(state.current_phenomenon_ids)
        self.assertIsNone(state.current_cut_id)
        self.assertIsNone(state.current_articulation_id)
        self.assertFalse(state.articulation_eligible)
        self.assertTrue(
            old_pattern_ids.issubset(
                {item.pattern_id for item in state.patterns}
            )
        )
        self.assertTrue(
            old_phenomenon_ids.issubset(
                {item.phenomenon_id for item in state.phenomena}
            )
        )
        self.assertIn(old_cut.cut_id, {item.cut_id for item in state.cuts})
        self.assertIn(
            old_articulation.articulation_id,
            {item.articulation_id for item in state.articulations},
        )
        self.assertEqual(
            set(reintegration.invalidated_phenomenon_ids),
            set(entry.after_drift_detection.current_phenomenon_ids),
        )
        self.assertIsNone(entry.after.cut_id)
        self.assertTrue(entry.after.cuts)
        self.assertIsNone(entry.cut_id)

    def test_direct_reintegration_invalidates_current_cut_and_articulation(self):
        state = self.make_field()
        hypotheses = RuntimeHypotheses(
            articulation_emergence_floor=0.10,
            articulation_coherence_floor=0.08,
        )
        update_field(state, hypotheses)
        cut = form_provisional_cut(state, hypotheses)
        result = articulate(state, cut)
        signal = DriftSignal(
            kind=DriftKind.MORALIZATION,
            intensity=0.70,
            evidence=["corrective language"],
            detected_at=state.timestep,
            source="test",
        )

        trace = reintegrate_field(state, [signal], hypotheses)[0]

        self.assertEqual(trace.invalidated_cut_id, cut.cut_id)
        self.assertEqual(
            trace.invalidated_articulation_id,
            result.articulation_id,
        )
        self.assertIsNone(state.current_cut())
        self.assertIsNone(state.current_articulation())
        self.assertIn(cut, state.cuts)
        self.assertIn(result, state.articulations)

    def test_next_cycle_forms_anew_and_applies_reentry_directive(self):
        state = self.make_field()
        state.pending_drifts.append(
            DriftSignal(
                kind=DriftKind.COMPRESSION,
                intensity=0.70,
                evidence=["premature coherence"],
                detected_at=state.timestep,
                source="test",
            )
        )

        first = run_cycle(state)
        invalidated_ids = set(first.reintegrations[0].invalidated_phenomenon_ids)
        self.assertEqual(
            state.pending_reentry_targets,
            [ReentryTarget.NOTICING],
        )

        second = run_cycle(state)

        self.assertEqual(
            second.trace.reentry_targets_applied,
            [ReentryTarget.NOTICING],
        )
        self.assertFalse(state.pending_reentry_targets)
        self.assertTrue(state.current_phenomenon_ids)
        self.assertTrue(
            invalidated_ids.isdisjoint(state.current_phenomenon_ids)
        )
        self.assertTrue(
            all(
                state.phenomenon(item_id).timestep == state.timestep
                for item_id in state.current_phenomenon_ids
            )
        )

    def test_history_is_append_only_and_does_not_alias_later_state(self):
        state = self.make_field()
        run_cycle(state)
        first_entry = deepcopy(state.history[0])

        run_cycle(state)

        self.assertIsInstance(state.history, tuple)
        self.assertEqual(state.history[0], first_entry)
        self.assertEqual([item.cycle for item in state.history], [1, 2])

    def test_situated_expression_preserves_distinct_forms_without_runtime_language(self):
        state, hypotheses = self.make_two_constellation_field()

        result = run_cycle(state, hypotheses)

        self.assertIsNotNone(result.articulation)
        self.assertIsNotNone(result.articulation_candidate)
        self.assertIsNotNone(result.articulation_evaluation)
        self.assertTrue(result.articulation_evaluation.accepted)
        entry = state.history[-1]
        self.assertEqual(
            entry.after_articulation_evaluation.current_candidate_id,
            result.articulation_candidate.candidate_id,
        )
        self.assertEqual(
            entry.after_articulation_evaluation.current_evaluation_id,
            result.articulation_evaluation.evaluation_id,
        )
        self.assertIsNone(
            entry.after_articulation_evaluation.current_articulation_id
        )
        self.assertEqual(
            entry.after.current_articulation_id,
            result.articulation.articulation_id,
        )
        basis = result.articulation_candidate.basis
        self.assertEqual(len(basis.formations), 2)
        self.assertEqual(
            {
                item.phenomenon_id for item in basis.formations
            },
            set(result.cut.phenomenon_ids),
        )

        text = result.articulation.text
        self.assertEqual(text.count("One formation"), 1)
        self.assertEqual(text.count("Another formation"), 1)
        self.assertIn("cedar roots shelter soil", text)
        self.assertIn("river currents shape stone", text)
        self.assertIn("lantern ember waits", text)
        self.assertIn("remains held open", text)
        for internal in (
            "stream:",
            "phenomenon:",
            "cut:",
            "text chat apparatus",
            "relational strength",
            "cut permeability",
            "user_input",
        ):
            self.assertNotIn(internal, text.lower())
        self.assertNotRegex(
            text.lower(),
            r"(?:stream|phenomenon|relation|cut|articulation):[a-z0-9]",
        )

    def test_prior_articulation_returns_through_lineage_without_text_growth(self):
        state, hypotheses = self.make_two_constellation_field()
        texts = []

        for _ in range(6):
            result = run_cycle(state, hypotheses)
            self.assertIsNotNone(result.articulation)
            texts.append(result.articulation.text)

        articulation_streams = [
            item for item in state.streams if item.kind == "articulation"
        ]
        self.assertEqual(
            len(articulation_streams),
            len(state.articulations),
        )
        self.assertEqual(
            len({item.stream_id for item in articulation_streams}),
            len(articulation_streams),
        )
        self.assertTrue(
            all("text" not in item.payload for item in articulation_streams)
        )
        self.assertTrue(
            all(item.payload["included_stream_ids"] for item in articulation_streams)
        )
        self.assertTrue(
            all(item.payload["source_stream_ids"] for item in articulation_streams)
        )
        self.assertTrue(
            all(
                state.stream(source_id).kind
                not in {"apparatus", "articulation", "play_variation"}
                for item in articulation_streams
                for source_id in item.payload["source_stream_ids"]
            )
        )
        self.assertLess(len(state.relations), 40)
        self.assertLess(max(map(len, texts)) - min(map(len, texts)), 900)
        self.assertTrue(
            all(
                text.count(
                    "What has already been articulated is present through "
                    "its effects"
                )
                <= 2
                for text in texts
            )
        )

    def test_post_articulation_moralization_reenters_at_articulation(self):
        state, hypotheses = self.make_two_constellation_field()
        text = (
            "One formation says you should accept the right answer. "
            "\n\nAnother formation remains perceptible. "
            "Other material remains held open. This settles the matter."
        )

        result = self.run_cycle_with_candidate_text(
            state,
            hypotheses,
            text,
        )

        self.assertIsNone(result.articulation)
        self.assertIsNone(result.reinserted_stream_id)
        self.assertFalse(result.articulation_evaluation.accepted)
        self.assertEqual(
            {
                item.kind
                for item in result.articulation_evaluation.drift_signals
            },
            {DriftKind.MORALIZATION},
        )
        self.assertEqual(
            {item.reentry_target for item in result.reintegrations},
            {ReentryTarget.ARTICULATION},
        )
        self.assertEqual(
            result.reintegrations[0].invalidated_candidate_id,
            result.articulation_candidate.candidate_id,
        )
        self.assertEqual(
            result.reintegrations[0].invalidated_evaluation_id,
            result.articulation_evaluation.evaluation_id,
        )
        entry = state.history[-1]
        self.assertEqual(
            entry.after_articulation_evaluation.current_candidate_id,
            result.articulation_candidate.candidate_id,
        )
        self.assertTrue(
            entry.after_articulation_evaluation.active_drifts
        )
        self.assertIsNone(entry.after.current_candidate_id)
        self.assertIsNone(entry.after.current_evaluation_id)
        self.assertIsNone(entry.articulation_id)
        self.assertIn(
            result.articulation_candidate.candidate_id,
            {
                item.candidate_id
                for item in entry.after.articulation_candidates
            },
        )

    def test_post_articulation_procedural_bypass_reenters_at_field_entry(self):
        state, hypotheses = self.make_two_constellation_field()
        text = (
            "One formation reports that the pipeline selected "
            "stream:user:1.\n\nAnother formation remains perceptible. "
            "Other material remains held open."
        )

        result = self.run_cycle_with_candidate_text(
            state,
            hypotheses,
            text,
        )

        self.assertFalse(result.articulation_evaluation.accepted)
        self.assertEqual(
            {
                item.kind
                for item in result.articulation_evaluation.drift_signals
            },
            {DriftKind.PROCEDURAL_BYPASS},
        )
        self.assertEqual(
            {item.reentry_target for item in result.reintegrations},
            {ReentryTarget.FIELD_ENTRY},
        )

    def test_post_articulation_narrative_dominance_reopens_mapping(self):
        state, hypotheses = self.make_two_constellation_field()
        text = (
            "One formation remains visible. Another formation remains "
            "visible. The only explanation is a single story. "
            "Other material remains held open."
        )

        result = self.run_cycle_with_candidate_text(
            state,
            hypotheses,
            text,
        )

        self.assertFalse(result.articulation_evaluation.accepted)
        self.assertEqual(
            {
                item.kind
                for item in result.articulation_evaluation.drift_signals
            },
            {DriftKind.NARRATIVE_DOMINANCE},
        )
        self.assertEqual(
            {item.reentry_target for item in result.reintegrations},
            {ReentryTarget.DIFFRACTIVE_MAPPING},
        )

    def run_cycle_with_candidate_text(self, state, hypotheses, text):
        native_factory = form_articulation_candidate

        def forced_factory(inner_state, cut, inner_hypotheses):
            candidate = native_factory(
                inner_state,
                cut,
                inner_hypotheses,
            )
            forced = replace(
                candidate,
                candidate_id="{0}:forced".format(candidate.candidate_id),
                text=text,
            )
            inner_state.articulation_candidates = [
                item
                for item in inner_state.articulation_candidates
                if item.candidate_id != candidate.candidate_id
            ]
            inner_state.articulation_candidates.append(forced)
            inner_state.current_candidate_id = forced.candidate_id
            return forced

        with patch(
            "cbra.native.runtime.form_articulation_candidate",
            side_effect=forced_factory,
        ):
            return run_cycle(state, hypotheses)

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
