import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cbra.engine import initialize_field_state, step_field


class LiveWorldCompatibilityTests(unittest.TestCase):
    def test_high_tension_low_coherence_activates_live_world_material(self):
        """Preserve the June activation contract without a stale constant."""
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            (vault / "situated_material.txt").write_text(
                (
                    "Situated material enters the field with enough thickness "
                    "to participate in relation without becoming an authority "
                    "or a simulated placeholder."
                ),
                encoding="utf-8",
            )
            state = initialize_field_state("Complex Inquiry")
            state.field_values.care_tension = 0.7
            state.field_values.coherence = 0.1

            with patch("cbra.operators.VAULT_DIR", vault):
                step_field(state, "Complex Inquiry")

        live_streams = [
            stream for stream in state.streams
            if stream.kind == "live_world"
        ]
        self.assertGreater(len(live_streams), 0)
        self.assertEqual(state.notes["vault_ingestion_status"], "ingested")
        self.assertTrue(
            all(stream.payload.get("text") for stream in live_streams)
        )
        self.assertTrue(
            all(stream.payload.get("source") for stream in live_streams)
        )
        self.assertGreater(
            state.field_values.openness,
            initialize_field_state("comparison").field_values.openness,
        )


if __name__ == "__main__":
    unittest.main()
