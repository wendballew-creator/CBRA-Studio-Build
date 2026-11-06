"""Provider-neutral native articulation renderer contracts."""

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path

from cbra.application import NativeApplicationService
from cbra.native import (
    MAX_RENDERED_ARTICULATION_CHARS,
    Apparatus,
    ArticulationRendererBinding,
    ArticulationRendererError,
    DriftKind,
    NativeTemplateArticulationRenderer,
    RuntimeHypotheses,
    StaleRevisionError,
    Stream,
    TurnConflictError,
    TurnOutcomeKind,
    build_articulation_basis,
    form_articulation_candidate,
    form_provisional_cut,
    initialize_field,
    materialize_renderer_binding,
    update_field,
)
from cbra.store import NativeSessionRepository


FIRST_STRAND = "Cedar roots shelter soil and hold moisture."
RELATED_STRAND = "Cedar soil holds water around the roots."
CUSTOM_TEXT = (
    "One formation keeps cedar roots and sheltering soil in relation.\n\n"
    "Another formation keeps river current, stone, and silt perceptible.\n\n"
    "Other material remains held open while the relation stays revisable."
)
DRIFTING_TEXT = (
    "One formation says you should accept the right answer. "
    "Another formation remains perceptible. "
    "Other material remains held open. This settles the matter."
)
BASELINE_NATIVE_TEXT = (
    "One formation brings these strands into relation: river stone carries "
    "silt; and river currents shape stone. Shared pattern and difference "
    "remain active together, so neither has to absorb the other.\n\n"
    "Another formation brings these strands into relation: cedar soil holds "
    "moisture; and cedar roots shelter soil. Shared pattern and difference "
    "remain active together, so neither has to absorb the other.\n\n"
    "Alongside these formations, this material remains held open: lantern "
    "ember waits. It stays available without being forced into resolution."
    "\n\nThis orientation is temporary: it can change as these relations and "
    "the conditions around them change."
)
CUSTOM_BINDING = ArticulationRendererBinding(
    renderer_id="renderer:static",
    contract_version="1",
    provider_id="provider:test",
    model_id="model:test",
    instruction_set_id="instruction:test",
    max_output_chars=MAX_RENDERED_ARTICULATION_CHARS,
    constraints=("text only",),
)


class StaticRenderer:
    def __init__(self, text):
        self.text = text
        self.calls = 0
        self.bases = []
        self._guard = threading.Lock()

    def render(self, basis):
        with self._guard:
            self.calls += 1
            self.bases.append(basis)
        return self.text


class FailingRenderer:
    def __init__(self):
        self.calls = 0

    def render(self, basis):
        self.calls += 1
        raise RuntimeError("renderer failed")


class NativeArticulationRendererTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.hypotheses = RuntimeHypotheses(
            articulation_emergence_floor=0.05,
            articulation_coherence_floor=0.05,
        )

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def relational_material():
        return [
            Stream(
                stream_id="memory:cedar",
                kind="memory",
                participation=0.72,
                persistence=0.80,
                payload={"text": "cedar roots shelter soil"},
                provenance={"source": "field note"},
            ),
            Stream(
                stream_id="document:cedar",
                kind="document",
                participation=0.74,
                persistence=0.80,
                payload={"text": "cedar soil holds moisture"},
                provenance={"source": "document"},
            ),
            Stream(
                stream_id="environment:river",
                kind="environment",
                participation=0.70,
                persistence=0.80,
                payload={"text": "river currents shape stone"},
            ),
            Stream(
                stream_id="document:river",
                kind="document",
                participation=0.75,
                persistence=0.80,
                payload={"text": "river stone carries silt"},
            ),
        ]

    def renderable_field(self, renderer_binding=None):
        apparatus = materialize_renderer_binding(
            Apparatus(
                apparatus_id="apparatus:renderer",
                framing="shared inquiry",
                medium="text_chat",
            ),
            renderer_binding,
        )
        state = initialize_field(
            self.relational_material()
            + [
                Stream(
                    stream_id="quiet:lantern",
                    kind="other",
                    participation=0.61,
                    persistence=0.80,
                    payload={"text": "lantern ember waits"},
                )
            ],
            apparatus=apparatus,
            field_id="field:renderer",
            hypotheses=self.hypotheses,
        )
        update_field(state, self.hypotheses)
        cut = form_provisional_cut(state, self.hypotheses)
        self.assertIsNotNone(cut)
        return state, cut

    def service(
        self,
        renderer=None,
        max_cycles=2,
        renderer_binding=None,
    ):
        return NativeApplicationService(
            NativeSessionRepository(self.root),
            max_cycles=max_cycles,
            hypotheses=self.hypotheses,
            renderer=renderer,
            renderer_binding=renderer_binding,
        )

    def test_default_renderer_preserves_candidate_text_and_identity(self):
        source, _ = self.renderable_field()
        implicit_state = deepcopy(source)
        explicit_state = deepcopy(source)

        implicit = form_articulation_candidate(
            implicit_state,
            implicit_state.current_cut(),
            self.hypotheses,
        )
        explicit = form_articulation_candidate(
            explicit_state,
            explicit_state.current_cut(),
            self.hypotheses,
            NativeTemplateArticulationRenderer(self.hypotheses),
        )

        self.assertEqual(explicit, implicit)
        self.assertEqual(implicit.text, BASELINE_NATIVE_TEXT)
        self.assertEqual(
            implicit.candidate_id,
            "candidate:eadd40138a0c25",
        )
        self.assertEqual(
            explicit_state.articulation_candidates,
            implicit_state.articulation_candidates,
        )

    def test_renderer_receives_an_isolated_basis(self):
        state, cut = self.renderable_field(CUSTOM_BINDING)
        authoritative = build_articulation_basis(state, cut)

        class MutatingRenderer:
            def __init__(self):
                self.retained_basis = None

            def render(self, basis):
                self.retained_basis = basis
                basis.cut_id = "cut:renderer-owned"
                basis.included_stream_ids.append("stream:invented")
                basis.formations[0].materials[0].text = "mutated"
                basis.formations[0].materials[0].provenance["new"] = True
                return CUSTOM_TEXT

        renderer = MutatingRenderer()
        candidate = form_articulation_candidate(
            state,
            cut,
            self.hypotheses,
            renderer,
            CUSTOM_BINDING,
        )
        renderer.retained_basis.relation_ids.append(
            "relation:later-mutation"
        )

        self.assertEqual(candidate.basis, authoritative)
        self.assertEqual(candidate.text, CUSTOM_TEXT)
        self.assertNotIn(
            "stream:invented",
            candidate.basis.included_stream_ids,
        )
        self.assertNotEqual(candidate.basis.cut_id, "cut:renderer-owned")

    def test_renderer_results_are_validated_before_candidate_mutation(self):
        invalid_results = (
            None,
            17,
            "",
            " \n ",
            "x" * (MAX_RENDERED_ARTICULATION_CHARS + 1),
            "unsafe\x00text",
            "unsafe\x7ftext",
            "unsafe\ud800text",
        )
        for value in invalid_results:
            with self.subTest(value_type=type(value).__name__):
                state, cut = self.renderable_field(CUSTOM_BINDING)
                with self.assertRaises(ArticulationRendererError):
                    form_articulation_candidate(
                        state,
                        cut,
                        self.hypotheses,
                        StaticRenderer(value),
                        CUSTOM_BINDING,
                    )
                self.assertFalse(state.articulation_candidates)
                self.assertIsNone(state.current_candidate_id)

    def test_custom_text_persists_projects_and_replays_without_rendering(self):
        renderer = StaticRenderer(CUSTOM_TEXT)
        service = self.service(
            renderer,
            renderer_binding=CUSTOM_BINDING,
        )
        result = service.create_thread(
            "thread:custom-renderer",
            "How do cedar soil and river stone remain distinct?",
            turn_id="turn:first",
            additional_streams=self.relational_material(),
        )

        self.assertEqual(
            result.outcome.kind,
            TurnOutcomeKind.ACCEPTED_ARTICULATION,
        )
        self.assertEqual(result.outcome.text, CUSTOM_TEXT)
        self.assertEqual(renderer.calls, 1)
        projection = service.project_thread_turns(
            "thread:custom-renderer"
        )
        self.assertEqual(projection.turns[0].text, CUSTOM_TEXT)

        restarted = self.service()
        replay = restarted.create_thread(
            "thread:custom-renderer",
            "How do cedar soil and river stone remain distinct?",
            turn_id="turn:first",
            additional_streams=self.relational_material(),
        )
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.outcome.text, CUSTOM_TEXT)

    def test_preflight_and_sparse_turns_do_not_render(self):
        sparse_renderer = StaticRenderer(CUSTOM_TEXT)
        sparse = NativeApplicationService(
            NativeSessionRepository(self.root),
            max_cycles=3,
            renderer=sparse_renderer,
            renderer_binding=CUSTOM_BINDING,
        )
        sparse.create_thread(
            "thread:sparse-renderer",
            "One strand enters without relational evidence.",
            turn_id="turn:sparse",
        )
        self.assertEqual(sparse_renderer.calls, 0)

        renderer = StaticRenderer(CUSTOM_TEXT)
        service = self.service(
            renderer,
            renderer_binding=CUSTOM_BINDING,
        )
        created = service.create_thread(
            "thread:renderer-preflight",
            "How do cedar soil and river stone remain distinct?",
            turn_id="turn:first",
            additional_streams=self.relational_material(),
        )
        self.assertEqual(renderer.calls, 1)

        replay = service.create_thread(
            "thread:renderer-preflight",
            "How do cedar soil and river stone remain distinct?",
            turn_id="turn:first",
            additional_streams=self.relational_material(),
        )
        self.assertTrue(replay.replayed)
        with self.assertRaises(TurnConflictError):
            service.submit_thread_turn(
                "thread:renderer-preflight",
                "Changed material.",
                turn_id="turn:first",
                expected_revision=created.outcome.revision,
            )
        with self.assertRaises(StaleRevisionError):
            service.submit_thread_turn(
                "thread:renderer-preflight",
                RELATED_STRAND,
                turn_id="turn:second",
                expected_revision=0,
            )
        self.assertEqual(renderer.calls, 1)

    def test_concurrent_identical_creation_renders_once(self):
        renderer = StaticRenderer(CUSTOM_TEXT)

        def create():
            return self.service(
                renderer,
                renderer_binding=CUSTOM_BINDING,
            ).create_thread(
                "thread:concurrent-renderer",
                "How do cedar soil and river stone remain distinct?",
                turn_id="turn:first",
                additional_streams=self.relational_material(),
            )

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda _: create(), range(16)))

        self.assertEqual(renderer.calls, 1)
        self.assertEqual(
            sum(not item.replayed for item in results),
            1,
        )
        self.assertEqual(
            {item.outcome.text for item in results},
            {CUSTOM_TEXT},
        )

    def test_concurrent_identical_continuation_renders_once(self):
        setup_renderer = StaticRenderer(CUSTOM_TEXT)
        self.service(
            setup_renderer,
            renderer_binding=CUSTOM_BINDING,
        ).create_thread(
            "thread:concurrent-renderer-continuation",
            FIRST_STRAND,
            turn_id="turn:first",
        )
        renderer = StaticRenderer(CUSTOM_TEXT)

        def submit():
            return self.service(
                renderer,
                renderer_binding=CUSTOM_BINDING,
            ).submit_thread_turn(
                "thread:concurrent-renderer-continuation",
                RELATED_STRAND,
                turn_id="turn:second",
                expected_revision=1,
            )

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda _: submit(), range(16)))

        self.assertEqual(renderer.calls, 1)
        self.assertEqual(
            sum(not item.replayed for item in results),
            1,
        )
        self.assertEqual(
            {item.outcome.text for item in results},
            {CUSTOM_TEXT},
        )

    def test_renderer_failure_and_invalid_text_roll_back_cleanly(self):
        failing = FailingRenderer()
        service = self.service(
            failing,
            renderer_binding=CUSTOM_BINDING,
        )
        with self.assertRaises(RuntimeError):
            service.create_thread(
                "thread:renderer-failure",
                "How do cedar soil and river stone remain distinct?",
                turn_id="turn:first",
                additional_streams=self.relational_material(),
            )

        repository = NativeSessionRepository(self.root)
        self.assertFalse(repository.exists("thread:renderer-failure"))
        self.assertFalse(list(self.root.glob(".*.tmp")))
        retry = self.service(
            StaticRenderer(CUSTOM_TEXT),
            renderer_binding=CUSTOM_BINDING,
        ).create_thread(
            "thread:renderer-failure",
            "How do cedar soil and river stone remain distinct?",
            turn_id="turn:first",
            additional_streams=self.relational_material(),
        )
        self.assertEqual(retry.outcome.text, CUSTOM_TEXT)

        invalid = StaticRenderer("")
        with self.assertRaises(ArticulationRendererError):
            self.service(
                invalid,
                renderer_binding=CUSTOM_BINDING,
            ).create_thread(
                "thread:invalid-render",
                "How do cedar soil and river stone remain distinct?",
                turn_id="turn:first",
                additional_streams=self.relational_material(),
            )
        self.assertFalse(repository.exists("thread:invalid-render"))

    def test_continuation_failure_preserves_prior_revision_for_retry(self):
        setup_renderer = StaticRenderer(CUSTOM_TEXT)
        self.service(
            setup_renderer,
            renderer_binding=CUSTOM_BINDING,
        ).create_thread(
            "thread:renderer-continuation-failure",
            FIRST_STRAND,
            turn_id="turn:first",
        )
        repository = NativeSessionRepository(self.root)
        path = repository.path_for(
            "thread:renderer-continuation-failure"
        )
        before = path.read_bytes()
        failing = FailingRenderer()

        with self.assertRaises(RuntimeError):
            self.service(
                failing,
                renderer_binding=CUSTOM_BINDING,
            ).submit_thread_turn(
                "thread:renderer-continuation-failure",
                RELATED_STRAND,
                turn_id="turn:second",
                expected_revision=1,
            )

        self.assertEqual(failing.calls, 1)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(
            repository.load(
                "thread:renderer-continuation-failure"
            ).revision,
            1,
        )
        retry = self.service(
            StaticRenderer(CUSTOM_TEXT),
            renderer_binding=CUSTOM_BINDING,
        ).submit_thread_turn(
            "thread:renderer-continuation-failure",
            RELATED_STRAND,
            turn_id="turn:second",
            expected_revision=1,
        )
        self.assertFalse(retry.replayed)
        self.assertEqual(retry.outcome.revision, 2)
        self.assertEqual(retry.outcome.text, CUSTOM_TEXT)

    def test_drifting_text_uses_native_evaluation_and_reintegration(self):
        renderer = StaticRenderer(DRIFTING_TEXT)
        service = self.service(
            renderer,
            renderer_binding=CUSTOM_BINDING,
        )
        result = service.create_thread(
            "thread:renderer-drift",
            "How do cedar soil and river stone remain distinct?",
            turn_id="turn:first",
            additional_streams=self.relational_material(),
        )

        self.assertEqual(renderer.calls, 1)
        self.assertEqual(
            result.outcome.kind,
            TurnOutcomeKind.REINTEGRATION_PENDING,
        )
        self.assertIsNone(result.outcome.text)
        session = service.load_session("thread:renderer-drift")
        self.assertFalse(session.turns[0].articulation_ids)
        self.assertEqual(len(session.turns[0].evaluation_ids), 1)
        evaluation = session.field.articulation_evaluations[0]
        self.assertFalse(evaluation.accepted)
        self.assertIn(
            DriftKind.MORALIZATION,
            {item.kind for item in evaluation.drift_signals},
        )
        self.assertTrue(session.field.pending_reentry_targets)

    def test_different_threads_can_render_concurrently(self):
        barrier = threading.Barrier(2)

        class BarrierRenderer:
            def render(self, basis):
                barrier.wait(timeout=2)
                return CUSTOM_TEXT

        renderer = BarrierRenderer()

        def create(thread_id):
            return self.service(
                renderer,
                renderer_binding=CUSTOM_BINDING,
            ).create_thread(
                thread_id,
                "How do cedar soil and river stone remain distinct?",
                turn_id="turn:first",
                additional_streams=self.relational_material(),
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    create,
                    ("thread:renderer-a", "thread:renderer-b"),
                )
            )

        self.assertEqual(
            {item.outcome.thread_id for item in results},
            {"thread:renderer-a", "thread:renderer-b"},
        )
        self.assertEqual(
            {item.outcome.text for item in results},
            {CUSTOM_TEXT},
        )

    def test_service_rejects_an_object_without_render_method(self):
        with self.assertRaises(TypeError):
            self.service(renderer=object())


if __name__ == "__main__":
    unittest.main()
