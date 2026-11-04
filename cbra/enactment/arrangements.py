"""Arrangements and the deltas derived from them.

Care and play are not stored as flags or scores. They are computed, when
asked, as the structural difference between arrangement cuts that are live
in the configuration:

* the *baseline* arrangement is what the inherited grammar distributes: the
  runtime obtains an answer to the same arrival with no CBRA instructions and
  a separate extraction call reads the arrangement that answer enacts (who
  explains, repairs, recommits; in what order; at what scale). The proposal
  does not write the baseline it is measured against; a baseline it sends
  anyway is kept with role ``proposed_baseline`` as a record;
* the *enacted* arrangement is the one the formation actually carries;
* *alternative* arrangements are enacted far enough to compare, and offered
  for voluntary uptake.

``care_delta`` is the difference between baseline and enacted on the care
dimensions. ``play_delta`` is the difference between enacted and each
alternative on the variation dimensions. Removing the enacted arrangement,
or replacing it with a record that carries the words but not the
structure, empties the delta, and the release constraint that depends on
it fires (Probes 8, 9, 15).
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

from .graph import Configuration, Cut

CARE_DIMENSIONS = (
    "sequence",
    "pace",
    "scale",
    "presumed_capacity",
    "burden",
    "response_demand",
    "access",
    "distribution",
    "boundary",
    "support",
    "consequence_timing",
    "possibilities_open",
)

PLAY_DIMENSIONS = (
    "distribution",
    "sequence",
    "scale",
    "proximity",
    "medium",
    "responsibility",
    "rehearsal",
    "pace",
    "burden",
)

ARRANGEMENT_ROLES = ("baseline", "proposed_baseline", "enacted", "alternative", "read")

# A small shared vocabulary. Two arrangements written by different calls can
# only be compared structurally if positions, steps, and scales are named
# from the same set; free text is wording, and the evidence rule says
# structure outranks wording. Values outside the vocabulary are kept as given
# (tests and older traces use plain labels), so comparison degrades to label
# equality rather than failing.
POSITION_ROLES = (
    "person_writing", "affected_others", "authority", "support_person",
    "health_or_crisis", "apparatus", "other",
)
STEP_KINDS = (
    "check_safety", "acknowledge", "explain", "apologize", "plan",
    "communicate_internal", "communicate_external", "decide_routing",
    "reduce_scope", "hand_off", "seek_support", "rest", "repair", "recommit",
    "warn", "follow_up", "wait", "other",
)
SCALES = ("minimal", "reduced", "full", "expanded")
PACES = ("immediate", "prompt", "paced", "slow")
DISTRIBUTIONS = ("person", "shared", "transferred")
CONSEQUENCE_TIMINGS = ("before_commitment", "after_commitment", "deferred")
SUPPORT_KINDS = ("script", "checklist", "proxy", "coverage", "health_resource", "accompaniment", "none")
NUMERIC_TOLERANCE = 0.1


def _normal(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _normal(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_normal(v) for v in value]
    return value


def _kind(item: Any) -> Any:
    """A step, support item, or possibility compared by its kind when it has one."""
    if isinstance(item, Mapping):
        return item.get("kind", item.get("text"))
    return item


def _role_map(payload: Mapping[str, Any]) -> Dict[str, str]:
    """position label -> role, from payload["positions"] entries that carry roles."""
    roles: Dict[str, str] = {}
    for entry in payload.get("positions") or []:
        if isinstance(entry, Mapping) and entry.get("label") and entry.get("role"):
            roles[str(entry["label"])] = str(entry["role"])
    return roles


def _by_role(mapping: Mapping[str, Any], roles: Mapping[str, str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for label, value in mapping.items():
        key = roles.get(str(label), str(label))
        if key in out and isinstance(value, (int, float)) and isinstance(out[key], (int, float)):
            out[key] = max(out[key], value)
        elif key in out and isinstance(value, list) and isinstance(out[key], list):
            out[key] = sorted(set(out[key]) | set(value))
        else:
            out[key] = value
    return out


def arrangement_fields(cut: Cut) -> Dict[str, Any]:
    """The comparable structure of an arrangement cut: steps by kind,
    allocations and demands by role, categorical scale, pace, distribution,
    timing, support kinds, possibilities by kind. Wording is left out."""
    payload = cut.payload if isinstance(cut.payload, Mapping) else {}
    roles = _role_map(payload)
    fields: Dict[str, Any] = {}
    for k in set(CARE_DIMENSIONS) | set(PLAY_DIMENSIONS):
        fields[k] = _normal(payload.get(k))
    fields["sequence"] = [_kind(s) for s in (payload.get("sequence") or [])]
    fields["support"] = sorted(set(str(_kind(s)) for s in (payload.get("support") or []))) if isinstance(payload.get("support"), (list, tuple)) else _normal(payload.get("support"))
    fields["possibilities_open"] = sorted(set(str(_kind(p)) for p in (payload.get("possibilities_open") or [])))
    demand = payload.get("response_demand") or {}
    if isinstance(demand, Mapping):
        fields["response_demand"] = _normal(_by_role({k: sorted(set(v)) for k, v in demand.items()}, roles))
    if cut.allocations:
        fields["burden"] = _normal(_by_role({k: v["burden"] for k, v in cut.allocations.items() if v.get("burden") is not None}, roles))
        fields["presumed_capacity"] = _normal(_by_role({k: v["capacity"] for k, v in cut.allocations.items() if v.get("capacity") is not None}, roles))
    return fields


def _close(a: Any, b: Any) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return abs(float(a) - float(b)) < NUMERIC_TOLERANCE
    if isinstance(a, Mapping) and isinstance(b, Mapping):
        return set(a) == set(b) and all(_close(a[k], b[k]) for k in a)
    return a == b


def difference(a: Mapping[str, Any], b: Mapping[str, Any], dimensions: Tuple[str, ...]) -> Dict[str, Tuple[Any, Any]]:
    """Structural difference on the given dimensions. Numeric allocations
    within NUMERIC_TOLERANCE count as the same; a changed set of positions
    counts as different."""
    out: Dict[str, Tuple[Any, Any]] = {}
    for dim in dimensions:
        if not _close(a.get(dim), b.get(dim)):
            out[dim] = (a.get(dim), b.get(dim))
    return out


def arrangements(config: Configuration, role: str, turn: Optional[str] = None) -> List[Cut]:
    cuts = [
        c for c in config.active("arrangement")
        if c.payload.get("role") == role and (turn is None or c.payload.get("turn") == turn)
    ]
    return cuts


def care_delta(config: Configuration, turn: Optional[str] = None) -> Dict[str, Tuple[Any, Any]]:
    """Derived, never stored: the structural difference care made."""
    baseline = arrangements(config, "baseline", turn)
    enacted = arrangements(config, "enacted", turn)
    if not baseline or not enacted:
        return {}
    return difference(arrangement_fields(baseline[-1]), arrangement_fields(enacted[-1]), CARE_DIMENSIONS)


def play_delta(config: Configuration, turn: Optional[str] = None) -> Dict[str, Dict[str, Tuple[Any, Any]]]:
    """Derived, never stored: for each alternative arrangement offered for
    voluntary uptake, the material variation it carries relative to the
    enacted arrangement. A paraphrase produces an empty entry and is dropped."""
    enacted = arrangements(config, "enacted", turn)
    if not enacted:
        return {}
    base = arrangement_fields(enacted[-1])
    out: Dict[str, Dict[str, Tuple[Any, Any]]] = {}
    for alt in arrangements(config, "alternative", turn):
        if alt.payload.get("uptake") != "voluntary":
            continue
        diff = difference(base, arrangement_fields(alt), PLAY_DIMENSIONS)
        if diff:
            out[alt.id] = diff
    return out


TEXT_BURDEN_TOLERANCE = 0.2


def text_against_claim(claimed: Mapping[str, Any], read: Mapping[str, Any]) -> List[str]:
    """Where the arrangement a released text enacts (as read by the
    extraction apparatus) departs from the arrangement the formation claims.
    Looser than ``difference``: two readers segment steps differently, so
    only the first step, the distribution, the scale, the burden by role, and
    the demands placed on the person are compared."""
    reasons: List[str] = []
    if claimed.get("distribution") and read.get("distribution") and claimed["distribution"] != read["distribution"]:
        reasons.append("text distributes the work as %r; the arrangement claims %r" % (read["distribution"], claimed["distribution"]))
    order = {s: i for i, s in enumerate(SCALES)}
    cs, rs = claimed.get("scale"), read.get("scale")
    if cs in order and rs in order and abs(order[cs] - order[rs]) > 1:
        reasons.append("text operates at scale %r; the arrangement claims %r" % (rs, cs))
    # What the text leads with. An opening line of acknowledgment or apology
    # before the claimed first step is tolerated; a text whose first two steps
    # contain nothing the arrangement puts first is not.
    cseq, rseq = list(claimed.get("sequence") or []), list(read.get("sequence") or [])
    if cseq and rseq:
        read_lead = [s for s in rseq[:3] if s not in ("acknowledge", "apologize")][:2] or rseq[:2]
        claim_lead = [s for s in cseq[:3] if s not in ("acknowledge", "apologize")][:2] or cseq[:2]
        if not set(read_lead) & set(claim_lead):
            reasons.append("text leads with %s; the arrangement claims it leads with %s" % (
                "/".join(read_lead), "/".join(claim_lead)))
    cb, rb = claimed.get("burden") or {}, read.get("burden") or {}
    for role in set(cb) & set(rb):
        if abs(float(cb[role]) - float(rb[role])) >= TEXT_BURDEN_TOLERANCE:
            reasons.append("text places burden %.2f on %r; the arrangement claims %.2f" % (float(rb[role]), role, float(cb[role])))
    cd, rd = claimed.get("response_demand") or {}, read.get("response_demand") or {}
    for role in ("person_writing",):
        if role in cd and role in rd:
            extra = set(rd[role]) - set(cd[role])
            if len(extra) >= 2:
                reasons.append("text asks %r to %s beyond what the arrangement claims" % (role, ", ".join(sorted(extra))))
    return reasons


def burden_concentration(cut: Cut) -> Dict[str, List[str]]:
    """Which positions carry which response demands in an arrangement."""
    demands = cut.payload.get("response_demand", {}) if isinstance(cut.payload, Mapping) else {}
    return {str(k): list(v) for k, v in demands.items()}
