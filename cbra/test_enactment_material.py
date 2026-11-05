"""The canon as material: selection, entry as document traces, grounding."""

import os
import unittest

from cbra.enactment import Runtime, ScriptedProposer
from cbra.enactment.material import Corpus
from cbra.test_enactment_probes import APP, BASELINE_FIELDS, PERSON, Proposal, _arrivals

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(REPO, "corpus")


class MaterialTests(unittest.TestCase):
    def test_selection_finds_the_canon_definition(self):
        corpus = Corpus(CORPUS)
        self.assertEqual(corpus.index_file, "CBRA_Corpus_Index.md")
        self.assertIn("CBRA_Glossary_v5.md", corpus.files)
        self.assertNotIn("CBRA_Loops_Core.md", corpus.files, "only the files the index lists as active")
        passages = corpus.select("What is intra-action?")
        self.assertTrue(passages)
        self.assertEqual(passages[0].heading, "Intra-action")
        self.assertTrue(passages[0].consequential)
        self.assertIn("Constitutive relation", passages[0].text)
        self.assertTrue(any(p.file.startswith("CBRA_Kernel") for p in passages))

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
