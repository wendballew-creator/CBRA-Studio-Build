import unittest

from cbra.engine import (
    OPERATOR_SEQUENCE,
    _state_patch,
    articulate,
    diffractive_read,
    execute_field_pipeline,
    field_entry,
    initialize_field_state,
    notice,
    relational_frame,
    run_cbra,
    situated_relevance_select,
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
    def test_attachment_count_operation_bypasses_generic_diffraction(self):
        attachment_body = "intra-action matters. Intra-action continues. Another intra-action appears here."
        state = initialize_field_state(
            thread_id="thread-6",
            field_id="field-6",
            user_text="How many times is the word intra-action used in the attached document?",
            sources=[f"ATTACHMENT (draft.txt):\n{attachment_body}"],
            citations=[],
            raw_hits=[],
            prior_field=None,
            live_retrieval=None,
        )

        state, invariants, _, _, _ = execute_field_pipeline(state)
        self.assertTrue(invariants["ok"])

        operation_event = next(event for event in state.events if event.kind == "attachment_operation_result")
        self.assertEqual(operation_event.payload["operation"], "count")
        self.assertEqual(operation_event.payload["term"], "intra-action")
        self.assertEqual(operation_event.payload["value"], 3)

        self.assertTrue(state.notes["attachment_operation_resolved"])
        self.assertEqual(state.articulation_output, "3")
        self.assertIn("number_only", state.surface_flags)
        self.assertEqual(state.selected_elements, state.relevance_gradient["selected_elements"])
        self.assertEqual(state.operator_path, OPERATOR_SEQUENCE)
    def test_run_cbra_does_not_auto_ground_general_source_less_turns(self):
        result = run_cbra("What is diffraction?", mode="debug")
        self.assertEqual(result["debug"]["sources_used"], [])
        self.assertEqual(result["debug"]["retrieval_hits"], [])
        self.assertFalse(any(event.get("kind") == "retrieval" for event in result["debug"]["events"]))
        self.assertEqual(result["loopcycle"]["notes"]["grounding_scope"], "world_or_user_material")

    def test_run_cbra_runtime_design_turn_still_grounds_canon(self):
        result = run_cbra("In CBRA runtime design, what does the glossary say about diffraction?", mode="debug")
        self.assertTrue(result["debug"]["sources_used"])
        self.assertTrue(result["debug"]["retrieval_hits"])
        self.assertTrue(any(event.get("kind") == "retrieval" for event in result["debug"]["events"]))
        self.assertEqual(result["loopcycle"]["notes"]["grounding_scope"], "runtime_design")

    def test_run_cbra_does_not_auto_supplement_attachment_with_canon_without_runtime_scope(self):
        result = run_cbra(
            "What is diffraction in the attached document?",
            mode="debug",
            sources=["ATTACHMENT (notes.txt):\\nDiffraction is a physics term about wave interference."],
        )
        self.assertEqual(result["debug"]["sources_used"], [])
        self.assertEqual(result["debug"]["retrieval_hits"], [])
        self.assertFalse(any(event.get("kind") == "retrieval" for event in result["debug"]["events"]))
        self.assertEqual(result["loopcycle"]["notes"]["grounding_scope"], "world_or_user_material")
    def test_run_cbra_treats_attachment_as_field_matter_while_ontology_remains_ground(self):
        result = run_cbra(
            "What is diffraction in the attached document?",
            mode="debug",
            sources=[
                "ATTACHMENT (notes.txt):\n"
                "Diffraction traces patterns across difference and keeps multiplicity visible."
            ],
        )

        self.assertEqual(result["debug"]["sources_used"], [])
        self.assertEqual(result["debug"]["retrieval_hits"], [])
        self.assertEqual(
            result["loopcycle"]["notes"]["grounding_scope"],
            "world_or_user_material",
        )
        self.assertEqual(
            result["loopcycle"]["field_signature"]["material_lineages"],
            ["attachment"],
        )
        self.assertEqual(
            result["loopcycle"]["field_signature"]["ontology_kind"],
            result["loopcycle"]["notes"]["ontology_kind"],
        )
        self.assertEqual(
            result["debug"]["attachments"]["active_attachment_names"],
            ["notes.txt"],
        )

    def test_non_repair_turn_does_not_materialize_prior_field_state(self):
        prior_field = {
            "id": "prior-world-1",
            "selected_elements": [{"label": "older cut", "rationale": "old", "stage_source": "prior"}],
            "field_signature": {"phenomena": "older"},
            "cut_ledger": {"foregrounded": ["older cut"]},
            "notes": {},
        }
        state = initialize_field_state(
            thread_id="thread-world-1",
            field_id="field-world-1",
            user_text="What is diffraction?",
            sources=[],
            citations=[],
            raw_hits=[],
            prior_field=prior_field,
            live_retrieval=None,
        )
        self.assertFalse(any(event.kind == "prior_field_state" for event in state.events))
        self.assertFalse(state.notes["prior_field_materialized"])
        self.assertIsNone(state.prior_field_id)

    def test_correction_turn_still_materializes_prior_field_state(self):
        prior_field = {
            "id": "prior-world-2",
            "selected_elements": [{"label": "older cut", "rationale": "old", "stage_source": "prior"}],
            "field_signature": {"phenomena": "older"},
            "cut_ledger": {"foregrounded": ["older cut"]},
            "notes": {},
        }
        state = initialize_field_state(
            thread_id="thread-world-2",
            field_id="field-world-2",
            user_text="You misunderstood my last response. Rewrite it.",
            sources=[],
            citations=[],
            raw_hits=[],
            prior_field=prior_field,
            live_retrieval=None,
        )
        self.assertTrue(any(event.kind == "prior_field_state" for event in state.events))
        self.assertTrue(state.notes["prior_field_materialized"])
        self.assertEqual(state.prior_field_id, "prior-world-2")
    def test_definition_turn_traces_inquiry_pressure_in_turn_apparatus(self):
        state = initialize_field_state(
            thread_id="thread-inquiry-1",
            field_id="field-inquiry-1",
            user_text="What is diffraction?",
            sources=[],
            citations=[],
            raw_hits=[],
            prior_field=None,
            live_retrieval=None,
        )
        self.assertEqual(state.turn_apparatus.enacted_pressures["inquiry_pressure"], "definition")
        self.assertEqual(state.turn_apparatus.context_inputs["inquiry_pressure"], "definition")
        self.assertTrue(state.turn_apparatus.signal_register["inquiry_signals"]["definition_request"])
        self.assertTrue(
            any(
                item.get("pressure") == "inquiry_pressure"
                for item in state.turn_apparatus.boundary_logic
            )
        )
    def test_definition_questions_prefer_direct_material_over_prior_field_bridge(self):
        prior_field = {
            "id": "prior-6",
            "selected_elements": [
                {
                    "label": "bridge:canonical:CBRA_Loops_Core.md<->prior_field:snapshot",
                    "rationale": "older bridge",
                    "stage_source": "diffractive_cross_read",
                }
            ],
            "field_signature": {"phenomena": "older"},
            "cut_ledger": {"foregrounded": ["bridge:canonical:CBRA_Loops_Core.md<->prior_field:snapshot"]},
            "notes": {},
        }
        raw_hits = [
            {
                "file": "CBRA_Glossary_v3.md",
                "line": 40,
                "role": "operator_anchor",
                "snippet": "Diffraction traces patterns across difference.",
                "text": "Diffraction traces patterns across difference. It reveals interference and relational complexity while preserving multiplicity.",
                "score": 120,
            },
            {
                "file": "CBRA_Loops_Core.md",
                "line": 48,
                "role": "ground_anchor",
                "snippet": "Trace pattern formation through difference and interference.",
                "text": "Trace pattern formation through difference and interference across available material. Preserve multiplicity.",
                "score": 90,
            },
        ]
        state = initialize_field_state(
            thread_id="thread-7",
            field_id="field-7",
            user_text="What is diffraction?",
            sources=[],
            citations=["[CBRA_Glossary_v3.md L40+]", "[CBRA_Loops_Core.md L48+]"],
            raw_hits=raw_hits,
            prior_field=prior_field,
            live_retrieval=None,
        )

        state, invariants, _, _, _ = execute_field_pipeline(state)
        self.assertTrue(invariants["ok"])

        bundle = state.relevance_gradient.get("grouped_selection_bundle", {})
        self.assertEqual(state.turn_apparatus.enacted_pressures["inquiry_pressure"], "definition")
        self.assertTrue(bundle.get("direct_material"))
        self.assertFalse(
            any("prior_field:snapshot" in item.get("label", "") for item in state.selected_elements)
        )
    def test_movement_language_stays_out_of_answer_text_by_default(self):
        attachment_body = "This attached document emphasizes directness and field repair through repeated detail."
        sources = [f"ATTACHMENT (draft.txt):\n{attachment_body}"]
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
            thread_id="thread-8",
            field_id="field-8",
            user_text="Explain the attachment with the canon.",
            sources=sources,
            citations=["[CBRA_Loops_Core.md L12+]"],
            raw_hits=raw_hits,
            prior_field=None,
            live_retrieval=None,
        )

        state, invariants, _, _, _ = execute_field_pipeline(state)
        self.assertTrue(invariants["ok"])
        self.assertEqual(state.stabilization_frame.mode, "operative_sentence")
        self.assertTrue(state.situated_expression.movement_note)
        self.assertNotIn("Keep ", state.articulation_output)
        self.assertNotIn("Move from the foregrounded cut without forcing full closure.", state.articulation_output)
    def test_ontology_ground_is_installed_and_persisted_in_state_patch(self):
        state = initialize_field_state(
            thread_id="thread-ontology-1",
            field_id="field-ontology-1",
            user_text="What is diffraction?",
            sources=[],
            citations=[],
            raw_hits=[],
            prior_field=None,
            live_retrieval=None,
        )

        self.assertTrue(state.notes["ontology_ground_installed"])
        self.assertEqual(state.notes["ontology_kind"], state.ontology_ground.ontology_kind)
        self.assertTrue(state.ontology_ground.principles["entanglement_primary"])
        self.assertTrue(state.ontology_ground.principles["diffraction_pattern_mapping"])

        patch = _state_patch(state)
        self.assertIn("ontology_ground", patch)
        self.assertEqual(patch["ontology_ground"]["ontology_kind"], state.ontology_ground.ontology_kind)
        self.assertTrue(patch["ontology_ground"]["principles"]["entanglement_primary"])
        self.assertTrue(patch["ontology_ground"]["principles"]["diffraction_pattern_mapping"])
    def test_field_entry_reads_ontology_ground_into_field_signature(self):
        state = initialize_field_state(
            thread_id="thread-field-entry-1",
            field_id="field-field-entry-1",
            user_text="What is diffraction?",
            sources=[],
            citations=[],
            raw_hits=[],
            prior_field=None,
            live_retrieval=None,
        )

        state = field_entry(state)

        self.assertTrue(state.notes["ontology_ground_read_in_field_entry"])
        self.assertEqual(
            state.field_signature["ontology_kind"],
            state.ontology_ground.ontology_kind,
        )
        self.assertTrue(
            state.field_signature["ontology_principles"]["entanglement_primary"]
        )
        self.assertTrue(
            state.field_signature["ontology_principles"]["diffraction_pattern_mapping"]
        )
        self.assertEqual(state.field_signature["material_lineages"], ["user_turn"])
        self.assertIn(
            "ontology ground is active before material interpretation",
            state.field_signature["constraints"],
        )

    def test_notice_reads_ontology_ground_into_noticing_register(self):
        state = initialize_field_state(
            thread_id="thread-notice-1",
            field_id="field-notice-1",
            user_text="What is diffraction?",
            sources=[],
            citations=[],
            raw_hits=[],
            prior_field=None,
            live_retrieval=None,
        )

        state = field_entry(state)
        state = notice(state)

        self.assertTrue(state.notes["ontology_ground_read_in_notice"])
        self.assertEqual(
            state.noticing_register["ontology_kind"],
            state.ontology_ground.ontology_kind,
        )
        self.assertTrue(
            state.noticing_register["ontology_principles"]["entanglement_primary"]
        )
        self.assertTrue(
            state.noticing_register["ontology_principles"]["diffraction_pattern_mapping"]
        )
        self.assertEqual(state.noticing_register["material_lineages"], ["user_turn"])
        self.assertIn(
            "entanglement is active as pre-interpretive ground",
            state.noticing_register["signals"],
        )
        self.assertIn(
            "difference is available for pattern tracing without consolidation",
            state.noticing_register["signals"],
        )
    def test_relational_frame_reads_ontology_ground_into_relational_map(self):
        state = initialize_field_state(
            thread_id="thread-relational-1",
            field_id="field-relational-1",
            user_text="What is diffraction?",
            sources=[],
            citations=[],
            raw_hits=[],
            prior_field=None,
            live_retrieval=None,
        )

        state = field_entry(state)
        state = notice(state)
        state = relational_frame(state)

        self.assertTrue(state.notes["ontology_ground_read_in_relational_frame"])
        self.assertEqual(
            state.relational_map["ontology_kind"],
            state.ontology_ground.ontology_kind,
        )
        self.assertTrue(
            state.relational_map["ontology_principles"]["entanglement_primary"]
        )
        self.assertTrue(
            state.relational_map["ontology_principles"]["diffraction_pattern_mapping"]
        )
        self.assertIn("entangled_field", state.relational_map["agency"])
        self.assertIn(
            "identity is treated as emergent within relation",
            state.relational_map["constraints"],
        )
        self.assertTrue(
            state.relational_map["capacity"]["field_conditioned_reasoning"]
        )
        self.assertTrue(
            state.relational_map["consequence_visibility"]["distributed_consequence"]
        )
    def test_diffractive_read_reads_ontology_ground_into_diffractive_map(self):
        state = initialize_field_state(
            thread_id="thread-diffraction-1",
            field_id="field-diffraction-1",
            user_text="What is diffraction?",
            sources=[
                "ATTACHMENT (notes.txt):\nDiffraction traces patterns across difference."
            ],
            citations=[],
            raw_hits=[],
            prior_field=None,
            live_retrieval=None,
        )

        state = field_entry(state)
        state = notice(state)
        state = relational_frame(state)
        state = diffractive_read(state)

        self.assertTrue(state.notes["ontology_ground_read_in_diffractive_read"])
        self.assertEqual(
            state.diffractive_map["ontology_kind"],
            state.ontology_ground.ontology_kind,
        )
        self.assertTrue(
            state.diffractive_map["ontology_principles"]["entanglement_primary"]
        )
        self.assertTrue(
            state.diffractive_map["ontology_principles"]["diffraction_pattern_mapping"]
        )
        self.assertTrue(state.diffractive_map["candidate_elements"])
        self.assertTrue(
            any(
                item["stage_source"] == "diffractive_material"
                for item in state.diffractive_map["candidate_elements"]
            )
        )
    def test_situated_relevance_select_reads_ontology_ground_into_relevance_gradient(self):
        state = initialize_field_state(
            thread_id="thread-selection-1",
            field_id="field-selection-1",
            user_text="What is diffraction?",
            sources=[
                "ATTACHMENT (notes.txt):\nDiffraction traces patterns across difference."
            ],
            citations=[],
            raw_hits=[],
            prior_field=None,
            live_retrieval=None,
        )

        state = field_entry(state)
        state = notice(state)
        state = relational_frame(state)
        state = diffractive_read(state)
        state = situated_relevance_select(state)

        self.assertTrue(state.notes["ontology_ground_read_in_situated_relevance_select"])
        self.assertEqual(
            state.relevance_gradient["ontology_kind"],
            state.ontology_ground.ontology_kind,
        )
        self.assertTrue(
            state.relevance_gradient["ontology_principles"]["entanglement_primary"]
        )
        self.assertTrue(
            state.relevance_gradient["ontology_principles"]["diffraction_pattern_mapping"]
        )
        bundle = state.relevance_gradient["grouped_selection_bundle"]
        self.assertEqual(bundle["ontology_kind"], state.ontology_ground.ontology_kind)
        self.assertTrue(bundle["multiplicity_preserved"])
        self.assertIn(bundle["movement_priority"], ["movement", "movement_and_multiplicity"])
        self.assertEqual(state.selected_elements, state.relevance_gradient["selected_elements"])
    def test_articulate_reads_ontology_ground_and_keeps_held_open_language(self):
        state = initialize_field_state(
            thread_id="thread-articulate-1",
            field_id="field-articulate-1",
            user_text="What is diffraction?",
            sources=[
                "ATTACHMENT (notes.txt):\nDiffraction traces patterns across difference."
            ],
            citations=[],
            raw_hits=[],
            prior_field=None,
            live_retrieval=None,
        )

        state = field_entry(state)
        state = notice(state)
        state = relational_frame(state)
        state = diffractive_read(state)
        state = situated_relevance_select(state)
        state = articulate(state)

        self.assertTrue(state.notes["ontology_ground_read_in_articulate"])
        self.assertIn(
            "keep articulation livable across affected systems",
            state.stabilization_frame.language_constraints,
        )
        self.assertIn(
            "do not collapse held-open multiplicity into one closure",
            state.stabilization_frame.language_constraints,
        )
        self.assertNotIn("Keep ", state.articulation_output)
        self.assertNotIn(
            "Move from the foregrounded cut without forcing full closure.",
            state.articulation_output,
        )

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
