"""Lossless persistence contracts for the architecture-native runtime."""

import hashlib
import json
import tempfile
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from cbra.native import (
    Apparatus,
    ArticulationCandidate,
    CyclePhase,
    DriftKind,
    FieldSnapshot,
    HistoryEntry,
    IntegrityError,
    NativeFormatError,
    NativeValidationError,
    PayloadTypeError,
    ReentryTarget,
    RuntimeHypotheses,
    Stream,
    UnsupportedSchemaVersionError,
    load_checkpoint,
    load_trace,
    restore_checkpoint,
    restore_trace,
    run_cycle,
    save_checkpoint,
    save_trace,
    serialize_checkpoint,
    serialize_trace,
)
from cbra.native.articulation import form_articulation_candidate


class NativePersistenceTests(unittest.TestCase):
    def setUp(self):
        self.hypotheses = RuntimeHypotheses(
            articulation_emergence_floor=0.05,
            articulation_coherence_floor=0.05,
        )

    def make_field(self):
        from cbra.native import initialize_field

        return initialize_field(
            [
                Stream(
                    stream_id="a:1",
                    kind="memory",
                    payload={
                        "text": "cedar roots shelter soil",
                        "nested": {
                            "source": "field note",
                            "pages": [1, 2],
                            "available": True,
                        },
                    },
                    participation=0.72,
                    persistence=0.80,
                    provenance={"author": "Wend", "revision": None},
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
                apparatus_id="apparatus:persistence",
                framing="shared inquiry",
                medium="text chat",
                institutions=["ChatGPT"],
                constraints=["preserve multiplicity"],
            ),
            field_id="field:persistence",
            hypotheses=self.hypotheses,
        )

    def run_rejected_cycle(self, state):
        text = (
            "One formation says you should accept the right answer. "
            "Another formation remains perceptible. "
            "Other material remains held open. This settles the matter."
        )
        native_factory = form_articulation_candidate

        def forced_factory(inner_state, cut, inner_hypotheses):
            candidate = native_factory(
                inner_state,
                cut,
                inner_hypotheses,
            )
            forced = replace(
                candidate,
                candidate_id="{0}:forced".format(
                    candidate.candidate_id
                ),
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
            return run_cycle(state, self.hypotheses)

    def test_accepted_articulation_checkpoint_round_trips_exactly(self):
        state = self.make_field()
        result = run_cycle(state, self.hypotheses)
        self.assertIsNotNone(result.articulation)

        data = serialize_checkpoint(state)
        restored = restore_checkpoint(data)

        self.assertEqual(restored, state)
        self.assertIsInstance(restored.history, tuple)
        self.assertIsInstance(restored.history[0], HistoryEntry)
        self.assertIsInstance(restored.history[0].phases, tuple)
        self.assertIsInstance(
            restored.history[0].phases[0].field,
            FieldSnapshot,
        )
        self.assertIsInstance(
            restored.history[0].phases[0].field.streams,
            tuple,
        )
        self.assertIsInstance(
            restored.history[0].phases[0].phase,
            CyclePhase,
        )
        self.assertIsInstance(
            restored.articulation_candidates[0],
            ArticulationCandidate,
        )
        self.assertIsInstance(
            restored.articulation_evaluations[0].drift_signals,
            list,
        )

    def test_rejected_candidate_reintegration_and_pending_reentry_round_trip(self):
        state = self.make_field()
        result = self.run_rejected_cycle(state)

        self.assertIsNone(result.articulation)
        self.assertFalse(result.articulation_evaluation.accepted)
        self.assertTrue(result.reintegrations)
        self.assertIn(
            ReentryTarget.ARTICULATION,
            state.pending_reentry_targets,
        )

        restored = restore_checkpoint(serialize_checkpoint(state))

        self.assertEqual(restored, state)
        self.assertTrue(
            all(
                isinstance(item, ReentryTarget)
                for item in restored.pending_reentry_targets
            )
        )
        self.assertTrue(
            all(
                isinstance(item.drift_kind, DriftKind)
                for item in restored.history[-1].reintegrations
            )
        )

    def test_trace_preserves_every_phase_and_historical_record(self):
        state = self.make_field()
        run_cycle(state, self.hypotheses)
        run_cycle(state, self.hypotheses)

        archive = restore_trace(serialize_trace(state))

        self.assertEqual(archive.field_id, state.field_id)
        self.assertEqual(archive.entries, state.history)
        self.assertEqual(
            [
                phase.phase
                for phase in archive.entries[-1].phases
            ],
            list(CyclePhase),
        )

    def test_restored_history_is_append_only_and_mutation_isolated(self):
        state = self.make_field()
        run_cycle(state, self.hypotheses)
        original = deepcopy(state)

        restored = restore_checkpoint(serialize_checkpoint(state))
        restored.streams[0].payload["text"] = "changed current material"
        restored.streams[0].participation = 0.01

        self.assertEqual(state, original)
        self.assertNotEqual(
            restored.streams[0].payload,
            restored.history[0].before.streams[0].payload,
        )
        self.assertIsInstance(restored.history, tuple)
        with self.assertRaises(AttributeError):
            restored.history.append(restored.history[0])

    def test_continuation_matches_an_uninterrupted_equivalent_field(self):
        state = self.make_field()
        run_cycle(state, self.hypotheses)
        serialized = serialize_checkpoint(state)
        uninterrupted = restore_checkpoint(serialized)
        resumed = restore_checkpoint(serialized)

        uninterrupted_result = run_cycle(
            uninterrupted,
            self.hypotheses,
        )
        resumed_result = run_cycle(resumed, self.hypotheses)

        self.assertEqual(resumed_result, uninterrupted_result)
        self.assertEqual(resumed, uninterrupted)

    def test_canonical_json_and_atomic_plain_and_gzip_files(self):
        state = self.make_field()
        run_cycle(state, self.hypotheses)
        first = serialize_checkpoint(state)
        second = serialize_checkpoint(state)
        self.assertEqual(first, second)
        record = json.loads(first.decode("utf-8"))
        self.assertEqual(record["schema_version"], 1)
        self.assertEqual(
            record["payload_type"],
            "native_field_checkpoint",
        )
        self.assertEqual(record["integrity"]["algorithm"], "sha256")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plain_path = root / "field.checkpoint.json"
            gzip_path = root / "field.checkpoint.json.gz"
            trace_path = root / "field.trace.json.gz"
            save_checkpoint(plain_path, state)
            save_checkpoint(gzip_path, state)
            save_trace(trace_path, state)

            self.assertEqual(load_checkpoint(plain_path), state)
            self.assertEqual(load_checkpoint(gzip_path), state)
            self.assertEqual(
                load_trace(trace_path).entries,
                state.history,
            )
            self.assertTrue(
                gzip_path.read_bytes().startswith(b"\x1f\x8b")
            )
            self.assertLess(
                gzip_path.stat().st_size,
                plain_path.stat().st_size,
            )
            self.assertFalse(
                any(path.suffix == ".tmp" for path in root.iterdir())
            )

    def test_checksum_failure_and_wrong_payload_type_fail_explicitly(self):
        state = self.make_field()
        run_cycle(state, self.hypotheses)
        record = json.loads(
            serialize_checkpoint(state).decode("utf-8")
        )
        record["payload"]["field_id"] = "field:tampered"
        tampered = self.canonical_bytes(record)

        with self.assertRaises(IntegrityError):
            restore_checkpoint(tampered)
        with self.assertRaises(PayloadTypeError):
            restore_trace(serialize_checkpoint(state))

    def test_corrupt_incomplete_and_unsupported_records_fail_explicitly(self):
        state = self.make_field()
        data = serialize_checkpoint(state)
        with self.assertRaises(NativeFormatError):
            restore_checkpoint(b"\xff\xfe")
        with self.assertRaises(NativeFormatError):
            restore_checkpoint(b"{not-json")

        record = json.loads(data.decode("utf-8"))
        record["schema_version"] = 999
        with self.assertRaises(UnsupportedSchemaVersionError):
            restore_checkpoint(self.canonical_bytes(record))

        incomplete = json.loads(data.decode("utf-8"))
        incomplete["payload"].pop("apparatus")
        self.resign(incomplete)
        with self.assertRaises(NativeValidationError):
            restore_checkpoint(self.canonical_bytes(incomplete))

    def test_duplicate_ids_and_invalid_references_fail_after_integrity(self):
        state = self.make_field()
        run_cycle(state, self.hypotheses)
        base = json.loads(
            serialize_checkpoint(state).decode("utf-8")
        )

        duplicate = deepcopy(base)
        duplicate["payload"]["streams"][1]["stream_id"] = (
            duplicate["payload"]["streams"][0]["stream_id"]
        )
        self.resign(duplicate)
        with self.assertRaisesRegex(
            NativeValidationError,
            "duplicate stream IDs|stream IDs must be unique",
        ):
            restore_checkpoint(self.canonical_bytes(duplicate))

        invalid_reference = deepcopy(base)
        invalid_reference["payload"]["relations"][0]["left_id"] = (
            "stream:absent"
        )
        self.resign(invalid_reference)
        with self.assertRaisesRegex(
            NativeValidationError,
            "endpoint",
        ):
            restore_checkpoint(
                self.canonical_bytes(invalid_reference)
            )

    def test_strict_types_and_non_json_payloads_are_not_coerced(self):
        state = self.make_field()
        state.streams[0].payload["unsupported"] = ("tuple",)
        with self.assertRaisesRegex(
            NativeValidationError,
            "non-JSON-compatible",
        ):
            serialize_checkpoint(state)

        valid = self.make_field()
        record = json.loads(
            serialize_checkpoint(valid).decode("utf-8")
        )
        record["payload"]["timestep"] = "0"
        self.resign(record)
        with self.assertRaises(NativeValidationError):
            restore_checkpoint(self.canonical_bytes(record))

    @staticmethod
    def canonical_bytes(value):
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

    @classmethod
    def resign(cls, record):
        integrity_input = {
            "schema_version": record["schema_version"],
            "payload_type": record["payload_type"],
            "payload": record["payload"],
        }
        record["integrity"]["payload_sha256"] = hashlib.sha256(
            cls.canonical_bytes(integrity_input)
        ).hexdigest()


if __name__ == "__main__":
    unittest.main()
