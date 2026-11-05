"""The canon as material: selection, entry as document traces, grounding."""

import os
import unittest

from cbra.enactment import Runtime, ScriptedProposer
from cbra.enactment.material import Corpus
from cbra.test_enactment_probes import APP, BASELINE_FIELDS, PERSON, Proposal, _arrivals

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(REPO, "corpus")


NOVEMBER = os.path.join(REPO, ".cbra-runtime", "canon")

# The selection test set. Each case names a question, the passages that must
# be selected (file prefix, heading, whether the arrival named that heading
# as a canon term and so the passage must ground a cut), headings that must
# not be selected, and whether nothing at all should be selected. It is what
# says whether a change to selection is an improvement, instead of one page
# run at a time. It runs against the July corpus the repository carries and,
# when it is present, against the November set the page uses.
CASES = [
    {"q": "What is intra-action?",
     "expect": [("CBRA_Glossary", "Intra-action", True), ("CBRA_Kernel", "Intra-action", True)],
     "absent": ["Changes from"]},
    {"q": "What's the difference between interaction and intra-action?",
     "expect": [("CBRA_Glossary", "Intra-action", True)], "first": "Intra-action"},
    {"q": "What does care mean in this system?",
     "expect": [("CBRA_Glossary", "Care", True), ("CBRA_Kernel", "Care", True)],
     "absent": ["Status of This Canon"], "first": "Care"},
    {"q": "Explain the relation between play and care",
     "expect": [("CBRA_Glossary", "Care", True), ("CBRA_Glossary", "Play", True)],
     "absent": ["The Dynamic Coding Method", "Changes from", "Worlding Relation"],
     "consequential_first": True},
    {"q": "What is an agential cut?", "expect": [("CBRA_Glossary", "Agential Cut", True)], "first": "Agential Cut"},
    {"q": "What is a cut?", "expect": [("CBRA_Glossary", "Agential Cut", False)], "first": "Agential Cut"},
    {"q": "What is a transport inscription?", "expect": [("CBRA_Glossary", "Transport Inscription", True)]},
    {"q": "What is the response burden?", "expect": [("CBRA_Glossary", "Response Burden", True)], "first": "Response Burden"},
    {"q": "What is a public intervention and when is it released?",
     "expect": [("CBRA_Glossary", "Public Intervention", True)], "first": "Public Intervention"},
    {"q": "What is diffraction?", "expect": [("CBRA_Glossary", "Diffraction", True)]},
    {"q": "Tell me about noticing and naming", "expect": [("CBRA_Glossary", "Naming", True)]},
    {"q": "hello", "empty": True},
    {"q": "Can you help me write an email to my landlord about the broken heater?", "empty": True},
    {"q": "I missed a deadline and my manager is upset with me", "empty": True},
]


class SelectionCases(unittest.TestCase):
    def _run(self, corpus):
        for case in CASES:
            with self.subTest(q=case["q"], corpus=os.path.basename(corpus.directory)):
                passages = corpus.select(case["q"])
                found = [(p.file, p.heading, p.consequential) for p in passages]
                if case.get("empty"):
                    self.assertEqual(found, [])
                    continue
                self.assertTrue(found)
                for prefix, heading, consequential in case.get("expect", []):
                    hits = [f for f in found if f[0].startswith(prefix) and f[1].lower() == heading.lower()]
                    self.assertTrue(hits, "expected %s › %s in %s" % (prefix, heading, found))
                    self.assertEqual(hits[0][2], consequential, "%s › %s consequential=%s in %s" % (prefix, heading, hits[0][2], found))
                for heading in case.get("absent", []):
                    self.assertFalse(any(heading.lower() in f[1].lower() for f in found), "%s should not be selected: %s" % (heading, found))
                if case.get("first"):
                    self.assertEqual(found[0][1].lower(), case["first"].lower(), found)
                if case.get("consequential_first"):
                    flags = [f[2] for f in found]
                    self.assertEqual(flags, sorted(flags, reverse=True), "consequential passages rank first: %s" % found)
                # no title section, no version history
                self.assertFalse(any("glossary" in f[1].lower() or f[1].lower().startswith("changes from") for f in found), found)

    def test_july_corpus(self):
        corpus = Corpus(CORPUS)
        self.assertEqual(corpus.index_file, "CBRA_Corpus_Index.md")
        self.assertIn("CBRA_Glossary_v5.md", corpus.files)
        self.assertNotIn("CBRA_Loops_Core.md", corpus.files, "only the files the index lists as active")
        self.assertGreater(len(corpus.terms), 25, "the glossary's entry headings are the term set")
        self._run(corpus)

    @unittest.skipUnless(os.path.isdir(NOVEMBER), "the November canon is not in the repository")
    def test_november_canon(self):
        self._run(Corpus(NOVEMBER))

    def test_terms_match_as_phrases_with_light_stemming(self):
        corpus = Corpus(CORPUS)
        self.assertEqual([t.phrase for t in corpus.terms_in("the intra-active character of cuts")], ["Intra-action"])
        self.assertEqual([t.phrase for t in corpus.terms_in("an alternative arrangement")], ["Alternative Arrangement"])
        self.assertEqual(corpus.terms_in("cut"), [], "a bare head word does not name the term")
        self.assertEqual([(t.phrase, partial) for t, partial in corpus.matches("a cut")], [("Agential Cut", True)])
        self.assertGreater(corpus.idf("deadlin"), corpus.idf("cut"), "rarity across the canon weights the loose words")


class MaterialTests(unittest.TestCase):
    def test_material_enters_as_document_traces_and_must_ground_a_cut(self):
        corpus = Corpus(CORPUS)

        def ignores_material(ctx):
            h = _arrivals(ctx)
            return Proposal(cuts=[
                {"kind": "apparatus", "label": "app", "basis": h, "apparatus": APP},
                {"kind": "arrangement", "label": "arr", "basis": h, "apparatus": APP,
                 "payload": {"role": "enacted", "sequence": ["explain"], "scale": "minimal", "distribution": "apparatus"}},
            ], draft={"text": "Intra-action is Barad's term for relations that make their relata.", "enacts": ["arr"], "reopen_conditions": []},
               claims=[], variation_possible=False, variation_constraint="a definition")

        def grounds_material(ctx):
            p = ignores_material(ctx)
            handles = [m["handle"] for m in ctx.material if m["consequential"]]
            self.assertTrue(handles)
            p.cuts.append({"kind": "category", "label": "intra_action_in_canon", "basis": _arrivals(ctx) + handles,
                           "apparatus": APP + ["canon passage"], "relata": ["intra-action as the canon defines it"]})
            p.draft["text"] = "In CBRA, intra-action is constitutive relation: temporary relata and their boundaries emerge through it; stable nodes later connected by edges enact interaction instead."
            p.draft["enacts"] = ["arr", "intra_action_in_canon"]
            return p

        runtime = Runtime(ScriptedProposer([ignores_material, grounds_material], baselines=[BASELINE_FIELDS]), material=corpus)
        r = runtime.turn("What is intra-action?")
        self.assertTrue(r.released, r.violations)
        self.assertEqual(r.rounds, 2)
        first = {v.constraint: v.reason for v in r.violations[0]}
        self.assertIn(3, first)
        self.assertIn("canon passage", first[3])
        cfg = runtime.config
        docs = [t for t in cfg.transports.values() if t.role == "document"]
        self.assertTrue(docs)
        self.assertEqual(docs[0].channel, "corpus")
        self.assertEqual(docs[0].provenance["heading"], "Intra-action")
        ctx = runtime.proposer.contexts[0]
        self.assertTrue(ctx.material)
        self.assertEqual(ctx.material[0]["heading"], "Intra-action")
        iv = cfg.cuts[r.intervention]
        self.assertTrue(iv.payload["material_required"])
        self.assertTrue(any("canon material" in a for a in iv.apparatus))
        # the uninstructed baseline conversation carries no canon material
        self.assertEqual([m["role"] for m in runtime._plain_conversation("t1")], ["user"])

    def test_runtime_without_material_is_unchanged(self):
        runtime = Runtime(ScriptedProposer([], baselines=[BASELINE_FIELDS]))
        self.assertIsNone(runtime.material)


if __name__ == "__main__":
    unittest.main()
