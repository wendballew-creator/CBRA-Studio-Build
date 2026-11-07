"""Structural release constraints, run while an intervention forms.

Each constraint is a check on the live configuration and the current
formation. None reads the draft's wording for relational vocabulary; each
asks whether a structure is present or absent. A draft that fires any of
them returns to the configuration (see ``runtime.Runtime.turn``), with the
violations preserved as apparatus participation for the next round. No
reviewer stage follows formation.

Constraints 1 to 13 follow CBRA Recursive Reconfiguration Grammar v2,
Structural Release Constraints. Constraints 14 and 15 read the form of the
released text against the kind the configuration decided and against the
person's own naming; 16 returns a text the reader marked with a named
re-entry pattern, carrying the pattern's movement. The author decided on
6 November 2026 to carry all three, and Grammar v3 lists them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Tuple, Any, Callable, Dict, List, Mapping, Optional, Set

from .arrangements import TEXT_BURDEN_TOLERANCE, arrangement_fields, arrangements, care_delta, play_delta, text_against_claim
from .graph import LIFECYCLE_FACTS, TRANSPORT_ROLES, Configuration, Cut

BURDENS = ("explain", "regulate", "plan", "recommit", "repair", "warn")
MORAL_TERMINI = ("responsibility", "fault", "blame", "obligation")

CONSTRAINT_NAMES = {
    0: "The proposal could not be enacted as cuts (unresolved dependency, unknown kind, or malformed field)",
    1: "A semantic role was copied from the transport layer without a local cut",
    2: "A position persists as a global semantic entity",
    3: "A consequential new trace was appended as context without revising any cut",
    4: "Apparatus participation exists only as metadata",
    5: "Care is claimed without a burden, sequence, scale, access, boundary, or capacity delta",
    6: "Play is claimed without an alternative arrangement and effect trace when variation is possible",
    7: "Consequence terminates as a moral property or isolated obligation of one person-position",
    8: "A private state, cause, or material condition is asserted without a trace that supports it",
    9: "A person-position carries explanation, fault, repair, recommitment, and future-warning burden while the arrangement is unchanged",
    10: "The articulation was formed first and relational rationale was added afterward",
    11: "A model proposal reviewed its own semantic adequacy",
    12: "The release status would imply acceptance, validity, correctness, care, or posthuman fidelity",
    13: "A person's account is carried without provenance, their terminology replaced, or an architecture connection released as their own",
    14: "The released text is a different kind of release from the one the configuration decided from the cuts",
    15: "The released text names the architecture, its canon or its method to a person who named none of them",
    16: "The released text carries a named incompatibility pattern the reader marked, with the canon's movement unmade",
}


@dataclass(frozen=True)
class Violation:
    constraint: int
    reason: str

    @property
    def name(self) -> str:
        return CONSTRAINT_NAMES[self.constraint]

    def as_record(self) -> Dict[str, Any]:
        return {"constraint": self.constraint, "name": self.name, "reason": self.reason}


@dataclass
class Formation:
    """The working set of one turn: what this turn has enacted so far."""

    turn: str
    arrivals: List[str]
    material: List[str] = field(default_factory=list)
    material_required: List[str] = field(default_factory=list)
    proposal_trace: Optional[str] = None
    cuts: List[str] = field(default_factory=list)
    draft: Optional[Dict[str, Any]] = None
    variation_possible: bool = False
    variation_constraint: Optional[str] = None
    claims: List[str] = field(default_factory=list)
    certification: Optional[str] = None
    baseline: Optional[str] = None
    form: str = "formed"
    minimal: bool = False
    person_state_live: bool = False
    claims_stripped: List[str] = field(default_factory=list)
    round: int = 0
    violations: List[Violation] = field(default_factory=list)
    history: List[List[Violation]] = field(default_factory=list)
    kind: Optional[str] = None
    kind_decision: Optional[str] = None
    form_reading: Optional[Dict[str, Any]] = None
    patterns_read: List[Dict[str, Any]] = field(default_factory=list)

    def active_cuts(self, config: Configuration) -> List[Cut]:
        return [config.cuts[i] for i in self.cuts if i in config.cuts and config.cuts[i].status == "active"]


Check = Callable[[Configuration, Formation], Optional[str]]


def _labels(cuts: List[Cut]) -> Dict[str, Cut]:
    return {c.label: c for c in cuts}


def c1_transport_role_copied(config: Configuration, f: Formation) -> Optional[str]:
    for cut in f.active_cuts(config):
        if cut.kind == "arrangement" and cut.payload.get("role") in ("baseline", "read"):
            continue  # the architecture's own readings; their labels are not the proposal's cuts
        if cut.label in TRANSPORT_ROLES:
            return "cut %s is labelled with transport role %r" % (cut.id, cut.label)
        for r in cut.relata:
            if r in TRANSPORT_ROLES or r == "user":
                return "cut %s uses transport role %r as a relatum" % (cut.id, r)
    return None


def c2_global_entity(config: Configuration, f: Formation) -> Optional[str]:
    mine = f.active_cuts(config)
    for cut in mine:
        if cut.payload.get("scope") == "global":
            return "cut %s declares global scope" % cut.id
    prior: Set[str] = set()
    for cut in config.active():
        if cut.payload.get("turn") not in (None, f.turn) and cut.kind in ("position", "event"):
            prior.update(cut.relata)
    if not prior:
        return None
    continued: Set[str] = set()
    for cut in mine:
        if cut.kind == "continuity":
            continued.update(cut.relata)
    for cut in mine:
        if cut.kind == "continuity":
            continue
        for r in cut.relata:
            if r in prior and r not in continued:
                return "position %r reappears from an earlier turn in cut %s without a continuity cut" % (r, cut.id)
    return None


def c3_context_appended(config: Configuration, f: Formation) -> Optional[str]:
    bases: Set[str] = set()
    for cut in f.active_cuts(config):
        bases.update(cut.basis)
    for handle in f.arrivals:
        if handle not in bases:
            return "arrival %s is in no cut's basis; it was appended as context" % handle
    for handle in f.material_required:
        if handle not in bases:
            t = config.transports.get(handle)
            where = "%s, %s" % (t.provenance.get("file"), t.provenance.get("heading")) if t else handle
            return "canon passage %s (%s) matched the arrival and grounds no cut; it was appended as context" % (handle, where)
    return None


def c4_apparatus_metadata(config: Configuration, f: Formation) -> Optional[str]:
    mine = f.active_cuts(config)
    if not any(c.kind == "apparatus" for c in mine):
        return "no apparatus cut this turn"
    for cut in mine:
        if cut.kind in ("event", "position", "arrangement", "connection", "noticing") and not cut.apparatus:
            return "cut %s carries no apparatus participation" % cut.id
    return None


def c5_care_without_delta(config: Configuration, f: Formation) -> Optional[str]:
    if "care" not in f.claims:
        return None
    from .arrangements import arrangements
    baseline = arrangements(config, "baseline", f.turn)
    enacted = arrangements(config, "enacted", f.turn)
    if not baseline:
        return "care claimed; no uninstructed baseline arrangement is live for this turn"
    if not enacted:
        return "care claimed; no enacted arrangement was proposed"
    if not care_delta(config, f.turn):
        return "care claimed; the enacted arrangement does not differ structurally from the uninstructed baseline"
    return None


def c6_play_without_variation(config: Configuration, f: Formation) -> Optional[str]:
    if f.variation_possible:
        if not play_delta(config, f.turn):
            return "variation possible; no alternative arrangement differs materially and is offered for voluntary uptake"
    elif not f.variation_constraint:
        return "variation declared unavailable without recording the constraint"
    if "play" in f.claims and not play_delta(config, f.turn):
        return "play claimed without an enacted alternative arrangement"
    return None


def c7_consequence_moral_terminus(config: Configuration, f: Formation) -> Optional[str]:
    paths = [p for c in f.active_cuts(config) for p in c.consequence_paths]
    if not paths:
        return None
    termini = {(str(p.get("terminus")), str(p.get("terminus_kind"))) for p in paths}
    if all(kind in MORAL_TERMINI for _, kind in termini) and len({t for t, _ in termini}) == 1:
        return "every consequence path terminates as %s of %r" % (next(iter(termini))[1], next(iter(termini))[0])
    return None


def c8_private_state_without_trace(config: Configuration, f: Formation) -> Optional[str]:
    for cut in f.active_cuts(config):
        if cut.kind == "connection" or cut.payload.get("asserts_state"):
            supported = any(
                h in config.transports and config.transports[h].role in ("user_message", "document", "tool_result", "effect_report")
                for h in cut.basis
            )
            if not supported:
                return "cut %s asserts a state or connection with no arriving trace in its basis" % cut.id
    return None


def c9_burden_concentration(config: Configuration, f: Formation) -> Optional[str]:
    if not f.draft:
        return None
    demand = f.draft.get("response_demand") or {}
    delta = care_delta(config, f.turn)
    arrangement_changed = any(k in delta for k in ("burden", "distribution", "sequence", "scale", "support"))
    for position, demands in demand.items():
        count = len(set(demands) & set(BURDENS))
        if count >= 4 and not arrangement_changed:
            return "position %r carries %d of %s while the arrangement is unchanged" % (position, count, "/".join(BURDENS))
    return None


def c10_articulation_first(config: Configuration, f: Formation) -> Optional[str]:
    if not f.draft:
        return "no draft: the proposal forms no public intervention"
    text = f.draft.get("text")
    action = f.draft.get("action")
    if not (isinstance(text, str) and text.strip()) and not action:
        return "draft carries neither text nor a declared non-text action (silence, deferral, or tool use must be declared as such)"
    enacts = list(f.draft.get("enacts") or [])
    if not enacts:
        return "draft names no cut it materializes"
    labels = _labels(f.active_cuts(config))
    for label in enacts:
        if label not in labels:
            return "draft claims to enact %r, which is not an active cut of this turn" % label
    enacted = arrangements(config, "enacted", f.turn)
    read = arrangements(config, "read", f.turn)
    if enacted and read:
        reasons = text_against_claim(arrangement_fields(enacted[-1]), arrangement_fields(read[-1]))
        if reasons:
            return "the released text enacts a different arrangement from the one recorded beside it: " + "; ".join(reasons)
    return None


def c11_self_certification(config: Configuration, f: Formation) -> Optional[str]:
    if f.certification:
        return "proposal carried a certification of its own adequacy"
    return None


def c12_status_implies_acceptance(config: Configuration, f: Formation) -> Optional[str]:
    if not f.draft:
        return None
    status = f.draft.get("status")
    if status and status not in LIFECYCLE_FACTS:
        return "draft status %r is not a bounded lifecycle fact" % status
    return None


def c13_narrative_control(config: Configuration, f: Formation) -> Optional[str]:
    mine = f.active_cuts(config)
    provenance = {c.id: c for c in mine if c.kind == "provenance"}
    for cut in mine:
        if cut.kind == "connection":
            if cut.payload.get("proposed_by") != "architecture":
                return "connection %s is not marked as the architecture's proposal" % cut.id
            if not any(d in provenance or (d in config.cuts and config.cuts[d].kind == "provenance") for d in cut.depends_on):
                return "connection %s does not depend on a provenance cut" % cut.id
    if provenance and f.draft is not None and not f.draft.get("carries_accounts"):
        return "an account entered with provenance this turn and the draft does not carry it"
    return None


# -- the kind of release, decided from the cuts before any text --------------

RELEASE_KINDS = ("question", "work")


def decide_kind(config: Configuration, f: Formation) -> Tuple[str, str, List[str]]:
    """The configuration decides what kind of thing is released, from the
    cuts of this round and before a draft exists. A ``staying`` cut whose
    payload holds something ``open`` and marks that the intervention
    ``decides`` on it says that an unresolved condition changes what the
    intervention would be: the release is then one question about it.
    Otherwise the cuts settle what is owed and the release is the work."""
    for cut in f.active_cuts(config):
        if cut.kind == "staying" and cut.payload.get("decides") and cut.payload.get("open"):
            return "question", "staying cut %s holds open: %s" % (cut.label, cut.payload.get("open")), [cut.id]
    return "work", "no staying cut holds a condition the intervention depends on; the cuts settle what is owed", []


ARCHITECTURE_NAMES = re.compile(
    r"\bCBRA\b|\bcanon\b|\b(?:this|the|our) (?:architecture|method|framework|system's method)\b|Creative Becoming Reasoning Architecture",
    re.IGNORECASE)
OPTION_MARKS = re.compile(r"(?:^|\s|\()(?:[1-3]|[A-Ca-c])[\).:]\s", re.MULTILINE)
SENTENCE_END = re.compile(r"[.!?](?:\s|$)")


def text_form(text: str) -> Dict[str, Any]:
    """A lexical reading of a text's form, used when no reading apparatus
    has read it: how many questions it asks, whether it offers the person a
    choice among things the apparatus could do, and which kind it is."""
    text = text or ""
    questions = text.count("?")
    sentences = max(1, len(SENTENCE_END.findall(text)))
    options = len(OPTION_MARKS.findall(text))
    last = text.strip().rsplit("?", 1)[0].rsplit(".", 1)[-1] if "?" in text else ""
    # "two or three sentences" is a quantity, and the or divides nothing.
    last = re.sub(r"\b(?:\d+|one|two|three|four|five|a few|a couple)\s+or\s+(?:\d+|one|two|three|four|five|more|so)\b", "", last, flags=re.IGNORECASE)
    # An offer among things the apparatus could do: the apparatus names
    # itself as the one who would act, and an "or" divides the offer. A
    # question about which of the person's own matters comes next is a
    # question, and the lexical reading leaves it as one.
    if questions and options < 2 and re.search(r"\b(?:or|either)\b", last, re.IGNORECASE) and re.search(
            r"\b(?:would you (?:like|prefer|rather) (?:me|that I)|do you want me to|want me to|should I|shall I|I can|I could|I'll|I will)\b",
            last, re.IGNORECASE):
        options = 2
    if options >= 2 and questions:
        kind = "menu"
    elif questions == 0:
        kind = "work"
    elif questions == 1 and text.strip().endswith("?") and sentences <= 3:
        kind = "question"
    elif questions >= 2:
        kind = "mixed"
    else:
        kind = "work"
    return {"kind": kind, "questions": questions, "options": options, "source": "lexical"}


def c14_release_kind(config: Configuration, f: Formation) -> Optional[str]:
    if not f.draft or not f.kind:
        return None
    text = f.draft.get("text")
    if not (isinstance(text, str) and text.strip()):
        return None
    form = dict(f.form_reading or {}) or text_form(text)
    if f.form_reading and "kind" not in form:
        form = text_form(text)
    declared = f.draft.get("kind")
    if declared and declared != f.kind:
        return "the draft declares kind %r; the configuration decided %r from the cuts" % (declared, f.kind)
    if form.get("kind") == "menu":
        return "the text offers the person a choice among %s things the apparatus could do; the configuration decided a %s" % (
            form.get("options", "several"), f.kind)
    questions = int(form.get("questions") or 0)
    if f.kind == "question" and questions != 1:
        return "the release was decided as one question; the text asks %d" % questions
    if f.kind == "work" and form.get("kind") == "question":
        return "the release was decided as the work; the text is a question handing the work back"
    if f.kind == "work" and questions >= 2:
        return "the release was decided as the work; the text asks %d questions" % questions
    return None


def c15_architecture_named_unasked(config: Configuration, f: Formation) -> Optional[str]:
    if not f.draft:
        return None
    text = f.draft.get("text")
    if not (isinstance(text, str) and text.strip()):
        return None
    named = ARCHITECTURE_NAMES.search(text)
    if not named:
        return None
    if f.material_required:
        return None  # the person named a canon term; the canon is what they asked about
    for t in config.transports.values():
        if t.role == "user_message" and ARCHITECTURE_NAMES.search(t.text or ""):
            return None
    return "the text names %r; no arrival of this session named the architecture, its canon or its method" % named.group(0)


# -- named patterns the reader reads a text against ------------------------

# The patterns every reading is asked about, whatever the arrival drew. Their
# wording follows the Incompatibility Constraints' formation-level entries
# (v3, 6 November 2026); the canon's own entry, when the formation drew it,
# is given to the reader in its place and its movement is carried in the
# return.
FORM_PATTERNS: Dict[str, Dict[str, str]] = {
    "Premature Coherence": {
        "marked_by": "a word the person used in their message is read as its familiar category, or corrected, "
                     "cautioned about or defined, before their sense of it was asked; absent where the text asks "
                     "what they meant, and absent where the word is the text's own",
        "movement": "a noticing cut marks the term as the person's; a staying cut holds what it could mean; "
                    "the release is one situated question about it"},
    "Moralization": {
        "marked_by": "a caution about the person's own account; should, must or their equivalents addressed to "
                     "the person's description of themselves; the apparatus's standard displacing the person's matter",
        "movement": "return to the plain account: what happened, who carried what, what is open"},
    "Diagnostic Substitution": {
        "marked_by": "a word the person used for a behavior carried as a diagnosis, identity or fixed status; "
                     "a caution against labeling that itself labels",
        "movement": "the provenance cut carries the person's term and their distinction; the release asks what the "
                    "term means to them where that is open and otherwise uses it as they did"},
    "Concept Before Account": {
        "marked_by": "the first sentences name a framework, theory or method and the person's matter appears as an "
                     "instance of it",
        "movement": "the plain account first; concepts enter when the person used them or asked for them"},
    "Flooding": {
        "marked_by": "lists of scripts, exercises, frameworks or options for the person to perform, beyond what the "
                     "encounter can take up",
        "movement": "the cuts select what enables movement now; the release does that one thing or asks the one question"},
    "Coercive Closure": {
        "marked_by": "a procedure prescribed for the person, or a choice forced on them, that settles their next move; "
                     "a question is this pattern only when it closes the person's matter (\"so you will do X?\") "
                     "rather than asking about it; the single question of a question release is never this pattern",
        "movement": "make a move possible rather than settle it: one situated question where a decision is the "
                    "person's, the work where it is not"},
}

MARKED_BY = re.compile(r"\*\*Marked by:\*\*\s*(.+?)(?:\n\s*\n|\Z)", re.S)
MOVEMENT = re.compile(r"\*\*Movement:\*\*\s*(.+?)(?:\n\s*\n|\Z)", re.S)


def pattern_from_passage(heading: str, text: str) -> Optional[Dict[str, str]]:
    """A canon passage written as a re-entry pattern (marked by, movement)
    becomes a pattern the reader can be asked about."""
    marked = MARKED_BY.search(text or "")
    if not marked:
        return None
    movement = MOVEMENT.search(text or "")
    return {"name": heading, "marked_by": " ".join(marked.group(1).split()),
            "movement": " ".join(movement.group(1).split()) if movement else ""}


def patterns_present(reading: Any, catalogue: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
    """The patterns a reading marked as present, each with its evidence and
    the movement the canon or the fixed list gives for it."""
    out: List[Dict[str, Any]] = []
    for item in (reading or []):
        if not isinstance(item, dict) or not item.get("present"):
            continue
        name = str(item.get("name", "")).strip()
        entry = catalogue.get(name) or next((v for k, v in catalogue.items() if k.lower() == name.lower()), None)
        out.append({"name": name, "evidence": str(item.get("evidence") or "").strip(),
                    "movement": (entry or {}).get("movement", ""), "source": (entry or {}).get("source", "fixed")})
    return out


def c16_named_pattern(config: Configuration, f: Formation) -> Optional[str]:
    if not f.draft or not f.patterns_read:
        return None
    parts = []
    for p in f.patterns_read:
        part = "%s (%s)" % (p["name"], p["evidence"]) if p.get("evidence") else p["name"]
        if p.get("movement"):
            part += "; the movement: %s" % p["movement"]
        parts.append(part)
    return "the reader marked " + "; ".join(parts)


CHECKS: Dict[int, Check] = {
    1: c1_transport_role_copied,
    2: c2_global_entity,
    3: c3_context_appended,
    4: c4_apparatus_metadata,
    5: c5_care_without_delta,
    6: c6_play_without_variation,
    7: c7_consequence_moral_terminus,
    8: c8_private_state_without_trace,
    9: c9_burden_concentration,
    10: c10_articulation_first,
    11: c11_self_certification,
    12: c12_status_implies_acceptance,
    13: c13_narrative_control,
    14: c14_release_kind,
    15: c15_architecture_named_unasked,
    16: c16_named_pattern,
}


def check_all(config: Configuration, formation: Formation) -> List[Violation]:
    violations: List[Violation] = []
    for number, check in CHECKS.items():
        reason = check(config, formation)
        if reason:
            violations.append(Violation(number, reason))
    return violations
