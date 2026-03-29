import unittest

from cbra.engine import (
    OPERATOR_SEQUENCE,
    execute_field_pipeline,
    initialize_field_state,
    run_cbra,
)


class FieldPipelineTests(unittest.TestCase):
    def test_correction_forces_field_reentry_and_removes_legacy_dispatch(self):
        prior_field = {
            "id": "prior-1",
            "selected_elements": [{"label": "older cut", "rationale": "old", "stage_source": "prior"}],
            "field_signature": {"phenomena": "older"},
            "cut_ledger": {"foregrounded": ["older cut"]},
            "notes": {},
        }
        state = initialize_field_state(
            thread_id="thread-1",
            field_id="field-1",
            user_text="Just answer in one sentence.",
            sources=[],
            citations=[],
            raw_hits=[],
            prior_field=prior_field,
            live_retrieval=None,
        )

        self.assertEqual(state.surface_flags, ["plain"])
        self.assertTrue(state.notes["surface_flags_deferred"])

        state, invariants, drift_detected, drift_kind, reintegration_stage = execute_field_pipeline(state)

        self.assertEqual(state.operator_path, OPERATOR_SEQUENCE)
        self.assertTrue(any(event.kind == "correction" for event in state.events))
        self.assertTrue(state.notes["correction_forced_reentry"])
        self.assertTrue(invariants["ok"])
        self.assertFalse(drift_detected)
        self.assertIsNone(drift_kind)
        self.assertEqual(reintegration_stage, "Field Entry")
        self.assertFalse(state.notes["surface_flags_deferred"])
        for key in ["response_formation", "turn_profile", "active_stages", "render_payload_keys"]:
            self.assertNotIn(key, state.notes)

    def test_attachment_and_canonical_events_carry_full_bodies_and_material_handles(self):
        attachment_body = "This attached document emphasizes directness and field repair through repeated detail."
        sources = [
            f"ATTACHMENT (draft.txt):\n{attachment_body}",
        ]
        raw_hits = [
            {
                "file": "CBRA_Loops_Core.md",
                "line": 12,
                "role": "ground_anchor",
                "snippet": "Field repair and directness remain visible during articulation.",
                "text": "Field repair and directness remain visible during articulation.",
                "score": 99,
            }
        ]
        state = initialize_field_state(
            thread_id="thread-2",
            field_id="field-2",
            user_text="Use the attachment and the canon together.",
            sources=sources,
            citations=["[CBRA_Loops_Core.md L12+]"],
            raw_hits=raw_hits,
            prior_field=None,
            live_retrieval=None,
        )

        attachment_event = next(event for event in state.events if event.kind == "attachment")
        retrieval_event = next(event for event in state.events if event.kind == "retrieval")
        self.assertEqual(attachment_event.payload["material_handle"], "attachment:1:draft.txt")
        self.assertEqual(attachment_event.payload["body"], attachment_body)
        self.assertTrue(retrieval_event.payload["documents"])
        self.assertIn("material_handle", retrieval_event.payload["documents"][0])
        self.assertIn("body", retrieval_event.payload["documents"][0])
        self.assertGreater(retrieval_event.payload["documents"][0]["body_chars"], 100)

        state, invariants, _, _, _ = execute_field_pipeline(state)
        self.assertTrue(invariants["ok"])
        self.assertTrue(any(item["stage_source"] == "diffractive_cross_read" for item in state.selected_elements))
        self.assertTrue(any(item.get("handle") == "attachment:1:draft.txt" for item in state.diffractive_map["materials"]))
        self.assertTrue(any(item.startswith("bridge:") for item in state.cut_ledger.foregrounded))

    def test_surface_flags_are_derived_downstream_from_field_and_cut(self):
        state = initialize_field_state(
            thread_id="thread-3",
            field_id="field-3",
            user_text="Give me only the number from this field: 42.",
            sources=[],
            citations=[],
            raw_hits=[],
            prior_field=None,
            live_retrieval=None,
        )
        self.assertEqual(state.surface_flags, ["plain"])

        state, invariants, _, _, _ = execute_field_pipeline(state)
        self.assertTrue(invariants["ok"])
        self.assertIn("number_only", state.surface_flags)
        self.assertEqual(state.articulation_output, "42")
        self.assertIn("surface_flag_status", state.notes)
        self.assertEqual(state.notes["surface_flag_status"], "derived_from_field_and_cut")
        self.assertEqual(state.notes["surface_flag_status"], "derived_from_field_and_cut")
        self.assertEqual(state.selected_elements, state.relevance_gradient["selected_elements"])


    def test_current_retrieval_is_field_inferred_not_preset_in_notes(self):
        state = initialize_field_state(
            thread_id="thread-4",
            field_id="field-4",
            user_text="What is the latest status today?",
            sources=[],
            citations=[],
            raw_hits=[],
            prior_field=None,
            live_retrieval=None,
        )
        self.assertFalse(state.notes["current_retrieval_requested"])
        self.assertEqual(state.field_signature, {})

        state, invariants, _, _, _ = execute_field_pipeline(state)
        self.assertTrue(invariants["ok"])
        self.assertTrue(state.notes["current_retrieval_requested"])
        self.assertEqual(state.turn_apparatus.enacted_pressures["timing"], "current")
        self.assertTrue(any(event.kind == "current_retrieval_request" for event in state.events))

    def test_live_retrieval_documents_enter_as_full_thickness_material(self):
        live_body = "Current external document body with enough detail to support diffractive crossing across present conditions."
        state = initialize_field_state(
            thread_id="thread-5",
            field_id="field-5",
            user_text="Cross-read the current material with the canon.",
            sources=[],
            citations=[],
            raw_hits=[],
            prior_field=None,
            live_retrieval={
                "summary": "Current status summary.",
                "summary_body": "Current status summary.",
                "summary_chars": len("Current status summary."),
                "sources": ["Example (https://example.com)"],
                "results": [{"title": "Example", "source": "Example", "url": "https://example.com", "snippet": "short snippet"}],
                "external_documents": [
                {
                    "doc_id": "extdoc:1",
                    "title": "Example",
                    "url": "https://example.com",
                    "source": "example.com",
                    "content_type": "text/html",
                    "fetch_status": "full_body",
                    "parse_status": "parsed",
                    "body": live_body,
                    "body_chars": len(live_body),
                    "sections": [{"label": "body", "text": live_body[:4000]}],
                    "chunk_handles": ["external:1:section:body"],
                    "body_hash": "",
                    "provenance": {"discovery_query": "What is the latest status today?", "candidate_rank": 1},
                }
                ],
            },
        )

        state, invariants, _, _, _ = execute_field_pipeline(state)
        self.assertTrue(invariants["ok"])

        live_event = next(event for event in state.events if event.kind == "external_document")
        self.assertGreater(live_event.payload["body_chars"], 0)
        self.assertTrue(any(item.get("handle") == "external:extdoc:1" for item in state.diffractive_map["materials"]))
        self.assertTrue(any(item.get("label") == "external:extdoc:1" for item in state.diffractive_map["candidate_elements"]))
    def test_run_cbra_debug_reports_operator_path_not_response_family(self):
        result = run_cbra(
            "Use the attached document.",
            mode="debug",
            sources=["ATTACHMENT (notes.txt):\nUse the local attachment and stay plain."],
        )
        debug = result["debug"]
        self.assertEqual(debug["operator_path"], OPERATOR_SEQUENCE)
        self.assertIn("surface_flags", debug)
        self.assertNotIn("response_formation", debug)
        self.assertNotIn("turn_profile", debug)
        self.assertNotIn("active_stages", debug)
        self.assertEqual(result["loopcycle"]["notes"]["articulation_renderer"], "field_native")
        self.assertIn("stabilization_frame", result["loopcycle"])

if __name__ == "__main__":
    unittest.main()
