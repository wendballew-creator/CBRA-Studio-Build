"""The recursive canon cannot run through the retained entity/stream runtime."""

import tempfile
import unittest
from pathlib import Path

from cbra.application import (
    NativeApplicationService,
    RuntimeCorpusIncompatibilityError,
)
from cbra.corpus import (
    RECURSIVE_RECONFIGURATION_GRAMMAR,
    load_canonical_snapshot,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RecursiveCorpusBoundaryTests(unittest.TestCase):
    def test_repository_canon_declares_recursive_grammar(self):
        snapshot = load_canonical_snapshot(PROJECT_ROOT / "corpus")
        self.assertEqual(
            snapshot.execution_grammar,
            RECURSIVE_RECONFIGURATION_GRAMMAR,
        )
        self.assertEqual(
            tuple(item.filename for item in snapshot.sources),
            (
                "CBRA_Kernel_v12.md",
                "CBRA_Reconfiguration_Grammar_v1.md",
                "CBRA_Glossary_v5.md",
                "CBRA_Incompatibility_Constraints_v1.md",
                "CBRA_Falsification_Probes_v2.md",
            ),
        )
        for stream in snapshot.to_streams():
            self.assertEqual(
                stream.provenance["execution_grammar"],
                RECURSIVE_RECONFIGURATION_GRAMMAR,
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
