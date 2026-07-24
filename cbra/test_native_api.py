"""Native application-service and truthful HTTP-boundary contracts."""

import gzip
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from cbra.app import create_app
from cbra.application import (
    NativeApplicationService,
    TurnProjectionPaginationError,
)
from cbra.native import (
    NativeSessionError,
    RuntimeHypotheses,
    StaleRevisionError,
    TurnConflictError,
    TurnOutcomeKind,
    create_session,
)
from cbra.native.articulation import form_articulation_candidate
from cbra.store import (
    NativeSessionRepository,
    SessionAlreadyExistsError,
)


FIRST_STRAND = "Cedar roots shelter soil and hold moisture."
RELATED_STRAND = "Cedar soil holds water around the roots."
THREAD_A = "thread:{0}".format("a" * 32)
THREAD_B = "thread:{0}".format("b" * 32)
TURN_A = "turn:{0}".format("1" * 32)
TURN_B = "turn:{0}".format("2" * 32)


class NativeApplicationServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = NativeSessionRepository(self.root)
        self.service = NativeApplicationService(self.repository)

    def tearDown(self):
        self.temporary.cleanup()

    def test_create_restart_continue_and_summary_are_native_and_durable(self):
        first = self.service.create_thread(
            "thread:service",
            FIRST_STRAND,
            turn_id="turn:1",
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

    def test_turn_projection_is_exact_bounded_and_read_only(self):
        first = self.service.create_thread(
            "thread:projection",
            FIRST_STRAND,
            turn_id="turn:first",
        )
        second = self.service.submit_thread_turn(
            first.outcome.thread_id,
            RELATED_STRAND,
            turn_id="turn:second",
            expected_revision=1,
        )
        path = self.repository.path_for(first.outcome.thread_id)
        before = path.read_bytes()

        first_page = self.service.project_thread_turns(
            first.outcome.thread_id,
            limit=1,
        )
        second_page = self.service.project_thread_turns(
            first.outcome.thread_id,
            after_revision=first_page.next_after_revision,
            limit=1,
        )
        complete = first_page.turns + second_page.turns

        self.assertEqual(first_page.session_revision, 2)
        self.assertEqual(first_page.next_after_revision, 1)
        self.assertTrue(first_page.has_more)
        self.assertEqual(second_page.next_after_revision, 2)
        self.assertFalse(second_page.has_more)
        self.assertEqual(
            [item.revision for item in complete],
            [1, 2],
        )
        self.assertEqual(
            [item.user_text for item in complete],
            [FIRST_STRAND, RELATED_STRAND],
        )
        self.assertIsNone(complete[0].text)
        self.assertEqual(complete[1].text, second.outcome.text)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(
            self.repository.load(first.outcome.thread_id).revision,
            2,
        )

    def test_turn_projection_validates_cursor_and_native_references(self):
        first = self.service.create_thread(
            "thread:projection-validation",
            FIRST_STRAND,
            turn_id="turn:first",
        )
        self.service.submit_thread_turn(
            first.outcome.thread_id,
            RELATED_STRAND,
            turn_id="turn:second",
            expected_revision=1,
        )
        with self.assertRaises(TurnProjectionPaginationError):
            self.service.project_thread_turns(
                first.outcome.thread_id,
                after_revision=3,
            )
        with self.assertRaises(TurnProjectionPaginationError):
            self.service.project_thread_turns(
                first.outcome.thread_id,
                limit=101,
            )

        corrupt = deepcopy(
            self.repository.load(first.outcome.thread_id)
        )
        user_stream_id = corrupt.turns[0].user_stream_id
        next(
            item
            for item in corrupt.field.streams
            if item.stream_id == user_stream_id
        ).payload = {}
        with patch.object(
            self.repository,
            "load",
            return_value=corrupt,
        ):
            with self.assertRaises(NativeSessionError):
                self.service.project_thread_turns(
                    first.outcome.thread_id,
                )

        missing_articulation = deepcopy(
            self.repository.load(first.outcome.thread_id)
        )
        accepted_id = missing_articulation.turns[1].articulation_ids[0]
        missing_articulation.field.articulations = [
            item
            for item in missing_articulation.field.articulations
            if item.articulation_id != accepted_id
        ]
        with patch.object(
            self.repository,
            "load",
            return_value=missing_articulation,
        ):
            with self.assertRaises(NativeSessionError):
                self.service.project_thread_turns(
                    first.outcome.thread_id,
                    after_revision=1,
                )

    def test_retry_is_idempotent_and_changed_reuse_conflicts(self):
        first = self.service.create_thread(
            "thread:retry",
            FIRST_STRAND,
            turn_id="turn:stable",
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
            "thread:stale",
            FIRST_STRAND,
            turn_id="turn:1",
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

    def test_claimed_creation_replays_after_restart_without_duplication(self):
        first = self.service.create_thread(
            "thread:claimed",
            FIRST_STRAND,
            turn_id="turn:initial",
        )
        restarted = NativeApplicationService(
            NativeSessionRepository(self.root),
        )

        replay = restarted.create_thread(
            "thread:claimed",
            FIRST_STRAND,
            turn_id="turn:initial",
        )

        self.assertFalse(first.replayed)
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.outcome, first.outcome)
        restored = self.repository.load("thread:claimed")
        self.assertEqual(restored.revision, 1)
        self.assertEqual(len(restored.turns), 1)
        self.assertEqual(
            len(list(self.root.glob("native-session-*"))),
            1,
        )

    def test_claimed_creation_conflicts_do_not_mutate_existing_session(self):
        first = self.service.create_thread(
            "thread:claimed-conflict",
            FIRST_STRAND,
            turn_id="turn:initial",
        )
        before = self.repository.load(first.outcome.thread_id)

        with self.assertRaises(TurnConflictError):
            self.service.create_thread(
                "thread:claimed-conflict",
                "Different initial material.",
                turn_id="turn:initial",
            )
        with self.assertRaises(SessionAlreadyExistsError):
            self.service.create_thread(
                "thread:claimed-conflict",
                FIRST_STRAND,
                turn_id="turn:different",
            )
        self.assertEqual(
            self.repository.load(first.outcome.thread_id),
            before,
        )

    def test_same_turn_identity_is_valid_in_different_claimed_threads(self):
        first = self.service.create_thread(
            "thread:first-claim",
            FIRST_STRAND,
            turn_id="turn:shared",
        )
        second = self.service.create_thread(
            "thread:second-claim",
            FIRST_STRAND,
            turn_id="turn:shared",
        )

        self.assertNotEqual(
            first.outcome.thread_id,
            second.outcome.thread_id,
        )
        self.assertEqual(first.outcome.turn_id, second.outcome.turn_id)
        self.assertFalse(first.replayed)
        self.assertFalse(second.replayed)

    def test_concurrent_identical_creation_converges_on_one_session(self):
        def create():
            service = NativeApplicationService(
                NativeSessionRepository(self.root),
            )
            return service.create_thread(
                "thread:concurrent-claim",
                FIRST_STRAND,
                turn_id="turn:concurrent-initial",
            )

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda _: create(), range(16)))

        self.assertEqual(
            sum(not result.replayed for result in results),
            1,
        )
        self.assertEqual(
            sum(result.replayed for result in results),
            15,
        )
        self.assertEqual(
            [result.outcome for result in results],
            [results[0].outcome] * len(results),
        )
        restored = self.repository.load("thread:concurrent-claim")
        self.assertEqual(restored.revision, 1)
        self.assertEqual(len(restored.turns), 1)
        self.assertEqual(
            len(list(self.root.glob("native-session-*"))),
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
            "thread_id": values.pop("thread_id", THREAD_A),
            "user_text": text,
            "turn_id": values.pop("turn_id", TURN_A),
        }
        body.update(values)
        return self.client.post("/generate", json=body)

    def test_generate_is_durable_and_sparse_response_is_truthful(self):
        response = self.generate()

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["thread_id"], THREAD_A)
        self.assertEqual(body["turn_id"], TURN_A)
        self.assertEqual(body["revision"], 1)
        self.assertEqual(body["outcome"], "no_articulation")
        self.assertIsNone(body["text"])
        self.assertFalse(body["idempotent_replay"])
        self.assertIsNone(body["debug"])
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
        self.assertEqual(session.turns[0].turn_id, TURN_A)

    def test_generate_retry_recovers_preclaimed_thread_after_restart(self):
        first_response = self.generate()
        self.assertEqual(first_response.status_code, 201)
        first = first_response.json()
        self.client.close()
        restarted = create_app(session_root=self.root)
        self.application = restarted
        self.client = TestClient(
            restarted,
            raise_server_exceptions=False,
        )

        retry_response = self.generate()

        self.assertEqual(retry_response.status_code, 200)
        retry = retry_response.json()
        self.assertTrue(retry["idempotent_replay"])
        for field in (
            "thread_id",
            "turn_id",
            "revision",
            "outcome",
            "text",
        ):
            self.assertEqual(retry[field], first[field])
        repository = restarted.state.native_service.repository
        restored = repository.load(THREAD_A)
        self.assertEqual(restored.revision, 1)
        self.assertEqual(len(restored.turns), 1)
        self.assertEqual(
            len(list(self.root.glob("native-session-*"))),
            1,
        )

    def test_generate_conflicts_leave_claimed_session_unchanged(self):
        first = self.generate().json()
        repository = self.application.state.native_service.repository
        before = repository.load(first["thread_id"])

        changed_material = self.generate(
            "Changed initial material.",
        )
        changed_identity = self.generate(turn_id=TURN_B)

        self.assertEqual(changed_material.status_code, 409)
        self.assertEqual(
            changed_material.json()["error"]["code"],
            "turn_conflict",
        )
        self.assertEqual(changed_identity.status_code, 409)
        self.assertEqual(
            changed_identity.json()["error"]["code"],
            "session_conflict",
        )
        self.assertEqual(repository.load(first["thread_id"]), before)

    def test_same_initial_turn_id_can_claim_independent_threads(self):
        first = self.generate(thread_id=THREAD_A)
        second = self.generate(thread_id=THREAD_B)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.json()["turn_id"], TURN_A)
        self.assertEqual(second.json()["turn_id"], TURN_A)
        self.assertNotEqual(
            first.json()["thread_id"],
            second.json()["thread_id"],
        )
        repository = self.application.state.native_service.repository
        self.assertEqual(repository.load(THREAD_A).revision, 1)
        self.assertEqual(repository.load(THREAD_B).revision, 1)

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
                "turn_id": TURN_A,
                "expected_revision": 0,
                "mode": "debug",
            },
        )
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.json()["revision"], 1)
        self.assertTrue(retry.json()["idempotent_replay"])
        self.assertTrue(retry.json()["debug"]["idempotent_replay"])

        conflict = self.client.post(
            thread_path,
            json={
                "user_text": "Changed material.",
                "turn_id": TURN_A,
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

    def test_turn_pages_restore_exact_history_without_gaps_after_restart(self):
        first = self.generate().json()
        continuation = self.client.post(
            "/chat/{0}".format(first["thread_id"]),
            json={
                "user_text": RELATED_STRAND,
                "turn_id": TURN_B,
                "expected_revision": 1,
            },
        ).json()
        self.client.close()
        restarted = create_app(session_root=self.root)
        self.client = TestClient(
            restarted,
            raise_server_exceptions=False,
        )
        path = "/thread/{0}/turns".format(first["thread_id"])

        first_page_response = self.client.get(path, params={"limit": 1})
        first_page = first_page_response.json()
        second_page_response = self.client.get(
            path,
            params={
                "after_revision": first_page["next_after_revision"],
                "limit": 1,
            },
        )
        second_page = second_page_response.json()

        self.assertEqual(first_page_response.status_code, 200)
        self.assertEqual(second_page_response.status_code, 200)
        self.assertEqual(first_page["session_revision"], 2)
        self.assertTrue(first_page["has_more"])
        self.assertFalse(second_page["has_more"])
        turns = first_page["turns"] + second_page["turns"]
        self.assertEqual([item["revision"] for item in turns], [1, 2])
        self.assertEqual(
            [item["user_text"] for item in turns],
            [FIRST_STRAND, RELATED_STRAND],
        )
        self.assertIsNone(turns[0]["text"])
        self.assertEqual(turns[1]["text"], continuation["text"])
        forbidden = (
            "material_digest",
            "stream_id",
            "candidate_id",
            "cycle_start",
            "field_values",
            "reintegration",
        )
        for field in forbidden:
            self.assertNotIn(field, first_page_response.text)
            self.assertNotIn(field, second_page_response.text)

    def test_turn_page_pagination_errors_are_typed_and_safe(self):
        first = self.generate().json()
        path = "/thread/{0}/turns".format(first["thread_id"])

        negative = self.client.get(
            path,
            params={"after_revision": -1},
        )
        too_large = self.client.get(path, params={"limit": 101})
        future = self.client.get(
            path,
            params={"after_revision": 2},
        )
        missing = self.client.get(
            "/thread/{0}/turns".format(THREAD_B)
        )

        self.assertEqual(negative.status_code, 422)
        self.assertEqual(
            negative.json()["error"]["code"],
            "invalid_request",
        )
        self.assertEqual(too_large.status_code, 422)
        self.assertEqual(
            too_large.json()["error"]["code"],
            "invalid_request",
        )
        self.assertEqual(future.status_code, 422)
        self.assertEqual(
            future.json()["error"]["code"],
            "invalid_pagination",
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(
            missing.json()["error"]["code"],
            "session_not_found",
        )

    def test_invalid_projection_reference_returns_safe_server_error(self):
        first = self.generate().json()
        repository = self.application.state.native_service.repository
        corrupt = deepcopy(repository.load(first["thread_id"]))
        user_stream_id = corrupt.turns[0].user_stream_id
        next(
            item
            for item in corrupt.field.streams
            if item.stream_id == user_stream_id
        ).payload = {
            "text": {"private": "payload"}
        }

        with patch.object(
            repository,
            "load",
            return_value=corrupt,
        ):
            response = self.client.get(
                "/thread/{0}/turns".format(first["thread_id"])
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["error"]["code"],
            "invalid_durable_state",
        )
        self.assertNotIn("private", response.text)

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
        self.assertIn("thread_id", body["error"]["fields"])
        self.assertIn("turn_id", body["error"]["fields"])
        self.assertIn("user_text", body["error"]["fields"])
        self.assertIn("expected_revision", body["error"]["fields"])
        self.assertIn("unexpected", body["error"]["fields"])
        self.assertNotIn("private material", response.text)

        whitespace = self.client.post(
            "/generate",
            json={
                "thread_id": "thread:not-hex",
                "user_text": "   ",
                "turn_id": "turn:not-hex",
            },
        )
        self.assertEqual(whitespace.status_code, 422)
        self.assertEqual(
            whitespace.json()["error"]["code"],
            "invalid_request",
        )

        oversized = self.client.post(
            "/generate",
            json={
                "thread_id": "thread:{0}".format("a" * 33),
                "user_text": FIRST_STRAND,
                "turn_id": "turn:{0}".format("1" * 33),
            },
        )
        self.assertEqual(oversized.status_code, 422)
        self.assertIn(
            "thread_id",
            oversized.json()["error"]["fields"],
        )
        self.assertIn(
            "turn_id",
            oversized.json()["error"]["fields"],
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
        turns = self.client.get(
            "/thread/{0}/turns".format(first["thread_id"])
        ).json()["turns"]
        self.assertEqual(
            [item["outcome"] for item in turns],
            ["no_articulation", "reintegration_pending"],
        )
        self.assertEqual(
            [item["text"] for item in turns],
            [None, None],
        )

    def test_openapi_declares_typed_errors_and_no_delete_operation(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        document = response.json()
        generate = document["paths"]["/generate"]["post"]
        self.assertIn("201", generate["responses"])
        self.assertIn("200", generate["responses"])
        self.assertIn("409", generate["responses"])
        self.assertIn("422", generate["responses"])
        request_reference = generate["requestBody"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        request_name = request_reference.rsplit("/", 1)[-1]
        create_request = document["components"]["schemas"][request_name]
        self.assertEqual(
            set(create_request["required"]),
            {"thread_id", "turn_id", "user_text"},
        )
        self.assertNotIn(
            "expected_revision",
            create_request["properties"],
        )
        response_schema = document["components"]["schemas"][
            "TurnResponse"
        ]
        self.assertIn(
            "idempotent_replay",
            response_schema["required"],
        )
        thread_path = document["paths"]["/thread/{thread_id}"]
        self.assertNotIn("delete", thread_path)
        turn_path = document["paths"][
            "/thread/{thread_id}/turns"
        ]["get"]
        self.assertIn("200", turn_path["responses"])
        self.assertIn("404", turn_path["responses"])
        self.assertIn("422", turn_path["responses"])
        self.assertIn("500", turn_path["responses"])
        self.assertEqual(
            turn_path["responses"]["200"]["content"][
                "application/json"
            ]["schema"]["$ref"],
            "#/components/schemas/TurnPageResponse",
        )


if __name__ == "__main__":
    unittest.main()
