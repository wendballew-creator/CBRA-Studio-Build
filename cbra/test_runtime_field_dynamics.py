import unittest

from cbra.engine import articulate, initialize_field_state, step_field
from cbra.models import Stream
from cbra.operators import reintegrate_field


class RuntimeFieldDynamicsTests(unittest.TestCase):
    def test_user_input_streams_are_appended_once(self):
        state = initialize_field_state("posthuman field inquiry")

        state.streams.append(
            Stream(
                stream_id="user_0",
                kind="user_input",
                payload={"text": "posthuman field inquiry"},
                participation=1.0,
                persistence=0.8,
            )
        )

        step_field(state, "posthuman field inquiry")

        user_streams = [s for s in state.streams if s.kind == "user_input"]
        self.assertEqual(len(user_streams), 1)
        self.assertEqual(user_streams[0].payload.get("text"), "posthuman field inquiry")

    def test_articulation_changes_when_topology_changes(self):
        state = initialize_field_state("creative becoming under pressure")
        step_field(state, "creative becoming under pressure")
        first = articulate(state)

        state.streams.append(
            Stream(
                stream_id="live_1",
                kind="live_world",
                payload={
                    "text": "vault fragment: prison identities destabilize under posthuman relational pressure"
                },
                participation=0.82,
                persistence=0.78,
            )
        )
        step_field(state, "creative becoming under pressure")
        second = articulate(state)

        self.assertNotEqual(first, second)
        self.assertIn("A primary live strand", second)

    def test_reintegration_redistributes_rather_than_resetting(self):
        state = initialize_field_state("rigid cut")
        state.streams.extend(
            [
                Stream(
                    stream_id="user_a",
                    kind="user_input",
                    payload={"text": "rigid identity claim"},
                    participation=0.95,
                    persistence=0.95,
                ),
                Stream(
                    stream_id="live_a",
                    kind="live_world",
                    payload={"text": "counter-fragment from the vault"},
                    participation=0.15,
                    persistence=0.25,
                ),
            ]
        )
        state.field_values.cut_permeability = 0.10
        state.field_values.cut_pressure = 0.90
        state.field_values.openness = 0.20

        gap_before = abs(state.streams[0].participation - state.streams[1].participation)
        reintegrate_field(state)
        gap_after = abs(state.streams[0].participation - state.streams[1].participation)

        self.assertLess(gap_after, gap_before)
        self.assertNotEqual(state.field_values.cut_permeability, 1.0)
        self.assertNotEqual(state.field_values.cut_pressure, 0.2)
        self.assertNotEqual(state.field_values.openness, 0.8)

    def test_emergence_and_coherence_change_when_relations_change(self):
        aligned = initialize_field_state("posthuman relational field")
        aligned.streams.extend(
            [
                Stream(
                    stream_id="user_aligned",
                    kind="user_input",
                    payload={"text": "posthuman relational field"},
                    participation=1.0,
                    persistence=0.8,
                ),
                Stream(
                    stream_id="live_aligned",
                    kind="live_world",
                    payload={"text": "posthuman relational field dynamics and emergence"},
                    participation=0.75,
                    persistence=0.7,
                ),
            ]
        )
        step_field(aligned, "posthuman relational field")

        divergent = initialize_field_state("posthuman relational field")
        divergent.streams.extend(
            [
                Stream(
                    stream_id="user_divergent",
                    kind="user_input",
                    payload={"text": "posthuman relational field"},
                    participation=1.0,
                    persistence=0.8,
                ),
                Stream(
                    stream_id="live_divergent",
                    kind="live_world",
                    payload={"text": "baseball weather shopping mall gasoline"},
                    participation=0.75,
                    persistence=0.7,
                ),
            ]
        )
        step_field(divergent, "posthuman relational field")

        self.assertGreater(aligned.field_values.coherence, divergent.field_values.coherence)
        self.assertNotEqual(
            round(aligned.field_values.emergence_level, 4),
            round(divergent.field_values.emergence_level, 4),
        )
        self.assertNotEqual(
            round(aligned.field_values.difference_activity, 4),
            round(divergent.field_values.difference_activity, 4),
        )

    def test_real_vault_ingestion_records_source_and_non_simulated_text(self):
        state = initialize_field_state("creative becoming under pressure")
        step_field(state, "creative becoming under pressure")

        live_streams = [s for s in state.streams if s.kind == "live_world"]
        self.assertGreater(len(live_streams), 0)
        self.assertEqual(state.notes.get("vault_ingestion_status"), "ingested")

        ingested_streams = [s for s in live_streams if s.payload.get("source")]
        self.assertGreater(len(ingested_streams), 0)

        for stream in ingested_streams:
            self.assertTrue(stream.payload.get("source"))
            self.assertTrue(stream.payload.get("text"))
            self.assertNotIn("Live-world trace for", stream.payload.get("text", ""))

if __name__ == "__main__":
    unittest.main()
