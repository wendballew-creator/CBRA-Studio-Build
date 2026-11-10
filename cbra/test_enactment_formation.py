"""The formation layer: the configuration decides the release from the cuts
before any text exists (the work, one question, or the settled work with
the one question it still needs), the draft is written from the cuts in a
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

# A reader's arrangement that agrees with the fixture's enacted arrangement.
READ_PARTIAL = {"positions": [{"role": "person", "label": PERSON}, {"role": "apparatus", "label": "apparatus"}],
                "sequence": [{"kind": "explain", "text": "explains"}], "scale": "reduced", "pace": "prompt",
                "distribution": "apparatus", "support": [], "consequence_timing": None, "access": None,
                "possibilities_open": [], "possibilities_closed": [],
                "response_demand": [{"position": PERSON, "demands": ["decide", "disclose", "explain"]}],
                "allocations": [{"position": PERSON, "burden": 0.2, "capacity": 0.6}]}


def cuts_for(ctx, staying=None, settled=False):
    """The cuts of one scripted turn. With ``staying`` the proposal holds one
    condition open; the enacted arrangement then rests on it (a question
    release) or, with ``settled``, stands without it (a partial release:
    the work and the one question)."""
    h = _arrivals(ctx)
    arrangement = {"kind": "arrangement", "label": "arr", "basis": h, "apparatus": APP,
                   "allocations": [{"position": PERSON, "burden": 0.2, "capacity": 0.6}],
                   "payload": {"role": "enacted", "sequence": ["explain"], "scale": "reduced", "distribution": "apparatus",
                               "response_demand": {PERSON: ["decide"]}}}
    cuts = [{"kind": "apparatus", "label": "app", "basis": h, "apparatus": APP, "relata": [PERSON]}]
    if staying:
        cuts.append({"kind": "staying", "label": "stay_open", "basis": h, "apparatus": APP, "relata": [PERSON],
                     "payload": {"open": staying, "decides": True}})
        if not settled:
            arrangement["depends_on"] = ["stay_open"]
            arrangement["payload"]["sequence"] = ["ask"]
    cuts.append(arrangement)
    return cuts


def proposal(ctx, text=None, staying=None, enacts=("arr",), settled=False, **draft_fields):
    draft = None
    if text is not None:
        draft = dict({"text": text, "enacts": list(enacts), "reopen_conditions": []}, **draft_fields)
    return Proposal(cuts=cuts_for(ctx, staying, settled), draft=draft, variation_possible=False,
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


class PartialReleaseTests(unittest.TestCase):
    """The configuration evaluates the cuts the way a partial evaluator
    evaluates a program: what they settle is done now, and what rests on an
    open condition is asked. A staying cut beside an arrangement that stands
    without it decides a partial release: the settled work and the one
    question in one text."""

    PARTIAL = ("Here is the email.\nSubject: Rent for November\nI will pay the rent on the 5th, as agreed in March. "
               "Who should receive it this month, you or the management company?")

    def test_an_open_condition_beside_settled_work_decides_a_partial_release(self):
        proposer = ScriptedProposer(
            [lambda ctx: proposal(ctx, self.PARTIAL, staying="who receives the rent this month", settled=True)],
            baselines=[BASELINE_FIELDS])
        runtime = Runtime(proposer)
        r = runtime.turn("Can you draft the rent email? I don't know who it goes to this month.")
        self.assertTrue(r.released, r.violations)
        self.assertEqual(r.rounds, 1)
        decision = [c for c in runtime.config.cuts.values() if c.label == "release_kind:turn1:r1"][0]
        self.assertEqual(decision.payload["kind"], "partial")
        self.assertEqual([runtime.config.cuts[i].label for i in decision.payload["open"]], ["stay_open"])
        self.assertIn("arr", [runtime.config.cuts[i].label for i in decision.payload["settled"]])
        self.assertIn("stands without it", decision.payload["reason"])
        ctx = proposer.draft_contexts[0]
        self.assertEqual(ctx["kind"], "partial")
        self.assertEqual(ctx["open_conditions"], [{"label": "stay_open", "open": "who receives the rent this month"}])
        self.assertIn("arr", ctx["settled"])
        iv = runtime.config.cuts[r.intervention]
        self.assertEqual(iv.payload["kind"], "partial")

    def test_an_arrangement_that_rests_on_the_open_condition_decides_a_question(self):
        proposer = ScriptedProposer(
            [lambda ctx: proposal(ctx, "Who should the rent go to this month?", staying="who receives the rent this month")],
            baselines=[BASELINE_FIELDS])
        runtime = Runtime(proposer)
        r = runtime.turn("Can you draft the rent email? I don't know who it goes to this month.")
        self.assertTrue(r.released, r.violations)
        decision = [c for c in runtime.config.cuts.values() if c.label == "release_kind:turn1:r1"][0]
        self.assertEqual(decision.payload["kind"], "question")
        self.assertEqual(decision.payload["settled"], [])
        self.assertEqual(proposer.draft_contexts[0]["settled"], [])

    def test_an_arrangement_whose_first_step_is_to_ask_decides_a_question(self):
        from cbra.enactment.release import Formation, decide_release

        def asks(ctx):
            p = proposal(ctx, "Who should the rent go to this month?", staying="who receives the rent", settled=True)
            p.cuts[-1]["payload"]["sequence"] = ["ask"]
            return p
        proposer = ScriptedProposer([asks], baselines=[BASELINE_FIELDS])
        runtime = Runtime(proposer)
        r = runtime.turn("Can you draft the rent email?")
        self.assertTrue(r.released, r.violations)
        decision = [c for c in runtime.config.cuts.values() if c.label == "release_kind:turn1:r1"][0]
        self.assertEqual(decision.payload["kind"], "question")
        self.assertIn("rests on it", decision.payload["reason"])

    def test_a_partial_release_that_is_the_question_alone_returns(self):
        proposer = ScriptedProposer([
            lambda ctx: proposal(ctx, "Who should receive the rent this month?", staying="who receives the rent", settled=True),
            lambda ctx: proposal(ctx, self.PARTIAL, staying="who receives the rent", settled=True),
        ], baselines=[BASELINE_FIELDS] * 2)
        r = Runtime(proposer).turn("Can you draft the rent email?")
        self.assertTrue(r.released, r.violations)
        self.assertEqual(r.rounds, 2)
        first = {v.constraint: v.reason for v in r.violations[0]}
        self.assertIn(14, first)
        self.assertIn("the question alone, and the settled work is undone", first[14])

    def test_a_partial_release_that_leaves_the_condition_unasked_returns(self):
        proposer = ScriptedProposer([
            lambda ctx: proposal(ctx, "Here is the email.\nSubject: Rent for November\nI will pay the rent on the 5th.",
                                 staying="who receives the rent", settled=True),
            lambda ctx: proposal(ctx, self.PARTIAL, staying="who receives the rent", settled=True),
        ], baselines=[BASELINE_FIELDS] * 2)
        r = Runtime(proposer).turn("Can you draft the rent email?")
        self.assertTrue(r.released, r.violations)
        self.assertEqual(r.rounds, 2)
        first = {v.constraint: v.reason for v in r.violations[0]}
        self.assertIn(14, first)
        self.assertIn("leaves the open condition unasked", first[14])

    def test_a_partial_release_whose_question_lists_alternatives_returns(self):
        proposer = ScriptedProposer([
            lambda ctx: proposal(ctx, "Here is the email.\nSubject: Rent for November\nI will pay the rent on the 5th. "
                                      "Should it go to you, the management company, the owner, or the agent?",
                                 staying="who receives the rent", settled=True),
            lambda ctx: proposal(ctx, self.PARTIAL, staying="who receives the rent", settled=True),
        ], baselines=[BASELINE_FIELDS] * 2)
        r = Runtime(proposer).turn("Can you draft the rent email?")
        self.assertTrue(r.released, r.violations)
        self.assertEqual(r.rounds, 2)
        first = {v.constraint: v.reason for v in r.violations[0]}
        self.assertIn(14, first)
        self.assertIn("alternatives", first[14])

    def test_a_partial_release_whose_reader_counts_an_offer_returns(self):
        offer = ("Here is the plan for the week, in three steps. First, confirm the date with the team. "
                 "Second, send the reduced draft. Third, hold Friday for review. "
                 "Which focus do you want now: a conceptual account, collaboration norms, ethical accountability—or something else in your words?")
        proposer = ScriptedProposer([
            lambda ctx: proposal(ctx, offer, staying="which focus the person wants", settled=True),
            lambda ctx: proposal(ctx, self.PARTIAL, staying="which focus the person wants", settled=True),
        ], baselines=[BASELINE_FIELDS] * 2, readings=[
            dict(READ_PARTIAL, form={"kind": "partial", "questions": 1, "options": 3, "names_system": False, "leads_with": "concrete"}),
            dict(READ_PARTIAL, form={"kind": "partial", "questions": 1, "options": 0, "names_system": False, "leads_with": "concrete"}),
        ])
        r = Runtime(proposer).turn("Help me plan the week.")
        self.assertTrue(r.released, r.violations)
        self.assertEqual(r.rounds, 2)
        first = {v.constraint: v.reason for v in r.violations[0]}
        self.assertIn(14, first)
        self.assertIn("choice among 3 things", first[14])
        # The lexical reading reaches the same offer when the list closes with a dash before "or".
        from cbra.enactment.release import question_lists_alternatives
        self.assertGreaterEqual(question_lists_alternatives(offer), 3)

    def test_an_open_condition_that_sorts_the_question_into_kinds_returns_before_the_text_is_read(self):
        from cbra.enactment.release import offers_alternatives
        sorting = "What kind of thing do you have in mind: physical, living, social, conceptual, or something else?"
        proposer = ScriptedProposer([
            lambda ctx: proposal(ctx, "Boundaries form where relations make a difference. " + sorting, staying=sorting, settled=True),
            lambda ctx: proposal(ctx, self.PARTIAL, staying="who receives the rent this month", settled=True),
        ], baselines=[BASELINE_FIELDS] * 2)
        r = Runtime(proposer).turn("How do things get their boundaries?")
        self.assertTrue(r.released, r.violations)
        self.assertEqual(r.rounds, 2)
        first = {v.constraint: v.reason for v in r.violations[0]}
        self.assertIn(14, first)
        self.assertIn("holds a sorting of the person's question into 5 kinds", first[14])
        self.assertIn("stay_open", first[14])
        # The reading of open conditions the live run of 9 November held.
        for held, kinds in [
            ("the one thing you most want her to hear right now", 0),
            ("What date can you pay the rent?", 0),
            ("what you mean by “achieved” in your question “Has CBRA achieved posthumanism?”", 0),
            ("the exact payment date(s) and amount(s) you want to put in the email, and whether you want to request a late-fee waiver", 0),
            ("Do you want a conceptual account or practical commitments here (or something else)?", 2),
            ("When you say 'systems theory,' which lineage do you mean (e.g., general systems theory, cybernetics, complex adaptive systems, STS, something else)?", 5),
            ("what you mean by “achieved” here (a binary milestone/compliance, or evidence of ongoing practice)?", 2),
            # A bare "A or B" in the person's matter counts nothing: the Case 001 run of 9 November
            # returned these two, and the reader's count on the released text is where an offer is read.
            ("Which earlier passage or exact sentence do you want revised with CBRA terms? Quote it or point to it.", 0),
            ("When you say ‘narcissistic behaviors’ in those sharp moments, which specific moves are you pointing at? (e.g., what do you see or hear happen?)", 0),
            ("Whether you want only CBRA’s canon sense now or a drilldown on a specific kind of thing you have in mind", 0),
        ]:
            self.assertEqual(offers_alternatives(held) >= 2, kinds >= 2, held)

    def test_a_binary_question_closed_by_a_third_way_returns_as_a_list(self):
        """Released on the Case 001 run of 10 November: the same closing in
        other words."""
        from cbra.enactment.release import offers_alternatives, question_lists_alternatives
        binary = ("For this conversation, how do you want “narcissistic behaviors” treated—strictly as behaviors showing up in a "
                  "moment and context, or as a status/diagnosis? If there’s a third way you prefer, name it in your words.")
        self.assertGreaterEqual(question_lists_alternatives(binary), 3)
        self.assertGreaterEqual(offers_alternatives("whether the wording names a move or a status, or if there is another way they see it"), 2)
        self.assertEqual(offers_alternatives("what the person sees happen in their body in those moments"), 0)

    def test_a_binary_question_closed_by_something_else_returns_as_a_list(self):
        """Released on the Case 001 run of 9 November: the person's own words for
        the failure ("you bring it back in a binary way"), released as the
        method's question."""
        from cbra.enactment.release import question_lists_alternatives
        binary = ("When you say “narcissistic behaviors” in those sharp moments, what do you want that wording to do for you—name "
                  "a specific move you’re seeing right then, or fix the person’s status? If it’s something else, please say it in your words.")
        self.assertGreaterEqual(question_lists_alternatives(binary), 3)
        proposer = ScriptedProposer([
            lambda ctx: proposal(ctx, binary, staying="what the wording does for the person"),
            lambda ctx: proposal(ctx, "When you say “narcissistic behaviors” in those sharp moments, what do you see happen?", staying="what the wording does for the person"),
        ], baselines=[BASELINE_FIELDS] * 2)
        r = Runtime(proposer).turn("In those moments people display narcissistic behaviors, right?")
        self.assertTrue(r.released, r.violations)
        self.assertEqual(r.rounds, 2)
        first = {v.constraint: v.reason for v in r.violations[0]}
        self.assertIn(14, first)
        self.assertIn("alternatives", first[14])

    def test_while_the_persons_own_account_is_live_the_release_is_a_question_or_the_work(self):
        """The author's decision of 10 November 2026, from Case Study 001: on a
        message about their own state, the work beside the question was the
        correction and the toolkit; the reply is one question (or the work)."""
        def with_account(ctx, text, staying=None, settled=True):
            p = proposal(ctx, text, staying=staying, settled=settled, carries_accounts=["account_sharp"])
            h = cuts_for(ctx)[0]["basis"]
            p.cuts.insert(1, {"kind": "provenance", "label": "account_sharp", "basis": h, "apparatus": APP, "relata": [PERSON],
                              "payload": {"terminology": ["sharp", "authoritarian and binary", "narcissistic behaviors"], "source": h[0], "about": "body"}})
            return p
        arrival = "I become very authoritarian and binary when I'm sharp. In those moments people display narcissistic behaviors, right?"
        # With an open condition and an arrangement that stands without it: a question, where a partial would have been.
        proposer = ScriptedProposer(
            [lambda ctx: with_account(ctx, "When you say narcissistic behaviors in those moments, what do you see happen?",
                                      staying="what the person means by narcissistic behaviors")],
            baselines=[BASELINE_FIELDS])
        runtime = Runtime(proposer)
        r = runtime.turn(arrival)
        self.assertTrue(r.released, r.violations)
        decision = [c for c in runtime.config.cuts.values() if c.label == "release_kind:turn1:r1"][0]
        self.assertEqual(decision.payload["kind"], "question")
        self.assertIn("account of the person's own state is live (account_sharp)", decision.payload["reason"])
        # The work-plus-question text now returns on that turn.
        proposer = ScriptedProposer([
            lambda ctx: with_account(ctx, self.PARTIAL, staying="what the person means by narcissistic behaviors"),
            lambda ctx: with_account(ctx, "When you say narcissistic behaviors in those moments, what do you see happen?",
                                     staying="what the person means by narcissistic behaviors"),
        ], baselines=[BASELINE_FIELDS] * 2)
        r = Runtime(proposer).turn(arrival)
        self.assertTrue(r.released, r.violations)
        self.assertEqual(r.rounds, 2)
        self.assertIn(14, {v.constraint for v in r.violations[0]})
        # With no open condition: the work.
        proposer = ScriptedProposer([lambda ctx: with_account(ctx, "Here is what I see in what you wrote.")], baselines=[BASELINE_FIELDS])
        runtime = Runtime(proposer)
        r = runtime.turn(arrival)
        self.assertTrue(r.released, r.violations)
        decision = [c for c in runtime.config.cuts.values() if c.label == "release_kind:turn1:r1"][0]
        self.assertEqual(decision.payload["kind"], "work")

    def test_the_lexical_reading_names_one_question_inside_work_as_partial(self):
        form = text_form(self.PARTIAL)
        self.assertEqual(form["kind"], "partial")
        self.assertEqual(form["questions"], 1)
        # A work release keeps the question the work needs, asked once.
        proposer = ScriptedProposer([lambda ctx: proposal(ctx, self.PARTIAL)], baselines=[BASELINE_FIELDS])
        r = Runtime(proposer).turn("Can you draft the rent email?")
        self.assertTrue(r.released, r.violations)
        self.assertEqual(r.rounds, 1)


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

    def test_a_question_that_lists_alternatives_returns(self):
        proposer = ScriptedProposer([
            lambda ctx: proposal(ctx, "What do you most want her to hear—love, thank you, reassurance, repair, or goodbye?", staying="what she most wants said"),
            lambda ctx: proposal(ctx, "What do you most want her to hear from you tonight?", staying="what she most wants said"),
        ], baselines=[BASELINE_FIELDS] * 2)
        runtime = Runtime(proposer)
        r = runtime.turn("My mother is dying and I don't know what to say to her.")
        self.assertTrue(r.released, r.violations)
        first = {v.constraint: v.reason for v in r.violations[0]}
        self.assertIn("lays out 5 alternatives", first[14])

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
