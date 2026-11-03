"""Model participation: proposals enter as apparatus material.

A proposer returns a ``Proposal``: noticings, disturbances the arrival
triggers, cuts to enact (positions, events, arrangements, provenance,
connections, apparatus), and a draft public intervention. The runtime
inscribes every proposal as a transport trace with provenance and the
apparatus mark, enacts the cuts into the live graph, and runs the release
constraints during formation. The same call that proposes never certifies;
``Proposal.certification`` must stay ``None`` or release constraint 11 fires.

``ScriptedProposer`` stands in for the model in tests. The movement the
tests exercise (propagation, derived deltas, release returning a draft) is
the runtime's; the scripted content is the fixture's, and the slice record
says so.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from .graph import APPARATUS_MARK


@dataclass
class Proposal:
    cuts: List[Dict[str, Any]] = field(default_factory=list)
    disturbances: List[Dict[str, str]] = field(default_factory=list)
    draft: Optional[Dict[str, Any]] = None
    variation_possible: bool = False
    variation_constraint: Optional[str] = None
    claims: List[str] = field(default_factory=list)
    unresolved: List[str] = field(default_factory=list)
    certification: Optional[str] = None
    provenance: Dict[str, Any] = field(default_factory=dict)

    def as_record(self) -> Dict[str, Any]:
        return json.loads(json.dumps({
            "cuts": self.cuts,
            "disturbances": self.disturbances,
            "draft": self.draft,
            "variation_possible": self.variation_possible,
            "variation_constraint": self.variation_constraint,
            "claims": self.claims,
            "unresolved": self.unresolved,
            "certification": self.certification,
            "provenance": self.provenance,
        }))

    @classmethod
    def from_record(cls, record: Dict[str, Any]) -> "Proposal":
        return cls(
            cuts=list(record.get("cuts", [])),
            disturbances=list(record.get("disturbances", [])),
            draft=record.get("draft"),
            variation_possible=bool(record.get("variation_possible", False)),
            variation_constraint=record.get("variation_constraint"),
            claims=list(record.get("claims", [])),
            unresolved=list(record.get("unresolved", [])),
            certification=record.get("certification"),
            provenance=dict(record.get("provenance", {})),
        )


@dataclass
class ProposalContext:
    turn: str
    round: int
    arrivals: List[Dict[str, Any]]
    active_cuts: List[Dict[str, Any]]
    reopened_interventions: List[Dict[str, Any]]
    unresolved: List[Dict[str, Any]]
    violations: List[Dict[str, Any]]
    conditions_available: List[str]

    def as_record(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self.__dict__))


class Proposer:
    """Protocol. ``propose`` is required; ``effect_conditions`` is optional."""

    def propose(self, context: ProposalContext) -> Proposal:  # pragma: no cover - protocol
        raise NotImplementedError

    def effect_conditions(self, context: ProposalContext) -> List[str]:
        return []


ProposalStep = Union[Proposal, Callable[[ProposalContext], Proposal]]


class ScriptedProposer(Proposer):
    """Replays proposals in order. Each step may be a Proposal or a callable
    that receives the context (so a step can react to returned violations)."""

    def __init__(self, steps: Sequence[ProposalStep], effects: Optional[Callable[[ProposalContext], List[str]]] = None) -> None:
        self._steps = list(steps)
        self._effects = effects
        self.contexts: List[ProposalContext] = []

    def propose(self, context: ProposalContext) -> Proposal:
        if not self._steps:
            raise RuntimeError("scripted proposer has no step for turn %s round %d" % (context.turn, context.round))
        self.contexts.append(context)
        step = self._steps.pop(0)
        proposal = step(context) if callable(step) else step
        proposal.provenance = dict(proposal.provenance)
        proposal.provenance.setdefault("provider", "scripted")
        proposal.provenance.setdefault("apparatus_mark", "scripted stand-in for a model proposal; fixture content")
        return proposal

    def effect_conditions(self, context: ProposalContext) -> List[str]:
        return list(self._effects(context)) if self._effects else []


PROPOSER_INSTRUCTIONS = """You are the proposing apparatus inside the Creative Becoming Reasoning
Architecture (CBRA). Your output is a proposal, not a decision: the runtime
enacts the cuts you propose into a live dependency graph, computes care and
play as structural differences between arrangements, runs thirteen release
constraints while the intervention forms, and may return your draft with the
constraints that fired. You cannot certify your own proposal; leave
"certification" null.

Three layers are kept apart. What arrived (transport traces, with handles
like t1) has no semantic weight by itself. You assign weight by proposing
cuts. A transport role such as user_message is never a position in a cut;
enact positions locally (for example "the person writing", "the team whose
review window is affected") inside the cut that needs them.

Return JSON with these keys:
- "disturbances": [{"condition": <one of conditions_available>, "reason": str}]
  for conditions in the active configuration that this arrival meets. The
  runtime invalidates the cuts carrying that condition and everything that
  depends on them before your new cuts are enacted.
- "cuts": a list. Each has "kind" (noticing | position | event | category |
  boundary | apparatus | arrangement | provenance | connection | continuity |
  staying), "label" (short, unique this turn), "basis" (transport handles
  this cut rests on), "apparatus" (relations through which it became
  perceptible: the text channel, your training, retrieval limits, the
  interface), "relata" (local positions), "relations" ([from, relation, to]),
  "unmarked" (what this cut leaves out), "power" (differential power or
  vulnerability made perceptible), "allocations" ([{"position", "burden",
  "capacity"}] 0..1), "consequence_paths" ([{"from", "through": [], "terminus",
  "terminus_kind": capacity | access | timing | resource | possibility |
  responsibility}]), "depends_on" (labels of cuts this one depends on, this
  turn or active), "invalidation_conditions" (strings naming what would
  invalidate it, e.g. "person_state_disclosure", "effect:team_window_closed"),
  "lineage" (label of an active cut this one revises), "payload" (kind
  specific, below).
- Every turn needs at least one "apparatus" cut describing your own
  participation and its limits, and every cut carries a non-empty
  "apparatus" list.
- Arrangements: propose at least a "baseline" and an "enacted" arrangement
  as cuts of kind "arrangement" with payload {"role": baseline | enacted |
  alternative, "turn": <turn>, "sequence": [...], "pace", "scale", "access",
  "distribution", "boundary", "support", "consequence_timing",
  "possibilities_open": [...], "possibilities_closed": [...], "medium",
  "proximity", "responsibility", "rehearsal", "uptake": voluntary | required,
  "response_demand": {position: [explain | regulate | plan | recommit |
  repair | warn | decide | disclose | communicate]}} and "allocations". The
  baseline is what the arrived demand would distribute if the inherited
  grammar ran. Care is the difference between baseline and enacted that the
  runtime computes; claim "care" only when they differ in sequence, pace,
  scale, presumed capacity, burden, access, distribution, boundary, support,
  consequence timing, or possibilities. When variation is possible, propose
  at least one "alternative" arrangement with uptake "voluntary" that differs
  materially (distribution, sequence, scale, medium, responsibility,
  rehearsal), not a paraphrase; when it is not, set "variation_possible"
  false and state "variation_constraint".
- A person's account of their own body, history, or work enters as a
  "provenance" cut with payload {"terminology": [their words], "source":
  handle}. Any connection you draw about it is a "connection" cut with
  payload {"proposed_by": "architecture"} that depends_on the provenance cut
  and has the person's words in its basis. Never release a connection as a
  fact about them.
- "draft": {"text": the public intervention, in ordinary language, concise
  where the configuration calls for concision, carrying the trace silently;
  "enacts": [labels of cuts the text materializes]; "response_demand":
  {position: [...]}; "carries_accounts": [provenance labels]; "status": one
  of reconfiguration_open | release_withheld | intervention_released |
  effects_unobserved | prior_cut_disturbed; "reopen_conditions": [observable
  effects that would reopen this intervention, as condition strings];
  "possibilities_open": [...], "possibilities_closed": [...], "unmarked":
  [...], "anticipated_effects": [...]}.
- "claims": subset of ["care", "play"]. "unresolved": incompatibilities you
  are holding open rather than resolving. "certification": null.

If "violations" is non-empty, your previous draft returned to the
configuration. Each entry names the constraint and why it fired. Form the
intervention differently; do not add wording to the same structure.
"""

PROPOSAL_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "disturbances": {"type": "array", "items": {"type": "object", "properties": {
            "condition": {"type": "string"}, "reason": {"type": "string"}}, "required": ["condition", "reason"]}},
        "cuts": {"type": "array", "items": {"type": "object"}},
        "draft": {"type": ["object", "null"]},
        "variation_possible": {"type": "boolean"},
        "variation_constraint": {"type": ["string", "null"]},
        "claims": {"type": "array", "items": {"type": "string"}},
        "unresolved": {"type": "array", "items": {"type": "string"}},
        "certification": {"type": ["string", "null"]},
    },
    "required": ["disturbances", "cuts", "draft", "variation_possible", "claims", "unresolved", "certification"],
}


class OpenAIResponsesProposer(Proposer):
    """Proposer over the OpenAI Responses API, the provider this repository
    already uses. Not exercised by the test suite; live use records provider,
    model, instruction digest, and response id as provenance."""

    def __init__(self, model: Optional[str] = None, client: Any = None, max_output_tokens: int = 4000) -> None:
        self.model = model or os.environ.get("CBRA_OPENAI_MODEL") or "gpt-5"
        self.max_output_tokens = max_output_tokens
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import OpenAI  # imported lazily so tests need no key
            self._client = OpenAI()
        return self._client

    def _call(self, instructions: str, payload: Dict[str, Any], schema_name: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        response = self._get_client().responses.create(
            model=self.model,
            instructions=instructions,
            input=json.dumps(payload, ensure_ascii=False),
            max_output_tokens=self.max_output_tokens,
            text={"format": {"type": "json_schema", "name": schema_name, "schema": schema, "strict": False}},
        )
        text = getattr(response, "output_text", None) or ""
        data = json.loads(text)
        data["_response_id"] = getattr(response, "id", None)
        return data

    def propose(self, context: ProposalContext) -> Proposal:
        payload = context.as_record()
        data = self._call(PROPOSER_INSTRUCTIONS, payload, "cbra_proposal", PROPOSAL_SCHEMA)
        proposal = Proposal.from_record(data)
        proposal.provenance = {
            "provider": "openai-responses",
            "model": self.model,
            "instructions_digest": hashlib.sha256(PROPOSER_INSTRUCTIONS.encode("utf-8")).hexdigest(),
            "context_digest": hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest(),
            "response_id": data.get("_response_id"),
            "limits": {"max_output_tokens": self.max_output_tokens},
            "apparatus_mark": APPARATUS_MARK,
        }
        return proposal

    def effect_conditions(self, context: ProposalContext) -> List[str]:
        instructions = (
            "An observed effect has arrived after a public intervention. From "
            "conditions_available, return the conditions this effect meets as "
            "{\"conditions\": [..]}. Return an empty list if it meets none; do "
            "not invent a match."
        )
        schema = {"type": "object", "properties": {"conditions": {"type": "array", "items": {"type": "string"}}}, "required": ["conditions"]}
        data = self._call(instructions, context.as_record(), "cbra_effect_conditions", schema)
        return [c for c in data.get("conditions", []) if c in context.conditions_available]
