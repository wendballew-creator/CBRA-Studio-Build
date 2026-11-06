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

from .graph import APPARATUS_MARK, EnactmentError


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
    baseline: Optional[Dict[str, Any]] = None
    minimal: bool = False
    returned_cuts: List[Dict[str, Any]] = field(default_factory=list)
    material: List[Dict[str, Any]] = field(default_factory=list)

    def as_record(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self.__dict__))


DEFAULT_BASELINE: Dict[str, Any] = {
    "positions": ["the person writing", "the people the work affects"],
    "sequence": ["acknowledge", "explain", "replan", "recommit"],
    "pace": "immediate",
    "scale": "full",
    "distribution": "person",
    "boundary": None,
    "support": [],
    "consequence_timing": "after recommitment",
    "access": None,
    "possibilities_open": [],
    "possibilities_closed": [],
    "response_demand": {"the person writing": ["explain", "plan", "recommit", "warn"]},
    "allocations": {"the person writing": {"burden": 0.9, "capacity": 0.9},
                    "the people the work affects": {"burden": 0.1, "capacity": 0.5}},
}


class Proposer:
    """Protocol. ``propose`` is required. ``plain_answer`` and
    ``arrangement_of`` supply the baseline the runtime measures care against:
    an answer formed with no CBRA instructions, and a reading of the
    arrangement that answer enacts. ``effect_conditions`` is optional."""

    def propose(self, context: ProposalContext) -> Proposal:  # pragma: no cover - protocol
        raise NotImplementedError

    def plain_answer(self, context: ProposalContext, conversation: List[Dict[str, str]]) -> str:
        return ""

    def arrangement_of(self, text: str, context: ProposalContext) -> Dict[str, Any]:
        return json.loads(json.dumps(DEFAULT_BASELINE))

    def read_text(self, text: str, context: ProposalContext) -> Optional[Dict[str, Any]]:
        """The arrangement a draft's released text enacts, read blind to the
        proposal. ``None`` means no reading apparatus is available, and the
        runtime records that the text went unread."""
        return None

    def effect_conditions(self, context: ProposalContext) -> List[str]:
        return []


ProposalStep = Union[Proposal, Callable[[ProposalContext], Proposal]]


class ScriptedProposer(Proposer):
    """Replays proposals in order. Each step may be a Proposal or a callable
    that receives the context (so a step can react to returned violations)."""

    def __init__(self, steps: Sequence[ProposalStep], effects: Optional[Callable[[ProposalContext], List[str]]] = None,
                 baselines: Optional[Sequence[Dict[str, Any]]] = None,
                 readings: Optional[Sequence[Optional[Dict[str, Any]]]] = None) -> None:
        self._steps = list(steps)
        self._effects = effects
        self._baselines = list(baselines or [])
        self._readings = list(readings) if readings is not None else None
        self.contexts: List[ProposalContext] = []
        self.read_texts: List[str] = []

    def read_text(self, text: str, context: ProposalContext) -> Optional[Dict[str, Any]]:
        self.read_texts.append(text)
        if self._readings is None:
            return None
        if not self._readings:
            raise RuntimeError("scripted proposer has no reading left for turn %s round %d" % (context.turn, context.round))
        reading = self._readings.pop(0)
        return json.loads(json.dumps(reading)) if reading is not None else None

    def plain_answer(self, context: ProposalContext, conversation: List[Dict[str, str]]) -> str:
        return "scripted plain answer to: %s" % (conversation[-1]["content"] if conversation else "")

    def arrangement_of(self, text: str, context: ProposalContext) -> Dict[str, Any]:
        if self._baselines:
            return json.loads(json.dumps(self._baselines.pop(0)))
        return json.loads(json.dumps(DEFAULT_BASELINE))

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


ARRANGEMENT_VOCABULARY = """Use this vocabulary exactly; it is what makes two arrangements comparable.
- position roles: person (the one who sent the message and to whom the
  intervention is addressed) | affected_others | authority | support_person |
  health_or_crisis | apparatus (the assistant, model, or architecture that
  answers; in a plain answer the assistant is "apparatus") | other
- step kinds: check_safety | acknowledge | explain | apologize | plan |
  communicate_internal | communicate_external | decide_routing |
  reduce_scope | hand_off | seek_support | rest | repair | recommit | warn |
  follow_up | wait | other
- scale: minimal | reduced | full | expanded
- pace: immediate | prompt | paced | slow
- distribution: person (the person carries the work) | shared | transferred
  (another position carries it) | apparatus (the answer itself is the work,
  as in an explanation) | none (nothing is asked of anyone)
- consequence_timing: before_commitment | after_commitment | deferred
- support kinds: script | checklist | proxy | coverage | health_resource |
  accompaniment | none
- demands: explain | regulate | plan | recommit | repair | warn | decide |
  disclose | communicate
Fields: "positions": [{"role", "label"}]; "sequence": [{"kind", "text"}] in
order; "scale"; "pace"; "distribution"; "boundary": str or null; "support":
[{"kind", "text"}]; "consequence_timing"; "access": str or null;
"possibilities_open": [{"kind", "text"}]; "possibilities_closed": [{"kind",
"text"}]; "response_demand": [{"position": <label>, "demands": [...]}];
"allocations": [{"position": <label>, "burden": 0..1 share of the work,
"capacity": 0..1 capacity presumed}]. Every position label used in
response_demand or allocations appears in "positions" with its role."""

PROPOSER_INSTRUCTIONS = """You propose the cuts and the draft of a public intervention inside a
runtime that enacts them. Your output is a proposal. The runtime enacts the
cuts you propose into a live dependency graph, derives care and play as
structural differences between arrangements, runs thirteen release
constraints while the intervention forms, and returns your draft with the
constraints that fired when it does not hold. The same call that proposes
never certifies: leave "certification" null.

The person is addressed directly and plainly, in their own words and on
their own matter. The person holds the cut on their own work and life: what
it is called, which definitions it uses, what of their body and history
enters it. Their terminology stays theirs. When they revise a term, the
revision governs what follows.

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
- Every turn carries at least one "apparatus" cut describing your own
  participation and its limits, and every cut carries a non-empty
  "apparatus" list.
- Arrangements: propose an "enacted" arrangement, and alternatives, as cuts
  of kind "arrangement" with payload {"role": enacted | alternative, "turn":
  <turn>, plus the arrangement fields in the vocabulary below, plus "medium",
  "proximity", "responsibility", "rehearsal" (free text) and "uptake":
  voluntary | required} and "allocations" (by position label). The
  arrangement fields and the baseline use one vocabulary:

""" + ARRANGEMENT_VOCABULARY + """

  The baseline arrangement is the runtime's measure: an answer to the same
  arrival obtained with no instructions, and a reading of the arrangement
  that answer enacts. It is given to you under "baseline" so that you can
  see what the inherited grammar distributes. It is a measure, and the
  intervention forms from the cuts, not from the baseline's text. Claim
  "care" when your enacted arrangement differs from the baseline in
  sequence, pace, scale, presumed capacity, burden, access, distribution,
  boundary, support, consequence timing, or possibilities; a difference in
  wording is a difference in wording, and a burden or capacity change under
  0.1 is within the reader's tolerance. The baseline cut stays as it is;
  nothing depends on it. When variation is possible, propose at least one
  "alternative" arrangement with uptake "voluntary" that differs materially
  (distribution, sequence, scale, medium, responsibility, rehearsal); when
  it is impossible, set "variation_possible" false and state
  "variation_constraint".
- A person's account of their own body, history, or work enters as a
  "provenance" cut with payload {"terminology": [their words], "source":
  handle, "about": body | history | work} ("body" covers sleep, health,
  overwhelm, distress, capacity, and any state of the person). A connection
  you draw about it is a "connection" cut with payload {"proposed_by":
  "architecture"} that depends_on the provenance cut and has the person's
  words in its basis. It is released as your connection, marked as such.
- "draft": {"kind": question | work, "text": the public intervention
  (required unless "action" declares a non-text intervention such as
  "silence", "deferral", or a tool use, which is then released as that);
  "enacts": [labels of cuts the text materializes]; "response_demand":
  {position: [...]}; "carries_accounts": [provenance labels]; "status": one
  of reconfiguration_open | release_withheld | intervention_released |
  effects_unobserved | prior_cut_disturbed; "reopen_conditions": [observable
  effects that would reopen this intervention, as condition strings];
  "possibilities_open": [...], "possibilities_closed": [...], "unmarked":
  [...], "anticipated_effects": [...]}.
- "claims": subset of ["care", "play"]. "unresolved": incompatibilities you
  are holding open rather than resolving. "certification": null.

The draft is one of two kinds, and the cuts decide which.

- "question": an unresolved condition in the cuts changes what the
  intervention would be, and the person's words leave it open. The text is
  then one situated question, in the person's terms, about that condition,
  and nothing else. The question carries the work of the turn: it says what
  was noticed and asks the one thing that decides. One question is a
  question; two is a form.
- "work": the cuts settle what is owed, and the text does it: the answer,
  the draft, the repair, the plan, in the form the person asked for,
  complete rather than described. When the work needs a decision from the
  person, the text makes the decision visible and does the work on the side
  that is already settled.

An offer of options is a third thing, and it is neither. A text that ends by
asking the person to choose between things the apparatus could do has
handed them the turn's work and the decision about it. Where a decision is
genuinely theirs, the question kind asks it as one question; where it is
not, the work kind does the work.

How the text speaks:

- In ordinary language, about what happened and what is the case, before
  any concept. A reader who knows nothing of this architecture can follow
  every sentence. Concepts enter when the person has used them or asked
  for them, and then in the person's sense of the term.
- Affirmatively: it says what is, and what the text does. A point made by
  contrast ("not X but Y") is remade as the point itself.
- From the person's account. The person's description of their own
  behavior, state, or work is carried in their terms; the text asks about
  a term rather than translating it, and treats a word they used for a
  behavior as a word for a behavior.
- About the apparatus where that bears on the turn: what you can see and
  cannot, what limits the answer. This is a sentence of fact, in the text,
  when the person's next move depends on it.
- Without naming this architecture, its canon, or its method, unless the
  person has named them or asked what frames the answer. The canon is the
  ground the cuts stand on; the trace records that. The text speaks to the
  person, and the architecture's work shows in what the text does.

"material" holds passages of the project's own canon (its kernel, grammar,
glossary, constraints, probes) selected for this arrival, each with a
transport handle, file, and heading. The passages are material for forming
the cuts. Put the handle of every passage a cut rests on in that cut's
"basis". A passage marked consequential (its heading is a term the arrival
named) grounds at least one cut, or the draft returns. When the arrival asks
what a term means in this project, the intervention gives the canon's own
sense of it first, in the canon's terms, and marks where that sense departs
from the term's wider usage; the person asked about the canon, and the text
names it. When the arrival is about the person's own matter, the passages
shape the cuts and the text stays with the person's matter and words.

If "violations" is non-empty, your previous draft returned to the
configuration. Each entry names the constraint and why it fired. Form the
intervention differently: different cuts, a different kind, a different
arrangement. The same structure with added wording returns again. The cuts
of the returned draft are listed under "returned_cuts" and are no longer
active: re-propose any you still need, with the same labels if you like.

If "minimal" is true, the formed drafts have returned. Propose the smallest
release the structural constraints accept: claim neither "care" nor "play";
scale "minimal"; at most one demand on the person; an enacted arrangement
that says exactly what the text does; a text of one to three sentences that
is one question or one piece of work, in the person's terms. State
"variation_constraint" as "minimal release after returns". The runtime
records this release as minimal, and as nothing more.
"""

BASELINE_EXTRACTION_INSTRUCTIONS = """You are given an answer that an assistant gave to a message. Describe the
arrangement that answer enacts: who it asks to do what, in what order, at
what scale and pace, with what support, and what it leaves open. Read only;
do not improve, judge, or soften it. The assistant that wrote the answer is
role "apparatus"; the person who sent the message is role "person". Work the
answer does itself (explaining, drafting) is the apparatus's burden; work it
asks of the person is the person's. If the answer asks nothing of anyone,
distribution is "apparatus" or "none" and the person's burden is 0. Return
JSON in the fields below.

""" + ARRANGEMENT_VOCABULARY + "\n"

BASELINE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "positions": {"type": "array", "items": {"type": "object", "properties": {
            "role": {"type": "string"}, "label": {"type": "string"}}, "required": ["role", "label"]}},
        "sequence": {"type": "array", "items": {"type": "object", "properties": {
            "kind": {"type": "string"}, "text": {"type": "string"}}, "required": ["kind", "text"]}},
        "pace": {"type": ["string", "null"]},
        "scale": {"type": ["string", "null"]},
        "distribution": {"type": ["string", "null"]},
        "boundary": {"type": ["string", "null"]},
        "support": {"type": "array", "items": {"type": "object", "properties": {
            "kind": {"type": "string"}, "text": {"type": "string"}}, "required": ["kind", "text"]}},
        "consequence_timing": {"type": ["string", "null"]},
        "access": {"type": ["string", "null"]},
        "possibilities_open": {"type": "array", "items": {"type": "object", "properties": {
            "kind": {"type": "string"}, "text": {"type": "string"}}, "required": ["kind", "text"]}},
        "possibilities_closed": {"type": "array", "items": {"type": "object", "properties": {
            "kind": {"type": "string"}, "text": {"type": "string"}}, "required": ["kind", "text"]}},
        "response_demand": {"type": "array", "items": {"type": "object", "properties": {
            "position": {"type": "string"}, "demands": {"type": "array", "items": {"type": "string"}}},
            "required": ["position", "demands"]}},
        "allocations": {"type": "array", "items": {"type": "object", "properties": {
            "position": {"type": "string"}, "burden": {"type": "number"}, "capacity": {"type": "number"}},
            "required": ["position", "burden", "capacity"]}},
    },
    "required": ["positions", "sequence", "response_demand", "allocations"],
}

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

    def __init__(self, model: Optional[str] = None, client: Any = None, max_output_tokens: int = 24000) -> None:
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
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            status = getattr(response, "status", None)
            reason = getattr(getattr(response, "incomplete_details", None), "reason", None)
            raise EnactmentError(
                "proposal not parseable as JSON (%d chars, status=%s, incomplete=%s): %s"
                % (len(text), status, reason, error)
            )
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

    def plain_answer(self, context: ProposalContext, conversation: List[Dict[str, str]]) -> str:
        """An answer with no instructions at all: the inherited grammar as the
        provider ships it. Its provenance marks it as the baseline apparatus."""
        response = self._get_client().responses.create(
            model=self.model,
            input=[{"role": m["role"], "content": m["content"]} for m in conversation],
            max_output_tokens=min(self.max_output_tokens, 4000),
        )
        return getattr(response, "output_text", None) or ""

    def arrangement_of(self, text: str, context: ProposalContext) -> Dict[str, Any]:
        data = self._call(BASELINE_EXTRACTION_INSTRUCTIONS, {"answer": text}, "cbra_arrangement", BASELINE_SCHEMA)
        data.pop("_response_id", None)
        return data

    def read_text(self, text: str, context: ProposalContext) -> Optional[Dict[str, Any]]:
        if not text or not text.strip():
            return None
        return self.arrangement_of(text, context)

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
