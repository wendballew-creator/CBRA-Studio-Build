from pathlib import Path
import unittest

from cbra_runtime.runtime.field_state import Stream
from cbra_runtime.runtime.runtime_loop import initialize_field, run_until_articulation
from cbra_runtime.runtime.operators import step_field
from cbra_runtime.articulation.decoder import (
    decode_articulation,
    choose_articulation_stock,
)
from cbra_runtime.articulation.readiness import ready_to_articulate



class TestDynamicalFieldRuntime(unittest.TestCase):
    def test_concept_question_reaches_articulation_without_pipeline_selection(self):
        streams = [
            Stream(
                stream_id="s_user",
                kind="user_turn",
                payload={"text": "What is diffraction?"},
                participation=0.85,
                persistence=0.90,
            ),
            Stream(
                stream_id="s_diffraction",
                kind="ontology",
                payload={"concept": "diffraction"},
                participation=0.70,
                persistence=0.95,
            ),
            Stream(
                stream_id="s_play",
                kind="ontology",
                payload={"concept": "play"},
                participation=0.40,
                persistence=0.85,
            ),
        ]

        state = initialize_field(streams)
        self.assertFalse(ready_to_articulate(state))

        text, traces, reintegrations, history = run_until_articulation(state, max_steps=6)

        self.assertTrue(text)
        self.assertIn("diffraction", text.lower())
        self.assertEqual("plain_conceptual", choose_articulation_stock(state))
        self.assertGreaterEqual(len(traces), 1)
        self.assertEqual(len(history), len(traces))
        self.assertEqual(state.timestep, len(traces))
        self.assertTrue(state.emergent_form.lead_stream_ids)
        self.assertGreaterEqual(state.field_values.coherence, 0.45)
        self.assertGreaterEqual(state.field_values.emergence_level, 0.55)

        self.assertFalse(hasattr(state, "selected_elements"))
        self.assertFalse(hasattr(state, "relevance_gradient"))

        operator_names = [delta.operator_name for trace in traces for delta in trace.deltas]
        self.assertIn("intra_action", operator_names)
        self.assertIn("diffraction", operator_names)
        self.assertIn("becoming", operator_names)
        self.assertIsInstance(reintegrations, list)
        self.assertEqual(len(history), len(traces))
        self.assertTrue(all(h.operator_names for h in history))
        self.assertIn('coherence', history[-1].after_values)
        self.assertIn('foregrounded', history[-1].cut_after)
        self.assertEqual(text, decode_articulation(state))

    def test_live_world_stock_is_selected_without_changing_field_step_logic(self):
        streams = [
            Stream(
                stream_id="s_user",
                kind="user_turn",
                payload={"text": "What is happening in Atlanta tomorrow?"},
                participation=0.88,
                persistence=0.92,
            ),
            Stream(
                stream_id="s_atlanta",
                kind="live_world",
                payload={"label": "Atlanta forecast", "place": "Atlanta", "time": "tomorrow"},
                participation=0.82,
                persistence=0.90,
            ),
            Stream(
                stream_id="s_timing",
                kind="timing",
                payload={"time": "tomorrow"},
                participation=0.60,
                persistence=0.95,
            ),
        ]

        state = initialize_field(streams)
        text, traces, _, history = run_until_articulation(state, max_steps=6)

        self.assertEqual("situated_live_world", choose_articulation_stock(state))
        self.assertIn("situated", text.lower())
        self.assertIn("atlanta", text.lower())
        self.assertIn("tomorrow", text.lower())
        self.assertGreaterEqual(len(traces), 1)


from cbra_runtime.runtime.history_inspector import (
    history_to_rows,
    render_history,
    render_history_step,
)

class TestHistoryInspector(unittest.TestCase):
    def test_history_inspector_renders_readable_steps(self):
        streams = [
            Stream(
                stream_id="s_user",
                kind="user_turn",
                payload={"text": "What is diffraction?"},
                participation=0.85,
                persistence=0.90,
            ),
            Stream(
                stream_id="s_diffraction",
                kind="ontology",
                payload={"concept": "diffraction"},
                participation=0.70,
                persistence=0.95,
            ),
        ]
        state = initialize_field(streams)
        _, traces, _, history = run_until_articulation(state, max_steps=4)

        rows = history_to_rows(history)
        self.assertEqual(len(rows), len(history))
        self.assertIn("coherence_after", rows[0])

        step_text = render_history_step(history[0])
        self.assertIn("Step", step_text)
        self.assertIn("field_values:", step_text)

        full_text = render_history(history)
        self.assertIn("Field History", full_text)
        self.assertIn("steps:", full_text)
        self.assertIn("diffraction", full_text.lower())


from cbra_runtime.runtime.history_export import (
    history_entry_to_dict,
    export_history,
    export_history_payload,
)

class TestHistoryExport(unittest.TestCase):
    def test_history_export_is_json_safe_and_stable(self):
        streams = [
            Stream(
                stream_id="s_user",
                kind="user_turn",
                payload={"text": "What is diffraction?"},
                participation=0.85,
                persistence=0.90,
            ),
            Stream(
                stream_id="s_diffraction",
                kind="ontology",
                payload={"concept": "diffraction"},
                participation=0.70,
                persistence=0.95,
            ),
        ]
        state = initialize_field(streams)
        _, _, _, history = run_until_articulation(state, max_steps=4)

        entry_dict = history_entry_to_dict(history[0])
        self.assertIn("timestep", entry_dict)
        self.assertIn("before_values", entry_dict)
        self.assertIsInstance(entry_dict["operator_names"], list)

        exported = export_history(history)
        self.assertEqual(len(exported), len(history))
        self.assertIn("after_values", exported[-1])

        payload = export_history_payload(history, field_id=state.field_id, final_timestep=state.timestep)
        self.assertEqual(payload["field_id"], state.field_id)
        self.assertEqual(payload["final_timestep"], state.timestep)
        self.assertEqual(payload["step_count"], len(history))
        self.assertEqual(len(payload["history"]), len(history))


from cbra_runtime.runtime.snapshot import (
    build_snapshot_payload,
    save_snapshot,
    load_snapshot,
)

class TestSnapshotPersistence(unittest.TestCase):
    def test_snapshot_persists_field_state_and_history_together(self):
        streams = [
            Stream(
                stream_id="s_user",
                kind="user_turn",
                payload={"text": "What is diffraction?"},
                participation=0.85,
                persistence=0.90,
            ),
            Stream(
                stream_id="s_diffraction",
                kind="ontology",
                payload={"concept": "diffraction"},
                participation=0.70,
                persistence=0.95,
            ),
        ]
        state = initialize_field(streams)
        _, _, _, history = run_until_articulation(state, max_steps=4)

        payload = build_snapshot_payload(state, history)
        self.assertIn("field_state", payload)
        self.assertIn("history", payload)
        self.assertEqual(payload["field_state"]["field_id"], state.field_id)
        self.assertEqual(payload["history"]["field_id"], state.field_id)

        snapshot_path = Path("/mnt/data/cbra_runtime/tests/tmp_snapshot.json")
        saved = save_snapshot(state, history, snapshot_path)
        self.assertTrue(saved.exists())

        loaded = load_snapshot(saved)
        self.assertEqual(loaded["field_state"]["field_id"], state.field_id)
        self.assertEqual(loaded["history"]["step_count"], len(history))
        self.assertEqual(loaded["history"]["final_timestep"], state.timestep)


from cbra_runtime.runtime.snapshot import (
    restore_field_state,
    load_and_restore_snapshot,
)

class TestSnapshotRestore(unittest.TestCase):
    def test_restore_helper_reconstructs_live_field_state(self):
        streams = [
            Stream(
                stream_id="s_user",
                kind="user_turn",
                payload={"text": "What is diffraction?"},
                participation=0.85,
                persistence=0.90,
            ),
            Stream(
                stream_id="s_diffraction",
                kind="ontology",
                payload={"concept": "diffraction"},
                participation=0.70,
                persistence=0.95,
            ),
        ]
        state = initialize_field(streams)
        _, _, _, history = run_until_articulation(state, max_steps=4)

        snapshot_path = Path("/mnt/data/cbra_runtime/tests/tmp_restore_snapshot.json")
        save_snapshot(state, history, snapshot_path)

        raw = load_snapshot(snapshot_path)
        restored = restore_field_state(raw)

        self.assertEqual(restored.field_id, state.field_id)
        self.assertEqual(restored.timestep, state.timestep)
        self.assertEqual(len(restored.streams), len(state.streams))
        self.assertEqual(restored.emergent_form.label, state.emergent_form.label)
        self.assertEqual(restored.cut.foregrounded, state.cut.foregrounded)
        self.assertAlmostEqual(restored.field_values.coherence, state.field_values.coherence, places=6)

        resumed = load_and_restore_snapshot(snapshot_path)
        self.assertEqual(resumed.field_id, state.field_id)
        before_step = resumed.timestep
        trace = step_field(resumed)
        self.assertEqual(resumed.timestep, before_step + 1)
        self.assertTrue(trace.deltas)


if __name__ == "__main__":
    unittest.main()
