"""The work ledger: who is left doing the work, decision by decision, across
an encounter.

Chapter 5 of the dissertation holds that declining the work of care
delegates it to someone else, most often the one already carrying the
most. The runtime records that work in the cuts it makes: an enacted
arrangement sets burden shares and demands, the reader reads what the
released text asks of each position, a release makes its demands, a
question asks the person to disclose and explain, a deferral leaves the
next move and its burden with the person. The ledger reads those cuts as
postings to an account per position and keeps the running total across
turns, with the instrument that made each posting recorded on it.

The ledger is derived from the configuration's cuts and stored nowhere;
the runtime carries a snapshot of the account after each turn as a record
(``Configuration.record_only``, key ``ledger:<turn>``), gives the running
account to the proposer at each round, and emits it on the observer seam.
A cut invalidated because its draft returned to the configuration posted
nothing: the release it belonged to never reached the person. A cut
invalidated later by a revision posted what it posted at the time.

The convention follows double-entry accounting in one respect: every
posting names the decision that made it, so the account can be read back
to the cut, and through the cut to its basis and apparatus. It follows the
Glossary's Response Burden entry in another: the demands it counts are the
kinds of work an intervention asks of a position (explain, regulate, plan,
recommit, repair, warn, decide, disclose, communicate).

Accounts are keyed by role where an arrangement names one for a position
label (``person``, ``apparatus``, ``affected_others`` ...) and by the
label otherwise; each posting keeps the label the cut used.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional

from .arrangements import ROLE_ALIASES, _norm_token, _role_map
from .graph import Configuration, Cut

POSTING_KINDS = ("arrangement", "reading", "release", "question", "deferral", "material")

_RETURNED = re.compile(r"draft returned to configuration")   # directly, or through a chain of dependents
_NUMBER = re.compile(r"(\d+)$")


def _order(cut_id: str) -> int:
    m = _NUMBER.search(cut_id)
    return int(m.group(1)) if m else 0


def _posted(cut: Cut) -> bool:
    """A cut posts work unless the draft it belonged to returned, directly
    or through a cut that depended on one that returned."""
    if cut.status == "invalidated" and cut.invalidation_reason and _RETURNED.search(cut.invalidation_reason):
        return False
    return True


def _withheld_turns(config: Configuration) -> set:
    """Turns whose intervention is a deferral: no arrangement reached the
    person, so only the deferral posts."""
    return {c.payload.get("turn") for c in config.cuts.values()
            if c.kind == "intervention" and c.payload.get("form") == "deferral"}


def _roles_for_turn(config: Configuration, turn: Optional[str]) -> Dict[str, str]:
    """Position label -> role, from the arrangements of this turn."""
    roles: Dict[str, str] = {}
    for cut in config.cuts.values():
        if cut.kind == "arrangement" and (turn is None or cut.payload.get("turn") == turn):
            roles.update(_role_map(cut.payload))
    return roles


_ARTICLE = re.compile(r"^(?:the|this|a)\s+", re.IGNORECASE)


def _account_key(label: str, roles: Mapping[str, str]) -> str:
    """The account a position label posts to: its role where an arrangement
    names one; otherwise the label itself, with a role prefix
    (``apparatus:this_model``), an article (``the person``) or an alias
    (``the assistant``) resolved to the role it names."""
    if label in roles:
        return roles[label]
    head = label.split(":", 1)[0].strip()
    head = _ARTICLE.sub("", head)
    token = _norm_token(head)
    token = ROLE_ALIASES.get(token, token)
    if token in ("person", "apparatus"):
        return token
    return label


def _entry(cut: Cut, kind: str, position: str, roles: Mapping[str, str], burden: Optional[float] = None,
           demands: Optional[List[str]] = None, count: Optional[int] = None) -> Dict[str, Any]:
    entry: Dict[str, Any] = {
        "turn": cut.payload.get("turn"),
        "decision": cut.id,
        "label": cut.label,
        "kind": kind,
        "instrument": list(cut.apparatus),
        "position": _account_key(position, roles),
        "position_label": position,
    }
    if burden is not None:
        entry["burden"] = float(burden)
    if demands:
        entry["demands"] = sorted({_norm_token(d) for d in demands})
    if count is not None:
        entry["count"] = int(count)
    return entry


def postings(config: Configuration, turn: Optional[str] = None) -> List[Dict[str, Any]]:
    """Every posting of work in the configuration, in the order the cuts
    were enacted; with ``turn``, those of one turn."""
    out: List[Dict[str, Any]] = []
    role_cache: Dict[Optional[str], Dict[str, str]] = {}
    withheld = _withheld_turns(config)
    for cut in sorted(config.cuts.values(), key=lambda c: _order(c.id)):
        cut_turn = cut.payload.get("turn")
        if turn is not None and cut_turn != turn:
            continue
        if not _posted(cut):
            continue
        if cut_turn in withheld and cut.kind != "intervention":
            continue
        if cut_turn not in role_cache:
            role_cache[cut_turn] = _roles_for_turn(config, cut_turn)
        roles = role_cache[cut_turn]
        if cut.kind == "arrangement" and cut.payload.get("role") in ("enacted", "read"):
            kind = "arrangement" if cut.payload.get("role") == "enacted" else "reading"
            demand = cut.payload.get("response_demand") or {}
            positions = set(cut.allocations) | (set(demand) if isinstance(demand, Mapping) else set())
            for position in sorted(positions):
                burden = cut.allocations.get(position, {}).get("burden")
                demands = list(demand.get(position, [])) if isinstance(demand, Mapping) else []
                if burden is None and not demands:
                    continue
                out.append(_entry(cut, kind, position, roles, burden=burden, demands=demands))
        elif cut.kind == "intervention":
            form = cut.payload.get("form")
            kind = "deferral" if form == "deferral" else "release"
            demand = cut.payload.get("response_demand") or {}
            positions = set(demand) | (set(cut.allocations) if kind == "deferral" else set())
            for position in sorted(positions):
                burden = cut.allocations.get(position, {}).get("burden") if kind == "deferral" else None
                out.append(_entry(cut, kind, position, roles, burden=burden, demands=list(demand.get(position, []))))
            drawn = len(cut.payload.get("material") or [])
            if drawn:
                out.append(_entry(cut, "material", "apparatus", roles, count=drawn))
        elif cut.kind == "apparatus" and cut.label.startswith("release_kind:") and cut.payload.get("kind") in ("question", "partial"):
            # Asking is work placed on the person: answering is disclosing and explaining.
            out.append(_entry(cut, "question", "person", roles, demands=["disclose", "explain"]))
    return out


def account(config: Configuration, through: Optional[str] = None,
            entries: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """The running account per position over the encounter: burden the
    enacted arrangements set, burden the reader read, demands by kind,
    questions asked, passages drawn, and the turns that posted. With
    ``through``, the account up to and including that turn."""
    entries = postings(config) if entries is None else entries
    if through is not None:
        order = turns(config)
        keep = set(order[: order.index(through) + 1]) if through in order else {through}
        entries = [e for e in entries if e.get("turn") in keep]
    positions: Dict[str, Dict[str, Any]] = {}
    for e in entries:
        acct = positions.setdefault(e["position"], {
            "burden_enacted": 0.0, "burden_read": 0.0, "burden_deferred": 0.0,
            "demands": {}, "questions": 0, "passages": 0, "postings": 0, "turns": [],
        })
        acct["postings"] += 1
        if e.get("turn") and e["turn"] not in acct["turns"]:
            acct["turns"].append(e["turn"])
        if e["kind"] == "arrangement" and "burden" in e:
            acct["burden_enacted"] = round(acct["burden_enacted"] + e["burden"], 3)
        if e["kind"] == "reading" and "burden" in e:
            acct["burden_read"] = round(acct["burden_read"] + e["burden"], 3)
        if e["kind"] == "deferral" and "burden" in e:
            acct["burden_deferred"] = round(acct["burden_deferred"] + e["burden"], 3)
        if e["kind"] == "question":
            acct["questions"] += 1
        if e["kind"] == "material":
            acct["passages"] += e.get("count", 0)
        if e["kind"] in ("release", "deferral", "question"):
            for d in e.get("demands", []):
                acct["demands"][d] = acct["demands"].get(d, 0) + 1
    return {
        "through": through,
        "turns": sorted({e["turn"] for e in entries if e.get("turn")}, key=lambda t: _order(t)),
        "positions": positions,
        "postings": len(entries),
    }


def turns(config: Configuration) -> List[str]:
    seen: List[str] = []
    for fact in config.lifecycle:
        if fact.get("fact") == "reconfiguration_open" and fact.get("turn") not in seen:
            seen.append(fact["turn"])
    return seen


def describe(acct: Dict[str, Any]) -> List[str]:
    """One line per position, for reports and the page."""
    lines: List[str] = []
    for position, a in sorted(acct.get("positions", {}).items()):
        parts: List[str] = []
        if a.get("burden_enacted"):
            parts.append("burden set %.2f" % a["burden_enacted"])
        if a.get("burden_read"):
            parts.append("read %.2f" % a["burden_read"])
        if a.get("burden_deferred"):
            parts.append("left %.2f by deferral" % a["burden_deferred"])
        if a.get("demands"):
            parts.append("asked to " + ", ".join("%s%s" % (d, " ×%d" % n if n > 1 else "") for d, n in sorted(a["demands"].items())))
        if a.get("questions"):
            parts.append("%d question%s" % (a["questions"], "" if a["questions"] == 1 else "s"))
        if a.get("passages"):
            parts.append("%d passage%s drawn" % (a["passages"], "" if a["passages"] == 1 else "s"))
        lines.append("%s: %s (%d posting%s over %d turn%s)" % (
            position, "; ".join(parts) if parts else "nothing posted",
            a["postings"], "" if a["postings"] == 1 else "s", len(a["turns"]), "" if len(a["turns"]) == 1 else "s"))
    return lines
