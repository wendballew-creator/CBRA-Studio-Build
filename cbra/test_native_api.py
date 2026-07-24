"""Native application-service and truthful HTTP-boundary contracts."""

import gzip
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from cbra.app import create_app
from cbra.application import NativeApplicationService
from cbra.native import (
    RuntimeHypotheses,
    StaleRevisionError,
    TurnConflictError,
    TurnOutcomeKind,
    create_session,
)
from cbra.native.articulation import form_articulation_candidate
from cbra.store import NativeSessionRepository


FIRST_STRAND = "Cedar roots shelter soil and hold moisture."
RELATED_STRAND = "Cedar soil holds water around the roots."


class NativeApplicationServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = NativeSessionRepository(self.root)
        self.service = NativeApplicationService(
            self.repository,
            thread_id_factory=lambda: "thread:service",
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_create_restart_continue_and_summary_are_native_and_durable(self):
        first = self.service.create_thread(
            FIRST_STRAND,
            turn_id="turn:1",
            expected_revision=0,
        )

        self.assertEqual(
            first.outcome.kind,
            TurnOutcomeKind.NO_ARTICULATION,
        )
        self.assertIsNone(first.outcome.text)
        self.assertFalse(first.replayed)
        persisted = self.repository.load(first.outcome.thread_id)
        self.assertEqual(persisted.revision, 1)

        restarted = NativeApplicationService(
            NativeSessionRepository(self.root),
        )
        second = restarted.submit_thread_turn(
            first.outcome.thread_id,
            RELATED_STRAND,
            turn_id="turn:2",
            expected_revision=1,
        )
        self.assertEqual(
            second.outcome.kind,
            TurnOutcomeKind.ACCEPTED_ARTICULATION,
        )
        self.assertTrue(second.outcome.text)

        summary = restarted.summarize_thread(first.outcome.thread_id)
        self.assertEqual(summary.revision, 2)
        self.assertEqual(summary.turn_count, 2)
        self.assertEqual(summary.latest_outcome, second.outcome.kind)
        self.assertFalse(summary.reintegration_pending)
        self.assertGreaterEqual(summary.cycle_count, 2)

    def test_retry_is_idempotent_and_changed_reuse_conflicts(self):
        first = self.service.create_thread(
            FIRST_STRAND,
            turn_id="turn:stable",
            expected_revision=0,
        )
        before = self.repository.load(first.outcome.thread_id)

        retried = self.service.submit_thread_turn(
            first.outcome.thread_id,
            FIRST_STRAND,
            turn_id="turn:stable",
            expected_revision=0,
        )

        self.assertTrue(retried.replayed)
        self.assertEqual(retried.outcome, first.outcome)
        self.assertEqual(
            self.repository.load(first.outcome.thread_id),
            before,
        )
        with self.assertRaises(TurnConflictError):
            self.service.submit_thread_turn(
                first.outcome.thread_id,
                "Different material under the same turn identity.",
                turn_id="turn:stable",
                expected_revision=1,
            )

    def test_stale_revision_does_not_change_durable_session(self):
        first = self.service.create_thread(
            FIRST_STRAND,
            turn_id="turn:1",
            expected_revision=0,
        )
        before = self.repository.load(first.outcome.thread_id)

        with self.assertRaises(StaleRevisionError):
            self.service.submit_thread_turn(
                first.outcome.thread_id,
                RELATED_STRAND,
                turn_id="turn:2",
                expected_revision=0,
            )

        self.assertEqual(
            self.repository.load(first.outcome.thread_id),
            before,
        )

    def test_identical_concurrent_save_is_recovered_as_a_replay(self):
        class IdenticalRaceRepository(NativeSessionRepository):
            raced = False

            def save(self, session, expected_revision):
                if not self.raced:
                    self.raced = True
                    super().save(session, expected_revision)
                    raise StaleRevisionError("simulated concurrent save")
                return super().save(session, expected_revision)

        repository = IdenticalRaceRepository(self.root)
        base = create_session(thread_id="thread:race")
        repository.create(base)
        service = NativeApplicationService(repository)

        result = service.submit_thread_turn(
            base.thread_id,
            FIRST_STRAND,
            turn_id="turn:race",
            expected_revision=0,
        )

        self.assertTrue(result.replayed)
        self.assertEqual(result.outcome.revision, 1)
        restored = repository.load(base.thread_id)
        self.assertEqual(restored.revision, 1)
        self.assertEqual(len(restored.turns), 1)

    def test_creation_collision_retries_with_a_fresh_thread_identity(self):
        occupied = create_session(thread_id="thread:occupied")
        self.repository.create(occupied)
        identities = iter(("thread:occupied", "thread:fresh"))
        service = NativeApplicationService(
            self.repository,
            thread_id_factory=lambda: next(identities),
        )

        result = service.create_thread(
            FIRST_STRAND,
            expected_revision=0,
        )

        self.assertEqual(result.outcome.thread_id, "thread:fresh")
        self.assertEqual(
            self.repository.load("thread:occupied"),
            occupied,
        )
        self.assertEqual(
            self.repository.load("thread:fresh").revision,
            1,
        )


class NativeFastAPITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.application = create_app(session_root=self.root)
        self.client = TestClient(
            self.application,
            raise_server_exceptions=False,
        )

    def tearDown(self):
        self.client.close()
        self.temporary.cleanup()

    def generate(self, text=FIRST_STRAND, **values):
        body = {
            "user_text": text,
            "turn_id": values.pop("turn_id", "turn:1"),
            "expected_revision": values.pop("expected_revision", 0),
        }
        body.update(values)
        return self.client.post("/generate", json=body)

    def test_generate_is_durable_and_sparse_response_is_truthful(self):
        response = self.generate()

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["turn_id"], "turn:1")
        self.assertEqual(body["revision"], 1)
        self.assertEqual(body["outcome"], "no_articulation")
        self.assertIsNone(body["text"])
        self.assertIsNone(body["debug"])
        self.assertTrue(body["thread_id"].startswith("thread:"))
        self.assertTrue(body["request_id"])
        serialized = response.text
        for forbidden in (
            '"field"',
            '"streams"',
            '"candidate_id"',
            '"material_digest"',
            '"payload"',
            '"field_values"',
        ):
            self.assertNotIn(forbidden, serialized)

        repository = self.application.state.native_service.repository
        session = repository.load(body["thread_id"])
        self.assertEqual(session.revision, 1)
        self.assertEqual(session.turns[0].turn_id, "turn:1")

    def test_restart_continues_thread_and_related_turn_can_articulate(self):
        first = self.generate().json()
        self.client.close()
        restarted = create_app(session_root=self.root)
        self.client = TestClient(
            restarted,
            raise_server_exceptions=False,
        )

        response = self.client.post(
            "/chat/{0}".format(first["thread_id"]),
            json={
                "user_text": RELATED_STRAND,
                "turn_id": "turn:2",
                "expected_revision": 1,
            },
        )

        self.assertEqual(response.status_code, 200)
        second = response.json()
        self.assertEqual(second["revision"], 2)
        self.assertEqual(second["outcome"], "accepted_articulation")
        self.assertTrue(second["text"])
        restored = restarted.state.native_service.repository.load(
            first["thread_id"]
        )
        self.assertEqual(restored.revision, 2)
        self.assertEqual(len(restored.turns), 2)

    def test_retry_conflict_and_stale_revision_have_distinct_contracts(self):
        first = self.generate().json()
        thread_path = "/chat/{0}".format(first["thread_id"])

        retry = self.client.post(
            thread_path,
            json={
                "user_text": FIRST_STRAND,
                "turn_id": "turn:1",
                "expected_revision": 0,
                "mode": "debug",
            },
        )
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.json()["revision"], 1)
        self.assertTrue(retry.json()["debug"]["idempotent_replay"])

        conflict = self.client.post(
            thread_path,
            json={
                "user_text": "Changed material.",
                "turn_id": "turn:1",
                "expected_revision": 1,
            },
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(
            conflict.json()["error"]["code"],
            "turn_conflict",
        )

        stale = self.client.post(
            thread_path,
            json={
                "user_text": RELATED_STRAND,
                "turn_id": "turn:2",
                "expected_revision": 0,
            },
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(
            stale.json()["error"]["code"],
            "stale_revision",
        )
        summary = self.client.get(
            "/thread/{0}".format(first["thread_id"])
        ).json()
        self.assertEqual(summary["revision"], 1)
        self.assertEqual(summary["turn_count"], 1)

    def test_summary_is_bounded_missing_is_404_and_delete_is_unsupported(self):
        first = self.generate().json()
        path = "/thread/{0}".format(first["thread_id"])

        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            set(body),
            {
                "request_id",
                "thread_id",
                "revision",
                "turn_count",
                "latest_outcome",
                "reintegration_pending",
            },
        )
        self.assertEqual(body["latest_outcome"], "no_articulation")

        missing = self.client.get("/thread/thread:missing")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(
            missing.json()["error"]["code"],
            "session_not_found",
        )

        deletion = self.client.delete(path)
        self.assertEqual(deletion.status_code, 405)
        self.assertEqual(
            deletion.json()["error"]["code"],
            "method_not_allowed",
        )
        self.assertEqual(self.client.get(path).status_code, 200)

    def test_invalid_requests_are_422_without_echoing_payloads(self):
        response = self.client.post(
            "/generate",
            json={
                "user_text": "",
                "expected_revision": True,
                "unexpected": "private material",
            },
        )

        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertEqual(body["error"]["code"], "invalid_request")
        self.assertIn("user_text", body["error"]["fields"])
        self.assertIn("expected_revision", body["error"]["fields"])
        self.assertIn("unexpected", body["error"]["fields"])
        self.assertNotIn("private material", response.text)

        whitespace = self.client.post(
            "/generate",
            json={"user_text": "   ", "turn_id": "  "},
        )
        self.assertEqual(whitespace.status_code, 422)
        self.assertEqual(
            whitespace.json()["error"]["code"],
            "invalid_request",
        )

    def test_corrupt_durable_state_returns_safe_server_error(self):
        first = self.generate().json()
        repository = self.application.state.native_service.repository
        path = repository.path_for(first["thread_id"])
        path.write_bytes(gzip.compress(b'{"private":"payload"}'))

        response = self.client.get(
            "/thread/{0}".format(first["thread_id"])
        )

        self.assertEqual(response.status_code, 500)
        body = response.json()
        self.assertEqual(
            body["error"]["code"],
            "invalid_durable_state",
        )
        self.assertNotIn(str(path), response.text)
        self.assertNotIn("private", response.text)

    def test_pending_reintegration_remains_null_and_survives_restart(self):
        hypotheses = RuntimeHypotheses(
            articulation_emergence_floor=0.05,
            articulation_coherence_floor=0.05,
        )
        repository = NativeSessionRepository(self.root)
        service = NativeApplicationService(
            repository,
            hypotheses=hypotheses,
            thread_id_factory=lambda: "thread:reintegration-api",
        )
        self.client.close()
        self.application = create_app(service=service)
        self.client = TestClient(
            self.application,
            raise_server_exceptions=False,
        )
        first = self.generate().json()
        native_factory = form_articulation_candidate
        forced_text = (
            "One formation says you should accept the right answer. "
            "Another formation remains perceptible. "
            "Other material remains held open. This settles the matter."
        )

        def forced_factory(state, cut, runtime_hypotheses):
            candidate = native_factory(
                state,
                cut,
                runtime_hypotheses,
            )
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
            response = self.client.post(
                "/chat/{0}".format(first["thread_id"]),
                json={
                    "user_text": RELATED_STRAND,
                    "turn_id": "turn:2",
                    "expected_revision": 1,
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["outcome"], "reintegration_pending")
        self.assertIsNone(body["text"])

        self.client.close()
        restarted = create_app(session_root=self.root)
        self.client = TestClient(
            restarted,
            raise_server_exceptions=False,
        )
        summary = self.client.get(
            "/thread/{0}".format(first["thread_id"])
        ).json()
        self.assertEqual(
            summary["latest_outcome"],
            "reintegration_pending",
        )
        self.assertTrue(summary["reintegration_pending"])

    def test_openapi_declares_typed_errors_and_no_delete_operation(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        document = response.json()
        generate = document["paths"]["/generate"]["post"]
        self.assertIn("201", generate["responses"])
        self.assertIn("409", generate["responses"])
        self.assertIn("422", generate["responses"])
        thread_path = document["paths"]["/thread/{thread_id}"]
        self.assertNotIn("delete", thread_path)


if __name__ == "__main__":
    unittest.main()
