"""Durable provider-neutral renderer apparatus binding contracts."""

import tempfile
import threading
import unittest
from pathlib import Path

from cbra.application import NativeApplicationService
from cbra.native import (
    Apparatus,
    ArticulationRendererBinding,
    ArticulationRendererBindingError,
    ArticulationRendererError,
    RuntimeHypotheses,
    Stream,
    TurnOutcomeKind,
    create_session,
    restore_session,
    serialize_session,
)
from cbra.store import NativeSessionRepository


CUSTOM_TEXT = (
    "One formation keeps cedar roots and sheltering soil in relation.\n\n"
    "Another formation keeps river current, stone, and silt perceptible.\n\n"
    "Other material remains held open while the relation stays revisable."
)
INSTRUCTION_DIGEST = "a" * 64


def renderer_binding(
    renderer_id="renderer:bounded",
    *,
    max_output_chars=32768,
):
    return ArticulationRendererBinding(
        renderer_id=renderer_id,
        contract_version="1",
        provider_id="provider:local",
        model_id="model:bounded",
        instruction_set_id="instruction:relational",
        instruction_digest=INSTRUCTION_DIGEST,
        max_output_chars=max_output_chars,
        constraints=(
            "propose text only",
            "preserve held-open material",
        ),
    )


class CountingRenderer:
    def __init__(self, text=CUSTOM_TEXT):
        self.text = text
        self.calls = 0
        self._guard = threading.Lock()

    def render(self, basis):
        with self._guard:
            self.calls += 1
        return self.text


class RendererApparatusBindingTests(unittest.TestCase):
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
        return (
            Stream(
                stream_id="memory:cedar-binding",
                kind="memory",
                participation=0.72,
                persistence=0.80,
                payload={"text": "cedar roots shelter soil"},
            ),
            Stream(
                stream_id="document:cedar-binding",
                kind="document",
                participation=0.74,
                persistence=0.80,
                payload={"text": "cedar soil holds moisture"},
            ),
            Stream(
                stream_id="environment:river-binding",
                kind="environment",
                participation=0.70,
                persistence=0.80,
                payload={"text": "river currents shape stone"},
            ),
            Stream(
                stream_id="document:river-binding",
                kind="document",
                participation=0.75,
                persistence=0.80,
                payload={"text": "river stone carries silt"},
            ),
        )

    def service(self, renderer=None, binding=None):
        return NativeApplicationService(
            NativeSessionRepository(self.root),
            max_cycles=2,
            hypotheses=self.hypotheses,
            renderer=renderer,
            renderer_binding=binding,
        )

    def create_bound_thread(
        self,
        thread_id="thread:renderer-apparatus",
        turn_id="turn:first",
    ):
        renderer = CountingRenderer()
        binding = renderer_binding()
        result = self.service(renderer, binding).create_thread(
            thread_id,
            "How do cedar roots and river stone remain distinct?",
            turn_id=turn_id,
            additional_streams=self.relational_material(),
        )
        return renderer, binding, result

    def test_custom_renderer_requires_an_explicit_binding(self):
        renderer = CountingRenderer()
        with self.assertRaises(ArticulationRendererBindingError):
            self.service(renderer)
        self.assertEqual(renderer.calls, 0)
        self.assertFalse(list(self.root.iterdir()))

    def test_binding_materializes_through_existing_apparatus_facets(self):
        renderer, binding, result = self.create_bound_thread()
        self.assertEqual(
            result.outcome.kind,
            TurnOutcomeKind.ACCEPTED_ARTICULATION,
        )
        self.assertEqual(renderer.calls, 1)
        session = self.service().load_session(
            "thread:renderer-apparatus"
        )
        expected = binding.apparatus_material()
        for facet, descriptors in expected.items():
            self.assertTrue(
                set(descriptors).issubset(
                    set(getattr(session.field.apparatus, facet))
                )
            )

        apparatus_streams = {
            item.payload["facet"]: tuple(item.payload["values"])
            for item in session.field.streams
            if item.kind == "apparatus"
            and item.payload.get("facet") in expected
        }
        for facet, descriptors in expected.items():
            self.assertTrue(
                set(descriptors).issubset(
                    set(apparatus_streams[facet])
                )
            )

    def test_binding_survives_lossless_session_restoration(self):
        _, binding, _ = self.create_bound_thread(
            thread_id="thread:binding-restore"
        )
        original = self.service().load_session(
            "thread:binding-restore"
        )
        restored = restore_session(serialize_session(original))

        self.assertEqual(restored, original)
        for facet, descriptors in binding.apparatus_material().items():
            self.assertTrue(
                set(descriptors).issubset(
                    set(getattr(restored.field.apparatus, facet))
                )
            )

    def test_same_binding_continues_after_restart(self):
        _, binding, created = self.create_bound_thread(
            thread_id="thread:same-binding"
        )
        renderer = CountingRenderer()
        continued = self.service(renderer, binding).submit_thread_turn(
            "thread:same-binding",
            "A second strand keeps the relation open.",
            turn_id="turn:second",
            expected_revision=created.outcome.revision,
            additional_streams=(
                Stream(
                    stream_id="document:second-binding",
                    kind="document",
                    participation=0.76,
                    persistence=0.80,
                    payload={"text": "roots redirect moving water"},
                ),
            ),
        )

        self.assertFalse(continued.replayed)
        self.assertEqual(continued.outcome.revision, 2)
        self.assertEqual(renderer.calls, 1)

    def test_different_binding_fails_before_execution_or_replacement(self):
        _, _, created = self.create_bound_thread(
            thread_id="thread:different-binding"
        )
        repository = NativeSessionRepository(self.root)
        path = repository.path_for("thread:different-binding")
        before = path.read_bytes()
        before_session = repository.load("thread:different-binding")
        renderer = CountingRenderer()

        with self.assertRaises(ArticulationRendererBindingError):
            self.service(
                renderer,
                renderer_binding("renderer:different"),
            ).submit_thread_turn(
                "thread:different-binding",
                "A new turn attempts to change rendering apparatus.",
                turn_id="turn:second",
                expected_revision=created.outcome.revision,
            )

        self.assertEqual(renderer.calls, 0)
        self.assertEqual(path.read_bytes(), before)
        after = repository.load("thread:different-binding")
        self.assertEqual(after.revision, before_session.revision)
        self.assertEqual(
            len(after.field.history),
            len(before_session.field.history),
        )

    def test_exact_replays_precede_live_binding_validation(self):
        _, binding, created = self.create_bound_thread(
            thread_id="thread:binding-replays"
        )
        renderer = CountingRenderer()
        continued = self.service(renderer, binding).submit_thread_turn(
            "thread:binding-replays",
            "A second strand enters.",
            turn_id="turn:second",
            expected_revision=created.outcome.revision,
            additional_streams=(
                Stream(
                    stream_id="document:replay-binding",
                    kind="document",
                    participation=0.76,
                    persistence=0.80,
                    payload={"text": "moving water reshapes soil"},
                ),
            ),
        )
        self.assertEqual(renderer.calls, 1)

        no_provider = self.service()
        creation_replay = no_provider.create_thread(
            "thread:binding-replays",
            "How do cedar roots and river stone remain distinct?",
            turn_id="turn:first",
            additional_streams=self.relational_material(),
        )
        continuation_replay = no_provider.submit_thread_turn(
            "thread:binding-replays",
            "A second strand enters.",
            turn_id="turn:second",
            expected_revision=continued.outcome.revision,
            additional_streams=(
                Stream(
                    stream_id="document:replay-binding",
                    kind="document",
                    participation=0.76,
                    persistence=0.80,
                    payload={"text": "moving water reshapes soil"},
                ),
            ),
        )

        self.assertTrue(creation_replay.replayed)
        self.assertTrue(continuation_replay.replayed)
        self.assertEqual(
            continuation_replay.outcome.revision,
            continued.outcome.revision,
        )

    def test_sparse_turn_cannot_silently_change_binding(self):
        binding = renderer_binding()
        renderer = CountingRenderer()
        bound_service = NativeApplicationService(
            NativeSessionRepository(self.root),
            max_cycles=3,
            renderer=renderer,
            renderer_binding=binding,
        )
        created = bound_service.create_thread(
            "thread:sparse-binding",
            "A solitary quartz glyph.",
            turn_id="turn:first",
        )
        self.assertEqual(renderer.calls, 0)
        repository = NativeSessionRepository(self.root)
        path = repository.path_for("thread:sparse-binding")
        before = path.read_bytes()

        with self.assertRaises(ArticulationRendererBindingError):
            self.service().submit_thread_turn(
                "thread:sparse-binding",
                "A second sparse strand enters.",
                turn_id="turn:second",
                expected_revision=created.outcome.revision,
            )

        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(
            repository.load("thread:sparse-binding").revision,
            1,
        )

    def test_service_isolates_binding_from_later_mutation(self):
        binding = renderer_binding()
        expected = binding.apparatus_material()
        renderer = CountingRenderer()
        service = self.service(renderer, binding)
        object.__setattr__(binding, "model_id", "model:mutated")
        object.__setattr__(binding, "constraints", ("mutated",))

        service.create_thread(
            "thread:binding-mutation",
            "How do cedar roots and river stone remain distinct?",
            turn_id="turn:first",
            additional_streams=self.relational_material(),
        )
        apparatus = service.load_session(
            "thread:binding-mutation"
        ).field.apparatus
        for facet, descriptors in expected.items():
            self.assertTrue(
                set(descriptors).issubset(set(getattr(apparatus, facet)))
            )
        self.assertNotIn(
            "cbra.renderer.model=model:mutated",
            apparatus.models,
        )
        self.assertNotIn(
            "cbra.renderer.constraint=mutated",
            apparatus.constraints,
        )

    def test_binding_rejects_secret_bearing_material(self):
        invalid = (
            {"provider_id": "api-key"},
            {"model_id": "sk-proj-1234567890"},
            {"instruction_set_id": "authorization"},
            {"constraints": ("AKIA1234567890ABCDEF",)},
            {"constraints": ("Bearer private-token-value",)},
            {"constraints": ("token=private-token-value",)},
            {
                "constraints": (
                    "endpoint https://person:password@example.test/v1",
                )
            },
        )
        for overrides in invalid:
            values = {
                "renderer_id": "renderer:safe",
                "contract_version": "1",
                "instruction_set_id": "instruction:safe",
            }
            values.update(overrides)
            with self.subTest(overrides=overrides):
                with self.assertRaises(
                    ArticulationRendererBindingError
                ):
                    ArticulationRendererBinding(**values)

    def test_partial_or_forged_apparatus_binding_is_rejected(self):
        binding = renderer_binding()
        expected = binding.apparatus_material()
        partial = Apparatus(
            tools=[expected["tools"][0]],
        )
        with self.assertRaises(ArticulationRendererBindingError):
            create_session(
                thread_id="thread:partial-binding",
                apparatus=partial,
                renderer_binding=binding,
            )

        forged = Apparatus(
            models=list(expected["models"]),
            prompts=list(expected["prompts"]),
            tools=list(expected["tools"]),
            constraints=list(expected["constraints"])
            + ["cbra.renderer.constraint=forged"],
        )
        with self.assertRaises(ArticulationRendererBindingError):
            create_session(
                thread_id="thread:forged-binding",
                apparatus=forged,
                renderer_binding=binding,
            )

    def test_binding_output_limit_is_enforced_before_persistence(self):
        renderer = CountingRenderer("text longer than twelve characters")
        with self.assertRaises(ArticulationRendererError):
            self.service(
                renderer,
                renderer_binding(max_output_chars=12),
            ).create_thread(
                "thread:binding-limit",
                "How do cedar roots and river stone remain distinct?",
                turn_id="turn:first",
                additional_streams=self.relational_material(),
            )

        self.assertEqual(renderer.calls, 1)
        self.assertFalse(
            NativeSessionRepository(self.root).exists(
                "thread:binding-limit"
            )
        )

    def test_default_apparatus_remains_legacy_empty(self):
        service = self.service()
        service.create_thread(
            "thread:legacy-default-binding",
            "One strand enters.",
            turn_id="turn:first",
        )
        apparatus = service.load_session(
            "thread:legacy-default-binding"
        ).field.apparatus

        self.assertEqual(apparatus, Apparatus())
        for facet in ("models", "prompts", "tools", "constraints"):
            self.assertFalse(
                any(
                    value.startswith("cbra.renderer.")
                    for value in getattr(apparatus, facet)
                )
            )


if __name__ == "__main__":
    unittest.main()
