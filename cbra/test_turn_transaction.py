"""Per-thread execution and persistence transaction contracts."""

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor, wait
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from cbra.application import NativeApplicationService
from cbra.native import (
    SessionOwnershipError,
    StaleRevisionError,
    TurnConflictError,
    create_session,
    submit_turn,
)
from cbra.native.session import run_cycle as native_run_cycle
from cbra.store import (
    NativeSessionRepository,
    SessionRepositoryError,
)


FIRST_STRAND = "Cedar roots shelter soil and hold moisture."
RELATED_STRAND = "Cedar soil holds water around the roots."


class NativeTurnTransactionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = NativeSessionRepository(self.root)
        self.service = NativeApplicationService(
            self.repository,
            max_cycles=2,
        )

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def _cycle_counter():
        count = {"value": 0}
        guard = threading.Lock()

        def counted(*args, **kwargs):
            with guard:
                count["value"] += 1
            return native_run_cycle(*args, **kwargs)

        return count, counted

    def test_concurrent_identical_creation_executes_one_lifecycle(self):
        count, counted = self._cycle_counter()

        def create():
            service = NativeApplicationService(
                NativeSessionRepository(self.root),
                max_cycles=2,
            )
            return service.create_thread(
                "thread:transaction-create",
                FIRST_STRAND,
                turn_id="turn:create",
            )

        with patch(
            "cbra.native.session.run_cycle",
            side_effect=counted,
        ):
            with ThreadPoolExecutor(max_workers=8) as executor:
                results = list(
                    executor.map(lambda _: create(), range(16))
                )

        session = self.repository.load("thread:transaction-create")
        durable_cycles = len(session.field.history)
        self.assertEqual(count["value"], durable_cycles)
        self.assertEqual(
            sum(not item.replayed for item in results),
            1,
        )
        self.assertEqual(
            sum(item.replayed for item in results),
            15,
        )
        self.assertEqual(
            [item.outcome for item in results],
            [results[0].outcome] * len(results),
        )

    def test_concurrent_identical_continuation_executes_once(self):
        self.service.create_thread(
            "thread:transaction-continue",
            FIRST_STRAND,
            turn_id="turn:first",
        )
        count, counted = self._cycle_counter()

        def submit():
            service = NativeApplicationService(
                NativeSessionRepository(self.root),
                max_cycles=2,
            )
            return service.submit_thread_turn(
                "thread:transaction-continue",
                RELATED_STRAND,
                turn_id="turn:second",
                expected_revision=1,
            )

        with patch(
            "cbra.native.session.run_cycle",
            side_effect=counted,
        ):
            with ThreadPoolExecutor(max_workers=8) as executor:
                results = list(
                    executor.map(lambda _: submit(), range(16))
                )

        session = self.repository.load("thread:transaction-continue")
        record = session.turns[-1]
        durable_cycles = record.cycle_end - record.cycle_start + 1
        self.assertEqual(count["value"], durable_cycles)
        self.assertEqual(
            sum(not item.replayed for item in results),
            1,
        )
        self.assertEqual(
            sum(item.replayed for item in results),
            15,
        )
        self.assertEqual(session.revision, 2)

    def test_competing_turns_for_one_revision_execute_one_winner(self):
        self.service.create_thread(
            "thread:competing-turns",
            FIRST_STRAND,
            turn_id="turn:first",
        )
        count, counted = self._cycle_counter()

        def submit(turn_id, text):
            service = NativeApplicationService(
                NativeSessionRepository(self.root),
                max_cycles=2,
            )
            return service.submit_thread_turn(
                "thread:competing-turns",
                text,
                turn_id=turn_id,
                expected_revision=1,
            )

        with patch(
            "cbra.native.session.run_cycle",
            side_effect=counted,
        ):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(
                        submit,
                        "turn:competing-a",
                        RELATED_STRAND,
                    ),
                    executor.submit(
                        submit,
                        "turn:competing-b",
                        "River stone carries cedar silt.",
                    ),
                ]
                successes = []
                failures = []
                for future in futures:
                    try:
                        successes.append(future.result())
                    except Exception as exc:
                        failures.append(exc)

        session = self.repository.load("thread:competing-turns")
        record = session.turns[-1]
        durable_cycles = record.cycle_end - record.cycle_start + 1
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertIsInstance(failures[0], StaleRevisionError)
        self.assertEqual(count["value"], durable_cycles)
        self.assertEqual(session.revision, 2)

    def test_replay_conflict_and_stale_claim_execute_zero_cycles(self):
        first = self.service.create_thread(
            "thread:preflight",
            FIRST_STRAND,
            turn_id="turn:first",
        )
        path = self.repository.path_for(first.outcome.thread_id)
        before = path.read_bytes()

        with patch(
            "cbra.native.session.run_cycle",
            side_effect=AssertionError("cycle must not execute"),
        ), patch(
            "cbra.store.save_session",
            side_effect=AssertionError("replay must not replace storage"),
        ):
            replay = self.service.create_thread(
                "thread:preflight",
                FIRST_STRAND,
                turn_id="turn:first",
            )
            self.assertTrue(replay.replayed)
            with self.assertRaises(TurnConflictError):
                self.service.submit_thread_turn(
                    "thread:preflight",
                    "Changed material.",
                    turn_id="turn:first",
                    expected_revision=1,
                )
            with self.assertRaises(StaleRevisionError):
                self.service.submit_thread_turn(
                    "thread:preflight",
                    RELATED_STRAND,
                    turn_id="turn:second",
                    expected_revision=0,
                )

        self.assertEqual(path.read_bytes(), before)

    def test_callback_failure_writes_nothing_and_retry_starts_cleanly(self):
        with patch(
            "cbra.application.submit_turn",
            side_effect=RuntimeError("renderer failed"),
        ):
            with self.assertRaises(RuntimeError):
                self.service.create_thread(
                    "thread:failed-create",
                    FIRST_STRAND,
                    turn_id="turn:first",
                )

        self.assertFalse(self.repository.exists("thread:failed-create"))
        self.assertFalse(list(self.root.glob(".*.tmp")))
        restarted = NativeApplicationService(
            NativeSessionRepository(self.root),
            max_cycles=2,
        )
        retry = restarted.create_thread(
            "thread:failed-create",
            FIRST_STRAND,
            turn_id="turn:first",
        )
        self.assertFalse(retry.replayed)

        path = self.repository.path_for("thread:failed-create")
        before = path.read_bytes()
        with patch(
            "cbra.application.submit_turn",
            side_effect=RuntimeError("renderer failed"),
        ):
            with self.assertRaises(RuntimeError):
                self.service.submit_thread_turn(
                    "thread:failed-create",
                    RELATED_STRAND,
                    turn_id="turn:second",
                    expected_revision=1,
                )
        self.assertEqual(path.read_bytes(), before)
        restarted = NativeApplicationService(
            NativeSessionRepository(self.root),
            max_cycles=2,
        )
        continued = restarted.submit_thread_turn(
            "thread:failed-create",
            RELATED_STRAND,
            turn_id="turn:second",
            expected_revision=1,
        )
        self.assertFalse(continued.replayed)
        self.assertEqual(continued.outcome.revision, 2)

    def test_different_thread_transactions_execute_concurrently(self):
        barrier = threading.Barrier(2)

        def transact(thread_id):
            repository = NativeSessionRepository(self.root)

            def operation(current):
                self.assertIsNone(current)
                barrier.wait(timeout=2)
                session = create_session(thread_id=thread_id)
                updated, outcome = submit_turn(
                    session,
                    FIRST_STRAND,
                    turn_id="turn:first",
                    expected_revision=0,
                    max_cycles=1,
                )
                return updated, outcome

            return repository.transact(thread_id, operation)

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    transact,
                    ("thread:parallel-a", "thread:parallel-b"),
                )
            )

        self.assertEqual(
            {item.thread_id for item in results},
            {"thread:parallel-a", "thread:parallel-b"},
        )

    def test_readers_never_observe_an_intermediate_revision(self):
        self.service.create_thread(
            "thread:atomic-reader",
            FIRST_STRAND,
            turn_id="turn:first",
        )
        entered = threading.Event()
        release = threading.Event()
        reader_started = threading.Event()

        def transaction():
            def operation(current):
                entered.set()
                if not release.wait(timeout=2):
                    raise AssertionError("transaction release timed out")
                updated, outcome = submit_turn(
                    current,
                    RELATED_STRAND,
                    turn_id="turn:second",
                    expected_revision=1,
                    max_cycles=1,
                )
                return updated, outcome

            return self.repository.transact(
                "thread:atomic-reader",
                operation,
            )

        def read():
            reader_started.set()
            return self.repository.load("thread:atomic-reader")

        with ThreadPoolExecutor(max_workers=2) as executor:
            transaction_future = executor.submit(transaction)
            self.assertTrue(entered.wait(timeout=2))
            reader_future = executor.submit(read)
            self.assertTrue(reader_started.wait(timeout=2))
            done, _ = wait((reader_future,), timeout=0.05)
            self.assertFalse(done)
            release.set()
            transaction_future.result(timeout=2)
            observed = reader_future.result(timeout=2)

        self.assertEqual(observed.revision, 2)
        self.assertEqual(len(observed.turns), 2)

    def test_repository_rejects_invalid_transaction_results(self):
        thread_id = "thread:invalid-result"

        with self.assertRaises(StaleRevisionError):
            self.repository.transact(
                thread_id,
                lambda current: (
                    create_session(thread_id=thread_id),
                    None,
                ),
            )
        self.assertFalse(self.repository.exists(thread_id))

        wrong = create_session(thread_id="thread:wrong-owner")
        wrong, _ = submit_turn(
            wrong,
            FIRST_STRAND,
            turn_id="turn:first",
            expected_revision=0,
            max_cycles=1,
        )
        with self.assertRaises(SessionOwnershipError):
            self.repository.transact(
                thread_id,
                lambda current: (wrong, None),
            )
        self.assertFalse(self.repository.exists(thread_id))

        self.service.create_thread(
            thread_id,
            FIRST_STRAND,
            turn_id="turn:first",
        )
        before = deepcopy(self.repository.load(thread_id))

        def jump(current):
            second, _ = submit_turn(
                current,
                RELATED_STRAND,
                turn_id="turn:second",
                expected_revision=1,
                max_cycles=1,
            )
            third, outcome = submit_turn(
                second,
                "River stone carries cedar silt.",
                turn_id="turn:third",
                expected_revision=2,
                max_cycles=1,
            )
            return third, outcome

        with self.assertRaises(StaleRevisionError):
            self.repository.transact(thread_id, jump)
        self.assertEqual(self.repository.load(thread_id), before)

        rewritten, _ = submit_turn(
            deepcopy(before),
            RELATED_STRAND,
            turn_id="turn:second",
            expected_revision=1,
            max_cycles=1,
        )
        rewritten.turns = (
            replace(
                rewritten.turns[0],
                material_digest="0" * 64,
            ),
            rewritten.turns[1],
        )
        with self.assertRaises(SessionRepositoryError):
            self.repository.transact(
                thread_id,
                lambda current: (rewritten, None),
            )
        self.assertEqual(self.repository.load(thread_id), before)

        with self.assertRaises(SessionRepositoryError):
            self.repository.transact(
                thread_id,
                lambda current: current,
            )


if __name__ == "__main__":
    unittest.main()
