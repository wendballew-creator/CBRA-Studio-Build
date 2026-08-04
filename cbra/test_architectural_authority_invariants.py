"""Negative authority invariants for the reconfiguration checkpoint.

These probes constrain known representational re-entry paths. Passing them
does not certify the architecture or substitute for behavioral falsification.
"""

from dataclasses import fields
import unittest

from cbra.reconfiguration import (
    CompetingAlternatives,
    DimensionEffect,
    FeedbackDisposition,
    FeedbackProvenanceClosure,
    FormationFeedbackTrace,
)


FORBIDDEN_AUTHORITY_FIELDS = {
    "accepted",
    "adequate",
    "best",
    "certificate",
    "confidence",
    "correct",
    "final",
    "maturity",
    "preferred",
    "rank",
    "ranking",
    "reward",
    "score",
    "selected",
    "seniority",
    "success",
    "truth",
    "weight",
    "winner",
}


def field_names(record_type):
    return {item.name for item in fields(record_type)}


class ArchitecturalAuthorityInvariantTests(unittest.TestCase):
    def assertCarriesNoAuthorityFields(self, record_type):
        self.assertTrue(
            field_names(record_type).isdisjoint(FORBIDDEN_AUTHORITY_FIELDS)
        )

    def test_structural_measurements_are_effect_traces_not_scores(self):
        self.assertEqual(
            {
                "dimension",
                "total_before",
                "total_after",
                "maximum_before",
                "maximum_after",
                "occupied_positions_before",
                "occupied_positions_after",
                "direction",
            },
            field_names(DimensionEffect),
        )
        self.assertCarriesNoAuthorityFields(DimensionEffect)

    def test_competing_field_has_lineage_not_selection_authority(self):
        self.assertEqual(
            {"source_cut_id", "alternatives", "constraints"},
            field_names(CompetingAlternatives),
        )
        self.assertCarriesNoAuthorityFields(CompetingAlternatives)
        for method in ("best", "choose", "rank", "select", "winner"):
            self.assertFalse(hasattr(CompetingAlternatives, method))

    def test_feedback_dispositions_are_situated_not_evaluative(self):
        self.assertEqual(
            {"confirms", "complicates", "invalidates"},
            {item.value for item in FeedbackDisposition},
        )
        self.assertCarriesNoAuthorityFields(FormationFeedbackTrace)

    def test_continuity_closure_is_an_integrity_commitment_only(self):
        self.assertEqual(
            {
                "closure_id",
                "predecessor_closure_id",
                "observation_trace_id",
                "disturbance_delta_id",
                "counter_cut_id",
                "recomputed_alternative_id",
            },
            field_names(FeedbackProvenanceClosure),
        )
        self.assertCarriesNoAuthorityFields(FeedbackProvenanceClosure)


if __name__ == "__main__":
    unittest.main()
