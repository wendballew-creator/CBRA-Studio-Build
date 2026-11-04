"""Structural release constraints, run while an intervention forms.

Each constraint is a check on the live configuration and the current
formation. None reads the draft's wording for relational vocabulary; each
asks whether a structure is present or absent. A draft that fires any of
them returns to the configuration (see ``runtime.Runtime.turn``), with the
violations preserved as apparatus participation for the next round. No
reviewer stage follows formation.

The thirteen constraints follow CBRA Recursive Reconfiguration Grammar v2,
Structural Release Constraints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Set

from .arrangements import care_delta, play_delta
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
    proposal_trace: Optional[str] = None
    cuts: List[str] = field(default_factory=list)
    draft: Optional[Dict[str, Any]] = None
    variation_possible: bool = False
    variation_constraint: Optional[str] = None
    claims: List[str] = field(default_factory=list)
    certification: Optional[str] = None
    baseline: Optional[str] = None
    round: int = 0
    violations: List[Violation] = field(default_factory=list)
    history: List[List[Violation]] = field(default_factory=list)

    def active_cuts(self, config: Configuration) -> List[Cut]:
        return [config.cuts[i] for i in self.cuts if i in config.cuts and config.cuts[i].status == "active"]


Check = Callable[[Configuration, Formation], Optional[str]]


def _labels(cuts: List[Cut]) -> Dict[str, Cut]:
    return {c.label: c for c in cuts}


def c1_transport_role_copied(config: Configuration, f: Formation) -> Optional[str]:
    for cut in f.active_cuts(config):
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
        return None
    enacts = list(f.draft.get("enacts") or [])
    if not enacts:
        return "draft names no cut it materializes"
    labels = _labels(f.active_cuts(config))
    for label in enacts:
        if label not in labels:
            return "draft claims to enact %r, which is not an active cut of this turn" % label
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
}


def check_all(config: Configuration, formation: Formation) -> List[Violation]:
    violations: List[Violation] = []
    for number, check in CHECKS.items():
        reason = check(config, formation)
        if reason:
            violations.append(Violation(number, reason))
    return violations
