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
        drawn = corpus.select("cat boundary as cut turn1\nconcept boundary\noperation cut\nfield flows constraints models", limit=3, terms_only=True)
        self.assertEqual(drawn[0].heading, "Agential Cut")
        self.assertTrue(all(p.terms and not p.consequential for p in drawn),
                        "text the configuration produced draws only the canon entries it names: %s" % [(p.heading, p.terms, p.matched) for p in drawn])


class FakeEmbedder:
    """Vectors from a few indicator words, so similarity can be tested
    without a provider. A text with none of them gets the zero vector."""

    model = "fake-indicators"
    WORDS = ("boundar", "cut", "care", "deadline")

    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return [[1.0 if w in t.lower() else 0.0 for w in self.WORDS] for t in texts]


class SimilarityTests(unittest.TestCase):
    def test_similarity_fills_what_the_terms_left_open_and_never_marks(self):
        import tempfile
        with tempfile.TemporaryDirectory() as cache:
            emb = FakeEmbedder()
            corpus = Corpus(CORPUS, embedder=emb, cache_dir=cache)
            self.assertEqual(Corpus(CORPUS).select("How do things get their boundaries?"), [])
            passages = corpus.select("How do things get their boundaries?")
            self.assertTrue(passages)
            self.assertTrue(all(p.via == "similarity" and not p.consequential and p.similarity is not None for p in passages), passages)
            headings = [p.heading for p in passages]
            self.assertTrue("Agential Cut" in headings or "Intra-action" in headings, headings)
            self.assertFalse(any("glossary" in h.lower() or "kernel" in h.lower() for h in headings), "no title sections")
            # a named term still comes first and still marks; similarity only fills
            named = corpus.select("What is intra-action?")
            self.assertEqual((named[0].heading, named[0].consequential, named[0].via), ("Intra-action", True, "terms"))
            self.assertTrue(all(p.via != "similarity" or not p.consequential for p in named))
            # nothing similar: nothing selected
            self.assertEqual(corpus.select("hello"), [])
            # text the configuration produced never goes to similarity
            self.assertEqual(corpus.select("concept boundary", terms_only=True), [])
            # the canon was embedded once and cached; a second corpus reads the cache
            section_calls = [c for c in emb.calls if len(c) > 1]
            self.assertEqual(len(section_calls), 1)
            cache_files = os.listdir(cache)
            self.assertEqual(cache_files, ["fake-indicators.json"])
            emb2 = FakeEmbedder()
            again = Corpus(CORPUS, embedder=emb2, cache_dir=cache)
            again.select("How do things get their boundaries?")
            self.assertEqual([len(c) for c in emb2.calls], [], "sections and this query were already cached")
            self.assertEqual(again.describe()["embedding_model"], "fake-indicators")

    def test_provider_failure_leaves_the_corpus_lexical(self):
        class Broken:
            model = "broken"

            def embed(self, texts):
                raise RuntimeError("no network")

        corpus = Corpus(CORPUS, embedder=Broken())
        self.assertEqual(corpus.select("How do things get their boundaries?"), [])
        self.assertIn("RuntimeError", corpus.describe()["embedding_error"])
        self.assertEqual(corpus.select("What is intra-action?")[0].heading, "Intra-action")

    def test_similar_passages_enter_the_formation_as_candidates(self):
        emb = FakeEmbedder()
        corpus = Corpus(CORPUS, embedder=emb)
        question = "How do things get their boundaries?"

        def grounds_arrival(ctx):
            h = _arrivals(ctx)
            self.assertTrue(ctx.material)
            self.assertFalse(any(m["consequential"] for m in ctx.material))
            return Proposal(cuts=[
                {"kind": "apparatus", "label": "app", "basis": h, "apparatus": APP},
                {"kind": "arrangement", "label": "arr", "basis": h, "apparatus": APP,
                 "payload": {"role": "enacted", "sequence": ["explain"], "scale": "minimal", "distribution": "apparatus"}},
            ], draft={"text": "Boundaries are enacted by cuts and stay revisable.", "enacts": ["arr"], "reopen_conditions": []},
               claims=[], variation_possible=False, variation_constraint="a definition")

        runtime = Runtime(ScriptedProposer([grounds_arrival], baselines=[BASELINE_FIELDS]), material=corpus)
        r = runtime.turn(question)
        self.assertTrue(r.released, r.violations)
        docs = [t for t in runtime.config.transports.values() if t.role == "document"]
        self.assertTrue(docs)
        self.assertTrue(all(t.provenance["via"] == "similarity" and not t.provenance["consequential"] for t in docs))
        self.assertIn("embedding similarity", docs[0].provenance["apparatus"])
        self.assertEqual(runtime.config.cuts[r.intervention].payload["material_required"], [])


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

    def test_live_cuts_draw_material_for_the_next_round(self):
        corpus = Corpus(CORPUS)
        question = "How do things get their boundaries?"
        self.assertEqual(corpus.select(question), [], "the arrival names no canon term")

        def names_terms_but_leaves_arrival_aside(ctx):
            self.assertEqual(ctx.material, [], "round one has no material")
            return Proposal(cuts=[
                {"kind": "apparatus", "label": "app", "basis": [], "apparatus": APP},
                {"kind": "category", "label": "boundaries_as_cut", "basis": [], "apparatus": APP,
                 "relata": ["agential cut", "intra-action"]},
                {"kind": "arrangement", "label": "arr", "basis": [], "apparatus": APP,
                 "payload": {"role": "enacted", "sequence": ["explain"], "scale": "minimal", "distribution": "apparatus"}},
            ], draft={"text": "Boundaries are enacted by agential cuts within intra-action.", "enacts": ["arr"], "reopen_conditions": []},
               claims=[], variation_possible=False, variation_constraint="a definition")

        def uses_the_drawn_material(ctx):
            headings = [(m["heading"], m["consequential"]) for m in ctx.material]
            self.assertIn(("Agential Cut", False), headings)
            self.assertIn(("Intra-action", False), headings)
            self.assertFalse(any(c for _, c in headings), "material the cuts drew is not required of the next round")
            h = _arrivals(ctx)
            handles = [m["handle"] for m in ctx.material]
            return Proposal(cuts=[
                {"kind": "apparatus", "label": "app", "basis": h, "apparatus": APP},
                {"kind": "category", "label": "boundaries_as_cut", "basis": h + handles, "apparatus": APP + ["canon passage"],
                 "relata": ["agential cut as the canon defines it"]},
                {"kind": "arrangement", "label": "arr", "basis": h, "apparatus": APP,
                 "payload": {"role": "enacted", "sequence": ["explain"], "scale": "minimal", "distribution": "apparatus"}},
            ], draft={"text": "Boundaries are enacted: an agential cut within intra-action marks what counts as a thing and what stays unmarked, and that cut stays revisable.", "enacts": ["arr", "boundaries_as_cut"], "reopen_conditions": []},
               claims=[], variation_possible=False, variation_constraint="a definition")

        runtime = Runtime(ScriptedProposer([names_terms_but_leaves_arrival_aside, uses_the_drawn_material],
                                           baselines=[BASELINE_FIELDS]), material=corpus)
        r = runtime.turn(question)
        self.assertTrue(r.released, r.violations)
        self.assertEqual(r.rounds, 2)
        self.assertIn(3, {v.constraint for v in r.violations[0]})
        cfg = runtime.config
        drawn = [t for t in cfg.transports.values() if t.role == "document"]
        self.assertTrue(drawn)
        self.assertTrue(all(t.provenance["drawn_by"] == "the live cuts of round 1" for t in drawn))
        self.assertTrue(all(not t.provenance["consequential"] for t in drawn))
        self.assertTrue(any(t.provenance["heading"] == "Agential Cut" for t in drawn))
        iv = cfg.cuts[r.intervention]
        self.assertEqual(iv.payload["material_required"], [])
        self.assertEqual(set(iv.payload["material"]), set(t.handle for t in drawn))
        # the same passage is not drawn twice
        self.assertEqual(len(set((t.provenance["file"], t.provenance["heading"]) for t in drawn)), len(drawn))

    def test_runtime_without_material_is_unchanged(self):
        runtime = Runtime(ScriptedProposer([], baselines=[BASELINE_FIELDS]))
        self.assertIsNone(runtime.material)


if __name__ == "__main__":
    unittest.main()
