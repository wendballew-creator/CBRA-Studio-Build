"""Typed ownership and turn records for native CBRA sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple

from .models import (
    Articulation,
    DriftKind,
    FieldState,
    ReentryTarget,
)


class TurnOutcomeKind(str, Enum):
    ACCEPTED_ARTICULATION = "accepted_articulation"
    REINTEGRATION_PENDING = "reintegration_pending"
    NO_ARTICULATION = "no_articulation"


@dataclass(frozen=True)
class ReintegrationReference:
    """Stable location of one reintegration inside native lifecycle history."""

    cycle: int
    index: int
    drift_kind: DriftKind
    reentry_target: ReentryTarget


@dataclass(frozen=True)
class TurnRecord:
    """Append-only account of material and lifecycle work for one turn."""

    turn_id: str
    revision: int
    material_digest: str
    user_stream_id: str
    additional_stream_ids: Tuple[str, ...]
    cycle_start: int
    cycle_end: int
    candidate_ids: Tuple[str, ...]
    evaluation_ids: Tuple[str, ...]
    articulation_ids: Tuple[str, ...]
    reintegrations: Tuple[ReintegrationReference, ...]
    outcome: TurnOutcomeKind


@dataclass
class NativeSession:
    """One authoritative native field and its immutable turn ledger."""

    thread_id: str
    field_id: str
    field: FieldState
    revision: int = 0
    turns: Tuple[TurnRecord, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TurnOutcome:
    """Truthful result of bounded field movement for one submitted turn."""

    thread_id: str
    turn_id: str
    revision: int
    kind: TurnOutcomeKind
    cycle_start: int
    cycle_end: int
    articulation: Optional[Articulation]
    reintegrations: Tuple[ReintegrationReference, ...]

    @property
    def text(self) -> Optional[str]:
        return (
            self.articulation.text
            if self.articulation is not None
            else None
        )
