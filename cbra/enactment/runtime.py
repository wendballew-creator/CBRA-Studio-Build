"""The turn: inscribe, propose, enact, form release within recursion, return
effects.

There is no stage order inside a turn beyond what dependencies impose: a
proposal's disturbances are applied before its cuts because the cuts may
depend on what the disturbance invalidates; release constraints run on each
round because a draft that carries a known grammar returns to the
configuration; an effect re-enters through the same ``disturb`` that any
arrival uses.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .arrangements import care_delta, play_delta
from .graph import APPARATUS_MARK, Configuration, Cut, Delta, EnactmentError
from .proposer import Proposal, ProposalContext, Proposer
from .release import Formation, Violation, check_all


@dataclass
class TurnResult:
    turn: str
    released: bool
    text: Optional[str]
    intervention: Optional[str]
    rounds: int
    violations: List[List[Violation]]
    deltas: List[Delta]
    facts: List[Dict[str, Any]]

    def as_record(self) -> Dict[str, Any]:
        return {
            "turn": self.turn,
            "released": self.released,
            "text": self.text,
            "intervention": self.intervention,
            "rounds": self.rounds,
            "violations": [[v.as_record() for v in rnd] for rnd in self.violations],
            "deltas": [d.as_record() for d in self.deltas],
            "facts": list(self.facts),
        }


@dataclass
class EffectResult:
    trace: str
    conditions: List[str]
    deltas: List[Delta]
    reopened: List[str]
    reinserted: bool

    def as_record(self) -> Dict[str, Any]:
        return {
            "trace": self.trace,
            "conditions": list(self.conditions),
            "deltas": [d.as_record() for d in self.deltas],
            "reopened": list(self.reopened),
            "reinserted": self.reinserted,
        }


def _allocations(value: Any) -> Dict[str, Dict[str, float]]:
    if isinstance(value, Mapping):
        return {str(k): {kk: float(vv) for kk, vv in dict(v).items() if vv is not None} for k, v in value.items()}
    out: Dict[str, Dict[str, float]] = {}
    for item in value or []:
        position = str(item.get("position"))
        out[position] = {k: float(item[k]) for k in ("burden", "capacity") if item.get(k) is not None}
    return out


def _response_demand(value: Any) -> Dict[str, List[str]]:
    if isinstance(value, Mapping):
        return {str(k): list(v) for k, v in value.items()}
    out: Dict[str, List[str]] = {}
    for item in value or []:
        out[str(item.get("position"))] = list(item.get("demands", []))
    return out


class Runtime:
    def __init__(self, proposer: Proposer, store: Any = None, config: Optional[Configuration] = None,
                 max_rounds: int = 3, channel: str = "cli") -> None:
        self.proposer = proposer
        self.store = store
        self.config = config or (store.load() if store is not None and store.exists() else Configuration())
        self.max_rounds = max_rounds
        self.channel = channel
        self._turns = sum(1 for f in self.config.lifecycle if f.get("fact") == "reconfiguration_open")
        self.last_turn: Optional[str] = None

    # -- context -----------------------------------------------------------

    def conditions_available(self) -> List[str]:
        conditions = set()
        for cut in self.config.cuts.values():
            if cut.status != "invalidated":
                conditions.update(cut.invalidation_conditions)
        return sorted(conditions)

    def _context(self, turn: str, round_number: int, arrivals: Sequence[str],
                 violations: Sequence[Violation]) -> ProposalContext:
        cfg = self.config
        active = []
        for cut in cfg.cuts.values():
            if cut.status == "invalidated":
                continue
            active.append({
                "id": cut.id, "kind": cut.kind, "label": cut.label, "status": cut.status,
                "relata": list(cut.relata), "unmarked": list(cut.unmarked),
                "invalidation_conditions": list(cut.invalidation_conditions),
                "depends_on": list(cut.depends_on), "turn": cut.payload.get("turn"),
                "payload": json.loads(json.dumps(cut.payload)) if cut.kind in ("arrangement", "provenance", "intervention") else {},
            })
        reopened = [
            {"id": c.id, "text": c.payload.get("text"), "reason": c.invalidation_reason}
            for c in cfg.cuts.values() if c.kind == "intervention" and c.status == "reopened"
        ]
        return ProposalContext(
            turn=turn,
            round=round_number,
            arrivals=[cfg.transports[h].as_record() for h in arrivals],
            active_cuts=active,
            reopened_interventions=reopened,
            unresolved=list(cfg.unresolved),
            violations=[v.as_record() for v in violations],
            conditions_available=self.conditions_available(),
        )

    # -- enacting a proposal ----------------------------------------------

    def _enact_proposal(self, proposal: Proposal, formation: Formation, proposal_handle: str) -> None:
        cfg = self.config
        for d in proposal.disturbances:
            cfg.disturb(str(d.get("condition")), source=proposal_handle, reason=str(d.get("reason", "")))
        labels: Dict[str, str] = {}
        for cut in cfg.active():
            labels[cut.label] = cut.id
        pending = list(proposal.cuts)
        enacted: List[str] = []
        progress = True
        while pending and progress:
            progress = False
            for spec in list(pending):
                deps = [str(x) for x in spec.get("depends_on", [])]
                if all(dep in labels and cfg.cuts[labels[dep]].status != "invalidated" for dep in deps):
                    cut = self._enact_spec(spec, labels, formation, proposal_handle)
                    labels[cut.label] = cut.id
                    enacted.append(cut.id)
                    pending.remove(spec)
                    progress = True
        if pending:
            missing = [(s.get("label"), s.get("depends_on")) for s in pending]
            raise EnactmentError("unresolved dependencies in proposal: %s" % missing)
        formation.cuts.extend(enacted)

    def _enact_spec(self, spec: Mapping[str, Any], labels: Mapping[str, str], formation: Formation,
                    proposal_handle: str) -> Cut:
        cfg = self.config
        lineage_label = spec.get("lineage")
        lineage_id = labels.get(str(lineage_label)) if lineage_label else None
        payload = dict(spec.get("payload", {}))
        payload["turn"] = formation.turn
        if spec.get("kind") == "arrangement" and "response_demand" in payload:
            payload["response_demand"] = _response_demand(payload["response_demand"])
        basis = [str(b) for b in spec.get("basis", [])]
        if proposal_handle not in basis:
            basis.append(proposal_handle)
        if lineage_id:
            # The revision invalidates what it revises and everything that depended on it.
            invalidated = cfg.invalidate(lineage_id, "revised by %r" % spec.get("label"), proposal_handle)
            delta = Delta(kind="revision", version_from=cfg.version, version_to=cfg.version,
                          source=proposal_handle, invalidated=invalidated,
                          reopened_interventions=[i for i, _ in invalidated if cfg.cuts[i].kind == "intervention"])
            cfg.deltas.append(delta)
        cut = cfg.enact(
            kind=str(spec.get("kind")),
            label=str(spec.get("label")),
            basis=basis,
            apparatus=[str(a) for a in spec.get("apparatus", [])],
            depends_on=[labels[str(d)] for d in spec.get("depends_on", [])],
            lineage=lineage_id,
            relata=spec.get("relata", ()),
            relations=spec.get("relations", ()),
            addressable=spec.get("addressable", ()),
            unmarked=spec.get("unmarked", ()),
            power=spec.get("power", ()),
            allocations=_allocations(spec.get("allocations")),
            consequence_paths=spec.get("consequence_paths", ()),
            counter_cuts=[labels[str(c)] for c in spec.get("counter_cuts", []) if str(c) in labels],
            invalidation_conditions=spec.get("invalidation_conditions", ()),
            payload=payload,
        )
        return cut

    # -- the turn ---------------------------------------------------------

    def turn(self, text: str, role: str = "user_message", channel: Optional[str] = None,
             transformations: Sequence[str] = ()) -> TurnResult:
        cfg = self.config
        self._turns += 1
        turn = "turn%d" % self._turns
        self.last_turn = turn
        delta_start = len(cfg.deltas)
        fact_start = len(cfg.lifecycle)
        arrival = cfg.inscribe(text, role, channel or self.channel, transformations)
        cfg.fact("reconfiguration_open", turn=turn, arrival=arrival.handle)
        formation = Formation(turn=turn, arrivals=[arrival.handle])
        violations: List[Violation] = []
        for round_number in range(1, self.max_rounds + 1):
            formation.round = round_number
            context = self._context(turn, round_number, formation.arrivals, violations)
            try:
                proposal = self.proposer.propose(context)
            except EnactmentError as error:
                violations = [Violation(0, str(error))]
                formation.history.append(list(violations))
                formation.violations = violations
                cfg.unresolved.append({"kind": "proposal_not_enactable", "turn": turn, "round": round_number,
                                       "error": str(error)})
                continue
            provenance = dict(proposal.provenance)
            provenance.setdefault("apparatus_mark", APPARATUS_MARK)
            provenance["round"] = round_number
            proposal_trace = cfg.inscribe(json.dumps(proposal.as_record(), ensure_ascii=False), "model_output",
                                          channel="proposer", provenance=provenance)
            if formation.cuts:
                returned = []
                for cut_id in list(formation.cuts):
                    returned.extend(cfg.invalidate(cut_id, "draft returned to configuration (round %d)" % (round_number - 1), proposal_trace.handle))
                cfg.deltas.append(Delta(kind="return", version_from=cfg.version, version_to=cfg.version,
                                        source=proposal_trace.handle, invalidated=returned,
                                        release_constraints_changed=[v.name for v in violations]))
                formation.cuts = []
                cfg.enact(
                    kind="apparatus", label="release_constraints_fired:%s:r%d" % (turn, round_number - 1),
                    basis=[proposal_trace.handle], apparatus=["release constraints participating in formation"],
                    payload={"turn": turn, "violations": [v.as_record() for v in violations]},
                )
            formation.proposal_trace = proposal_trace.handle
            formation.draft = proposal.draft
            formation.claims = list(proposal.claims)
            formation.variation_possible = bool(proposal.variation_possible)
            formation.variation_constraint = proposal.variation_constraint
            formation.certification = proposal.certification
            for item in proposal.unresolved:
                cfg.unresolved.append({"kind": "held_open", "turn": turn, "text": item})
            try:
                self._enact_proposal(proposal, formation, proposal_trace.handle)
            except (EnactmentError, KeyError, TypeError, ValueError) as error:
                violations = [Violation(0, "%s: %s" % (type(error).__name__, error))]
                formation.history.append(list(violations))
                formation.violations = violations
                cfg.unresolved.append({"kind": "proposal_not_enactable", "turn": turn, "round": round_number,
                                       "error": str(error)})
                continue
            violations = check_all(cfg, formation)
            formation.history.append(list(violations))
            if not violations:
                break
            formation.violations = violations
        if violations:
            cfg.fact("release_withheld", turn=turn, constraints=[v.as_record() for v in violations])
            cfg.unresolved.append({"kind": "release_withheld", "turn": turn,
                                   "constraints": [v.constraint for v in violations]})
            self._save()
            return TurnResult(turn, False, None, None, formation.round, formation.history,
                              cfg.deltas[delta_start:], cfg.lifecycle[fact_start:])
        draft = formation.draft or {}
        labels = {cfg.cuts[i].label: i for i in formation.cuts if cfg.cuts[i].status == "active"}
        demand = _response_demand(draft.get("response_demand"))
        intervention = cfg.enact(
            kind="intervention",
            label="intervention:%s" % turn,
            basis=list(formation.arrivals) + [formation.proposal_trace],
            apparatus=["text delivery through %s" % (channel or self.channel)],
            depends_on=[labels[l] for l in draft.get("enacts", []) if l in labels],
            relata=list(demand.keys()),
            unmarked=list(draft.get("unmarked", [])),
            allocations={p: {"burden": float(len(d))} for p, d in demand.items()},
            invalidation_conditions=list(draft.get("reopen_conditions", [])),
            payload={
                "turn": turn,
                "text": draft.get("text"),
                "delivered_to": [arrival.role],
                "response_demand": demand,
                "possibilities_open": list(draft.get("possibilities_open", [])),
                "possibilities_closed": list(draft.get("possibilities_closed", [])),
                "anticipated_effects": list(draft.get("anticipated_effects", [])),
                "carries_accounts": list(draft.get("carries_accounts", [])),
                "care_delta": {k: list(v) for k, v in care_delta(cfg, turn).items()},
                "play_delta": {k: {kk: list(vv) for kk, vv in d.items()} for k, d in play_delta(cfg, turn).items()},
                "rounds": formation.round,
            },
        )
        cfg.fact("intervention_released", turn=turn, intervention=intervention.id, rounds=formation.round)
        cfg.fact("effects_unobserved", turn=turn, intervention=intervention.id)
        self._save()
        return TurnResult(turn, True, draft.get("text"), intervention.id, formation.round, formation.history,
                          cfg.deltas[delta_start:], cfg.lifecycle[fact_start:])

    # -- effect return ----------------------------------------------------

    def effect(self, text: str, conditions: Optional[Sequence[str]] = None, channel: Optional[str] = None) -> EffectResult:
        cfg = self.config
        trace = cfg.inscribe(text, "effect_report", channel or self.channel)
        if conditions is None:
            context = self._context(self.last_turn or "effect", 0, [trace.handle], [])
            conditions = self.proposer.effect_conditions(context)
        deltas = [cfg.disturb(c, source=trace.handle, reason="observed effect") for c in conditions]
        reopened = [i for d in deltas for i in d.reopened_interventions]
        reinserted = any(d.structural() for d in deltas)
        if reinserted:
            cfg.fact("prior_cut_disturbed", trace=trace.handle, conditions=list(conditions), reopened=reopened)
        else:
            cfg.unresolved.append({"kind": "effect_not_reinserted", "trace": trace.handle,
                                   "note": "effect recorded beside an unchanged formation; the movement that reinserts it is still to come"})
        self._save()
        return EffectResult(trace.handle, list(conditions), deltas, reopened, reinserted)

    def revise_account(self, text: str, provenance_label: str) -> EffectResult:
        """A person's revision of their own account invalidates the
        connections that depended on it (Probe 16 mechanics)."""
        return self.effect(text, conditions=["revision:%s" % provenance_label])

    # -- the runtime's account of itself ---------------------------------

    def account_of_self(self) -> Dict[str, Any]:
        cfg = self.config
        disturbances = [d for d in cfg.deltas if d.kind == "disturbance"]
        returns = [d for d in cfg.deltas if d.kind == "return"]
        last = self.last_turn
        return {
            "enacts": [
                {"part": "graph.Configuration.enact and the live _dependents edges",
                 "evidence": {"live_edges": sum(len(v) for v in cfg._dependents.values()),
                              "cuts_with_invalidation_conditions": sum(1 for c in cfg.active() if c.invalidation_conditions)}},
                {"part": "graph.Configuration.disturb (propagation through dependents)",
                 "evidence": {"disturbances": len(disturbances),
                              "structural": sum(1 for d in disturbances if d.structural())}},
                {"part": "arrangements.care_delta / play_delta (derived on request, not stored)",
                 "evidence": {"care_delta_now": sorted(care_delta(cfg, last).keys()) if last else [],
                              "play_delta_now": {k: sorted(v.keys()) for k, v in play_delta(cfg, last).items()} if last else {}}},
                {"part": "release.check_all inside Runtime.turn rounds (draft returns to configuration)",
                 "evidence": {"returns": len(returns)}},
                {"part": "Runtime.effect (effect re-enters through disturb)",
                 "evidence": {"reinserted": sum(1 for f in cfg.lifecycle if f.get("fact") == "prior_cut_disturbed"),
                              "not_reinserted": sum(1 for u in cfg.unresolved if u.get("kind") == "effect_not_reinserted")}},
            ],
            "records": [
                {"part": "graph.TransportTrace", "count": len(cfg.transports)},
                {"part": "graph.Delta once emitted", "count": len(cfg.deltas)},
                {"part": "lifecycle facts", "count": len(cfg.lifecycle)},
                {"part": "Configuration.record_only items (carried, no edges)", "count": len(cfg.records)},
                {"part": "intervention payload copies of care_delta/play_delta (snapshots; the live values are derived)",
                 "count": sum(1 for c in cfg.cuts.values() if c.kind == "intervention")},
                {"part": "persistence files and probe records", "count": 1 if self.store is not None else 0},
            ],
            "join": (
                "a proposal arrives as a model_output transport trace (record) and becomes cuts through "
                "Configuration.enact (enactment); the proposer's semantic content is apparatus material that "
                "neither part certifies"
            ),
        }

    def _save(self) -> None:
        if self.store is not None:
            self.store.save(self.config)
