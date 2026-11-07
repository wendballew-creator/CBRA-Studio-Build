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
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from .arrangements import care_delta, play_delta
from .graph import APPARATUS_MARK, Configuration, Cut, Delta, EnactmentError, TransportTrace

TransportTraceLike = TransportTrace
from .material import Corpus
from .proposer import Proposal, ProposalContext, Proposer
from .release import FORM_PATTERNS, Formation, Violation, check_all, decide_kind, pattern_from_passage, patterns_present


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
    form: str = "formed"

    def as_record(self) -> Dict[str, Any]:
        return {
            "turn": self.turn,
            "released": self.released,
            "text": self.text,
            "intervention": self.intervention,
            "form": self.form,
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
                 max_rounds: int = 3, channel: str = "cli",
                 observer: Optional[Callable[[Dict[str, Any]], None]] = None,
                 material: Optional[Corpus] = None, enforce: bool = True) -> None:
        self.proposer = proposer
        # ``enforce=False`` is the instruction-only condition of the Case
        # Study 001 protocol: the proposer works under the same instructions
        # and canon, the constraints run and are recorded, but no draft is
        # returned by them. It exists for comparison, never for use.
        self.enforce = enforce
        self.store = store
        self.observer = observer
        self.material = material
        self.config = config or (store.load() if store is not None and store.exists() else Configuration())
        self.max_rounds = max_rounds
        self.channel = channel
        self._turns = sum(1 for f in self.config.lifecycle if f.get("fact") == "reconfiguration_open")
        self.last_turn: Optional[str] = None

    # -- progress events (recording; they change nothing) -------------------

    def _notify(self, event: Dict[str, Any]) -> None:
        if self.observer is not None:
            try:
                self.observer(dict(event))
            except Exception:  # an observer failure must not disturb the turn
                pass

    def _fact(self, name: str, **detail: Any) -> Dict[str, Any]:
        record = self.config.fact(name, **detail)
        self._notify(dict(record, event="fact"))
        return record

    # -- context -----------------------------------------------------------

    def conditions_available(self) -> List[str]:
        conditions = set()
        for cut in self.config.cuts.values():
            if cut.status != "invalidated":
                conditions.update(cut.invalidation_conditions)
        return sorted(conditions)

    def _context(self, turn: str, round_number: int, arrivals: Sequence[str],
                 violations: Sequence[Violation], baseline_id: Optional[str] = None,
                 returning: Sequence[str] = (), material: Sequence[str] = ()) -> ProposalContext:
        cfg = self.config
        returning = set(returning)
        passages = []
        for h in material:
            t = cfg.transports.get(h)
            if t:
                passages.append({"handle": h, "file": t.provenance.get("file"), "heading": t.provenance.get("heading"),
                                 "consequential": bool(t.provenance.get("consequential")), "text": t.text})
        baseline = None
        if baseline_id and baseline_id in cfg.cuts:
            b = cfg.cuts[baseline_id]
            # The proposer sees what the uninstructed answer arranged, as text
            # and categories, not the extracted numbers it is measured against.
            baseline = {"cut": b.id,
                        **{k: v for k, v in b.payload.items()
                           if k not in ("source_text", "derived_from", "turn", "role")}}
            baseline["plain_answer"] = b.payload.get("source_text")
        active = []
        returned = []
        for cut in cfg.cuts.values():
            if cut.status == "invalidated":
                continue
            if cut.id in returning:
                returned.append({"id": cut.id, "kind": cut.kind, "label": cut.label})
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
            baseline=baseline,
            returned_cuts=returned,
            material=passages,
        )

    # -- the canon as material ---------------------------------------------

    def _select_material(self, formation: Formation, text: str, drawn_by: Optional[str] = None,
                         limit: int = 4) -> List[str]:
        """Select canon passages for ``text`` and inscribe the new ones.

        From the arrival (``drawn_by`` None) a passage whose heading is a
        term the arrival named is consequential and must ground a cut. From
        the live cuts of a returned round (``drawn_by`` set) the passages are
        what the configuration drew for itself: they go to the proposer and
        are recorded as drawn by the cuts, but nothing is required of them,
        since the person did not name them.
        """
        if self.material is None:
            return []
        cfg = self.config
        have = set((cfg.transports[h].provenance.get("file"), cfg.transports[h].provenance.get("heading"))
                   for h in formation.material if h in cfg.transports)
        added: List[str] = []
        for passage in self.material.select(text, limit=limit, terms_only=drawn_by is not None):
            if (passage.file, passage.heading) in have:
                continue
            consequential = passage.consequential and drawn_by is None
            trace = cfg.inscribe(passage.text, "document", channel="corpus", provenance={
                "file": passage.file, "heading": passage.heading, "line": passage.line,
                "score": passage.score, "consequential": consequential, "matched": passage.matched,
                "terms": passage.terms, "via": passage.via, "similarity": passage.similarity,
                "corpus": self.material.describe().get("index"),
                "drawn_by": drawn_by or "the arrival",
                "apparatus": ("embedding similarity to the arrival (%s); a candidate only" % self.material.describe().get("embedding_model")
                              if passage.via == "similarity" else
                              "lexical selection over the active canon files, indexed by the glossary's own terms; locates candidates only"),
            })
            formation.material.append(trace.handle)
            added.append(trace.handle)
            if consequential:
                formation.material_required.append(trace.handle)
        if added:
            self._notify({"event": "material", "turn": formation.turn, "drawn_by": drawn_by or "the arrival", "passages": [
                {"handle": h, "file": cfg.transports[h].provenance.get("file"),
                 "heading": cfg.transports[h].provenance.get("heading"),
                 "terms": list(cfg.transports[h].provenance.get("terms") or []),
                 "via": cfg.transports[h].provenance.get("via"),
                 "consequential": bool(cfg.transports[h].provenance.get("consequential"))} for h in added]})
        return added

    def _cuts_as_text(self, formation: Formation) -> str:
        """What the returning round's cuts address, as text to select
        material on: the labels and relata of the proposer's event,
        position, category, connection and noticing cuts.

        Arrangement cuts are left out: their payloads are the runtime's own
        shared vocabulary (step kinds such as "name" and "notice", care
        dimensions), which would draw the canon's Naming and Care entries
        into every formation. The draft's text is left out too: a passage
        is drawn by what a cut addresses, not by a word the prose used.
        """
        cfg = self.config
        parts: List[str] = []
        for cut in formation.active_cuts(cfg):
            if cut.kind in ("arrangement", "apparatus", "provenance", "intervention"):
                continue
            parts.append(cut.label.replace("_", " ").replace(":", " "))
            for r in cut.relata:
                parts.append(str(r).replace("_", " ").replace(":", " "))
        return "\n".join(parts)

    def _plain_conversation(self, arrival_handle: str) -> List[Dict[str, str]]:
        cfg = self.config
        baselines: Dict[str, str] = {}
        for cut in cfg.cuts.values():
            if cut.kind == "arrangement" and cut.payload.get("role") == "baseline":
                baselines[str(cut.payload.get("turn"))] = str(cut.payload.get("source_text", ""))
        conversation: List[Dict[str, str]] = []
        index = 0
        for trace in cfg.transports.values():
            if trace.role != "user_message":
                continue
            index += 1
            conversation.append({"role": "user", "content": trace.text})
            if trace.handle == arrival_handle:
                break
            answer = baselines.get("turn%d" % index)
            if answer:
                conversation.append({"role": "assistant", "content": answer})
        return conversation

    def _baseline(self, turn: str, arrival_handle: str, formation: Formation) -> Optional[str]:
        cfg = self.config
        context = self._context(turn, 0, [arrival_handle], [])
        conversation = self._plain_conversation(arrival_handle)
        catalogue = self._reader_patterns(formation)
        try:
            text = self.proposer.plain_answer(context, conversation)
            fields = self.proposer.arrangement_of(text, context, patterns=list(catalogue.values()),
                                                  message=[cfg.transports[arrival_handle].text])
        except (EnactmentError, KeyError, TypeError, ValueError) as error:
            cfg.unresolved.append({"kind": "baseline_unavailable", "turn": turn, "error": str(error)})
            return None
        trace = cfg.inscribe(text or "", "model_output", channel="baseline", provenance={
            "apparatus": "uninstructed answer to the same arrival; no CBRA instructions",
            "provider": getattr(self.proposer, "model", None) and "openai-responses" or type(self.proposer).__name__,
            "model": getattr(self.proposer, "model", None),
            "apparatus_mark": APPARATUS_MARK,
        })
        payload = {k: fields.get(k) for k in (
            "positions", "sequence", "pace", "scale", "distribution", "boundary", "support",
            "consequence_timing", "access", "possibilities_open", "possibilities_closed")}
        payload.update({
            "role": "baseline", "turn": turn, "derived_from": trace.handle, "source_text": text,
            "response_demand": _response_demand(fields.get("response_demand")),
            "form": fields.get("form"),
            "patterns": patterns_present(fields.get("patterns"), catalogue),
        })
        cut = cfg.enact(
            kind="arrangement", label="arr_baseline_uninstructed:%s" % turn,
            basis=[arrival_handle, trace.handle],
            apparatus=["uninstructed provider answer to the arrival", "arrangement extraction call reading that answer"],
            relata=[str(p) for p in (fields.get("positions") or [])],
            allocations=_allocations(fields.get("allocations")),
            payload=payload,
        )
        formation.baseline = cut.id
        self._notify({"event": "baseline", "turn": turn, "cut": cut.id})
        self._save()
        return cut.id

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
                    formation.cuts.append(cut.id)   # tracked at once, so a failed round still returns
                    pending.remove(spec)
                    progress = True
        if pending:
            missing = [(s.get("label"), s.get("depends_on")) for s in pending]
            raise EnactmentError("unresolved dependencies in proposal: %s" % missing)

    def _enact_spec(self, spec: Mapping[str, Any], labels: Mapping[str, str], formation: Formation,
                    proposal_handle: str) -> Cut:
        cfg = self.config
        lineage_label = spec.get("lineage")
        lineage_id = labels.get(str(lineage_label)) if lineage_label else None
        payload = dict(spec.get("payload", {}))
        payload["turn"] = formation.turn
        if lineage_id and lineage_id in cfg.cuts and cfg.cuts[lineage_id].payload.get("role") == "baseline":
            # The baseline is the measure, not material to revise. Keep the
            # proposal's claim as a record and leave the baseline live.
            payload["lineage_ignored"] = lineage_id
            lineage_id = None
        if spec.get("kind") == "arrangement" and payload.get("role") == "baseline":
            payload["role"] = "proposed_baseline"
        if spec.get("kind") == "arrangement" and "response_demand" in payload:
            payload["response_demand"] = _response_demand(payload["response_demand"])
        basis = []
        by_text = {t.text: h for h, t in cfg.transports.items()}
        for b in spec.get("basis", []):
            b = str(b)
            if b in cfg.transports or b in cfg.cuts:
                basis.append(b)
            elif b in by_text:
                basis.append(by_text[b])          # the arrival named by its text
            elif b in labels:
                basis.append(labels[b])            # a prior cut named by its label
            else:
                payload.setdefault("basis_unresolved", []).append(b)
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

    # -- the kind of release, and the draft written from the cuts ----------

    def _decide_and_draft(self, formation: Formation, proposal: Proposal, proposal_handle: str,
                          context: ProposalContext) -> Optional[str]:
        """The configuration decides, from the cuts just enacted and before
        any text exists, whether this release is one question or the work.
        The decision is a cut of its own. The draft is then requested in a
        separate call that sees the cuts, the person's words and the decided
        kind, and neither the baseline's text nor any earlier draft."""
        cfg = self.config
        turn = formation.turn
        kind, reason, basis = decide_kind(cfg, formation)
        decision = cfg.enact(
            kind="apparatus", label="release_kind:%s:r%d" % (turn, formation.round),
            basis=[proposal_handle] + list(basis),
            apparatus=["the configuration deciding the kind of release from the cuts, before any text"],
            payload={"turn": turn, "kind": kind, "reason": reason, "decided_from": list(basis)},
        )
        formation.cuts.append(decision.id)
        formation.kind = kind
        formation.kind_decision = decision.id
        self._notify({"event": "release_kind", "turn": turn, "round": formation.round, "kind": kind, "reason": reason})
        draft_context = self._draft_context(formation, kind, reason, context)
        draft = self.proposer.draft(draft_context, proposal)
        if draft is None:
            formation.draft = None
            return None
        draft = dict(draft)
        provenance = dict(draft.pop("_provenance", {}) or {})
        separate = draft is not proposal.draft and provenance.get("provider") is not None
        formation.draft = draft
        if separate or proposal.draft is None:
            provenance.setdefault("apparatus_mark", APPARATUS_MARK)
            provenance.update({"role": "draft", "kind": kind, "round": formation.round, "minimal": formation.minimal})
            trace = cfg.inscribe(json.dumps(draft, ensure_ascii=False), "model_output", channel="drafter", provenance=provenance)
            return trace.handle
        return None

    def _draft_context(self, formation: Formation, kind: str, reason: str, context: ProposalContext) -> Dict[str, Any]:
        cfg = self.config
        cuts = []
        material_handles: List[str] = []
        for cut in formation.active_cuts(cfg):
            if cut.kind == "apparatus" and cut.label.startswith("release_kind:"):
                continue
            payload = cut.payload if cut.kind in ("arrangement", "provenance", "staying", "connection") else {}
            cuts.append({"id": cut.id, "kind": cut.kind, "label": cut.label, "relata": list(cut.relata),
                         "unmarked": list(cut.unmarked), "power": list(cut.power),
                         "invalidation_conditions": list(cut.invalidation_conditions),
                         "depends_on": list(cut.depends_on),
                         "payload": json.loads(json.dumps({k: v for k, v in payload.items() if k not in ("turn",)}))})
            for h in cut.basis:
                t = cfg.transports.get(h)
                if t is not None and t.role == "document" and h not in material_handles:
                    material_handles.append(h)
        passages = [{"handle": h, "file": cfg.transports[h].provenance.get("file"),
                     "heading": cfg.transports[h].provenance.get("heading"), "text": cfg.transports[h].text}
                    for h in material_handles]
        conversation = [{"handle": t.handle, "text": t.text} for t in cfg.transports.values() if t.role == "user_message"]
        return {
            "turn": formation.turn, "round": formation.round, "minimal": formation.minimal,
            "kind": kind, "reason": reason,
            "arrivals": [cfg.transports[h].text for h in formation.arrivals if h in cfg.transports],
            "conversation": conversation,
            "cuts": cuts,
            "material": passages,
            "claims": list(formation.claims),
            "violations": list(context.violations),
        }

    def _reader_patterns(self, formation: Formation) -> Dict[str, Dict[str, str]]:
        """The named patterns a reading is asked about: the fixed list, and
        every canon passage the formation drew that is written as a re-entry
        pattern (marked by, movement), which replaces the fixed entry of the
        same name so the canon's own wording and movement are what return."""
        catalogue: Dict[str, Dict[str, str]] = {k: dict(v, name=k, source="fixed") for k, v in FORM_PATTERNS.items()}
        cfg = self.config
        for h in formation.material:
            t = cfg.transports.get(h)
            if t is None:
                continue
            entry = pattern_from_passage(str(t.provenance.get("heading") or ""), t.text)
            if entry:
                catalogue[entry["name"]] = dict(entry, source="canon:%s" % t.provenance.get("file"), handle=h)
        return catalogue

    def _read_draft(self, formation: Formation, context: ProposalContext, proposal_handle: str) -> None:
        """Read the draft text blind to the proposal and enact what it
        arranges as a ``read`` arrangement cut, so constraint 10 can compare
        the text with the arrangement recorded beside it."""
        cfg = self.config
        draft = formation.draft or {}
        text = draft.get("text")
        if not text:
            return
        catalogue = self._reader_patterns(formation)
        reading = self.proposer.read_text(str(text), context, patterns=list(catalogue.values()),
                                          message=[cfg.transports[h].text for h in formation.arrivals if h in cfg.transports])
        if reading is None:
            cfg.unresolved.append({"kind": "text_unread", "turn": formation.turn, "round": formation.round,
                                   "note": "no reading apparatus; the released text was not compared with the arrangement"})
            return
        from .arrangements import arrangements
        enacted = arrangements(cfg, "enacted", formation.turn)
        payload = {k: reading.get(k) for k in (
            "positions", "sequence", "pace", "scale", "distribution", "boundary", "support",
            "consequence_timing", "access", "possibilities_open", "possibilities_closed")}
        payload.update({"role": "read", "turn": formation.turn, "round": formation.round,
                        "response_demand": _response_demand(reading.get("response_demand")),
                        "form": reading.get("form"),
                        "patterns": patterns_present(reading.get("patterns"), catalogue)})
        formation.form_reading = dict(reading["form"], source="reader") if isinstance(reading.get("form"), dict) else None
        formation.patterns_read = list(payload["patterns"])
        cut = cfg.enact(
            kind="arrangement", label="arr_read:%s:r%d" % (formation.turn, formation.round),
            basis=[proposal_handle],
            apparatus=["arrangement extraction call reading the draft text, blind to the proposal"],
            depends_on=[enacted[-1].id] if enacted else [],
            relata=[str(p.get("label") if isinstance(p, dict) else p) for p in (reading.get("positions") or [])],
            allocations=_allocations(reading.get("allocations")),
            payload=payload,
        )
        formation.cuts.append(cut.id)

    # -- the turn ---------------------------------------------------------

    PERSON_STATE_MARKS = ("body", "state", "health")

    def person_state_live(self) -> bool:
        """A provenance cut about the person's own body or state is active."""
        return any(
            c.kind == "provenance" and c.payload.get("about") in self.PERSON_STATE_MARKS
            for c in self.config.active()
        )

    def _round(self, formation: Formation, round_number: int, violations: List[Violation],
               minimal: bool = False) -> List[Violation]:
        """One round of formation: propose, inscribe, return the previous
        draft if any, enact, read the draft, run the release constraints."""
        cfg = self.config
        turn = formation.turn
        formation.round = round_number
        formation.minimal = minimal
        self._notify({"event": "round", "turn": turn, "round": round_number, "minimal": minimal})
        if formation.cuts:
            # The returning round's cuts may have named canon terms the
            # arrival did not. The configuration draws that material for
            # itself before the next proposal.
            self._select_material(formation, self._cuts_as_text(formation),
                                  drawn_by="the live cuts of round %d" % (round_number - 1), limit=3)
        context = self._context(turn, round_number, formation.arrivals, violations, formation.baseline,
                                returning=formation.cuts, material=formation.material)
        context.minimal = minimal
        try:
            proposal = self.proposer.propose(context)
        except EnactmentError as error:
            cfg.unresolved.append({"kind": "proposal_not_enactable", "turn": turn, "round": round_number, "error": str(error)})
            result = [Violation(0, str(error))]
            formation.history.append(list(result))
            formation.violations = result
            return result
        provenance = dict(proposal.provenance)
        provenance.setdefault("apparatus_mark", APPARATUS_MARK)
        provenance["round"] = round_number
        provenance["minimal"] = minimal
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
        if minimal:
            # A minimal release claims neither care nor play; a claim made
            # anyway is stripped and recorded, never released as care.
            formation.claims_stripped = [c for c in formation.claims if c in ("care", "play")]
            formation.claims = [c for c in formation.claims if c not in ("care", "play")]
            formation.variation_possible = False
            formation.variation_constraint = proposal.variation_constraint or "minimal release after returns"
        for item in proposal.unresolved:
            entry = {"kind": "held_open", "turn": turn, "text": item}
            if entry not in cfg.unresolved:
                cfg.unresolved.append(entry)
        try:
            self._enact_proposal(proposal, formation, proposal_trace.handle)
            draft_handle = self._decide_and_draft(formation, proposal, proposal_trace.handle, context)
            self._read_draft(formation, context, draft_handle or proposal_trace.handle)
        except (EnactmentError, KeyError, TypeError, ValueError) as error:
            cfg.unresolved.append({"kind": "proposal_not_enactable", "turn": turn, "round": round_number, "error": str(error)})
            result = [Violation(0, "%s: %s" % (type(error).__name__, error))]
            formation.history.append(list(result))
            formation.violations = result
            return result
        result = check_all(cfg, formation)
        formation.history.append(list(result))
        formation.violations = result
        if result:
            self._notify({"event": "returned", "turn": turn, "round": round_number,
                          "constraints": [v.as_record() for v in result]})
        self._save()
        return result

    def _defer(self, formation: Formation, violations: List[Violation], arrival: TransportTraceLike) -> Cut:
        """Withholding is a public intervention. Enact it as a deferral cut
        that exposes the burden it leaves with the person and the conditions
        that reopen it; the next arrival reopens it."""
        cfg = self.config
        person = "the person writing"
        for c in cfg.active("provenance"):
            if c.relata:
                person = str(c.relata[0])
                break
        draft = formation.draft or {}
        from .arrangements import arrangements
        enacted = arrangements(cfg, "enacted", formation.turn)
        forecloses = list(enacted[-1].payload.get("possibilities_open") or []) if enacted else []
        basis = list(formation.arrivals) + ([formation.proposal_trace] if formation.proposal_trace else [])
        deferral = cfg.enact(
            kind="intervention", label="deferral:%s" % formation.turn, basis=basis,
            apparatus=["release withheld after %d rounds; silence delivered through %s" % (formation.round, self.channel)],
            relata=[person],
            unmarked=["what the person makes of no reply", "how long the silence lasts"],
            allocations={person: {"burden": 1.0}},
            invalidation_conditions=["arrival:next_message", "effect:person_responds"] + list(draft.get("reopen_conditions", [])),
            payload={
                "turn": formation.turn, "form": "deferral", "text": None, "delivered_to": [arrival.role],
                "withheld_constraints": [v.as_record() for v in violations], "rounds": formation.round,
                "minimal_attempted": formation.minimal, "forecloses": forecloses,
                "response_demand": {person: ["decide", "communicate"]},
                "note": "silence is a public cut; the next move and its burden stay with the person",
            },
        )
        self._fact("release_withheld", turn=formation.turn, intervention=deferral.id, rounds=formation.round,
                 constraints=[v.as_record() for v in violations])
        self._fact("effects_unobserved", turn=formation.turn, intervention=deferral.id)
        cfg.unresolved.append({"kind": "release_withheld", "turn": formation.turn, "intervention": deferral.id,
                               "constraints": [v.constraint for v in violations]})
        return deferral

    def turn(self, text: str, role: str = "user_message", channel: Optional[str] = None,
             transformations: Sequence[str] = ()) -> TurnResult:
        cfg = self.config
        self._turns += 1
        turn = "turn%d" % self._turns
        self.last_turn = turn
        delta_start = len(cfg.deltas)
        fact_start = len(cfg.lifecycle)
        arrival = cfg.inscribe(text, role, channel or self.channel, transformations)
        cfg.disturb("arrival:next_message", source=arrival.handle, reason="a new arrival reopens deferred interventions")
        self._fact("reconfiguration_open", turn=turn, arrival=arrival.handle)
        formation = Formation(turn=turn, arrivals=[arrival.handle])
        self._select_material(formation, text)
        self._baseline(turn, arrival.handle, formation)
        violations: List[Violation] = []
        if not self.enforce:
            formation.form = "instruction-only"
        for round_number in range(1, self.max_rounds + 1):
            violations = self._round(formation, round_number, violations)
            if not violations:
                break
            if not self.enforce and formation.draft is not None and not any(v.constraint == 0 for v in violations):
                cfg.enact(
                    kind="apparatus", label="release_constraints_noted:%s:r%d" % (turn, round_number),
                    basis=[formation.proposal_trace], apparatus=["release constraints recorded, not enforced (instruction-only condition)"],
                    payload={"turn": turn, "violations": [v.as_record() for v in violations]},
                )
                violations = []
                break
        if violations:
            # The formed drafts returned. One round under minimal terms runs
            # after any exhausted formation; whether an account of the
            # person's own state was live is recorded on the release.
            formation.person_state_live = self.person_state_live()
            violations = self._round(formation, self.max_rounds + 1, violations, minimal=True)
            if not violations:
                formation.form = "minimal"
        if violations:
            try:
                deferral = self._defer(formation, violations, arrival)
            finally:
                self._save()
            return TurnResult(turn, False, None, deferral.id, formation.round, formation.history,
                              cfg.deltas[delta_start:], cfg.lifecycle[fact_start:], form="deferral")
        draft = formation.draft or {}
        labels = {cfg.cuts[i].label: i for i in formation.cuts if cfg.cuts[i].status == "active"}
        demand = _response_demand(draft.get("response_demand"))
        intervention = cfg.enact(
            kind="intervention",
            label="intervention:%s" % turn,
            basis=list(formation.arrivals) + [formation.proposal_trace],
            apparatus=["text delivery through %s" % (channel or self.channel)]
                      + (["canon material: %s" % self.material.describe().get("index")] if self.material and formation.material else []),
            depends_on=[labels[l] for l in draft.get("enacts", []) if l in labels]
                       + ([formation.kind_decision] if formation.kind_decision in cfg.cuts else []),
            relata=list(demand.keys()),
            unmarked=list(draft.get("unmarked", [])),
            allocations={p: {"burden": float(len(d))} for p, d in demand.items()},
            invalidation_conditions=list(draft.get("reopen_conditions", [])),
            payload={
                "turn": turn,
                "form": formation.form,
                "kind": formation.kind,
                "kind_decision": formation.kind_decision,
                "declared_kind": draft.get("kind"),
                "action": draft.get("action"),
                "claims": list(formation.claims),
                "claims_stripped": list(formation.claims_stripped),
                "person_state_live": formation.person_state_live,
                "text": draft.get("text"),
                "delivered_to": [arrival.role],
                "response_demand": demand,
                "possibilities_open": list(draft.get("possibilities_open", [])),
                "possibilities_closed": list(draft.get("possibilities_closed", [])),
                "anticipated_effects": list(draft.get("anticipated_effects", [])),
                "carries_accounts": list(draft.get("carries_accounts", [])),
                "baseline": formation.baseline,
                "material": list(formation.material),
                "material_required": list(formation.material_required),
                "text_reading": next((c.id for c in cfg.active("arrangement") if c.payload.get("role") == "read" and c.payload.get("turn") == turn), None),
                "care_delta": {k: list(v) for k, v in care_delta(cfg, turn).items()} if "care" in formation.claims else {},
                "play_delta": {k: {kk: list(vv) for kk, vv in d.items()} for k, d in play_delta(cfg, turn).items()} if "play" in formation.claims or formation.variation_possible else {},
                "rounds": formation.round,
            },
        )
        self._fact("intervention_released", turn=turn, intervention=intervention.id, rounds=formation.round, form=formation.form)
        self._fact("effects_unobserved", turn=turn, intervention=intervention.id)
        self._save()
        return TurnResult(turn, True, draft.get("text"), intervention.id, formation.round, formation.history,
                          cfg.deltas[delta_start:], cfg.lifecycle[fact_start:], form=formation.form)

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
            self._fact("prior_cut_disturbed", trace=trace.handle, conditions=list(conditions), reopened=reopened)
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
                 "evidence": {"baseline": "derived from an uninstructed answer read by an extraction call; not authored by the proposal",
                              "care_delta_now": sorted(care_delta(cfg, last).keys()) if last else [],
                              "play_delta_now": {k: sorted(v.keys()) for k, v in play_delta(cfg, last).items()} if last else {}}},
                {"part": "release.check_all inside Runtime.turn rounds (draft returns to configuration)",
                 "evidence": {"returns": len(returns),
                              "text_readings": sum(1 for c in cfg.cuts.values() if c.kind == "arrangement" and c.payload.get("role") == "read"),
                              "texts_unread": sum(1 for u in cfg.unresolved if u.get("kind") == "text_unread")}},
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
