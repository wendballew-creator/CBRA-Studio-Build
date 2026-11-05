"""Enacting core of the dynamic coding method: cuts in a live dependency graph.

What enacts here
    ``Configuration.enact`` brings a cut into being at runtime and registers
    its dependencies as live edges. ``Configuration.disturb`` walks those
    edges, invalidating dependents and reopening the public interventions
    that materialized them. Nothing is declared in advance as a schema class
    that carries a role: every ``Cut`` is created from arriving material or a
    model proposal during a turn.

What records here
    ``TransportTrace`` (what arrived), ``Delta`` once emitted, lifecycle
    facts, and anything placed with ``Configuration.record_only``. Records
    are carried as evidence. They do not propagate.

The distinction matters for Probe 15: a record that carries the same
vocabulary and field values as a cut has no edges in ``_dependents`` and no
entry in ``cuts``; a disturbance passes it by.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

TRANSPORT_ROLES = (
    "user_message",
    "tool_result",
    "document",
    "model_output",
    "effect_report",
    "system",
)

LIFECYCLE_FACTS = (
    "reconfiguration_open",
    "release_withheld",
    "intervention_released",
    "effects_unobserved",
    "prior_cut_disturbed",
)

CUT_KINDS = (
    "noticing",
    "position",
    "event",
    "category",
    "boundary",
    "apparatus",
    "arrangement",
    "provenance",
    "connection",
    "intervention",
    "continuity",
    "staying",
)

APPARATUS_MARK = (
    "proposal came through a language model whose training material is "
    "saturated with human-centered formations"
)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tuple(value: Any) -> Tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        return (value,)
    return tuple(value)


def _label(item: Any) -> str:
    """A proposal may name a position or condition as an object; the cut
    carries its label. Objects keep their other fields only in payload."""
    if isinstance(item, Mapping):
        for key in ("label", "text", "kind", "role", "name", "id"):
            if item.get(key):
                return str(item[key])
        return json.dumps(item, sort_keys=True)
    return str(item)


def _labels(value: Any) -> Tuple[str, ...]:
    return tuple(_label(v) for v in _tuple(value))


@dataclass(frozen=True)
class TransportTrace:
    """A record of arrival. It carries no semantic weight by itself."""

    handle: str
    channel: str
    role: str
    text: str
    sequence: int
    digest: str
    timestamp: float
    transformations: Tuple[str, ...] = ()
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def as_record(self) -> Dict[str, Any]:
        return {
            "handle": self.handle,
            "channel": self.channel,
            "role": self.role,
            "text": self.text,
            "sequence": self.sequence,
            "digest": self.digest,
            "timestamp": self.timestamp,
            "transformations": list(self.transformations),
            "provenance": dict(self.provenance),
        }


@dataclass
class Cut:
    """A local enactment. Relata are local to this cut."""

    id: str
    kind: str
    label: str
    version: int
    basis: Tuple[str, ...]
    apparatus: Tuple[str, ...]
    relata: Tuple[str, ...] = ()
    relations: Tuple[Tuple[str, str, str], ...] = ()
    addressable: Tuple[str, ...] = ()
    unmarked: Tuple[str, ...] = ()
    power: Tuple[str, ...] = ()
    allocations: Dict[str, Dict[str, float]] = field(default_factory=dict)
    consequence_paths: Tuple[Dict[str, Any], ...] = ()
    counter_cuts: Tuple[str, ...] = ()
    depends_on: Tuple[str, ...] = ()
    invalidation_conditions: Tuple[str, ...] = ()
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = "active"
    lineage: Optional[str] = None
    invalidated_by: Optional[str] = None
    invalidation_reason: Optional[str] = None

    def as_record(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "version": self.version,
            "basis": list(self.basis),
            "apparatus": list(self.apparatus),
            "relata": list(self.relata),
            "relations": [list(r) for r in self.relations],
            "addressable": list(self.addressable),
            "unmarked": list(self.unmarked),
            "power": list(self.power),
            "allocations": {k: dict(v) for k, v in self.allocations.items()},
            "consequence_paths": [dict(p) for p in self.consequence_paths],
            "counter_cuts": list(self.counter_cuts),
            "depends_on": list(self.depends_on),
            "invalidation_conditions": list(self.invalidation_conditions),
            "payload": json.loads(json.dumps(self.payload)),
            "status": self.status,
            "lineage": self.lineage,
            "invalidated_by": self.invalidated_by,
            "invalidation_reason": self.invalidation_reason,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Cut":
        return cls(
            id=record["id"],
            kind=record["kind"],
            label=record["label"],
            version=int(record["version"]),
            basis=tuple(record.get("basis", ())),
            apparatus=tuple(record.get("apparatus", ())),
            relata=tuple(record.get("relata", ())),
            relations=tuple(tuple(r) for r in record.get("relations", ())),
            addressable=tuple(record.get("addressable", ())),
            unmarked=tuple(record.get("unmarked", ())),
            power=tuple(record.get("power", ())),
            allocations={k: dict(v) for k, v in record.get("allocations", {}).items()},
            consequence_paths=tuple(dict(p) for p in record.get("consequence_paths", ())),
            counter_cuts=tuple(record.get("counter_cuts", ())),
            depends_on=tuple(record.get("depends_on", ())),
            invalidation_conditions=tuple(record.get("invalidation_conditions", ())),
            payload=dict(record.get("payload", {})),
            status=record.get("status", "active"),
            lineage=record.get("lineage"),
            invalidated_by=record.get("invalidated_by"),
            invalidation_reason=record.get("invalidation_reason"),
        )


@dataclass
class Delta:
    """An inspectable record of structural difference.

    A delta with nothing in its structural fields is a description, not a
    movement; ``structural()`` says which.
    """

    kind: str
    version_from: int
    version_to: int
    source: Optional[str] = None
    added: List[str] = field(default_factory=list)
    revised: List[Tuple[str, str]] = field(default_factory=list)
    invalidated: List[Tuple[str, str]] = field(default_factory=list)
    reopened_interventions: List[str] = field(default_factory=list)
    allocations_changed: List[Dict[str, Any]] = field(default_factory=list)
    consequence_changed: List[Dict[str, Any]] = field(default_factory=list)
    possibilities_opened: List[str] = field(default_factory=list)
    possibilities_closed: List[str] = field(default_factory=list)
    unmarked_revised: List[str] = field(default_factory=list)
    release_constraints_changed: List[str] = field(default_factory=list)
    note: str = ""

    def structural(self) -> bool:
        return any(
            (
                self.added,
                self.revised,
                self.invalidated,
                self.reopened_interventions,
                self.allocations_changed,
                self.consequence_changed,
                self.possibilities_opened,
                self.possibilities_closed,
                self.unmarked_revised,
                self.release_constraints_changed,
            )
        )

    def as_record(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "version_from": self.version_from,
            "version_to": self.version_to,
            "source": self.source,
            "added": list(self.added),
            "revised": [list(r) for r in self.revised],
            "invalidated": [list(r) for r in self.invalidated],
            "reopened_interventions": list(self.reopened_interventions),
            "allocations_changed": list(self.allocations_changed),
            "consequence_changed": list(self.consequence_changed),
            "possibilities_opened": list(self.possibilities_opened),
            "possibilities_closed": list(self.possibilities_closed),
            "unmarked_revised": list(self.unmarked_revised),
            "release_constraints_changed": list(self.release_constraints_changed),
            "structural": self.structural(),
            "note": self.note,
        }


class EnactmentError(ValueError):
    pass


class Configuration:
    """The active configuration: transport traces, live cuts, deltas, facts."""

    def __init__(self, session: str = "local") -> None:
        self.session = session
        self.version = 0
        self.transports: Dict[str, TransportTrace] = {}
        self._sequence = 0
        self._cut_sequence = 0
        self.cuts: Dict[str, Cut] = {}
        self._dependents: Dict[str, Set[str]] = {}
        self.deltas: List[Delta] = []
        self.lifecycle: List[Dict[str, Any]] = []
        self.unresolved: List[Dict[str, Any]] = []
        self.records: Dict[str, Dict[str, Any]] = {}
        self.continuity: List[Dict[str, Any]] = []

    # -- transport layer ---------------------------------------------------

    def inscribe(
        self,
        text: str,
        role: str,
        channel: str = "cli",
        transformations: Sequence[str] = (),
        provenance: Optional[Mapping[str, Any]] = None,
    ) -> TransportTrace:
        if role not in TRANSPORT_ROLES:
            raise EnactmentError("unknown transport role: %s" % role)
        self._sequence += 1
        handle = "t%d" % self._sequence
        trace = TransportTrace(
            handle=handle,
            channel=channel,
            role=role,
            text=text,
            sequence=self._sequence,
            digest=_digest(text),
            timestamp=time.time(),
            transformations=tuple(transformations),
            provenance=dict(provenance or {}),
        )
        self.transports[handle] = trace
        return trace

    # -- cut layer (enacting) ---------------------------------------------

    def enact(
        self,
        kind: str,
        label: str,
        basis: Iterable[str] = (),
        apparatus: Iterable[str] = (),
        depends_on: Iterable[str] = (),
        lineage: Optional[str] = None,
        **fields: Any,
    ) -> Cut:
        if kind not in CUT_KINDS:
            raise EnactmentError("unknown cut kind: %s" % kind)
        depends = tuple(depends_on)
        for dep in depends:
            if dep not in self.cuts:
                raise EnactmentError("dependency %s is not a cut in this configuration" % dep)
            if self.cuts[dep].status == "invalidated":
                raise EnactmentError("dependency %s is invalidated" % dep)
        for handle in basis:
            if handle not in self.transports and handle not in self.cuts:
                raise EnactmentError("basis %s is neither a transport trace nor a cut" % handle)
        self._cut_sequence += 1
        self.version += 1
        cut = Cut(
            id="c%d" % self._cut_sequence,
            kind=kind,
            label=label,
            version=self.version,
            basis=tuple(basis),
            apparatus=tuple(apparatus),
            depends_on=depends,
            lineage=lineage,
            relata=_labels(fields.pop("relata", ())),
            relations=tuple(tuple(_label(x) for x in r) for r in fields.pop("relations", ()) if isinstance(r, (list, tuple))),
            addressable=_labels(fields.pop("addressable", ())),
            unmarked=_labels(fields.pop("unmarked", ())),
            power=_labels(fields.pop("power", ())),
            allocations={k: dict(v) for k, v in dict(fields.pop("allocations", {})).items()},
            consequence_paths=tuple(dict(p) for p in fields.pop("consequence_paths", ())),
            counter_cuts=_labels(fields.pop("counter_cuts", ())),
            invalidation_conditions=_labels(fields.pop("invalidation_conditions", ())),
            payload=dict(fields.pop("payload", {})),
        )
        if fields:
            raise EnactmentError("unknown cut fields: %s" % sorted(fields))
        self.cuts[cut.id] = cut
        self._dependents.setdefault(cut.id, set())
        for dep in depends:
            self._dependents.setdefault(dep, set()).add(cut.id)
        delta = Delta(kind="enact", version_from=self.version - 1, version_to=self.version,
                      source=cut.basis[0] if cut.basis else None, added=[cut.id])
        if lineage:
            delta.revised.append((lineage, cut.id))
        if cut.allocations:
            delta.allocations_changed.append({"cut": cut.id, "allocations": cut.allocations})
        if cut.consequence_paths:
            delta.consequence_changed.append({"cut": cut.id, "paths": list(cut.consequence_paths)})
        opened = cut.payload.get("possibilities_open") if isinstance(cut.payload, dict) else None
        closed = cut.payload.get("possibilities_closed") if isinstance(cut.payload, dict) else None
        if opened:
            delta.possibilities_opened.extend(list(opened))
        if closed:
            delta.possibilities_closed.extend(list(closed))
        if cut.unmarked:
            delta.unmarked_revised.extend(list(cut.unmarked))
        self.deltas.append(delta)
        return cut

    def dependents_of(self, cut_id: str) -> Set[str]:
        """Live reverse edges. Computed from the graph, never stored on the cut."""
        return set(self._dependents.get(cut_id, set()))

    def invalidate(self, cut_id: str, reason: str, by: Optional[str] = None,
                   _seen: Optional[Set[str]] = None) -> List[Tuple[str, str]]:
        seen = _seen if _seen is not None else set()
        if cut_id in seen or cut_id not in self.cuts:
            return []
        seen.add(cut_id)
        cut = self.cuts[cut_id]
        if cut.status == "invalidated":
            return []
        changed: List[Tuple[str, str]] = []
        if cut.kind == "intervention":
            cut.status = "reopened"
            cut.invalidated_by = by
            cut.invalidation_reason = reason
            changed.append((cut_id, reason))
        else:
            cut.status = "invalidated"
            cut.invalidated_by = by
            cut.invalidation_reason = reason
            changed.append((cut_id, reason))
        for dep in sorted(self._dependents.get(cut_id, set())):
            changed.extend(
                self.invalidate(dep, "depends on %s (%s)" % (cut_id, reason), by, seen)
            )
        return changed

    def disturb(self, condition: str, source: Optional[str] = None, reason: str = "") -> Delta:
        """Apply a disturbance: every active cut whose invalidation conditions
        include ``condition`` is invalidated, and the invalidation propagates
        through the live dependency graph."""
        version_from = self.version
        delta = Delta(kind="disturbance", version_from=version_from, version_to=version_from,
                      source=source, note=reason or condition)
        seen: Set[str] = set()
        for cut in list(self.cuts.values()):
            if cut.status == "invalidated":
                continue
            if condition in cut.invalidation_conditions:
                delta.invalidated.extend(
                    self.invalidate(cut.id, "condition met: %s" % condition, source, seen)
                )
        for cut_id, _ in delta.invalidated:
            if self.cuts[cut_id].kind == "intervention":
                delta.reopened_interventions.append(cut_id)
        if delta.structural():
            self.version += 1
            delta.version_to = self.version
        self.deltas.append(delta)
        return delta

    def record_only(self, record: Mapping[str, Any], key: Optional[str] = None) -> str:
        """Carry a record without enacting it. It gets no edges and no
        status; disturbances do not reach it. This is evidence, not movement."""
        key = key or "r%d" % (len(self.records) + 1)
        self.records[key] = json.loads(json.dumps(dict(record)))
        return key

    def active(self, kind: Optional[str] = None) -> List[Cut]:
        return [
            c for c in self.cuts.values()
            if c.status == "active" and (kind is None or c.kind == kind)
        ]

    def by_label(self, label: str, kind: Optional[str] = None) -> Optional[Cut]:
        matches = [c for c in self.active(kind) if c.label == label]
        return matches[-1] if matches else None

    # -- lifecycle facts (recording) ---------------------------------------

    def fact(self, name: str, **detail: Any) -> Dict[str, Any]:
        if name not in LIFECYCLE_FACTS:
            raise EnactmentError(
                "%r is not a bounded lifecycle fact; permitted: %s" % (name, ", ".join(LIFECYCLE_FACTS))
            )
        record = {"fact": name, "version": self.version, "timestamp": time.time()}
        record.update(detail)
        self.lifecycle.append(record)
        return record

    # -- projection --------------------------------------------------------

    def trace(self) -> Dict[str, Any]:
        """Versioned projection for inspection and persistence. A working
        record, distinct from the configuration it traces."""
        return {
            "session": self.session,
            "version": self.version,
            "transports": [t.as_record() for t in self.transports.values()],
            "cuts": [c.as_record() for c in self.cuts.values()],
            "deltas": [d.as_record() for d in self.deltas],
            "lifecycle": list(self.lifecycle),
            "unresolved": list(self.unresolved),
            "records": dict(self.records),
            "continuity": list(self.continuity),
            "live_edges": sum(len(v) for v in self._dependents.values()),
        }

    def rebuild_edges(self) -> None:
        self._dependents = {}
        for cut in self.cuts.values():
            self._dependents.setdefault(cut.id, set())
            for dep in cut.depends_on:
                self._dependents.setdefault(dep, set()).add(cut.id)
