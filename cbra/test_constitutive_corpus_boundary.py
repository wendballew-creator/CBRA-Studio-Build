"""The new canon cannot be executed by the legacy entity/stream runtime."""

import tempfile
import unittest
from pathlib import Path

from cbra.application import (
    NativeApplicationService,
    RuntimeCorpusIncompatibilityError,
)
from cbra.corpus import (
    CONSTITUTIVE_EXECUTION_GRAMMAR,
    load_canonical_snapshot,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ConstitutiveCorpusBoundaryTests(unittest.TestCase):
    def test_repository_canon_declares_constitutive_grammar(self):
        snapshot = load_canonical_snapshot(PROJECT_ROOT / "corpus")
        self.assertEqual(
            snapshot.execution_grammar,
            CONSTITUTIVE_EXECUTION_GRAMMAR,
        )
        self.assertEqual(
            tuple(item.filename for item in snapshot.sources),
            (
                "CBRA_Kernel_v11.md",
                "CBRA_Phenomenon_Formation_Core_v1.md",
                "CBRA_Glossary_v4.md",
                "Drift_Constraints_v2.md",
                "CBRA_Paradigmatic_Invariants_v1.md",
            ),
        )
        for stream in snapshot.to_streams():
            self.assertEqual(
                stream.provenance["execution_grammar"],
                CONSTITUTIVE_EXECUTION_GRAMMAR,
            )

    def test_legacy_runtime_stops_before_loading_new_canon_as_context(self):
        snapshot = load_canonical_snapshot(PROJECT_ROOT / "corpus")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(
                RuntimeCorpusIncompatibilityError,
                "Startup stopped",
            ):
                NativeApplicationService(
                    object(),
                    canonical_corpus=snapshot,
                )
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
