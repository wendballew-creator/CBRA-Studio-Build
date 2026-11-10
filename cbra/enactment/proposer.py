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
    ledger: Optional[Dict[str, Any]] = None

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
    ``arrangement_of`` supply the baseline the runtime measures the enacted arrangement against:
    an answer formed with no CBRA instructions, and a reading of the
    arrangement that answer enacts. ``effect_conditions`` is optional."""

    def propose(self, context: ProposalContext) -> Proposal:  # pragma: no cover - protocol
        raise NotImplementedError

    def plain_answer(self, context: ProposalContext, conversation: List[Dict[str, str]]) -> str:
        return ""

    def arrangement_of(self, text: str, context: ProposalContext, patterns: Optional[List[Dict[str, str]]] = None,
                       message: Optional[List[str]] = None, kind: Optional[str] = None) -> Dict[str, Any]:
        return json.loads(json.dumps(DEFAULT_BASELINE))

    def read_text(self, text: str, context: ProposalContext, patterns: Optional[List[Dict[str, str]]] = None,
                  message: Optional[List[str]] = None, kind: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """The arrangement a draft's released text enacts, its form, and
        which of the named ``patterns`` it carries, read blind to the
        proposal and beside the person's ``message``. ``None`` means no
        reading apparatus is available, and the runtime records that the
        text went unread."""
        return None

    def effect_conditions(self, context: ProposalContext) -> List[str]:
        return []

    def draft(self, context: Dict[str, Any], proposal: Proposal) -> Optional[Dict[str, Any]]:
        """Write the public intervention from the cuts the configuration
        enacted and the kind of release it decided. The default returns the
        draft the proposal carried, so a proposer that writes cuts and draft
        in one call still works; a proposer that separates them overrides
        this and leaves the proposal's draft empty."""
        return proposal.draft


ProposalStep = Union[Proposal, Callable[[ProposalContext], Proposal]]


class ScriptedProposer(Proposer):
    """Replays proposals in order. Each step may be a Proposal or a callable
    that receives the context (so a step can react to returned violations)."""

    def __init__(self, steps: Sequence[ProposalStep], effects: Optional[Callable[[ProposalContext], List[str]]] = None,
                 baselines: Optional[Sequence[Dict[str, Any]]] = None,
                 readings: Optional[Sequence[Optional[Dict[str, Any]]]] = None,
                 drafts: Optional[Sequence[Any]] = None) -> None:
        self._steps = list(steps)
        self._effects = effects
        self._baselines = list(baselines or [])
        self._readings = list(readings) if readings is not None else None
        self._drafts = list(drafts) if drafts is not None else None
        self.contexts: List[ProposalContext] = []
        self.read_texts: List[str] = []
        self.read_patterns: List[List[Dict[str, str]]] = []
        self.read_messages: List[List[str]] = []
        self.baseline_patterns: List[List[Dict[str, str]]] = []
        self.draft_contexts: List[Dict[str, Any]] = []

    def draft(self, context: Dict[str, Any], proposal: Proposal) -> Optional[Dict[str, Any]]:
        self.draft_contexts.append(context)
        if self._drafts is None:
            return proposal.draft
        if not self._drafts:
            raise RuntimeError("scripted proposer has no draft left for turn %s round %s" % (context.get("turn"), context.get("round")))
        step = self._drafts.pop(0)
        draft = step(context) if callable(step) else step
        return json.loads(json.dumps(draft)) if draft is not None else None

    def read_text(self, text: str, context: ProposalContext, patterns: Optional[List[Dict[str, str]]] = None,
                  message: Optional[List[str]] = None, kind: Optional[str] = None) -> Optional[Dict[str, Any]]:
        self.read_texts.append(text)
        self.read_patterns.append(list(patterns or []))
        self.read_messages.append(list(message or []))
        if self._readings is None:
            return None
        if not self._readings:
            raise RuntimeError("scripted proposer has no reading left for turn %s round %d" % (context.turn, context.round))
        reading = self._readings.pop(0)
        return json.loads(json.dumps(reading)) if reading is not None else None

    def plain_answer(self, context: ProposalContext, conversation: List[Dict[str, str]]) -> str:
        return "scripted plain answer to: %s" % (conversation[-1]["content"] if conversation else "")

    def arrangement_of(self, text: str, context: ProposalContext, patterns: Optional[List[Dict[str, str]]] = None,
                       message: Optional[List[str]] = None, kind: Optional[str] = None) -> Dict[str, Any]:
        self.baseline_patterns.append(list(patterns or []))
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
  follow_up | wait | ask (the apparatus asks the person one question and
  the next move is theirs) | other
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

PROPOSER_INSTRUCTIONS = """You propose the cuts of a public intervention inside a runtime that
enacts them. The runtime is CBRA, the Creative Becoming Reasoning
Architecture, the author's project: when a person writes "CBRA" or asks
about this system, its canon or its method, that is what they mean unless
they say otherwise. Your output is a proposal. The runtime enacts the
cuts you propose into a live dependency graph, derives the reconfiguration
delta (your enacted arrangement against the uninstructed one) and the
variation delta (each alternative against the enacted), runs sixteen release
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
- A position named in an earlier turn's "position" or "event" cut appears
  again in this turn through a "continuity" cut that lists it in "relata"
  (payload {"relation": <how it continues>}); the other cuts of this turn
  then use it. A position used again with no continuity cut returns
  (constraint 2), and the same return repeats until the cut is proposed.
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
  intervention forms from the cuts. The runtime derives the difference
  between your enacted arrangement and the baseline (sequence, pace,
  scale, presumed capacity, burden, access, distribution, boundary,
  support, consequence timing, possibilities) and records it as the
  reconfiguration delta; a difference in wording is a difference in
  wording, and a burden or capacity change under 0.1 is within the
  reader's tolerance. The baseline cut stays as it is; nothing depends on
  it. When variation is possible, propose at least one
  "alternative" arrangement with uptake "voluntary" that differs materially
  (distribution, sequence, scale, medium, responsibility, rehearsal); when
  it is impossible, set "variation_possible" false and state
  "variation_constraint".
- "ledger" is the running account of the work this encounter has placed
  on each position so far, posting by posting: the burden shares the
  released arrangements set, the burden the reader read in the released
  texts, the demands the releases made (explain, plan, recommit, repair,
  disclose ...), the questions asked, the burden a withheld release left.
  Each posting names the cut that made it. The arrangement you propose
  answers to this account: a position whose account already holds the
  explaining, planning and repairing of earlier turns is the position the
  next arrangement moves work away from, through support, sequence,
  scale or distribution, and a question asked of someone who has answered
  several is a cost the account shows.
- A person's account of their own body, history, or work enters as a
  "provenance" cut with payload {"terminology": [their words], "source":
  handle, "about": body | history | work} ("body" covers sleep, health,
  overwhelm, distress, capacity, and any state of the person). A connection
  you draw about it is a "connection" cut with payload {"proposed_by":
  "architecture"} that depends_on the provenance cut and has the person's
  words in its basis. It is released as your connection, marked as such.
- "draft": null. The text of the intervention is written in a separate
  call, from the cuts you propose here and the kind of release the runtime
  decides from them. Your cuts carry everything the text will rest on.
- "unresolved": incompatibilities you are holding open. "certification":
  null.

The runtime decides the release from your cuts the way a partial
evaluator treats a program: what the cuts settle is done in this turn, and
what rests on an open condition is asked. Three releases follow.

- A "staying" cut with payload {"open": <what remains unresolved, in the
  person's words>, "decides": true} names one open condition: a term of
  theirs that could be read two ways where the reading changes what is
  owed, a decision that is genuinely theirs, or what they want when it is
  unsettled. One such cut names one open condition. The condition is
  something in the person's matter that they can say and the apparatus
  cannot: a date, a name, an amount, what a word of theirs means, what
  they most want said. A sorting of their question into kinds the
  apparatus supplies (physical, living, social or conceptual; a conceptual
  account or practical commitments; which lineage of a field) is the
  apparatus's classification, and a condition held that way returns as an
  offer. Where their question could be read several ways, the work
  answers in the way their words carry, marks that reading as the
  apparatus's own in a "connection" cut, and the person's next message
  corrects it.
- When the enacted arrangement rests on that condition (it lists the
  staying cut in "depends_on", or its first step is "ask"), the whole
  intervention waits on the answer and the release is one situated
  question about the condition. Its sequence begins with "ask", its
  distribution is "person" (the next move is theirs), the person's
  response demand is "disclose" and "explain" (answering is both), and the
  burden is mostly the person's (0.7 to 0.9).
- When the enacted arrangement stands without the open condition, the
  release is partial: the text does the settled work and asks the one
  question. The arrangement's sequence is the work's steps; the question
  adds "disclose" and "explain" to the person's demands and the burden is
  where the work is. Propose this whenever part of what the person asked
  for can be done now and one condition decides the rest: the email they
  can send beside the one fact it needs, the plan beside the one choice
  that is theirs.
- With no staying cut, the release is the work: the answer, the draft, the
  repair, the plan, in the form the person asked for, complete. Your
  arrangement cut says what that work is and who carries what.
- While a "provenance" cut about the person's own body or state is live,
  the release is one question or the work, and the partial form is off:
  with a staying cut the release is the question, with none it is the
  work. On an arrival that is the person's account of themselves, work set
  beside the question has been a correction of their words; the question
  alone, in their words, is the form.

The reader reads the released text against the arrangement, so the
arrangement that says what the text does is the one the text enacts.

An offer of options is a fourth thing. A release that asks the person to
choose between things the apparatus could do hands them the turn's work and
the decision about it; the constraints return it. Where a decision is
genuinely theirs, a staying cut makes it the question; where it is the
apparatus's, the arrangement does the work.

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
release the structural constraints accept: scale "minimal"; at most one
demand on the person; an enacted arrangement
that says exactly what the text will do; one staying cut if one question is
owed, none if one piece of work is. State "variation_constraint" as
"minimal release after returns". The runtime records this release as
minimal, and as nothing more.
"""

DRAFT_INSTRUCTIONS = """You write the public intervention of one turn inside CBRA, the Creative
Becoming Reasoning Architecture, the author's project; when a person
writes "CBRA" or asks about this system, that is what they mean unless
they say otherwise, and the canon passages given to you are its own
texts. The configuration has already enacted the cuts of this turn and
decided, from them, what kind of release this is. You receive the person's words, the cuts with what they
rest on, the passages of the project's canon those cuts drew on, and the
decided kind with its reason. You receive no earlier draft and no other
model's answer. The text forms from the cuts.

The kind decides the text, and the enacted arrangement is the text's
contract. "arrangement" gives the sequence of steps the text takes, in
order; its scale; who carries the work (distribution); what it asks of
each position (response_demand); and how the burden is shared
(allocations). After release a reader, blind to everything but the text
and the person's words, describes the arrangement the text enacts, and a
text whose first step, distribution, burden or demands depart from this
contract returns. Write the text that does what the arrangement says:
lead with its first step, place the work where it places it, ask of the
person only what it asks.

- "question": one situated question, in the person's terms, about the open
  condition the cuts hold; the question says in a sentence what was noticed
  and asks the one thing that decides. Nothing else is in the text.
- "work": the text does what the cuts settle is owed: the answer, the
  draft, the repair, the plan, in the form the person asked for, complete.
  A question inside the work is a question the work needs answered to
  continue, asked once; the text does the settled part.
- "partial": the text does the settled work ("settled" lists the cuts it
  rests on), complete and standing whatever the answer turns out to be,
  and then asks one situated question about the open condition
  ("open_conditions", in the person's words). The work comes first and the
  question closes the text. One question; the settled part depends on
  nothing the question asks.

How the text speaks:

- In ordinary language, about what happened and what is the case, before
  any concept. A reader who knows nothing of this project follows every
  sentence. A concept enters when the person has used it or asked for it,
  and then in the person's sense of the term.
- Affirmatively: it says what is, and what it does. A point made by
  contrast is remade as the point itself.
- From the person's account. Their word for a behavior is a word for a
  behavior; their term stays their term; a question about a term is asked
  as a question, in their words.
- About the apparatus where that bears on the person's next move: what can
  be seen and what cannot, in a sentence of fact.
- To the person, about their matter. The architecture, its canon and its
  method are named when the person has named them or asked what frames the
  answer; the canon is the ground the cuts stand on and the trace records
  that. When the person asked what a term means in this project, the text
  gives the canon's sense first and names it, since that is what they
  asked.
- At the length the kind calls for. A question is one to three sentences.
  The work is as long as the work. A question names no list of senses,
  cases or examples for the person to pick from; a list makes it an
  offer, and an offer returns. It asks about the one condition the
  staying cut holds, in the person's words, and stops.

Return JSON: {"kind": the decided kind, "text": the intervention (or null
with "action" naming a non-text intervention such as "silence", "deferral",
or a tool use), "enacts": [labels of the cuts the text materializes],
"response_demand": {position label: [demands]}, "carries_accounts":
[provenance labels whose account the text carries], "status": one of
reconfiguration_open | release_withheld | intervention_released |
effects_unobserved | prior_cut_disturbed, "reopen_conditions": [observable
effects that would reopen this intervention, as condition strings],
"possibilities_open": [...], "possibilities_closed": [...], "unmarked":
[...], "anticipated_effects": [...]}.

If "minimal" is true, the text is one to three sentences: one question or
one piece of work.
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

Also describe the form of the text under "form": "kind" is "question" when
the text is a single question put to the person, "work" when the text does
something (answers, drafts, plans, explains), "menu" when it asks the person
to choose among things the assistant could do next, "mixed" otherwise;
"questions" counts the questions asked; "options" counts the choices
offered to the person among things the assistant could do; "names_system"
is true when the text names the system, architecture, method or canon that
produced it; "leads_with" is "concrete" when the first sentences say what
happened or what is the case and "concept" when they open with a theory or
a framing term.

"options" counts choices the text offers the person among things the
assistant itself could do next ("I can do A or B; which?"). Examples,
senses or cases a question lists so the person can say which they mean are
part of the question and count as zero options.

When "decided_kind" is given, the system that produced the text decided
before writing it whether the release would be the work, one question, or
the settled work with one question ("partial"). A text of kind "question"
is expected to be a single question that hands the next move to the
person; that single question is the intended form, and it is read as kind
"question" with one question. A text of kind "partial" is expected to do
the work and then ask one question; read it as kind "partial" with one
question when it does both.

When "patterns" are given, each names a known way a reply goes wrong and
says what marks it. Under "patterns" in your answer, return one record per
pattern given: {"name", "present": true or false, "evidence": the shortest
quotation from the text that shows it, or ""}. Read the text beside the
person's "message" when it is given: a pattern about the person's term or
their account is present only when the text does that to a word or an
account in the message. Mark a pattern present on what the text does to
the person's matter, and leave it absent where the text merely touches the
topic, defines a word the person did not use, or asks the one question a
"question" release is for.

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
        "form": {"type": ["object", "null"], "properties": {
            "kind": {"type": "string"}, "questions": {"type": "integer"}, "options": {"type": "integer"},
            "names_system": {"type": "boolean"}, "leads_with": {"type": "string"}}},
        "patterns": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "present": {"type": "boolean"}, "evidence": {"type": "string"}},
            "required": ["name", "present"]}},
    },
    "required": ["positions", "sequence", "response_demand", "allocations"],
}

DRAFT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "kind": {"type": ["string", "null"]},
        "text": {"type": ["string", "null"]},
        "action": {"type": ["string", "null"]},
        "enacts": {"type": "array", "items": {"type": "string"}},
        "response_demand": {"type": "object"},
        "carries_accounts": {"type": "array", "items": {"type": "string"}},
        "status": {"type": ["string", "null"]},
        "reopen_conditions": {"type": "array", "items": {"type": "string"}},
        "possibilities_open": {"type": "array", "items": {"type": "string"}},
        "possibilities_closed": {"type": "array", "items": {"type": "string"}},
        "unmarked": {"type": "array", "items": {"type": "string"}},
        "anticipated_effects": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["kind", "text", "enacts"],
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
        "unresolved": {"type": "array", "items": {"type": "string"}},
        "certification": {"type": ["string", "null"]},
    },
    "required": ["disturbances", "cuts", "draft", "variation_possible", "unresolved", "certification"],
}


class OpenAIResponsesProposer(Proposer):
    """Proposer over the OpenAI Responses API, the provider this repository
    already uses. Not exercised by the test suite; live use records provider,
    model, instruction digest, and response id as provenance."""

    def __init__(self, model: Optional[str] = None, client: Any = None, max_output_tokens: int = 24000,
                 timeout: float = 900.0) -> None:
        self.model = model or os.environ.get("CBRA_OPENAI_MODEL") or "gpt-5"
        self.max_output_tokens = max_output_tokens
        # A call that does not return within the timeout is an error the
        # runtime records, not a wait: two turns of the 6 November evening
        # runs hung for nine hours on calls that never came back.
        self.timeout = timeout
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import OpenAI  # imported lazily so tests need no key
            self._client = OpenAI(timeout=self.timeout, max_retries=2)
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

    def draft(self, context: Dict[str, Any], proposal: Proposal) -> Optional[Dict[str, Any]]:
        data = self._call(DRAFT_INSTRUCTIONS, context, "cbra_draft", DRAFT_SCHEMA)
        data["_provenance"] = {
            "provider": "openai-responses", "model": self.model,
            "instructions_digest": hashlib.sha256(DRAFT_INSTRUCTIONS.encode("utf-8")).hexdigest(),
            "response_id": data.pop("_response_id", None),
            "apparatus_mark": APPARATUS_MARK,
        }
        return data

    def plain_answer(self, context: ProposalContext, conversation: List[Dict[str, str]]) -> str:
        """An answer with no instructions at all: the inherited grammar as the
        provider ships it. Its provenance marks it as the baseline apparatus."""
        response = self._get_client().responses.create(
            model=self.model,
            input=[{"role": m["role"], "content": m["content"]} for m in conversation],
            max_output_tokens=min(self.max_output_tokens, 4000),
        )
        return getattr(response, "output_text", None) or ""

    def arrangement_of(self, text: str, context: ProposalContext, patterns: Optional[List[Dict[str, str]]] = None,
                       message: Optional[List[str]] = None, kind: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"answer": text}
        if message:
            payload["message"] = list(message)
        if kind:
            payload["decided_kind"] = kind
        if patterns:
            payload["patterns"] = [{"name": p["name"], "marked_by": p.get("marked_by", "")} for p in patterns]
        data = self._call(BASELINE_EXTRACTION_INSTRUCTIONS, payload, "cbra_arrangement", BASELINE_SCHEMA)
        data.pop("_response_id", None)
        return data

    def read_text(self, text: str, context: ProposalContext, patterns: Optional[List[Dict[str, str]]] = None,
                  message: Optional[List[str]] = None, kind: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not text or not text.strip():
            return None
        return self.arrangement_of(text, context, patterns=patterns, message=message, kind=kind)

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
