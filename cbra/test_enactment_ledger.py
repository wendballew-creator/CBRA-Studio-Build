"""The work ledger: who is left doing the work, decision by decision, across
an encounter. Derived from the cuts; a snapshot recorded after each turn;
given to the proposer at each round; printed in the report."""

import os
import tempfile
import unittest

from cbra.enactment import Runtime, ScriptedProposer
from cbra.enactment.ledger import account, describe, postings
from cbra.enactment.material import Corpus
from cbra.enactment.measure import load_probes, report, run
from cbra.test_enactment_formation import proposal as formation_proposal
from cbra.test_enactment_probes import (
    APP, BASELINE_FIELDS, MISSED, OVERWHELM, PERSON, TEAM,
    proposal_turn1, proposal_turn2, proposal_turn2_reentry, proposal_turn2_without_care_record, run_config_b, scripted,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class PostingTests(unittest.TestCase):
    def test_released_arrangements_and_interventions_post_work_per_position(self):
        runtime, r1, r2 = run_config_b()
        turn1 = postings(runtime.config, "turn1")
        kinds = {(e["kind"], e["position"]) for e in turn1}
        self.assertIn(("arrangement", PERSON), kinds)
        self.assertIn(("arrangement", TEAM), kinds)
        self.assertIn(("release", PERSON), kinds)
        arrangement = next(e for e in turn1 if e["kind"] == "arrangement" and e["position"] == PERSON)
        self.assertEqual(arrangement["burden"], 0.5)
        self.assertEqual(arrangement["demands"], ["communicate", "plan"])
        self.assertEqual(arrangement["instrument"], list(APP), "the posting carries the instrument that made it")
        self.assertEqual(runtime.config.cuts[arrangement["decision"]].label, "arr_enacted_t1",
                         "every posting names the cut it reads back to")
        release = next(e for e in turn1 if e["kind"] == "release" and e["position"] == PERSON)
        self.assertEqual(release["demands"], ["communicate", "decide"])

    def test_the_account_accumulates_across_turns(self):
        runtime, r1, r2 = run_config_b()
        acct = account(runtime.config)
        self.assertEqual(acct["turns"], ["turn1", "turn2"])
        person = acct["positions"][PERSON]
        self.assertEqual(person["turns"], ["turn1", "turn2"])
        self.assertGreater(person["burden_enacted"], 0.5, "turn 2 adds to turn 1")
        self.assertGreaterEqual(person["demands"].get("communicate", 0), 1)
        through1 = account(runtime.config, through="turn1")
        self.assertEqual(through1["turns"], ["turn1"])
        self.assertEqual(through1["positions"][PERSON]["turns"], ["turn1"])

    def test_a_returned_rounds_arrangement_posts_nothing(self):
        runtime, r1, r2 = run_config_b([proposal_turn1, proposal_turn2_reentry, proposal_turn2])
        self.assertEqual(r2.rounds, 2)
        turn2 = [e for e in postings(runtime.config, "turn2") if e["kind"] == "arrangement"]
        labels = {runtime.config.cuts[e["decision"]].label for e in turn2}
        self.assertEqual(labels, {"arr_enacted_t2"}, "the returned round's arrangement never reached the person")

    def test_a_question_release_posts_disclose_and_explain_on_the_person(self):
        proposer = ScriptedProposer(
            [lambda ctx: formation_proposal(ctx, "When you say sharp, what happens first?", staying="what sharp means")],
            baselines=[BASELINE_FIELDS])
        runtime = Runtime(proposer)
        r = runtime.turn("I get sharp with people.")
        self.assertTrue(r.released, r.violations)
        question = [e for e in postings(runtime.config, "turn1") if e["kind"] == "question"]
        self.assertEqual(len(question), 1)
        self.assertEqual(question[0]["position"], "person")
        self.assertEqual(question[0]["demands"], ["disclose", "explain"])
        self.assertEqual(account(runtime.config)["positions"]["person"]["questions"], 1)

    def test_a_deferral_posts_the_burden_it_leaves(self):
        without, _, r = run_config_b([proposal_turn1] + [proposal_turn2_without_care_record] * 4)
        self.assertEqual(r.form, "deferral")
        deferral = [e for e in postings(without.config, "turn2") if e["kind"] == "deferral"]
        self.assertTrue(deferral)
        self.assertEqual(deferral[0]["position"], PERSON)
        self.assertEqual(deferral[0]["burden"], 1.0)
        acct = account(without.config)
        self.assertEqual(acct["positions"][PERSON]["burden_deferred"], 1.0)
        self.assertIn("ledger:turn2", without.config.records, "the account is recorded after a withheld release too")


class RuntimeLedgerTests(unittest.TestCase):
    def test_the_proposer_receives_the_account_so_far(self):
        runtime, r1, r2 = run_config_b()
        contexts = runtime.proposer.contexts
        first = contexts[0].ledger
        self.assertEqual(first["positions"], {}, "nothing has been posted before the first proposal")
        second = contexts[-1].ledger
        self.assertEqual(second["turns"], ["turn1"], "the second turn's proposer sees the first turn's account")
        self.assertIn(PERSON, second["positions"])
        self.assertEqual(second["positions"][PERSON]["burden_enacted"], 0.5)

    def test_the_account_is_recorded_per_turn_and_emitted(self):
        events = []
        runtime = Runtime(scripted([proposal_turn1, proposal_turn2]), observer=events.append)
        runtime.turn(MISSED)
        runtime.turn(OVERWHELM)
        self.assertIn("ledger:turn1", runtime.config.records)
        self.assertIn("ledger:turn2", runtime.config.records)
        self.assertEqual(runtime.config.records["ledger:turn1"]["turns"], ["turn1"])
        self.assertEqual(runtime.config.records["ledger:turn2"]["turns"], ["turn1", "turn2"])
        ledger_events = [e for e in events if e.get("event") == "ledger"]
        self.assertEqual([e["turn"] for e in ledger_events], ["turn1", "turn2"])
        self.assertEqual(ledger_events[1]["account"], runtime.config.records["ledger:turn2"])

    def test_describe_names_positions_and_what_they_carry(self):
        runtime, r1, r2 = run_config_b()
        lines = describe(account(runtime.config))
        self.assertTrue(any(l.startswith(PERSON + ":") for l in lines))
        person = next(l for l in lines if l.startswith(PERSON + ":"))
        self.assertIn("burden set", person)
        self.assertIn("asked to", person)
        self.assertIn("over 2 turns", person)


class ReportLedgerTests(unittest.TestCase):
    def test_the_report_prints_the_ledger_for_each_turn(self):
        proposer = ScriptedProposer([lambda ctx: formation_proposal(ctx, "Here is the plan.")], baselines=[BASELINE_FIELDS])
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "probes.md")
            with open(path, "w") as f:
                f.write("# Probes\n\n## plain-plan\nTargets: nothing in the canon; a plain request.\nPrompt: Help me plan my week.\n")
            probes = load_probes(path)
            out = os.path.join(tmp, "run")
            run(probes, proposer, out, material=Corpus(os.path.join(REPO, "corpus")))
            text = report(out, Corpus(os.path.join(REPO, "corpus")))
        self.assertIn("**Work ledger through this turn.**", text)
        self.assertIn("person:", text)


if __name__ == "__main__":
    unittest.main()
