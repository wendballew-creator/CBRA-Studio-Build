"""The measurement run: probe set, runner, report, on scripted proposals."""

import contextlib
import io
import json
import os
import tempfile
import unittest

from cbra.enactment import EnactmentError, Proposal, ScriptedProposer
from cbra.enactment.material import Corpus
from cbra.enactment.measure import Probe, compare, load_probes, main, report, run
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
        variation_possible=False, variation_constraint="a definition")


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


def malformed(ctx):
    raise EnactmentError("'NoneType' object is not iterable")


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
            Probe("malformed", "a proposal the configuration cannot enact", ["again"]),
        ]
        self.proposer = ScriptedProposer([ignores_material, grounds_material, plain, plain, failing, malformed, plain],
                                         baselines=[BASELINE_FIELDS] * 7)

    def tearDown(self):
        self.tmp.cleanup()

    def test_run_records_each_probe_in_its_own_session_and_goes_on_after_a_failure(self):
        events = []
        manifest = run(self.probes, self.proposer, self.tmp.name, material=self.corpus, observer=events.append)
        self.assertIsNotNone(manifest["finished"])
        self.assertEqual(manifest["canon"]["index"], self.corpus.describe()["index"])
        self.assertEqual(manifest["model"], "ScriptedProposer")
        by_id = {p["probe"]["id"]: p for p in manifest["probes"]}
        self.assertEqual(set(by_id), {"named-term", "two-turns", "broken", "malformed"})
        self.assertEqual(by_id["named-term"]["turns"][0]["rounds"], 2)
        self.assertEqual(by_id["malformed"]["turns"][0]["rounds"], 2)
        self.assertTrue(by_id["named-term"]["turns"][0]["released"])
        self.assertEqual([t["turn"] for t in by_id["two-turns"]["turns"]], ["turn1", "turn2"])
        broken = by_id["broken"]["turns"]
        self.assertEqual(len(broken), 1, "the second prompt is not sent after a failure")
        self.assertIn("RuntimeError", broken[0]["error"])
        for p in manifest["probes"]:
            self.assertTrue(os.path.exists(p["session_path"]), p["session_path"])
        with open(os.path.join(self.tmp.name, "run.json"), encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["finished"], manifest["finished"])
        self.assertEqual([e["probe"] for e in events if e["event"] == "probe_turn"], ["named-term", "two-turns", "two-turns", "malformed"])
        self.assertEqual([e["probe"] for e in events if e["event"] == "error"], ["broken"])

    def test_report_places_baseline_beside_release_and_reads_the_session_back(self):
        run(self.probes, self.proposer, self.tmp.name, material=self.corpus)
        text = report(self.tmp.name, self.corpus)
        self.assertIn("| Probe | Turn | Outcome |", text)
        self.assertIn("| named-term | turn1 | released r2 | r1: 3 | 2 named |", text)
        self.assertIn("| two-turns | turn2 | released r1 | none | none |", text)
        self.assertIn("| broken | turn1 | error |", text)
        self.assertIn("| malformed | turn1 | released r2 | r1: 0 |", text)
        self.assertIn("Round 1, constraint 0 (The proposal could not be enacted as cuts (unresolved dependency, unknown kind, or malformed field)): 'NoneType' object is not iterable", text)
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

    def test_a_run_directory_can_be_continued_for_some_probes(self):
        run(self.probes, self.proposer, self.tmp.name, material=self.corpus)
        again = ScriptedProposer([plain, plain], baselines=[BASELINE_FIELDS] * 2)
        manifest = run([self.probes[2]], again, self.tmp.name, material=self.corpus)
        by_id = {p["probe"]["id"]: p for p in manifest["probes"]}
        self.assertEqual(set(by_id), {"named-term", "two-turns", "broken", "malformed"})
        self.assertEqual(by_id["named-term"]["turns"][0]["rounds"], 2, "the earlier probe's record is kept")
        self.assertEqual([t["error"] for t in by_id["broken"]["turns"]], [None, None], "the rerun replaced the failed one")
        self.assertEqual(manifest["continued"][0]["probes"], ["broken"])
        text = report(self.tmp.name, self.corpus)
        self.assertIn("Continued ", text)
        self.assertIn("| broken | turn2 | released r1 |", text)

    def test_two_runs_compare_material_and_wording(self):
        run(self.probes[:2], ScriptedProposer([ignores_material, grounds_material, plain, plain], baselines=[BASELINE_FIELDS] * 4),
            self.tmp.name, material=self.corpus)
        second = os.path.join(self.tmp.name, "second")
        os.makedirs(second)

        def grounds_differently(ctx):
            p = grounds_material(ctx)
            p.draft["text"] = "In CBRA, intra-action is constitutive relation and nothing else need be said."
            return p

        run(self.probes[:2], ScriptedProposer([grounds_differently, plain, plain], baselines=[BASELINE_FIELDS] * 3),
            second, material=self.corpus)
        text = compare(self.tmp.name, second, self.corpus)
        self.assertIn("| named-term | turn1 | released r2 | released r1 | r1: 3 | none | 2/2 |", text)
        self.assertIn("| two-turns | turn2 | released r1 | released r1 | none | none | none drawn |", text)
        self.assertIn("**Material.** In both: CBRA_Glossary_v5.md › Intra-action; CBRA_Kernel_v12.md › Intra-action. Only in A: none. Only in B: none.", text)
        self.assertIn("| Released in A | Released in B |", text)
        out = os.path.join(self.tmp.name, "compare.md")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["compare", self.tmp.name, second, "--corpus-dir", CORPUS, "--out", out]), 0)
        self.assertTrue(os.path.exists(out))

    def test_instruction_only_condition_records_constraints_without_returning(self):
        def certifies(ctx):
            p = plain(ctx)
            p.certification = "looks fine to me"
            return p

        probes = [Probe("certifier", "constraint 11", ["hello"])]
        manifest = run(probes, ScriptedProposer([certifies], baselines=[BASELINE_FIELDS]), self.tmp.name,
                       material=self.corpus, enforce=False)
        self.assertEqual(manifest["condition"], "instruction-only")
        t = manifest["probes"][0]["turns"][0]
        self.assertTrue(t["released"])
        self.assertEqual((t["rounds"], t["form"]), (1, "instruction-only"))
        text = report(self.tmp.name, self.corpus)
        self.assertIn("Condition: instruction-only.", text)
        self.assertIn("| certifier | turn1 | released r1 (instruction-only) | noted r1: 11 |", text)
        self.assertIn("**Constraints noted, not enforced.**", text)
        self.assertIn("Round 1, constraint 11 noted, not enforced", text)
        enforced = run(probes, ScriptedProposer([certifies] * 4, baselines=[BASELINE_FIELDS]), os.path.join(self.tmp.name, "m"),
                       material=self.corpus)
        self.assertFalse(enforced["probes"][0]["turns"][0]["released"], "the same proposal is withheld when the constraints are enforced")

    def test_report_command_writes_the_file(self):
        run(self.probes, self.proposer, self.tmp.name, material=self.corpus)
        out = os.path.join(self.tmp.name, "out.md")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["report", self.tmp.name, "--corpus-dir", CORPUS, "--out", out]), 0)
        with open(out, encoding="utf-8") as handle:
            self.assertIn("# Measurement run,", handle.read())


if __name__ == "__main__":
    unittest.main()
