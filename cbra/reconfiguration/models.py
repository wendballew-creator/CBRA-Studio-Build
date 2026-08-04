"""Records for the first ``recursive-reconfiguration-v1`` substrate slice.

The records are inscriptions about local enactments.  They are deliberately
not a domain model of persons, events, intentions, or phenomena.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Tuple


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return value


def frozen_mapping(value: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    return _freeze(dict(value or {}))


def _mapping_keys(value: Any) -> Tuple[str, ...]:
    if isinstance(value, Mapping):
        nested = tuple(
            child
            for item in value.values()
            for child in _mapping_keys(item)
        )
        return tuple(str(key) for key in value) + nested
    if isinstance(value, (tuple, list, set, frozenset)):
        return tuple(child for item in value for child in _mapping_keys(item))
    return ()


class StructuralDimension(str, Enum):
    BURDEN = "burden"
    CAPACITY = "capacity"
    CONSEQUENCE = "consequence"
    POSSIBILITY = "possibility"


@dataclass(frozen=True)
class TransportTrace:
    """Stable technical evidence without a semantic role.

    ``payload`` is opaque to this substrate.  Channel and provenance describe
    transport facts only; semantic interpretation belongs in a local cut.
    """

    trace_id: str
    channel: str
    digest: str
    payload: bytes
    observed_at: str
    provenance: Mapping[str, Any] = field(default_factory=frozen_mapping)

    def __post_init__(self) -> None:
        object.__setattr__(self, "provenance", frozen_mapping(self.provenance))
        if not self.trace_id or not self.channel or not self.digest:
            raise ValueError("transport trace identifiers must be nonempty")
        if not isinstance(self.payload, bytes):
            raise TypeError("transport payload must remain opaque bytes")
        forbidden = {
            "actor",
            "event",
            "explanation",
            "failure",
            "identity",
            "intent",
            "role",
            "user",
        }
        collision = forbidden.intersection(_mapping_keys(self.provenance))
        if collision:
            raise ValueError(
                "transport provenance cannot declare semantic roles: "
                + ", ".join(sorted(collision))
            )


@dataclass(frozen=True)
class LocalPositionRef:
    cut_id: str
    position_key: str


@dataclass(frozen=True)
class CutPosition:
    """A semantic position that has no identity outside its owning cut."""

    key: str
    local_name: str


@dataclass(frozen=True)
class Relation:
    relation_type: str
    source: LocalPositionRef
    target: LocalPositionRef


@dataclass(frozen=True)
class Allocation:
    dimension: StructuralDimension
    position: LocalPositionRef
    amount: float

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("structural allocation cannot be negative")


@dataclass(frozen=True)
class CutEnactment:
    cut_id: str
    transport_basis: Tuple[str, ...]
    dependency_ids: Tuple[str, ...]
    lineage_ids: Tuple[str, ...]
    positions: Tuple[CutPosition, ...]
    relations: Tuple[Relation, ...] = ()
    allocations: Tuple[Allocation, ...] = ()
    revision_conditions: Tuple[str, ...] = ()
    exclusions: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ReconfigurationDelta:
    delta_id: str
    activated_cut_ids: Tuple[str, ...]
    invalidated_cut_ids: Tuple[str, ...]
    changed_dimensions: Tuple[StructuralDimension, ...]
    allocation_before: Tuple[Allocation, ...]
    allocation_after: Tuple[Allocation, ...]
    triggering_trace_ids: Tuple[str, ...]

    @property
    def has_structural_change(self) -> bool:
        return bool(
            self.activated_cut_ids
            or self.invalidated_cut_ids
            or self.changed_dimensions
        )


@dataclass(frozen=True)
class ConfigurationTrace:
    version: int = 0
    transports: Mapping[str, TransportTrace] = field(default_factory=frozen_mapping)
    cuts: Mapping[str, CutEnactment] = field(default_factory=frozen_mapping)
    active_cut_ids: Tuple[str, ...] = ()
    invalidated_by: Mapping[str, str] = field(default_factory=frozen_mapping)
    deltas: Tuple[ReconfigurationDelta, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "transports", frozen_mapping(self.transports))
        object.__setattr__(self, "cuts", frozen_mapping(self.cuts))
        object.__setattr__(self, "invalidated_by", frozen_mapping(self.invalidated_by))
