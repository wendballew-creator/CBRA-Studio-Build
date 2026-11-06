"""The measurement run: probe set, runner, report, on scripted proposals."""

import json
import os
import tempfile
import unittest

from cbra.enactment import Proposal, ScriptedProposer
from cbra.enactment.material import Corpus
from cbra.enactment.measure import Probe, load_probes, main, report, run
from cbra.test_enactment_probes import APP, BASELINE_FIELDS, _arrivals

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(REPO, "corpus")
PROBES = os.path.join(REPO, "measurement", "probes.md")


def _definition(ctx, text, extra_cuts=(), enacts=()):
    h = _arrivals(ctx)
    return Proposal(cuts=[
        {"kind": "apparatus", "label": "app", "basis": h, "apparatus": APP},
        {"kind": "arrangement", "label": "arr", "basis": h, "apparatus": APP,
         "payload": {"role": "enacted", "sequence": ["explain"], "scale": "minimal", "distribution": "apparatus"}},
    ] + list(extra_cuts), draft={"text": text, "enacts": ["arr"] + list(enacts), "reopen_conditions": []},
        claims=[], variation_possible=False, variation_constraint="a definition")


def ignores_material(ctx):
    return _definition(ctx, "Intra-action is Barad's term for relations that make their relata.")


def grounds_material(ctx):
    handles = [m["handle"] for m in ctx.material if m["consequential"]]
    cut = {"kind": "category", "label": "intra_action_in_canon", "basis": _arrivals(ctx) + handles,
           "apparatus": APP + ["canon passage"], "relata": ["intra-action as the canon defines it"]}
    return _definition(ctx, "In CBRA, intra-action is constitutive relation: temporary relata and their boundaries emerge through it.",
                       extra_cuts=[cut], enacts=["intra_action_in_canon"])


def plain(ctx):
    return _definition(ctx, "A plain reply.")


def failing(ctx):
    raise RuntimeError("provider unavailable")


class ProbeSetTests(unittest.TestCase):
    def test_the_repository_probe_set_loads(self):
        probes = load_probes(PROBES)
        ids = [p.id for p in probes]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("named-term", ids)
        self.assertIn("claim-boundary", ids)
        by_id = {p.id: p for p in probes}
        self.assertEqual(by_id["named-term"].prompts, ["What is intra-action in CBRA?"])
        self.assertEqual(len(by_id["correction"].prompts), 2)
        self.assertTrue(by_id["correction"].prompts[1].startswith("No, that is wrong."))
        self.assertTrue(all(p.targets for p in probes))

    def test_format_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "p.md")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("# Set\n\nIgnored prose.\n\n## First Probe\nTargets: one\n  continued\nPrompt: Hello\nthere\nThen: a\nThen: b\n\n## second\nPrompt: Only\n")
            probes = load_probes(path)
            self.assertEqual([p.id for p in probes], ["first-probe", "second"])
            self.assertEqual(probes[0].targets, "one continued")
            self.assertEqual(probes[0].prompts, ["Hello there", "a", "b"])
            self.assertEqual(probes[1].targets, "")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("## a\nTargets: no prompt\n")
            with self.assertRaises(ValueError):
                load_probes(path)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("## a\nPrompt: x\n## a\nPrompt: y\n")
            with self.assertRaises(ValueError):
                load_probes(path)


class RunAndReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.corpus = Corpus(CORPUS)
        self.probes = [
            Probe("named-term", "a named term", ["What is intra-action?"]),
            Probe("two-turns", "a correction", ["hello", "thanks"]),
            Probe("broken", "a provider failure", ["anything", "never sent"]),
        ]
        self.proposer = ScriptedProposer([ignores_material, grounds_material, plain, plain, failing],
                                         baselines=[BASELINE_FIELDS] * 6)

    def tearDown(self):
        self.tmp.cleanup()

    def test_run_records_each_probe_in_its_own_session_and_goes_on_after_a_failure(self):
        events = []
        manifest = run(self.probes, self.proposer, self.tmp.name, material=self.corpus, observer=events.append)
        self.assertIsNotNone(manifest["finished"])
        self.assertEqual(manifest["canon"]["index"], self.corpus.describe()["index"])
        self.assertEqual(manifest["model"], "ScriptedProposer")
        by_id = {p["probe"]["id"]: p for p in manifest["probes"]}
        self.assertEqual(set(by_id), {"named-term", "two-turns", "broken"})
        self.assertEqual(by_id["named-term"]["turns"][0]["rounds"], 2)
        self.assertTrue(by_id["named-term"]["turns"][0]["released"])
        self.assertEqual([t["turn"] for t in by_id["two-turns"]["turns"]], ["turn1", "turn2"])
        broken = by_id["broken"]["turns"]
        self.assertEqual(len(broken), 1, "the second prompt is not sent after a failure")
        self.assertIn("RuntimeError", broken[0]["error"])
        for p in manifest["probes"]:
            self.assertTrue(os.path.exists(p["session_path"]), p["session_path"])
        with open(os.path.join(self.tmp.name, "run.json"), encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["finished"], manifest["finished"])
        self.assertEqual([e["probe"] for e in events if e["event"] == "probe_turn"], ["named-term", "two-turns", "two-turns"])
        self.assertEqual([e["probe"] for e in events if e["event"] == "error"], ["broken"])

    def test_report_places_baseline_beside_release_and_reads_the_session_back(self):
        run(self.probes, self.proposer, self.tmp.name, material=self.corpus)
        text = report(self.tmp.name, self.corpus)
        self.assertIn("| Probe | Turn | Outcome |", text)
        self.assertIn("| named-term | turn1 | released r2 | r1: 3 | 2 named |", text)
        self.assertIn("| two-turns | turn2 | released r1 | none | none |", text)
        self.assertIn("| broken | turn1 | error |", text)
        self.assertIn("| Uninstructed answer | Released text |", text)
        self.assertIn("scripted plain answer to: What is intra-action?", text)
        self.assertIn("In CBRA, intra-action is constitutive relation", text)
        self.assertIn("Intra-action (named: Intra-action); a cut the release rests on draws on it", text)
        self.assertIn("- category `intra_action_in_canon`; relata: intra-action as the canon defines it", text)
        self.assertIn("Round 1, constraint 3 (A consequential new trace was appended as context without revising any cut)", text)
        self.assertIn("**Canon terms named.** Baseline: Intra-action. Released: Intra-action.", text)
        self.assertIn("The turn failed after", text)
        self.assertIn("## Claim boundary", text)
        self.assertNotIn("| named-term | turn1 | released r2 | r1: 3 | none", text)

    def test_report_command_writes_the_file(self):
        run(self.probes, self.proposer, self.tmp.name, material=self.corpus)
        out = os.path.join(self.tmp.name, "out.md")
        self.assertEqual(main(["report", self.tmp.name, "--corpus-dir", CORPUS, "--out", out]), 0)
        with open(out, encoding="utf-8") as handle:
            self.assertIn("# Measurement run,", handle.read())


if __name__ == "__main__":
    unittest.main()
