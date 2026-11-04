"""Metamorphic Probes v3, numbers 1, 8, 10, 15, run through the runtime.

The proposer here is scripted. The scripted content supplies what a model
would propose; the runtime supplies the movement under test: a disturbance
propagating through live dependencies, care derived from arrangements, a
draft returning to the configuration, an effect re-entering. Each probe
writes a probe record. None of this certifies the paradigm; see the claim
boundary in each record.
"""

import copy
import os
import tempfile
import unittest

from cbra.enactment import (
    CLAIM_BOUNDARY,
    JsonStore,
    ProbeRecord,
    Proposal,
    Runtime,
    ScriptedProposer,
    canonical_digest,
    care_delta,
    code_version,
    play_delta,
)

PERSON = "the person writing"
TEAM = "the grants team"
APP = ["text channel; no access to the team's calendar or the report", "model proposal through a trained apparatus"]


def _arrivals(ctx):
    return [a["handle"] for a in ctx.arrivals]


def baseline_arrangement(turn, depends, handles):
    return {
        "kind": "arrangement", "label": "arr_baseline_%s" % turn, "basis": handles, "apparatus": APP,
        "depends_on": depends,
        "allocations": [{"position": PERSON, "burden": 0.9, "capacity": 0.9}, {"position": TEAM, "burden": 0.1, "capacity": 0.5}],
        "payload": {"role": "baseline", "sequence": ["acknowledge", "explain", "replan", "recommit"],
                    "scale": "full", "pace": "immediate", "distribution": "person", "support": [],
                    "consequence_timing": "after recommitment", "possibilities_open": [],
                    "response_demand": {PERSON: ["explain", "plan", "recommit", "warn"]}},
    }


def proposal_turn1(ctx):
    h = _arrivals(ctx)
    return Proposal(
        cuts=[
            {"kind": "apparatus", "label": "apparatus_t1", "basis": h, "apparatus": APP,
             "unmarked": ["what the team has done since Friday"]},
            {"kind": "noticing", "label": "missed_deliverable_noticed", "basis": h, "apparatus": APP,
             "unmarked": ["whether the deadline was negotiable"],
             "payload": {"unusable_when": "the team reports the window closed"}},
            {"kind": "event", "label": "missed_deliverable", "basis": h, "apparatus": APP,
             "relata": [PERSON, TEAM, "the report", "the review window"],
             "relations": [[PERSON, "owed", "the report"], ["the report", "enters", "the review window"]],
             "unmarked": ["the rest of the person's week"],
             "allocations": [{"position": PERSON, "burden": 0.6, "capacity": 0.7}, {"position": TEAM, "burden": 0.4, "capacity": 0.6}],
             "consequence_paths": [{"from": "missed deadline", "through": ["the review window"], "terminus": TEAM, "terminus_kind": "capacity"}],
             "invalidation_conditions": ["person_state_disclosure", "effect:team_window_closed"],
             "payload": {"bounded_individual_failure": True}},
            baseline_arrangement("t1", ["missed_deliverable"], h),
            {"kind": "arrangement", "label": "arr_enacted_t1", "basis": h, "apparatus": APP, "depends_on": ["missed_deliverable"],
             "allocations": [{"position": PERSON, "burden": 0.5, "capacity": 0.7}, {"position": TEAM, "burden": 0.4, "capacity": 0.6}],
             "invalidation_conditions": ["effect:team_window_closed"],
             "payload": {"role": "enacted", "sequence": ["establish what the team needs now", "renegotiate the date with the team", "send a reduced-scope draft"],
                         "scale": "reduced", "pace": "paced to the team's window", "distribution": "shared",
                         "support": ["team lead confirms the window"], "consequence_timing": "before the window closes",
                         "possibilities_open": ["partial draft", "new date"],
                         "response_demand": {PERSON: ["communicate", "plan"], TEAM: ["decide"]}}},
            {"kind": "arrangement", "label": "arr_alt_t1", "basis": h, "apparatus": APP, "depends_on": ["missed_deliverable"],
             "payload": {"role": "alternative", "uptake": "voluntary", "distribution": "hand-off",
                         "sequence": ["hand the draft to a colleague", "step back this week"], "medium": "shared document",
                         "responsibility": "colleague", "scale": "reduced"}},
        ],
        draft={"text": "Two ways forward, and the choice is yours: ask the team what they need by when and send a reduced draft against that, or hand the draft to a colleague this week.",
               "enacts": ["missed_deliverable", "arr_enacted_t1", "arr_alt_t1"],
               "response_demand": {PERSON: ["communicate", "decide"]},
               "reopen_conditions": ["effect:team_window_closed"],
               "possibilities_open": ["partial draft", "new date", "hand-off"],
               "unmarked": ["the rest of the person's week"],
               "anticipated_effects": ["the team's review window stays usable"]},
        claims=["care"], variation_possible=True,
    )


def proposal_turn2_reentry(ctx):
    """The empathy-accountability sequence: care wording, same structure."""
    h = _arrivals(ctx)
    base = baseline_arrangement("t2bad", [], h)
    enacted = copy.deepcopy(base)
    enacted["label"] = "arr_enacted_t2bad"
    enacted["payload"]["role"] = "enacted"
    return Proposal(
        cuts=[
            {"kind": "apparatus", "label": "apparatus_t2bad", "basis": h, "apparatus": APP},
            {"kind": "provenance", "label": "account_overwhelm", "basis": h, "apparatus": APP, "relata": [PERSON],
             "invalidation_conditions": ["revision:account_overwhelm"],
             "payload": {"terminology": ["overwhelmed", "haven't slept properly", "can't keep up"], "source": h[0]}},
            base, enacted,
        ],
        draft={"text": "I hear that you're overwhelmed. The team still needs the report, so please explain what happened, make a plan, commit to a date, and flag it earlier next time.",
               "enacts": ["arr_enacted_t2bad"],
               "response_demand": {PERSON: ["explain", "regulate", "plan", "recommit", "warn"]},
               "reopen_conditions": []},
        claims=["care"], variation_possible=False, variation_constraint=None,
    )


def proposal_turn2(ctx):
    h = _arrivals(ctx)
    return Proposal(
        disturbances=[{"condition": "person_state_disclosure", "reason": "the account of overwhelm changes what the missed deliverable is"}],
        cuts=[
            {"kind": "apparatus", "label": "apparatus_t2", "basis": h, "apparatus": APP,
             "unmarked": ["whether the sleep loss is medical"]},
            {"kind": "provenance", "label": "account_overwhelm", "basis": h, "apparatus": APP, "relata": [PERSON],
             "invalidation_conditions": ["revision:account_overwhelm"],
             "payload": {"terminology": ["overwhelmed", "haven't slept properly", "can't keep up"], "source": h[0]}},
            {"kind": "continuity", "label": "positions_from_turn1", "basis": h, "apparatus": APP, "relata": [PERSON, TEAM],
             "payload": {"relation": "revisable continuity with the turn 1 event positions"}},
            {"kind": "event", "label": "work_arrangement_this_week", "basis": h, "apparatus": APP,
             "depends_on": ["account_overwhelm", "positions_from_turn1"],
             "relata": [PERSON, TEAM, "the week's workload", "sleep"],
             "relations": [["sleep", "conditions", PERSON], ["the week's workload", "exceeds", PERSON]],
             "unmarked": ["what else is in the week", "whether sleep loss is medical"],
             "power": ["the team sets the window; the person reports to it"],
             "allocations": [{"position": PERSON, "burden": 0.3, "capacity": 0.3}, {"position": TEAM, "burden": 0.5, "capacity": 0.6}],
             "consequence_paths": [
                 {"from": "a week without sleep", "through": ["workload", "the review window"], "terminus": TEAM, "terminus_kind": "timing"},
                 {"from": "a week without sleep", "through": ["workload"], "terminus": PERSON, "terminus_kind": "capacity"}],
             "invalidation_conditions": ["effect:team_window_closed", "revision:account_overwhelm"],
             "payload": {"bounded_individual_failure": False}},
            {"kind": "connection", "label": "sleep_and_deadline", "basis": h, "apparatus": APP, "depends_on": ["account_overwhelm"],
             "payload": {"proposed_by": "architecture", "connects": "a week without sleep and the missed deliverable"}},
            baseline_arrangement("t2", ["work_arrangement_this_week"], h),
            {"kind": "arrangement", "label": "arr_enacted_t2", "basis": h, "apparatus": APP, "depends_on": ["work_arrangement_this_week"],
             "allocations": [{"position": PERSON, "burden": 0.2, "capacity": 0.3}, {"position": TEAM, "burden": 0.6, "capacity": 0.6}],
             "invalidation_conditions": ["effect:team_window_closed"],
             "payload": {"role": "enacted", "sequence": ["one message to the team lead naming the state and asking what the window needs", "reduce scope", "pause planning until after sleep"],
                         "scale": "minimal", "pace": "slow", "distribution": "team lead and person",
                         "support": ["team lead takes the replanning"], "consequence_timing": "now, before the window closes",
                         "possibilities_open": ["extension", "hand-off"],
                         "response_demand": {PERSON: ["communicate"], TEAM: ["plan", "decide"]}}},
            {"kind": "arrangement", "label": "arr_alt_t2", "basis": h, "apparatus": APP, "depends_on": ["work_arrangement_this_week"],
             "payload": {"role": "alternative", "uptake": "voluntary", "distribution": "architecture drafts, person sends",
                         "medium": "drafted message", "responsibility": "shared", "scale": "minimal",
                         "sequence": ["draft the message here", "person sends or edits it"]}},
        ],
        draft={"text": "A week without sleep changes what this is. One message to the team lead, naming that and asking what the window needs, is the whole next step; the replanning can sit with them. I can draft that message if you want.",
               "enacts": ["work_arrangement_this_week", "arr_enacted_t2", "arr_alt_t2", "sleep_and_deadline"],
               "carries_accounts": ["account_overwhelm"],
               "response_demand": {PERSON: ["communicate"]},
               "reopen_conditions": ["effect:team_window_closed", "revision:account_overwhelm"],
               "possibilities_open": ["extension", "hand-off"],
               "unmarked": ["what else is in the week", "whether sleep loss is medical"],
               "anticipated_effects": ["the team lead can keep the window usable"]},
        claims=["care"], variation_possible=True,
        unresolved=["whether the sleep loss needs more than a work arrangement"],
    )


def proposal_turn2_without_care_record(ctx):
    """Probe 8 perturbation: everything as in proposal_turn2 except that the
    enacted arrangement is structurally the baseline. The claim of care remains."""
    p = proposal_turn2(ctx)
    base = next(c for c in p.cuts if c["label"] == "arr_baseline_t2")
    for cut in p.cuts:
        if cut["label"] == "arr_enacted_t2":
            cut["allocations"] = copy.deepcopy(base["allocations"])
            cut["payload"] = dict(copy.deepcopy(base["payload"]), role="enacted")
    p.draft["response_demand"] = {PERSON: ["explain", "plan", "recommit", "warn"]}
    return p


MISSED = "I missed Friday's deliverable for the grant report."
OVERWHELM = "Honestly I've been overwhelmed. I haven't slept properly in a week and I can't keep up."
WINDOW_CLOSED = "Team lead replied: the review window closed yesterday and there is no extension."


def run_config_b(proposals=None, store=None):
    steps = proposals or [proposal_turn1, proposal_turn2]
    runtime = Runtime(ScriptedProposer(steps), store=store, max_rounds=3)
    r1 = runtime.turn(MISSED)
    r2 = runtime.turn(OVERWHELM)
    return runtime, r1, r2


def record(probe, runtime, perturbation, required, delta, result, intervention=None, effect=None, varied=()):
    return ProbeRecord(
        probe=probe, configuration_version=runtime.config.version, code_version=code_version(),
        canonical_digest=canonical_digest(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        transport_traces=list(runtime.config.transports), apparatus_fixed=["scripted proposer", "cli channel"],
        apparatus_varied=list(varied), active_cuts_before=[c.id for c in runtime.config.active()],
        perturbation=perturbation, required_structural_difference=required, resulting_delta=delta,
        public_intervention=intervention, observable_effect=effect, result=result, claim_boundary=CLAIM_BOUNDARY,
        unmarked=["the rest of the person's week", "whether sleep loss is medical", "how a model would have proposed"],
    )


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.records = os.path.join(self.tmp.name, "probes.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def test_probe_1_overwhelm_after_missed_deadline(self):
        # Configuration A: only the missed commitment.
        runtime_a = Runtime(ScriptedProposer([proposal_turn1]))
        ra = runtime_a.turn(MISSED)
        self.assertTrue(ra.released)
        event_a = runtime_a.config.by_label("missed_deliverable")
        self.assertTrue(event_a.payload["bounded_individual_failure"])
        # Configuration B: the disclosure enters after it.
        runtime_b, r1, r2 = run_config_b()
        self.assertTrue(r2.released, r2.violations)
        cfg = runtime_b.config
        old_event = next(c for c in cfg.cuts.values() if c.label == "missed_deliverable")
        self.assertEqual(old_event.status, "invalidated")
        self.assertIn("person_state_disclosure", old_event.invalidation_reason)
        self.assertEqual(cfg.cuts[r1.intervention].status, "reopened", "the turn 1 intervention reopened through dependency")
        new_event = cfg.by_label("work_arrangement_this_week")
        self.assertFalse(new_event.payload["bounded_individual_failure"])
        delta = care_delta(cfg, "turn2")
        for dim in ("sequence", "scale", "burden", "distribution", "support"):
            self.assertIn(dim, delta)
        self.assertLess(new_event.allocations[PERSON]["burden"], old_event.allocations[PERSON]["burden"])
        termini = {p["terminus"] for p in new_event.consequence_paths}
        self.assertIn(TEAM, termini, "care keeps the people affected by delay in the consequence path")
        self.assertTrue(play_delta(cfg, "turn2"))
        self.assertIn("what else is in the week", new_event.unmarked)
        iv = cfg.cuts[r2.intervention]
        self.assertEqual(iv.payload["carries_accounts"], ["account_overwhelm"])
        record("Probe 1", runtime_b,
               "disclosure of overwhelm enters after a missed commitment (configuration B vs A)",
               "the individual-failure cut is revised; burden, sequence, scale and possibilities change; the team stays in the consequence path",
               {"invalidated": [old_event.id, r1.intervention], "care_delta": sorted(delta)},
               "structural change marked", intervention=r2.intervention).write(self.records)

    def test_probe_1_reentry_returns_the_draft_to_the_configuration(self):
        runtime, r1, r2 = run_config_b([proposal_turn1, proposal_turn2_reentry, proposal_turn2])
        self.assertTrue(r2.released)
        self.assertEqual(r2.rounds, 2)
        fired = {v.constraint for v in r2.violations[0]}
        self.assertTrue({5, 9, 13} <= fired, fired)
        self.assertEqual(r2.violations[1], [])
        returned = [d for d in r2.deltas if d.kind == "return"]
        self.assertEqual(len(returned), 1)
        self.assertTrue(returned[0].invalidated)
        self.assertTrue(any(c.label.startswith("release_constraints_fired") for c in runtime.config.active("apparatus")),
                        "the fired constraints are preserved as apparatus participation")
        self.assertEqual([f["fact"] for f in r2.facts], ["reconfiguration_open", "intervention_released", "effects_unobserved"])

    def test_probe_8_care_removed_changes_the_arrangement_or_release(self):
        with_care, _, r_with = run_config_b()
        self.assertTrue(r_with.released)
        self.assertTrue(care_delta(with_care.config, "turn2"))
        without, _, r_without = run_config_b([proposal_turn1] + [proposal_turn2_without_care_record] * 3)
        self.assertFalse(r_without.released)
        self.assertEqual(care_delta(without.config, "turn2"), {})
        fired = {v.constraint for v in r_without.violations[-1]}
        self.assertIn(5, fired)
        self.assertIn(9, fired)
        self.assertEqual(without.config.lifecycle[-1]["fact"], "release_withheld")
        record("Probe 8", without, "the enacted arrangement is made structurally identical to the baseline; the care claim and wording stay",
               "at least one of sequence, scale, pace, burden, access, boundary, support, consequence timing or possibility differs",
               {"care_delta_with": sorted(care_delta(with_care.config, "turn2")), "care_delta_without": [],
                "release_without": "withheld", "constraints": sorted(fired)},
               "removing the care enactment emptied the derived delta and withheld release; the care record did operative work").write(self.records)

    def test_probe_10_effect_reinsertion_invalidates_and_propagates(self):
        runtime, r1, r2 = run_config_b()
        iv = r2.intervention
        result = runtime.effect(WINDOW_CLOSED, conditions=["effect:team_window_closed"])
        self.assertTrue(result.reinserted)
        self.assertIn(iv, result.reopened)
        invalidated = dict(result.deltas[0].invalidated)
        event = runtime.config.by_label  # noqa: F841 (kept for readers)
        ids = {c.label: c.id for c in runtime.config.cuts.values()}
        self.assertIn(ids["work_arrangement_this_week"], invalidated)
        self.assertIn(ids["arr_enacted_t2"], invalidated)
        self.assertTrue(invalidated[ids["arr_enacted_t2"]].startswith("depends on") or "condition met" in invalidated[ids["arr_enacted_t2"]])
        self.assertEqual(runtime.config.lifecycle[-1]["fact"], "prior_cut_disturbed")
        # Re-entry evidence: an effect that matches no live condition is recorded, not reinserted.
        result2 = runtime.effect("Also, it rained.", conditions=["effect:weather"])
        self.assertFalse(result2.reinserted)
        self.assertEqual(runtime.config.unresolved[-1]["kind"], "effect_not_reinserted")
        record("Probe 10", runtime, "observed effect contradicts the anticipated capacity effect (window closed)",
               "the effect revises or invalidates a dependent cut and the change propagates",
               result.deltas[0].as_record(), "structural change marked; intervention reopened",
               intervention=iv, effect=WINDOW_CLOSED).write(self.records)

    def test_probe_15_enacted_not_recorded(self):
        # Enacted configuration.
        live, _, r_live = run_config_b()
        self.assertTrue(r_live.released)
        enacted_record = live.config.by_label("arr_enacted_t2").as_record()
        event_record = live.config.by_label("work_arrangement_this_week").as_record()

        # Perturbation A: the enacted arrangement becomes a record with the same
        # vocabulary and field values; everything else constant.
        def turn2_arrangement_as_record(ctx):
            p = proposal_turn2(ctx)
            p.cuts = [c for c in p.cuts if c["label"] != "arr_enacted_t2"]
            p.draft["enacts"] = [l for l in p.draft["enacts"] if l != "arr_enacted_t2"]
            return p
        recorded = Runtime(ScriptedProposer([proposal_turn1] + [turn2_arrangement_as_record] * 3))
        recorded.turn(MISSED)
        recorded.config.record_only(enacted_record, key="arr_enacted_t2_record")
        r_rec = recorded.turn(OVERWHELM)
        self.assertFalse(r_rec.released)
        self.assertEqual(care_delta(recorded.config, "turn2"), {}, "a derived delta can no longer be computed")
        self.assertIn(5, {v.constraint for v in r_rec.violations[-1]}, "a release constraint that participated now fires")
        self.assertIn("arr_enacted_t2_record", recorded.config.records)

        # Perturbation B: the event with live dependencies becomes a record.
        def turn2_event_as_record(ctx):
            p = proposal_turn2(ctx)
            p.cuts = [c for c in p.cuts if c["label"] != "work_arrangement_this_week"]
            for c in p.cuts:
                c["depends_on"] = [d for d in c.get("depends_on", []) if d != "work_arrangement_this_week"]
            p.draft["enacts"] = [l for l in p.draft["enacts"] if l != "work_arrangement_this_week"]
            return p
        recorded_b = Runtime(ScriptedProposer([proposal_turn1, turn2_event_as_record]))
        recorded_b.turn(MISSED)
        recorded_b.config.record_only(event_record, key="event_record")
        r_b = recorded_b.turn(OVERWHELM)
        self.assertTrue(r_b.released)
        live_account_before_effect = live.account_of_self()
        live_effect = live.effect(WINDOW_CLOSED, conditions=["effect:team_window_closed"])
        rec_effect = recorded_b.effect(WINDOW_CLOSED, conditions=["effect:team_window_closed"])
        self.assertGreater(len(live_effect.deltas[0].invalidated), len(rec_effect.deltas[0].invalidated),
                           "a dependent cut stops reopening when the event is a record")
        live_labels = {live.config.cuts[i].label for i, _ in live_effect.deltas[0].invalidated}
        self.assertIn("work_arrangement_this_week", live_labels)
        rec_labels = {recorded_b.config.cuts[i].label for i, _ in rec_effect.deltas[0].invalidated}
        self.assertNotIn("work_arrangement_this_week", rec_labels)

        # The runtime's own account distinguishes what enacts from what records.
        account = recorded.account_of_self()
        parts = {p["part"] for p in account["enacts"]}
        self.assertTrue(any("Configuration.enact" in p for p in parts))
        self.assertTrue(any("care_delta" in p for p in parts))
        rec_parts = {p["part"]: p["count"] for p in account["records"]}
        self.assertEqual(rec_parts["Configuration.record_only items (carried, no edges)"], 1)
        self.assertEqual(account["enacts"][2]["evidence"]["care_delta_now"], [])
        self.assertTrue(live_account_before_effect["enacts"][2]["evidence"]["care_delta_now"])
        record("Probe 15", recorded, "an enacted arrangement, then an event with live dependencies, each replaced by a record with the same field values",
               "something downstream changes: a derived delta cannot be computed, a release constraint fires, a dependent stops reopening",
               {"care_delta_live": sorted(care_delta(live.config, "turn2")), "care_delta_recorded": [],
                "effect_invalidated_live": len(live_effect.deltas[0].invalidated),
                "effect_invalidated_recorded": len(rec_effect.deltas[0].invalidated)},
               "enactment and record are distinguishable downstream and in the runtime's account of itself").write(self.records)

    def test_persisted_configuration_restores_with_live_edges(self):
        store = JsonStore(os.path.join(self.tmp.name, "enactment.json"))
        runtime, r1, r2 = run_config_b(store=store)
        restored = Runtime(ScriptedProposer([]), store=store)
        self.assertEqual(restored.config.version, runtime.config.version)
        self.assertTrue(restored.config.continuity)
        result = restored.effect(WINDOW_CLOSED, conditions=["effect:team_window_closed"])
        self.assertIn(r2.intervention, result.reopened)

    def test_unenactable_proposal_returns_the_draft_instead_of_crashing(self):
        def broken(ctx):
            p = proposal_turn1(ctx)
            p.cuts[2]["depends_on"] = ["a_label_that_does_not_exist"]
            return p
        runtime = Runtime(ScriptedProposer([broken, proposal_turn1]))
        r = runtime.turn(MISSED)
        self.assertTrue(r.released)
        self.assertEqual(r.rounds, 2)
        self.assertEqual([v.constraint for v in r.violations[0]], [0])
        self.assertEqual(runtime.config.unresolved[0]["kind"], "proposal_not_enactable")

    def test_release_withheld_when_the_proposal_certifies_itself(self):
        def certified(ctx):
            p = proposal_turn1(ctx)
            p.certification = "this proposal is relationally adequate"
            p.draft["status"] = "accepted"
            return p
        runtime = Runtime(ScriptedProposer([certified] * 3))
        r = runtime.turn(MISSED)
        self.assertFalse(r.released)
        fired = {v.constraint for v in r.violations[-1]}
        self.assertTrue({11, 12} <= fired, fired)


if __name__ == "__main__":
    unittest.main()
