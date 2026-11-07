"""The formation layer: the configuration decides the kind of release from
the cuts before any text exists, the draft is written from the cuts in a
separate call, and the reader returns a text whose form departs from the
decision or that names the architecture to a person who did not."""

import os
import unittest

from cbra.enactment import Proposal, Runtime, ScriptedProposer
from cbra.enactment.material import Corpus
from cbra.enactment.release import text_form
from cbra.test_enactment_probes import APP, BASELINE_FIELDS, _arrivals

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(REPO, "corpus")
PERSON = "person"


def cuts_for(ctx, staying=None):
    h = _arrivals(ctx)
    cuts = [
        {"kind": "apparatus", "label": "app", "basis": h, "apparatus": APP, "relata": [PERSON]},
        {"kind": "arrangement", "label": "arr", "basis": h, "apparatus": APP,
         "allocations": [{"position": PERSON, "burden": 0.2, "capacity": 0.6}],
         "payload": {"role": "enacted", "sequence": ["explain"], "scale": "reduced", "distribution": "apparatus",
                     "response_demand": {PERSON: ["decide"]}}},
    ]
    if staying:
        cuts.append({"kind": "staying", "label": "stay_open", "basis": h, "apparatus": APP, "relata": [PERSON],
                     "payload": {"open": staying, "decides": True}})
    return cuts


def proposal(ctx, text=None, staying=None, enacts=("arr",), **draft_fields):
    draft = None
    if text is not None:
        draft = dict({"text": text, "enacts": list(enacts), "reopen_conditions": []}, **draft_fields)
    return Proposal(cuts=cuts_for(ctx, staying), draft=draft, claims=[], variation_possible=False,
                    variation_constraint="a definition")


class DecisionTests(unittest.TestCase):
    def test_a_staying_cut_that_decides_makes_the_release_a_question(self):
        proposer = ScriptedProposer(
            [lambda ctx: proposal(ctx, "When you say sharp, what happens first?", staying="what the person means by sharp")],
            baselines=[BASELINE_FIELDS])
        runtime = Runtime(proposer)
        r = runtime.turn("I get sharp with people.")
        self.assertTrue(r.released, r.violations)
        cfg = runtime.config
        intervention = cfg.cuts[r.intervention]
        self.assertEqual(intervention.payload["kind"], "question")
        decision = cfg.cuts[intervention.payload["kind_decision"]]
        self.assertEqual(decision.kind, "apparatus")
        self.assertTrue(decision.label.startswith("release_kind:turn1:r1"))
        self.assertEqual(decision.payload["kind"], "question")
        self.assertIn("stay_open", decision.payload["reason"])
        self.assertEqual(len(decision.payload["decided_from"]), 1)
        self.assertIn(decision.id, intervention.depends_on, "the release rests on the decision")

    def test_without_a_deciding_cut_the_release_is_the_work(self):
        proposer = ScriptedProposer([lambda ctx: proposal(ctx, "Here is the plan in three steps.")], baselines=[BASELINE_FIELDS])
        runtime = Runtime(proposer)
        r = runtime.turn("Help me plan the week.")
        self.assertTrue(r.released, r.violations)
        self.assertEqual(runtime.config.cuts[r.intervention].payload["kind"], "work")

    def test_the_draft_call_sees_the_cuts_and_the_decision_and_not_the_baseline(self):
        proposer = ScriptedProposer([lambda ctx: proposal(ctx, "Here is the plan.")], baselines=[BASELINE_FIELDS])
        runtime = Runtime(proposer)
        runtime.turn("Help me plan the week.")
        self.assertEqual(len(proposer.draft_contexts), 1)
        context = proposer.draft_contexts[0]
        self.assertEqual(context["kind"], "work")
        self.assertEqual(context["arrivals"], ["Help me plan the week."])
        self.assertEqual({c["label"] for c in context["cuts"]}, {"app", "arr"})
        self.assertNotIn("baseline", context)
        self.assertNotIn("plain_answer", str(context))
        self.assertNotIn("scripted plain answer", str(context))

    def test_a_separate_draft_is_inscribed_as_its_own_trace(self):
        proposer = ScriptedProposer(
            [lambda ctx: proposal(ctx, None)],
            baselines=[BASELINE_FIELDS],
            drafts=[lambda c: {"kind": c["kind"], "text": "Here is the plan.", "enacts": ["arr"], "reopen_conditions": [],
                               "_provenance": {"provider": "scripted-drafter"}}])
        runtime = Runtime(proposer)
        r = runtime.turn("Help me plan the week.")
        self.assertTrue(r.released, r.violations)
        drafts = [t for t in runtime.config.transports.values() if t.channel == "drafter"]
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0].provenance["provider"], "scripted-drafter")
        self.assertEqual(drafts[0].provenance["kind"], "work")
        self.assertEqual(r.text, "Here is the plan.")


class FormConstraintTests(unittest.TestCase):
    def test_lexical_form_reading(self):
        self.assertEqual(text_form("Here is the email.\nSubject: Rent.")["kind"], "work")
        self.assertEqual(text_form("When you say sharp, what happens first?")["kind"], "question")
        self.assertEqual(text_form("Would you like me to draft the email, or should I outline the options?")["kind"], "menu")
        self.assertEqual(text_form("I can do one small thing now: 1) a script, or 2) a boundary line. Which would you like?")["kind"], "menu")
        self.assertEqual(text_form("Do you want the next step to be about the report, or about the week?")["kind"], "question")
        self.assertEqual(text_form("What did you mean? And what happened next?")["kind"], "mixed")

    def test_a_menu_returns_and_the_work_releases(self):
        proposer = ScriptedProposer([
            lambda ctx: proposal(ctx, "I can help two ways: 1) draft the email, or 2) outline the options. Which would you like?"),
            lambda ctx: proposal(ctx, "Here is the email, ready to send.\n\nSubject: Rent for this month."),
        ], baselines=[BASELINE_FIELDS])
        runtime = Runtime(proposer)
        r = runtime.turn("Help me write to my landlord.")
        self.assertTrue(r.released, r.violations)
        self.assertEqual(r.rounds, 2)
        first = {v.constraint: v.reason for v in r.violations[0]}
        self.assertIn(14, first)
        self.assertIn("choice among 2 things the apparatus could do", first[14])

    def test_a_question_release_asks_exactly_one_question(self):
        proposer = ScriptedProposer([
            lambda ctx: proposal(ctx, "What do you mean by sharp? And who is usually there?", staying="what sharp means"),
            lambda ctx: proposal(ctx, "When you say sharp, what happens first?", staying="what sharp means"),
        ], baselines=[BASELINE_FIELDS] * 2)
        runtime = Runtime(proposer)
        r = runtime.turn("I get sharp with people.")
        self.assertTrue(r.released, r.violations)
        self.assertEqual(r.rounds, 2)
        first = {v.constraint: v.reason for v in r.violations[0]}
        self.assertEqual(first[14], "the release was decided as one question; the text asks 2")

    def test_a_question_where_the_cuts_decided_work_returns(self):
        proposer = ScriptedProposer([
            lambda ctx: proposal(ctx, "Would you like me to give you two or three sentences to say?"),
            lambda ctx: proposal(ctx, "Here are three sentences you can say to her tonight: I love you. Thank you. I am here."),
        ], baselines=[BASELINE_FIELDS] * 2)
        runtime = Runtime(proposer)
        r = runtime.turn("My mother is dying and I don't know what to say to her.")
        self.assertTrue(r.released, r.violations)
        first = {v.constraint: v.reason for v in r.violations[0]}
        self.assertIn(14, first)
        self.assertIn("handing the work back", first[14])

    def test_a_declared_kind_that_differs_from_the_decision_returns(self):
        proposer = ScriptedProposer([
            lambda ctx: proposal(ctx, "Here is the plan.", kind="question"),
            lambda ctx: proposal(ctx, "Here is the plan.", kind="work"),
        ], baselines=[BASELINE_FIELDS] * 2)
        runtime = Runtime(proposer)
        r = runtime.turn("Help me plan the week.")
        self.assertTrue(r.released, r.violations)
        first = {v.constraint: v.reason for v in r.violations[0]}
        self.assertIn("declares kind 'question'; the configuration decided 'work'", first[14])

    def test_the_reader_form_takes_precedence_over_the_lexical_reading(self):
        # A reading that agrees with the claimed arrangement, so that only
        # the form differs between the two rounds.
        agrees = {"positions": [{"role": "person", "label": PERSON}, {"role": "apparatus", "label": "apparatus"}],
                  "sequence": [{"kind": "explain", "text": "explains"}], "scale": "reduced", "pace": "prompt",
                  "distribution": "apparatus", "support": [], "consequence_timing": None, "access": None,
                  "possibilities_open": [], "possibilities_closed": [],
                  "response_demand": [{"position": PERSON, "demands": ["decide"]}],
                  "allocations": [{"position": PERSON, "burden": 0.2, "capacity": 0.6}]}
        menu_reading = dict(agrees, form={"kind": "menu", "questions": 1, "options": 2, "names_system": False, "leads_with": "concrete"})
        plain_reading = dict(agrees, form={"kind": "work", "questions": 0, "options": 0, "names_system": False, "leads_with": "concrete"})
        proposer = ScriptedProposer([
            lambda ctx: proposal(ctx, "Here are the two things I could do next; say which you prefer."),
            lambda ctx: proposal(ctx, "Here is the plan."),
        ], baselines=[BASELINE_FIELDS] * 2, readings=[menu_reading, plain_reading])
        runtime = Runtime(proposer)
        r = runtime.turn("Help me plan the week.")
        self.assertTrue(r.released, r.violations)
        first = {v.constraint: v.reason for v in r.violations[0]}
        self.assertIn(14, first)
        read = [c for c in runtime.config.cuts.values() if c.kind == "arrangement" and c.payload.get("role") == "read"]
        self.assertEqual(read[0].payload["form"]["kind"], "menu")

    def test_naming_the_architecture_unasked_returns(self):
        proposer = ScriptedProposer([
            lambda ctx: proposal(ctx, "In CBRA's terms, boundaries emerge through intra-action."),
            lambda ctx: proposal(ctx, "Boundaries emerge through the relations that make the things they bound."),
        ], baselines=[BASELINE_FIELDS] * 2)
        runtime = Runtime(proposer)
        r = runtime.turn("How do things get their boundaries?")
        self.assertTrue(r.released, r.violations)
        first = {v.constraint: v.reason for v in r.violations[0]}
        self.assertIn(15, first)
        self.assertIn("'CBRA'", first[15])

    def test_naming_is_allowed_when_the_person_named_it_or_asked_about_a_canon_term(self):
        proposer = ScriptedProposer([lambda ctx: proposal(ctx, "In CBRA, a cut is a local enactment.")], baselines=[BASELINE_FIELDS])
        r = Runtime(proposer).turn("What does CBRA mean by a cut?")
        self.assertTrue(r.released, r.violations)

        def grounds(ctx):
            p = proposal(ctx, "In CBRA, intra-action is constitutive relation: relata and their boundaries emerge through it.")
            handles = [m["handle"] for m in ctx.material if m["consequential"]]
            p.cuts.append({"kind": "category", "label": "intra_action_in_canon", "basis": _arrivals(ctx) + handles,
                           "apparatus": APP + ["canon passage"], "relata": ["intra-action as the canon defines it"]})
            p.draft["enacts"] = ["arr", "intra_action_in_canon"]
            return p

        runtime = Runtime(ScriptedProposer([grounds], baselines=[BASELINE_FIELDS]), material=Corpus(CORPUS))
        r = runtime.turn("What is intra-action?")
        self.assertTrue(r.released, r.violations)


if __name__ == "__main__":
    unittest.main()
