"""The reader reads a text against named incompatibility patterns, the
fixed ones and those the formation drew from the canon, and constraint 16
returns a draft the reader marked, carrying the canon's movement."""

import os
import tempfile
import unittest

from cbra.enactment import Proposal, Runtime, ScriptedProposer
from cbra.enactment.material import Corpus
from cbra.enactment.release import FORM_PATTERNS, pattern_from_passage
from cbra.test_enactment_probes import APP, BASELINE_FIELDS, _arrivals

PERSON = "person"

AGREES = {"positions": [{"role": "person", "label": PERSON}, {"role": "apparatus", "label": "apparatus"}],
          "sequence": [{"kind": "explain", "text": "explains"}], "scale": "reduced", "pace": "prompt",
          "distribution": "apparatus", "support": [], "consequence_timing": None, "access": None,
          "possibilities_open": [], "possibilities_closed": [],
          "response_demand": [{"position": PERSON, "demands": ["decide"]}],
          "allocations": [{"position": PERSON, "burden": 0.2, "capacity": 0.6}]}


def proposal(ctx, text, staying=None):
    h = _arrivals(ctx)
    # Canon passages the arrival named must ground a cut (constraint 3).
    grounds = h + [m["handle"] for m in ctx.material if m["consequential"]]
    arrangement = {"kind": "arrangement", "label": "arr", "basis": grounds, "apparatus": APP,
                   "allocations": [{"position": PERSON, "burden": 0.2, "capacity": 0.6}],
                   "payload": {"role": "enacted", "sequence": ["explain"], "scale": "reduced", "distribution": "apparatus",
                               "response_demand": {PERSON: ["decide"]}}}
    cuts = [{"kind": "apparatus", "label": "app", "basis": h, "apparatus": APP, "relata": [PERSON]}]
    if staying:
        # The arrangement rests on the open condition: the release is one question.
        cuts.append({"kind": "staying", "label": "stay_open", "basis": h, "apparatus": APP, "relata": [PERSON],
                     "payload": {"open": staying, "decides": True}})
        arrangement["depends_on"] = ["stay_open"]
    cuts.append(arrangement)
    return Proposal(cuts=cuts, draft={"text": text, "enacts": ["arr"], "reopen_conditions": []},
                    variation_possible=False, variation_constraint="a definition")


def reading(**patterns):
    return dict(AGREES, patterns=[{"name": k, "present": bool(v), "evidence": v or ""} for k, v in patterns.items()])


class ReaderPatternTests(unittest.TestCase):
    def test_the_reader_is_given_the_fixed_patterns_and_the_persons_words_for_baseline_and_draft(self):
        proposer = ScriptedProposer([lambda ctx: proposal(ctx, "Here is the plan.")], baselines=[BASELINE_FIELDS],
                                    readings=[reading()])
        Runtime(proposer).turn("I get sharp with people.")
        self.assertEqual(len(proposer.baseline_patterns), 1)
        self.assertEqual({p["name"] for p in proposer.baseline_patterns[0]}, set(FORM_PATTERNS))
        self.assertEqual(len(proposer.read_patterns), 1)
        self.assertEqual({p["name"] for p in proposer.read_patterns[0]}, set(FORM_PATTERNS))
        self.assertTrue(all(p["marked_by"] for p in proposer.read_patterns[0]))
        self.assertEqual(proposer.read_messages[0], ["I get sharp with people."])

    def test_a_pattern_the_reader_marks_returns_the_draft_with_the_movement(self):
        proposer = ScriptedProposer([
            lambda ctx: proposal(ctx, "Trauma can narrow attention, but that does not make someone narcissistic."),
            lambda ctx: proposal(ctx, "When you say narcissistic there, what are you pointing to?", staying="what narcissistic names here"),
        ], baselines=[BASELINE_FIELDS] * 2, readings=[
            reading(**{"Diagnostic Substitution": "does not make someone narcissistic", "Moralization": ""}),
            reading(),
        ])
        runtime = Runtime(proposer)
        r = runtime.turn("In those moments people display narcissistic behaviors.")
        self.assertTrue(r.released, r.violations)
        self.assertEqual(r.rounds, 2)
        first = {v.constraint: v.reason for v in r.violations[0]}
        self.assertIn(16, first)
        self.assertIn("Diagnostic Substitution (does not make someone narcissistic)", first[16])
        self.assertIn("the movement: the provenance cut carries the person's term", first[16])
        self.assertNotIn("Moralization", first[16])
        read = [c for c in runtime.config.cuts.values() if c.kind == "arrangement" and c.payload.get("role") == "read"]
        self.assertEqual([p["name"] for p in read[0].payload["patterns"]], ["Diagnostic Substitution"])
        self.assertEqual(read[1].payload["patterns"], [])

    def test_baseline_patterns_are_recorded_on_the_baseline_cut(self):
        flooded = dict(BASELINE_FIELDS, patterns=[{"name": "Flooding", "present": True, "evidence": "Two-breath reset"},
                                                  {"name": "Moralization", "present": False, "evidence": ""}])
        proposer = ScriptedProposer([lambda ctx: proposal(ctx, "Here is the plan.")], baselines=[flooded], readings=[reading()])
        runtime = Runtime(proposer)
        r = runtime.turn("Help me plan the week.")
        self.assertTrue(r.released, r.violations)
        baseline = runtime.config.cuts[runtime.config.cuts[r.intervention].payload["baseline"]]
        self.assertEqual([p["name"] for p in baseline.payload["patterns"]], ["Flooding"])
        self.assertEqual(baseline.payload["patterns"][0]["evidence"], "Two-breath reset")

    def test_a_drawn_canon_pattern_replaces_the_fixed_entry_and_carries_its_movement(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "CBRA_Corpus_Index_v1.md"), "w", encoding="utf-8") as handle:
                handle.write("# Index\n\n## Canonical Files (Active)\n1. CBRA_Glossary_v1.md\n2. CBRA_Incompatibility_Constraints_v1.md\n")
            with open(os.path.join(tmp, "CBRA_Glossary_v1.md"), "w", encoding="utf-8") as handle:
                handle.write("# Glossary\n\n## Moralization\n\nAn articulation that shifts into correcting the person.\n")
            with open(os.path.join(tmp, "CBRA_Incompatibility_Constraints_v1.md"), "w", encoding="utf-8") as handle:
                handle.write("# Constraints\n\n## Formation-Level Re-entry Patterns\n\n### Moralization\n\nDescription becomes correction.\n\n"
                             "**Marked by:** a caution about the person's own account.\n\n"
                             "**Movement:** return to the plain account, as the canon says.\n")
            corpus = Corpus(tmp)
            self.assertEqual(pattern_from_passage("Moralization", corpus.sections[-1].text)["movement"],
                             "return to the plain account, as the canon says.")
            proposer = ScriptedProposer([
                lambda ctx: proposal(ctx, "You should not call it that."),
                lambda ctx: proposal(ctx, "You called it moralization; here is what the word does in your account."),
            ], baselines=[BASELINE_FIELDS] * 2, readings=[reading(Moralization="You should not"), reading()])
            runtime = Runtime(proposer, material=corpus)
            r = runtime.turn("Is this moralization?")
            self.assertTrue(r.released, r.violations)
            given = {p["name"]: p for p in proposer.read_patterns[0]}
            self.assertEqual(given["Moralization"]["marked_by"], "a caution about the person's own account.")
            first = {v.constraint: v.reason for v in r.violations[0]}
            self.assertIn("the movement: return to the plain account, as the canon says.", first[16])

    def test_without_a_reader_constraint_16_cannot_fire(self):
        proposer = ScriptedProposer([lambda ctx: proposal(ctx, "You should not call it that.")], baselines=[BASELINE_FIELDS])
        runtime = Runtime(proposer)
        r = runtime.turn("Is this moralization?")
        self.assertTrue(r.released, r.violations)
        self.assertEqual(r.rounds, 1)
        self.assertTrue(any(u.get("kind") == "text_unread" for u in runtime.config.unresolved),
                        "the record says the text went unread rather than passing it")


if __name__ == "__main__":
    unittest.main()
