import unittest

from cbra_engine import OPERATOR_SEQUENCE, articulate, execute_field_pipeline, initialize_field_state, run_cbra


class FieldPipelineTests(unittest.TestCase):
    def test_surface_flags_start_deferred_and_not_lexically_assigned(self):
        state = initialize_field_state(
            thread_id="thread-1",
            field_id="field-1",
            user_text="Just answer in one sentence.",
            sources=[],
            citations=[],
            raw_hits=[],
            prior_field={"id": "prior-1"},
            live_retrieval=None,
        )
        self.assertEqual(state.surface_flags, ["plain"])
        self.assertTrue(state.notes["surface_flags_deferred"])
        self.assertEqual(state.notes["surface_flag_status"], "deferred_until_articulation")
        self.assertEqual(state.turn_apparatus.apparatus_kind, "turn_pressure_apparatus")
        self.assertTrue(state.turn_apparatus.enacted_pressures["correction_requested"])

    def test_current_retrieval_enters_as_external_document_bodies_not_summaries(self):
        live_retrieval = {
            "status": "discovered",
            "candidate_urls": ["https://example.com/status"],
            "document_ids": ["doc-1"],
            "external_documents": [
                {
                    "doc_id": "doc-1",
                    "url": "https://example.com/status",
                    "title": "Status Page",
                    "source": "example.com",
                    "content_type": "text/html",
                    "fetch_status": "fetched",
                    "parse_status": "parsed",
                    "body": "Current status page body with full text and current service notes.",
                    "body_chars": 61,
                    "sections": [{"label": "body", "text": "Current status page body with full text and current service notes."}],
                    "chunk_handles": ["external:doc-1:section:body"],
                    "body_hash": "hash-1",
                    "provenance": {"discovery_query": "current status"},
                }
            ],
        }
        state = initialize_field_state(
            thread_id="thread-2",
            field_id="field-2",
            user_text="What is the latest status today?",
            sources=[],
            citations=[],
            raw_hits=[],
            prior_field=None,
            live_retrieval=live_retrieval,
        )
        self.assertTrue(any(event.kind == "external_document" for event in state.events))
        ext_event = next(event for event in state.events if event.kind == "external_document")
        self.assertIn("body", ext_event.payload)
        self.assertNotIn("summary", ext_event.payload)
        state, invariants, _, _, _ = execute_field_pipeline(state)
        self.assertTrue(invariants["ok"])
        self.assertTrue(state.notes["current_retrieval_requested"])
        self.assertEqual(state.external_document_apparatus.document_ids, ["doc-1"])

    def test_articulation_is_field_native_and_records_stabilization_objects(self):
        sources = ["ATTACHMENT (draft.txt):\nThis attached document emphasizes directness and field repair."]
        state = initialize_field_state(
            thread_id="thread-3",
            field_id="field-3",
            user_text="Use the attachment and answer directly.",
            sources=sources,
            citations=[],
            raw_hits=[],
            prior_field=None,
            live_retrieval=None,
        )
        state, invariants, _, _, _ = execute_field_pipeline(state)
        self.assertTrue(invariants["ok"])
        self.assertEqual(state.operator_path, OPERATOR_SEQUENCE)
        self.assertEqual(state.notes["surface_flag_status"], "derived_from_field_and_cut")
        self.assertTrue(state.stabilization_frame.mode)
        self.assertIsNotNone(state.situated_expression)
        self.assertNotIn("render_payload_keys", state.notes)
        self.assertEqual(state.notes["renderer_mode"], "field_native_stabilization")

    def test_same_wording_can_yield_different_surface_flags_from_different_cuts(self):
        narrow = initialize_field_state(
            thread_id="thread-4",
            field_id="field-4",
            user_text="Answer this directly.",
            sources=[],
            citations=[],
            raw_hits=[],
            prior_field=None,
            live_retrieval=None,
        )
        narrow.selected_elements = [{"label": "42", "rationale": "stable scalar", "stage_source": "manual"}]
        narrow.cut_ledger.foregrounded = ["42"]
        narrow.relevance_gradient = {"selected_elements": narrow.selected_elements}
        narrow = articulate(narrow)
        self.assertIn("number_only", narrow.surface_flags)

        open_state = initialize_field_state(
            thread_id="thread-5",
            field_id="field-5",
            user_text="Answer this directly.",
            sources=[],
            citations=[],
            raw_hits=[],
            prior_field=None,
            live_retrieval=None,
        )
        open_state.selected_elements = [
            {"label": "bridge:user<->canon", "rationale": "cross-reading user and canon", "stage_source": "diffractive_cross_read"},
            {"label": "bridge:user<->attachment", "rationale": "cross-reading user and attachment", "stage_source": "diffractive_cross_read"},
        ]
        open_state.cut_ledger.foregrounded = ["bridge:user<->canon", "bridge:user<->attachment"]
        open_state.cut_ledger.held_open = ["bridge:canon<->attachment"]
        open_state.relevance_gradient = {"selected_elements": open_state.selected_elements}
        open_state = articulate(open_state)
        self.assertNotIn("number_only", open_state.surface_flags)
        self.assertIn("operative", open_state.surface_flags)

    def test_debug_and_loopcycle_expose_external_document_apparatus_and_stabilization(self):
        result = run_cbra(
            "What is the latest status today?",
            mode="debug",
            sources=["ATTACHMENT (notes.txt):\nKeep the local attachment visible."],
        )
        debug = result["debug"]
        loopcycle = result["loopcycle"]
        self.assertEqual(debug["operator_path"], OPERATOR_SEQUENCE)
        self.assertIn("external_document_apparatus", debug)
        self.assertIn("stabilization_frame", debug)
        self.assertIn("situated_expression", debug)
        self.assertIn("external_document_apparatus", loopcycle)
        self.assertIn("stabilization_frame", loopcycle)
        self.assertIn("situated_expression", loopcycle)


if __name__ == "__main__":
    unittest.main()
