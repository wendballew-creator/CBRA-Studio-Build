"""Persistence keeps relata local.

What is saved is the configuration trace: transport traces, cuts with their
versions and lineage, deltas, lifecycle facts, unresolved incompatibilities,
and carried records. Restoration rebuilds the live dependency edges from the
cuts' dependencies and adds, for every restored cut, a continuity entry
that names the session and version it came from. Nothing is restored as a
global entity record: positions exist only inside the cuts that enacted
them, and any continuity with the present is a revisable relation.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from .graph import Configuration, Cut, Delta, TransportTrace


def _delta_from_record(record: Dict[str, Any]) -> Delta:
    return Delta(
        kind=record["kind"],
        version_from=int(record["version_from"]),
        version_to=int(record["version_to"]),
        source=record.get("source"),
        added=list(record.get("added", [])),
        revised=[tuple(r) for r in record.get("revised", [])],
        invalidated=[tuple(r) for r in record.get("invalidated", [])],
        reopened_interventions=list(record.get("reopened_interventions", [])),
        allocations_changed=list(record.get("allocations_changed", [])),
        consequence_changed=list(record.get("consequence_changed", [])),
        possibilities_opened=list(record.get("possibilities_opened", [])),
        possibilities_closed=list(record.get("possibilities_closed", [])),
        unmarked_revised=list(record.get("unmarked_revised", [])),
        release_constraints_changed=list(record.get("release_constraints_changed", [])),
        note=record.get("note", ""),
    )


class JsonStore:
    def __init__(self, path: str) -> None:
        self.path = path

    def exists(self) -> bool:
        return os.path.exists(self.path)

    def save(self, config: Configuration) -> None:
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(config.trace(), handle, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def load(self, session: str = "restored") -> Configuration:
        with open(self.path, encoding="utf-8") as handle:
            trace = json.load(handle)
        return restore(trace, session)


def restore(trace: Dict[str, Any], session: str = "restored") -> Configuration:
    config = Configuration(session=session)
    config.version = int(trace.get("version", 0))
    for record in trace.get("transports", []):
        t = TransportTrace(
            handle=record["handle"], channel=record["channel"], role=record["role"], text=record["text"],
            sequence=int(record["sequence"]), digest=record["digest"], timestamp=float(record["timestamp"]),
            transformations=tuple(record.get("transformations", ())), provenance=dict(record.get("provenance", {})),
        )
        config.transports[t.handle] = t
        config._sequence = max(config._sequence, t.sequence)
    for record in trace.get("cuts", []):
        cut = Cut.from_record(record)
        config.cuts[cut.id] = cut
        config._cut_sequence = max(config._cut_sequence, int(cut.id[1:]))
        config.continuity.append({
            "cut": cut.id,
            "from_session": trace.get("session"),
            "from_version": cut.version,
            "relation": "restored continuity; revisable",
        })
    config.rebuild_edges()
    config.deltas = [_delta_from_record(r) for r in trace.get("deltas", [])]
    config.lifecycle = list(trace.get("lifecycle", []))
    config.unresolved = list(trace.get("unresolved", []))
    config.records = dict(trace.get("records", {}))
    config.continuity = list(trace.get("continuity", [])) + config.continuity
    return config
