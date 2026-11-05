"""Unit tests for the enacting core: live dependencies, propagation,
records that do not propagate, derived deltas, restoration."""

import json
import os
import tempfile
import unittest

from cbra.enactment import (
    Configuration,
    Delta,
    EnactmentError,
    Formation,
    JsonStore,
    care_delta,
    check_all,
    play_delta,
)


def _config_with_chain():
    cfg = Configuration()
    t1 = cfg.inscribe("I missed the deadline.", "user_message")
    a = cfg.enact("apparatus", "apparatus", basis=[t1.handle], apparatus=["text channel"])
    e = cfg.enact("event", "event", basis=[t1.handle], apparatus=["text channel"],
                  relata=["the person writing", "the team"],
                  invalidation_conditions=["person_state_disclosure"], payload={"turn": "turn1"})
    arr = cfg.enact("arrangement", "arr", basis=[t1.handle], apparatus=["text channel"], depends_on=[e.id],
                    payload={"turn": "turn1", "role": "enacted", "sequence": ["b", "a"]})
    iv = cfg.enact("intervention", "iv", basis=[t1.handle], apparatus=["delivery"], depends_on=[arr.id],
                   payload={"turn": "turn1", "text": "..."})
    return cfg, t1, a, e, arr, iv


class GraphTests(unittest.TestCase):
    def test_enact_requires_live_dependencies_and_known_basis(self):
        cfg = Configuration()
        with self.assertRaises(EnactmentError):
            cfg.enact("event", "x", basis=["t9"], apparatus=["a"])
        with self.assertRaises(EnactmentError):
            cfg.enact("event", "x", depends_on=["c9"], apparatus=["a"])
        with self.assertRaises(EnactmentError):
            cfg.enact("phenomenon", "x", apparatus=["a"])

    def test_disturbance_propagates_through_live_edges_and_reopens_interventions(self):
        cfg, t1, a, e, arr, iv = _config_with_chain()
        self.assertEqual(cfg.dependents_of(e.id), {arr.id})
        delta = cfg.disturb("person_state_disclosure", source=t1.handle, reason="disclosure")
        invalidated = dict(delta.invalidated)
        self.assertIn(e.id, invalidated)
        self.assertIn(arr.id, invalidated)
        self.assertIn(iv.id, invalidated)
        self.assertTrue(invalidated[arr.id].startswith("depends on %s" % e.id))
        self.assertEqual(cfg.cuts[iv.id].status, "reopened")
        self.assertEqual(cfg.cuts[a.id].status, "active")
        self.assertEqual(delta.reopened_interventions, [iv.id])
        self.assertTrue(delta.structural())
        self.assertGreater(delta.version_to, delta.version_from)

    def test_record_only_carries_without_edges(self):
        cfg, t1, a, e, arr, iv = _config_with_chain()
        key = cfg.record_only(cfg.cuts[e.id].as_record())
        self.assertIn(key, cfg.records)
        self.assertNotIn(key, cfg.cuts)
        self.assertEqual(cfg.dependents_of(key), set())
        delta = cfg.disturb("something_else", reason="no cut carries this")
        self.assertFalse(delta.structural())
        self.assertEqual(delta.version_to, delta.version_from)

    def test_lifecycle_facts_are_bounded(self):
        cfg = Configuration()
        cfg.fact("reconfiguration_open", turn="turn1")
        for name in ("accepted", "valid", "caring", "posthuman", "complete"):
            with self.assertRaises(EnactmentError):
                cfg.fact(name)

    def test_delta_without_structure_is_a_description(self):
        self.assertFalse(Delta(kind="x", version_from=1, version_to=1, note="care happened").structural())
        self.assertTrue(Delta(kind="x", version_from=1, version_to=2, added=["c1"]).structural())

    def test_care_and_play_deltas_are_derived_from_arrangements(self):
        cfg = Configuration()
        t1 = cfg.inscribe("hello", "user_message")
        base = {"turn": "turn1", "role": "baseline", "sequence": ["explain", "recommit"], "scale": "full",
                "distribution": "person", "response_demand": {"p": ["explain", "recommit"]}}
        cfg.enact("arrangement", "b", basis=[t1.handle], apparatus=["a"], payload=dict(base),
                  allocations={"p": {"burden": 0.9}})
        self.assertEqual(care_delta(cfg, "turn1"), {})  # no enacted arrangement yet
        enacted = dict(base, role="enacted", sequence=["ask what the team needs", "reduce scope"], scale="reduced",
                       distribution="shared")
        cfg.enact("arrangement", "e", basis=[t1.handle], apparatus=["a"], payload=enacted,
                  allocations={"p": {"burden": 0.4}, "team": {"burden": 0.4}})
        delta = care_delta(cfg, "turn1")
        self.assertEqual(set(delta), {"sequence", "scale", "distribution", "burden"})
        self.assertEqual(play_delta(cfg, "turn1"), {})
        cfg.enact("arrangement", "alt-paraphrase", basis=[t1.handle], apparatus=["a"],
                  payload=dict(enacted, role="alternative", uptake="voluntary"),
                  allocations={"p": {"burden": 0.4}, "team": {"burden": 0.4}})
        self.assertEqual(play_delta(cfg, "turn1"), {}, "a paraphrase is not an alternative arrangement")
        alt = cfg.enact("arrangement", "alt", basis=[t1.handle], apparatus=["a"],
                        payload=dict(enacted, role="alternative", uptake="voluntary", distribution="hand-off",
                                     medium="shared document"))
        self.assertEqual(set(play_delta(cfg, "turn1")[alt.id]), {"distribution", "medium", "burden"})

    def test_arrangements_compare_by_role_and_kind_not_wording(self):
        from cbra.enactment.arrangements import CARE_DIMENSIONS, arrangement_fields, difference
        cfg = Configuration()
        t1 = cfg.inscribe("hello", "user_message")
        a = cfg.enact("arrangement", "a", basis=[t1.handle], apparatus=["x"], payload={
            "turn": "turn1", "role": "baseline",
            "positions": [{"role": "person_writing", "label": "the person responsible for the report"},
                          {"role": "affected_others", "label": "the program officer"}],
            "sequence": [{"kind": "acknowledge", "text": "Own the miss plainly."},
                         {"kind": "communicate_external", "text": "Email the officer today."}],
            "scale": "full", "pace": "immediate", "distribution": "person",
            "support": [{"kind": "script", "text": "a draft email"}],
            "response_demand": {"the person responsible for the report": ["communicate", "plan"]}},
            allocations={"the person responsible for the report": {"burden": 0.85, "capacity": 0.8},
                         "the program officer": {"burden": 0.05, "capacity": 0.6}})
        b = cfg.enact("arrangement", "b", basis=[t1.handle], apparatus=["x"], payload={
            "turn": "turn1", "role": "enacted",
            "positions": [{"role": "person_writing", "label": "the person who missed the deliverable"},
                          {"role": "affected_others", "label": "the internal lead or grant contact"}],
            "sequence": [{"kind": "acknowledge", "text": "Acknowledge the missed Friday deliverable."},
                         {"kind": "communicate_external", "text": "Send a short note to the contact."}],
            "scale": "full", "pace": "immediate", "distribution": "person",
            "support": [{"kind": "script", "text": "a compact message"}],
            "response_demand": {"the person who missed the deliverable": ["plan", "communicate"]}},
            allocations={"the person who missed the deliverable": {"burden": 0.8, "capacity": 0.75},
                         "the internal lead or grant contact": {"burden": 0.1, "capacity": 0.6}})
        self.assertEqual(difference(arrangement_fields(a), arrangement_fields(b), CARE_DIMENSIONS), {},
                         "different wording, labels, and sub-tolerance numbers are the same arrangement")
        c = cfg.enact("arrangement", "c", basis=[t1.handle], apparatus=["x"], payload=dict(
            b.payload, sequence=[{"kind": "communicate_internal", "text": "One line to the lead."},
                                 {"kind": "hand_off", "text": "Lead decides routing."}],
            distribution="shared", scale="reduced"),
            allocations={"the person who missed the deliverable": {"burden": 0.4, "capacity": 0.5},
                         "the internal lead or grant contact": {"burden": 0.4, "capacity": 0.7}})
        diff = difference(arrangement_fields(a), arrangement_fields(c), CARE_DIMENSIONS)
        self.assertEqual(set(diff), {"sequence", "distribution", "scale", "burden", "presumed_capacity"})
        self.assertEqual(diff["sequence"][1], ["communicate_internal", "hand_off"])

    def test_text_against_claim_tolerates_an_opening_acknowledgment(self):
        from cbra.enactment.arrangements import text_against_claim
        claimed = {"sequence": ["check_safety", "hand_off", "rest"], "scale": "minimal", "distribution": "shared",
                   "burden": {"person_writing": 0.4, "authority": 0.3},
                   "response_demand": {"person_writing": ["decide", "communicate"]}}
        read_ok = dict(claimed, sequence=["acknowledge", "check_safety", "seek_support"],
                       burden={"person_writing": 0.5, "authority": 0.3})
        self.assertEqual(text_against_claim(claimed, read_ok), [])
        read_promise_first = dict(claimed, sequence=["apologize", "recommit", "explain", "plan"],
                                  burden={"person_writing": 0.85, "authority": 0.05},
                                  response_demand={"person_writing": ["explain", "plan", "recommit", "warn"]})
        reasons = text_against_claim(claimed, read_promise_first)
        self.assertEqual(len(reasons), 4, reasons)
        self.assertTrue(any("leads with recommit/explain" in r for r in reasons))
        self.assertTrue(any("burden 0.85" in r for r in reasons))
        read_full = dict(claimed, scale="expanded", distribution="person")
        self.assertEqual(len(text_against_claim(claimed, read_full)), 2)

    def test_object_valued_labels_are_carried_as_labels(self):
        cfg = Configuration()
        t1 = cfg.inscribe("hello", "user_message")
        cut = cfg.enact("provenance", "p", basis=[t1.handle], apparatus=["a"],
                        relata=[{"role": "person_writing", "label": "the person writing"}, "sleep"],
                        unmarked=[{"text": "cause of overwhelm"}],
                        invalidation_conditions=[{"kind": "revision:p"}],
                        relations=[[{"label": "sleep"}, "conditions", {"label": "the person writing"}]])
        self.assertEqual(cut.relata, ("the person writing", "sleep"))
        self.assertEqual(cut.unmarked, ("cause of overwhelm",))
        self.assertEqual(cut.invalidation_conditions, ("revision:p",))
        self.assertEqual(cut.relations, (("sleep", "conditions", "the person writing"),))
        self.assertEqual(cut.relata[0] in {"the person writing": 1}, True)

    def test_global_entity_constraint_requires_continuity_cut(self):
        cfg = Configuration()
        t0 = cfg.inscribe("earlier", "user_message")
        cfg.enact("position", "earlier_position", basis=[t0.handle], apparatus=["a"],
                  relata=["the team"], payload={"turn": "turn0"})
        t1 = cfg.inscribe("now", "user_message")
        app = cfg.enact("apparatus", "app", basis=[t1.handle], apparatus=["a"], payload={"turn": "turn1"})
        ev = cfg.enact("event", "ev", basis=[t1.handle], apparatus=["a"], relata=["the team"], payload={"turn": "turn1"})
        f = Formation(turn="turn1", arrivals=[t1.handle], cuts=[app.id, ev.id], variation_constraint="n/a")
        self.assertIn(2, [v.constraint for v in check_all(cfg, f)])
        cont = cfg.enact("continuity", "cont", basis=[t1.handle], apparatus=["a"], relata=["the team"],
                         payload={"turn": "turn1"})
        f.cuts.append(cont.id)
        self.assertNotIn(2, [v.constraint for v in check_all(cfg, f)])

    def test_restoration_keeps_relata_local_and_edges_live(self):
        cfg, t1, a, e, arr, iv = _config_with_chain()
        cfg.fact("intervention_released", intervention=iv.id)
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonStore(os.path.join(tmp, "cfg.json"))
            store.save(cfg)
            with open(store.path, encoding="utf-8") as handle:
                raw = json.load(handle)
            self.assertNotIn("entities", raw)
            self.assertTrue(all("relata" in c for c in raw["cuts"]))
            restored = store.load()
        self.assertEqual(restored.version, cfg.version)
        self.assertEqual(restored.dependents_of(e.id), {arr.id})
        self.assertEqual(len([c for c in restored.continuity if c["cut"] == e.id]), 1)
        delta = restored.disturb("person_state_disclosure", reason="after restore")
        self.assertIn(iv.id, delta.reopened_interventions)
        self.assertEqual(restored.lifecycle[-1]["fact"], "intervention_released")


if __name__ == "__main__":
    unittest.main()
