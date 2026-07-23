"""Reconciled contracts from the removed dispatcher-era field pipeline.

The former tests in this path required ``OPERATOR_SEQUENCE``,
``execute_field_pipeline``, ``selected_elements``, surface-flag routing, and
other interfaces that no longer exist.  Restoring those interfaces would make
the native runtime sequential and selection-driven.

This module preserves the architectural intent that remains active:

* field conditions and constraints enter materially through streams/apparatus;
* source bodies, handles, and lineage retain their thickness;
* drift produces traceable, form-specific re-entry;
* bounded operation results may enter as material without becoming routing;
* articulation does not merely echo the question; and
* debug evidence exposes co-active operators rather than response families.

Retrieval execution, attachment parsing, and bounded document operations remain
ingress/interface responsibilities.  They are not reimplemented in the native
field merely to retain obsolete test shapes.
"""

import unittest

from cbra.native import (
    Apparatus,
    DriftKind,
    DriftSignal,
    ReentryTarget,
    RuntimeHypotheses,
    Stream,
    initialize_field,
    run_cycle,
    snapshot_field,
    update_field,
)
from cbra.native.operators import OPERATOR_ORDER


class ReconciledFieldContractTests(unittest.TestCase):
    def setUp(self):
        self.hypotheses = RuntimeHypotheses(
            articulation_emergence_floor=0.05,
            articulation_coherence_floor=0.05,
        )

    def test_drift_reentry_replaces_legacy_dispatch_state(self):
        state = self.make_related_field()
        state.pending_drifts.append(
            DriftSignal(
                kind=DriftKind.MORALIZATION,
                intensity=0.72,
                evidence=["corrective closure entered the field"],
                detected_at=state.timestep,
                source="reconciliation_test",
            )
        )

        result = run_cycle(state, self.hypotheses)

        self.assertIsNone(result.articulation)
        self.assertEqual(
            {trace.reentry_target for trace in result.reintegrations},
            {ReentryTarget.ARTICULATION},
        )
        self.assertEqual(
            result.trace.operator_order,
            OPERATOR_ORDER,
        )
        self.assertEqual(
            state.pending_reentry_targets,
            [ReentryTarget.ARTICULATION],
        )
        self.assertIsNone(state.current_cut_id)
        for legacy_name in (
            "selected_elements",
            "response_formation",
            "surface_flags",
            "turn_profile",
        ):
            self.assertFalse(hasattr(state, legacy_name))

    def test_attachment_and_canonical_material_remain_full_thickness(self):
        attachment_body = (
            "This attached document emphasizes directness and field repair "
            "through repeated material detail."
        )
        canonical_body = (
            "Diffraction traces patterns through difference and interference "
            "while preserving multiplicity."
        )
        streams = [
            Stream(
                stream_id="attachment:1",
                kind="attachment",
                payload={
                    "text": attachment_body,
                    "material_handle": "attachment:1:draft.txt",
                    "filename": "draft.txt",
                },
                participation=0.72,
                persistence=0.80,
                provenance={"source": "user_attachment"},
            ),
            Stream(
                stream_id="canonical:loops",
                kind="document",
                payload={
                    "text": canonical_body,
                    "material_handle": "canonical:CBRA_Loops_Core.md",
                },
                participation=0.74,
                persistence=0.90,
                provenance={"source": "canonical_corpus"},
            ),
        ]
        state = initialize_field(
            streams,
            apparatus=Apparatus(
                apparatus_id="apparatus:material",
                framing="cross-read available material",
                medium="text_chat",
            ),
            hypotheses=self.hypotheses,
        )

        before = snapshot_field(state)
        update_field(state, self.hypotheses)
        after = snapshot_field(state)

        expected = {
            "attachment:1": (
                attachment_body,
                "attachment:1:draft.txt",
                "user_attachment",
            ),
            "canonical:loops": (
                canonical_body,
                "canonical:CBRA_Loops_Core.md",
                "canonical_corpus",
            ),
        }
        for snapshot in (before, after):
            self.assert_material_preserved(snapshot, expected)

    def test_live_world_material_remains_full_thickness(self):
        external_body = (
            "Current external conditions participate as situated material "
            "rather than authoritative truth."
        )
        state = initialize_field(
            [
                Stream(
                    stream_id="external:1",
                    kind="live_world",
                    payload={
                        "text": external_body,
                        "material_handle": "external:extdoc1",
                        "url": "https://example.com/current",
                    },
                    participation=0.70,
                    persistence=0.75,
                    provenance={"source": "current_external_document"},
                )
            ],
            apparatus=Apparatus(
                apparatus_id="apparatus:external",
                framing="current situated material",
                medium="text_chat",
            ),
            hypotheses=self.hypotheses,
        )

        before = snapshot_field(state)
        update_field(state, self.hypotheses)
        after = snapshot_field(state)
        expected = {
            "external:1": (
                external_body,
                "external:extdoc1",
                "current_external_document",
            ),
        }
        for snapshot in (before, after):
            self.assert_material_preserved(snapshot, expected)
            external = next(
                stream
                for stream in snapshot.streams
                if stream.stream_id == "external:1"
            )
            self.assertEqual(
                external.payload["url"],
                "https://example.com/current",
            )

    def test_surface_constraints_enter_through_apparatus_not_flags(self):
        apparatus = Apparatus(
            apparatus_id="apparatus:conditions",
            framing="bounded inquiry",
            medium="text_chat",
            constraints=["one sentence", "number only"],
        )
        state = initialize_field(
            [
                Stream(
                    stream_id="user:conditions",
                    kind="user_input",
                    payload={"text": "Give the current count."},
                    participation=0.78,
                    persistence=0.80,
                )
            ],
            apparatus=apparatus,
            hypotheses=self.hypotheses,
        )

        snapshot = snapshot_field(state)

        self.assertEqual(
            snapshot.apparatus.constraints,
            ["one sentence", "number only"],
        )
        facets = {
            stream.payload.get("facet"): stream.payload.get("values")
            for stream in snapshot.streams
            if stream.kind == "apparatus"
        }
        self.assertEqual(
            facets["constraints"],
            ["one sentence", "number only"],
        )
        self.assertNotIn("surface_flags", snapshot.__dataclass_fields__)

    def test_current_timing_enters_through_apparatus_not_hidden_flag(self):
        state = initialize_field(
            [
                Stream(
                    stream_id="user:current",
                    kind="user_input",
                    payload={"text": "What is the latest status today?"},
                    participation=0.78,
                    persistence=0.80,
                )
            ],
            apparatus=Apparatus(
                apparatus_id="apparatus:current",
                framing="current inquiry",
                medium="text_chat",
                tools=["current-world retrieval"],
                temporal_pressures=["current", "today"],
            ),
            hypotheses=self.hypotheses,
        )

        snapshot = snapshot_field(state)
        facets = {
            stream.payload.get("facet"): stream.payload.get("values")
            for stream in snapshot.streams
            if stream.kind == "apparatus"
        }

        self.assertEqual(
            snapshot.apparatus.temporal_pressures,
            ["current", "today"],
        )
        self.assertEqual(facets["temporal_pressures"], ["current", "today"])
        self.assertNotIn(
            "current_retrieval_requested",
            snapshot.__dataclass_fields__,
        )

    def test_bounded_operation_result_enters_as_material_not_routing(self):
        state = initialize_field(
            [
                Stream(
                    stream_id="user:count",
                    kind="user_input",
                    payload={
                        "text": (
                            "How many times is intra-action used in the "
                            "attached document?"
                        )
                    },
                    participation=0.72,
                    persistence=0.80,
                ),
                Stream(
                    stream_id="operation:count:1",
                    kind="attachment_operation_result",
                    payload={
                        "text": "3",
                        "operation": "count",
                        "term": "intra-action",
                        "value": 3,
                        "material_handle": "attachment:1:draft.txt",
                    },
                    participation=0.76,
                    persistence=0.80,
                    provenance={"source": "bounded_document_operation"},
                ),
            ],
            apparatus=Apparatus(
                apparatus_id="apparatus:count",
                framing="bounded attachment operation",
                medium="text_chat",
                tools=["attachment word count"],
            ),
            hypotheses=self.hypotheses,
        )

        operation = state.stream("operation:count:1")

        self.assertIsNotNone(operation)
        self.assertEqual(operation.payload["operation"], "count")
        self.assertEqual(operation.payload["term"], "intra-action")
        self.assertEqual(operation.payload["value"], 3)
        self.assertEqual(
            operation.payload["material_handle"],
            "attachment:1:draft.txt",
        )
        self.assertFalse(hasattr(state, "selected_elements"))
        self.assertFalse(hasattr(state, "response_formation"))

    def test_definition_articulation_uses_ground_without_question_echo(self):
        question = "What is diffraction?"
        state = initialize_field(
            [
                Stream(
                    stream_id="user:definition",
                    kind="user_input",
                    payload={"text": question},
                    participation=0.74,
                    persistence=0.80,
                ),
                Stream(
                    stream_id="ontology:diffraction",
                    kind="ontology",
                    payload={
                        "text": (
                            "Diffraction traces patterns through difference "
                            "and interference while preserving multiplicity."
                        )
                    },
                    participation=0.82,
                    persistence=0.90,
                    provenance={"source": "canonical_ground"},
                ),
            ],
            apparatus=Apparatus(
                apparatus_id="apparatus:definition",
                framing="definition inquiry",
                medium="text_chat",
            ),
            hypotheses=self.hypotheses,
        )

        result = run_cycle(state, self.hypotheses)

        self.assertIsNotNone(result.articulation)
        text = result.articulation.text.lower()
        self.assertIn("diffraction traces patterns", text)
        self.assertNotIn(question.lower(), text)
        self.assertNotIn("selected_elements", text)
        self.assertNotIn("response formation", text)

    def test_trace_reports_coactive_operators_not_response_families(self):
        state = self.make_related_field()

        trace = update_field(state, self.hypotheses)

        self.assertTrue(trace.coactive)
        self.assertEqual(trace.operator_order, OPERATOR_ORDER)
        self.assertEqual(
            {delta.operator_name for delta in trace.deltas},
            set(OPERATOR_ORDER),
        )
        for legacy_name in (
            "response_formation",
            "turn_profile",
            "active_stages",
            "render_payload_keys",
        ):
            self.assertFalse(hasattr(trace, legacy_name))

    def assert_material_preserved(self, snapshot, expected):
        material = {
            stream.stream_id: stream
            for stream in snapshot.streams
            if stream.stream_id in expected
        }
        self.assertEqual(set(material), set(expected))
        for stream_id, (body, handle, source) in expected.items():
            self.assertEqual(material[stream_id].payload["text"], body)
            self.assertEqual(
                material[stream_id].payload["material_handle"],
                handle,
            )
            self.assertEqual(
                material[stream_id].provenance["source"],
                source,
            )

    def make_related_field(self):
        return initialize_field(
            [
                Stream(
                    stream_id="user:1",
                    kind="user_input",
                    payload={"text": "cedar soil holds moisture"},
                    participation=0.74,
                    persistence=0.80,
                ),
                Stream(
                    stream_id="memory:1",
                    kind="memory",
                    payload={"text": "cedar roots shelter soil"},
                    participation=0.72,
                    persistence=0.80,
                ),
            ],
            apparatus=Apparatus(
                apparatus_id="apparatus:test",
                framing="shared inquiry",
                medium="text_chat",
            ),
            hypotheses=self.hypotheses,
        )


if __name__ == "__main__":
    unittest.main()
