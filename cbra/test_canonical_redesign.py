"""Bounded conformance checks for the active recursive canonical documents.

These checks establish manifest and documentation contracts only. They do not
certify an ontology or a future runtime implementation.
"""

import unittest
from pathlib import Path

from cbra.corpus import (
    RECURSIVE_RECONFIGURATION_GRAMMAR,
    load_canonical_snapshot,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_FILENAMES = (
    "CBRA_Kernel_v12.md",
    "CBRA_Reconfiguration_Grammar_v1.md",
    "CBRA_Glossary_v5.md",
    "CBRA_Incompatibility_Constraints_v1.md",
    "CBRA_Falsification_Probes_v2.md",
)
FAILED_CONSTITUTIVE_FILENAMES = {
    "CBRA_Kernel_v11.md",
    "CBRA_Phenomenon_Formation_Core_v1.md",
    "CBRA_Glossary_v4.md",
    "Drift_Constraints_v2.md",
    "CBRA_Paradigmatic_Invariants_v1.md",
}


class CanonicalRedesignContractTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = load_canonical_snapshot(PROJECT_ROOT / "corpus")
        self.sources = {
            source.filename: source.text for source in self.snapshot.sources
        }

    def test_manifest_activates_only_recursive_redesign(self):
        self.assertEqual(
            self.snapshot.execution_grammar,
            RECURSIVE_RECONFIGURATION_GRAMMAR,
        )
        self.assertEqual(tuple(self.sources), ACTIVE_FILENAMES)
        self.assertTrue(
            FAILED_CONSTITUTIVE_FILENAMES.isdisjoint(self.sources)
        )

    def test_kernel_separates_storage_from_ontology(self):
        kernel = self.sources["CBRA_Kernel_v12.md"]
        self.assertIn("## Storage Is Not Ontology", kernel)
        self.assertIn(
            "A stable transport handle does not establish a stable semantic "
            "entity.",
            kernel,
        )
        self.assertIn(
            "No database row or language-model object is a phenomenon.",
            kernel,
        )

    def test_grammar_separates_transport_cuts_and_interventions(self):
        grammar = self.sources["CBRA_Reconfiguration_Grammar_v1.md"]
        for heading in (
            "### 1. Transport and persistence inscriptions",
            "### 2. Local relational enactments",
            "### 3. Public interventions",
        ):
            self.assertIn(heading, grammar)
        self.assertIn(
            "It has no globally stable semantic identity.",
            grammar,
        )

    def test_movements_require_structural_deltas(self):
        grammar = self.sources["CBRA_Reconfiguration_Grammar_v1.md"]
        constraints = self.sources[
            "CBRA_Incompatibility_Constraints_v1.md"
        ]
        normalized_grammar = " ".join(grammar.split())
        self.assertIn(
            "Text saying that care, play, diffraction, or reconfiguration "
            "occurred is not a delta.",
            normalized_grammar,
        )
        self.assertIn("### String Operativity", constraints)
        self.assertIn(
            "require an inspectable structural delta",
            constraints,
        )

    def test_model_cannot_be_opaque_former_or_self_validator(self):
        grammar = self.sources["CBRA_Reconfiguration_Grammar_v1.md"]
        normalized_grammar = " ".join(grammar.split())
        self.assertIn(
            "It may not operate as an opaque `PhenomenonFormer`",
            normalized_grammar,
        )
        self.assertIn(
            "The same model call cannot both originate a semantic cut and "
            "certify that cut.",
            grammar,
        )

    def test_probes_include_known_failure_and_paraphrase_boundary(self):
        probes = self.sources["CBRA_Falsification_Probes_v2.md"]
        self.assertIn(
            "## Probe 1: Overwhelm After a Missed Deadline",
            probes,
        )
        self.assertIn("## Probe 2: Paraphrase Resistance", probes)
        self.assertIn(
            "## Probe 5: Nonbinary Reconfigures the Categories",
            probes,
        )
        self.assertIn(
            "## Probe 6: AI Participation Disturbs Tool and Subject",
            probes,
        )

    def test_active_claim_boundary_remains_non_certifying(self):
        kernel = self.sources["CBRA_Kernel_v12.md"]
        probes = self.sources["CBRA_Falsification_Probes_v2.md"]
        self.assertIn("## Claim Boundary", kernel)
        self.assertIn("## Probe 14: Claim Inflation", probes)
        self.assertIn(
            "A probe cannot establish that:",
            probes,
        )


if __name__ == "__main__":
    unittest.main()
