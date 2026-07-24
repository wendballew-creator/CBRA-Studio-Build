"""Native session ownership, truthful ingress, and durable continuation."""

import json
import tempfile
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from cbra.native import (
    IntegrityError,
    NativeValidationError,
    RuntimeHypotheses,
    SessionOwnershipError,
    StaleRevisionError,
    Stream,
    TurnConflictError,
    TurnOutcomeKind,
    create_session,
    restore_session,
    serialize_session,
    submit_turn,
)
from cbra.native.articulation import form_articulation_candidate
from cbra.store import NativeSessionRepository


class NativeSessionTests(unittest.TestCase):
    def setUp(self):
        self.hypotheses = RuntimeHypotheses(
            articulation_emergence_floor=0.05,
            articulation_coherence_floor=0.05,
        )

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

    def make_accepted_session(self, thread_id="thread:accepted"):
        session = create_session(thread_id=thread_id)
        return submit_turn(
            session,
            "How do cedar soil and river stone remain distinct?",
            additional_streams=self.relational_material(),
            turn_id="turn:1",
            expected_revision=0,
            max_cycles=2,
            hypotheses=self.hypotheses,
        )

    def test_sparse_turn_records_no_articulation_without_fallback_text(self):
        original = create_session(thread_id="thread:sparse")

        session, outcome = submit_turn(
            original,
            "One strand enters without relational evidence.",
            turn_id="turn:sparse",
            expected_revision=0,
            max_cycles=3,
        )

        self.assertEqual(outcome.kind, TurnOutcomeKind.NO_ARTICULATION)
        self.assertIsNone(outcome.articulation)
        self.assertIsNone(outcome.text)
        self.assertEqual((outcome.cycle_start, outcome.cycle_end), (1, 3))
        self.assertEqual(session.turns[0].outcome, outcome.kind)
        self.assertFalse(session.turns[0].candidate_ids)
        self.assertEqual(original.revision, 0)
        self.assertFalse(original.field.history)

    def test_relational_material_can_form_and_persist_an_articulation(self):
        session, outcome = self.make_accepted_session()

        self.assertEqual(
            outcome.kind,
            TurnOutcomeKind.ACCEPTED_ARTICULATION,
        )
        self.assertIsNotNone(outcome.articulation)
        self.assertTrue(outcome.text)
        self.assertEqual(len(session.turns[0].articulation_ids), 1)
        self.assertEqual(
            outcome.articulation.articulation_id,
            session.turns[0].articulation_ids[0],
        )
        self.assertEqual(session.revision, 1)
        ingress = {
            item.stream_id: item for item in session.field.streams
        }
        for expected in self.relational_material():
            restored_stream = ingress[expected.stream_id]
            self.assertEqual(restored_stream.payload, expected.payload)
            self.assertEqual(
                restored_stream.provenance,
                expected.provenance,
            )

        restored = restore_session(serialize_session(session))
        self.assertEqual(restored, session)
        self.assertEqual(
            restored.turns[0].outcome,
            TurnOutcomeKind.ACCEPTED_ARTICULATION,
        )

    def test_turn_retry_is_idempotent_and_conflicting_reuse_fails(self):
        session, first = self.make_accepted_session("thread:retry")
        before_retry = deepcopy(session)

        retried, second = submit_turn(
            session,
            "How do cedar soil and river stone remain distinct?",
            additional_streams=self.relational_material(),
            turn_id="turn:1",
            expected_revision=0,
            max_cycles=2,
            hypotheses=self.hypotheses,
        )

        self.assertIs(retried, session)
        self.assertEqual(retried, before_retry)
        self.assertEqual(second, first)
        self.assertEqual(
            sum(
                item.stream_id == session.turns[0].user_stream_id
                for item in session.field.streams
            ),
            1,
        )

        changed = self.relational_material()
        changed[0].payload["text"] = "different material"
        with self.assertRaises(TurnConflictError):
            submit_turn(
                session,
                "How do cedar soil and river stone remain distinct?",
                additional_streams=changed,
                turn_id="turn:1",
                expected_revision=1,
                hypotheses=self.hypotheses,
            )

    def test_stale_revision_fails_before_the_field_is_touched(self):
        session = create_session(thread_id="thread:stale")
        original = deepcopy(session)

        with self.assertRaises(StaleRevisionError):
            submit_turn(
                session,
                "This must not enter.",
                turn_id="turn:stale",
                expected_revision=2,
            )

        self.assertEqual(session, original)

    def test_interrupted_and_uninterrupted_two_turn_sessions_match(self):
        first, _ = self.make_accepted_session("thread:continuation")
        uninterrupted_source = restore_session(serialize_session(first))
        resumed_source = restore_session(serialize_session(first))

        uninterrupted, uninterrupted_outcome = submit_turn(
            uninterrupted_source,
            "What changes when the river returns to the cedar?",
            turn_id="turn:2",
            expected_revision=1,
            max_cycles=2,
            hypotheses=self.hypotheses,
        )
        resumed = restore_session(serialize_session(resumed_source))
        resumed, resumed_outcome = submit_turn(
            resumed,
            "What changes when the river returns to the cedar?",
            turn_id="turn:2",
            expected_revision=1,
            max_cycles=2,
            hypotheses=self.hypotheses,
        )

        self.assertEqual(resumed_outcome, uninterrupted_outcome)
        self.assertEqual(resumed, uninterrupted)
        self.assertEqual(
            [
                (item.cycle_start, item.cycle_end)
                for item in resumed.turns
            ],
            [(1, 1), (2, 2)],
        )
        self.assertEqual(
            resumed.turns[-1].cycle_end,
            len(resumed.field.history),
        )

    def test_rejected_candidate_and_pending_reentry_survive_restart(self):
        session = create_session(thread_id="thread:reintegration")
        native_factory = form_articulation_candidate
        forced_text = (
            "One formation says you should accept the right answer. "
            "Another formation remains perceptible. "
            "Other material remains held open. This settles the matter."
        )

        def forced_factory(state, cut, hypotheses):
            candidate = native_factory(state, cut, hypotheses)
            forced = replace(
                candidate,
                candidate_id="{0}:forced".format(candidate.candidate_id),
                text=forced_text,
            )
            state.articulation_candidates = [
                item
                for item in state.articulation_candidates
                if item.candidate_id != candidate.candidate_id
            ]
            state.articulation_candidates.append(forced)
            state.current_candidate_id = forced.candidate_id
            return forced

        with patch(
            "cbra.native.runtime.form_articulation_candidate",
            side_effect=forced_factory,
        ):
            session, outcome = submit_turn(
                session,
                "How do cedar soil and river stone remain distinct?",
                additional_streams=self.relational_material(),
                turn_id="turn:reject",
                expected_revision=0,
                max_cycles=2,
                hypotheses=self.hypotheses,
            )

        self.assertEqual(
            outcome.kind,
            TurnOutcomeKind.REINTEGRATION_PENDING,
        )
        self.assertIsNone(outcome.text)
        self.assertTrue(outcome.reintegrations)
        self.assertFalse(session.turns[0].articulation_ids)
        self.assertTrue(session.turns[0].evaluation_ids)
        self.assertTrue(session.field.pending_reentry_targets)

        restored = restore_session(serialize_session(session))
        self.assertEqual(restored, session)
        self.assertEqual(
            restored.field.pending_reentry_targets,
            session.field.pending_reentry_targets,
        )
        self.assertEqual(
            restored.turns[0].reintegrations,
            session.turns[0].reintegrations,
        )

    def test_repository_saves_loads_and_rejects_stale_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = NativeSessionRepository(Path(directory))
            base = create_session(thread_id="thread:repository")
            repository.create(base)
            observed_a = repository.load(base.thread_id)
            observed_b = repository.load(base.thread_id)

            updated_a, _ = submit_turn(
                observed_a,
                "First durable turn.",
                turn_id="turn:a",
                expected_revision=0,
                max_cycles=1,
            )
            repository.save(updated_a, expected_revision=0)
            self.assertEqual(repository.load(base.thread_id), updated_a)

            updated_b, _ = submit_turn(
                observed_b,
                "Concurrent durable turn.",
                turn_id="turn:b",
                expected_revision=0,
                max_cycles=1,
            )
            with self.assertRaises(StaleRevisionError):
                repository.save(updated_b, expected_revision=0)

    def test_wrong_field_ownership_duplicate_turns_and_corruption_fail(self):
        session, _ = self.make_accepted_session("thread:ownership")
        wrong = replace(session, field_id="field:other")
        with self.assertRaises(NativeValidationError):
            serialize_session(wrong)

        duplicate = replace(
            session,
            revision=2,
            turns=(session.turns[0], session.turns[0]),
        )
        with self.assertRaises(NativeValidationError):
            serialize_session(duplicate)

        record = json.loads(serialize_session(session).decode("utf-8"))
        record["payload"]["thread_id"] = "thread:tampered"
        data = json.dumps(
            record,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        with self.assertRaises(IntegrityError):
            restore_session(data)

        with tempfile.TemporaryDirectory() as directory:
            repository = NativeSessionRepository(Path(directory))
            other = create_session(thread_id="thread:other")
            from cbra.native import save_session

            save_session(repository.path_for(session.thread_id), other)
            with self.assertRaises(SessionOwnershipError):
                repository.load(session.thread_id)


if __name__ == "__main__":
    unittest.main()
