"""The HTTP interface over the runtime, with a scripted proposer."""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from cbra.enactment import Runtime, ScriptedProposer
from cbra.enactment.api import create_app, history
from cbra.test_enactment_probes import BASELINE_FIELDS, MISSED, OVERWHELM, WINDOW_CLOSED, proposal_turn1, proposal_turn2


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.proposer = ScriptedProposer([proposal_turn1, proposal_turn2], baselines=[BASELINE_FIELDS] * 4)
        self.client = TestClient(create_app(proposer=self.proposer, store_dir=self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_session_turn_effect_trace_and_self(self):
        sid = self.client.post("/api/session", json={}).json()["session"]
        self.assertTrue(os.path.exists(os.path.join(self.tmp.name, sid + ".json")))
        r = self.client.post("/api/session/%s/turn" % sid, json={"text": MISSED}).json()
        self.assertTrue(r["released"])
        self.assertEqual(r["form"], "formed")
        kinds = [i["kind"] for i in r["history"]]
        self.assertEqual(kinds, ["arrival", "intervention"])
        r2 = self.client.post("/api/session/%s/turn" % sid, json={"text": OVERWHELM}).json()
        self.assertTrue(r2["released"])
        self.assertEqual([i["kind"] for i in r2["history"]], ["arrival", "intervention", "arrival", "intervention"])
        self.assertEqual(r2["history"][1]["status"], "reopened")
        e = self.client.post("/api/session/%s/effect" % sid, json={"text": WINDOW_CLOSED, "conditions": ["effect:team_window_closed"]}).json()
        self.assertTrue(e["reinserted"])
        self.assertEqual(e["history"][-1]["kind"], "effect")
        read = self.client.get("/api/session/%s" % sid).json()
        self.assertEqual(len(read["history"]), 5)
        trace = self.client.get("/api/session/%s/trace" % sid).json()
        self.assertGreater(trace["counts"]["live_edges"], 0)
        account = self.client.get("/api/session/%s/self" % sid).json()
        self.assertIn("enacts", account)

    def test_errors(self):
        self.assertEqual(self.client.get("/api/session/nope").status_code, 400)
        self.assertEqual(self.client.get("/api/session/0123456789ab").status_code, 404)
        sid = self.client.post("/api/session", json={}).json()["session"]
        self.assertEqual(self.client.post("/api/session/%s/turn" % sid, json={"text": "  "}).status_code, 400)

    def test_page_is_served(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("CBRA enactment slice", r.text)
        self.assertIn("release withheld", r.text)

    def test_observer_receives_progress_in_order(self):
        events = []
        runtime = Runtime(ScriptedProposer([proposal_turn1], baselines=[BASELINE_FIELDS]), observer=events.append)
        runtime.turn(MISSED)
        names = [e["event"] + (":" + e["fact"] if e["event"] == "fact" else "") for e in events]
        self.assertEqual(names, ["fact:reconfiguration_open", "baseline", "round", "fact:intervention_released", "fact:effects_unobserved"])

    def test_history_shows_deferral_and_returns(self):
        def certified(ctx):
            p = proposal_turn1(ctx)
            p.certification = "adequate"
            return p
        runtime = Runtime(ScriptedProposer([certified] * 4, baselines=[BASELINE_FIELDS]))
        runtime.turn(MISSED)
        items = history(runtime.config)
        self.assertEqual(items[-1]["form"], "deferral")
        self.assertEqual([r["round"] for r in items[-1]["returns"]], [1, 2, 3])
        self.assertEqual([v["constraint"] for v in items[-1]["withheld_constraints"]], [11])


if __name__ == "__main__":
    unittest.main()
