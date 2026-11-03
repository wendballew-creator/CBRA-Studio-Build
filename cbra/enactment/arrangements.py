"""Arrangements and the deltas derived from them.

Care and play are not stored as flags or scores. They are computed, when
asked, as the structural difference between arrangement cuts that are live
in the configuration:

* the *baseline* arrangement is what the arrived demand distributes if the
  inherited grammar runs (who explains, repairs, recommits; in what order;
  at what scale);
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

ARRANGEMENT_ROLES = ("baseline", "enacted", "alternative")


def _normal(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _normal(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_normal(v) for v in value]
    return value


def arrangement_fields(cut: Cut) -> Dict[str, Any]:
    payload = cut.payload if isinstance(cut.payload, Mapping) else {}
    fields = {k: _normal(payload.get(k)) for k in set(CARE_DIMENSIONS) | set(PLAY_DIMENSIONS)}
    if cut.allocations:
        fields["burden"] = _normal({k: v["burden"] for k, v in cut.allocations.items() if v.get("burden") is not None})
        fields["presumed_capacity"] = _normal({k: v["capacity"] for k, v in cut.allocations.items() if v.get("capacity") is not None})
    return fields


def difference(a: Mapping[str, Any], b: Mapping[str, Any], dimensions: Tuple[str, ...]) -> Dict[str, Tuple[Any, Any]]:
    out: Dict[str, Tuple[Any, Any]] = {}
    for dim in dimensions:
        if a.get(dim) != b.get(dim):
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


def burden_concentration(cut: Cut) -> Dict[str, List[str]]:
    """Which positions carry which response demands in an arrangement."""
    demands = cut.payload.get("response_demand", {}) if isinstance(cut.payload, Mapping) else {}
    return {str(k): list(v) for k, v in demands.items()}
