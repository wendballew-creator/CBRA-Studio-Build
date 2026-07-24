"""Application service for durable, architecture-native CBRA sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from cbra.native import (
    DEFAULT_MAX_CYCLES,
    NativeSession,
    RuntimeHypotheses,
    StaleRevisionError,
    Stream,
    TurnOutcome,
    TurnOutcomeKind,
    create_session,
    submit_turn,
)
from cbra.store import (
    NativeSessionRepository,
    SessionAlreadyExistsError,
)


@dataclass(frozen=True)
class ApplicationTurnResult:
    """Publicly mappable result of one durable turn operation."""

    outcome: TurnOutcome
    replayed: bool


@dataclass(frozen=True)
class ApplicationSessionSummary:
    """Bounded session information that does not expose native field state."""

    thread_id: str
    revision: int
    turn_count: int
    cycle_count: int
    latest_outcome: Optional[TurnOutcomeKind]
    reintegration_pending: bool


class NativeApplicationService:
    """Coordinate native turn ingress with atomic durable ownership."""

    def __init__(
        self,
        repository: NativeSessionRepository,
        *,
        max_cycles: int = DEFAULT_MAX_CYCLES,
        hypotheses: Optional[RuntimeHypotheses] = None,
    ) -> None:
        if type(max_cycles) is not int or max_cycles < 1:
            raise ValueError("max_cycles must be a positive integer")
        self.repository = repository
        self.max_cycles = max_cycles
        self.hypotheses = hypotheses

    def create_thread(
        self,
        thread_id: str,
        user_text: str,
        *,
        turn_id: str,
    ) -> ApplicationTurnResult:
        """Create an exactly claimed session or replay its first turn."""
        session = create_session(thread_id=thread_id)
        updated, outcome = submit_turn(
            session,
            user_text,
            turn_id=turn_id,
            expected_revision=0,
            max_cycles=self.max_cycles,
            hypotheses=self.hypotheses,
        )
        try:
            self.repository.create(updated)
        except SessionAlreadyExistsError:
            current = self.repository.load(thread_id)
            if (
                not current.turns
                or current.turns[0].turn_id != turn_id
            ):
                raise
            _, replay_outcome = submit_turn(
                current,
                user_text,
                turn_id=turn_id,
                expected_revision=0,
                max_cycles=self.max_cycles,
                hypotheses=self.hypotheses,
            )
            return ApplicationTurnResult(
                outcome=replay_outcome,
                replayed=True,
            )
        return ApplicationTurnResult(
            outcome=outcome,
            replayed=False,
        )

    def submit_thread_turn(
        self,
        thread_id: str,
        user_text: str,
        *,
        turn_id: Optional[str] = None,
        expected_revision: Optional[int] = None,
        additional_streams: Sequence[Stream] = (),
    ) -> ApplicationTurnResult:
        """Load, submit, and compare-and-save one native turn."""
        session = self.repository.load(thread_id)
        observed_revision = session.revision
        updated, outcome = submit_turn(
            session,
            user_text,
            additional_streams=additional_streams,
            turn_id=turn_id,
            expected_revision=expected_revision,
            max_cycles=self.max_cycles,
            hypotheses=self.hypotheses,
        )
        if updated is session:
            return ApplicationTurnResult(
                outcome=outcome,
                replayed=True,
            )

        try:
            self.repository.save(
                updated,
                expected_revision=observed_revision,
            )
        except StaleRevisionError as conflict:
            current = self.repository.load(thread_id)
            retried, retry_outcome = submit_turn(
                current,
                user_text,
                additional_streams=additional_streams,
                turn_id=outcome.turn_id,
                expected_revision=expected_revision,
                max_cycles=self.max_cycles,
                hypotheses=self.hypotheses,
            )
            if retried is current:
                return ApplicationTurnResult(
                    outcome=retry_outcome,
                    replayed=True,
                )
            raise conflict

        return ApplicationTurnResult(
            outcome=outcome,
            replayed=False,
        )

    def load_session(self, thread_id: str) -> NativeSession:
        """Load a session for internal service use without exposing its field."""
        return self.repository.load(thread_id)

    def summarize_thread(
        self,
        thread_id: str,
    ) -> ApplicationSessionSummary:
        """Return a bounded public account of durable session progress."""
        session = self.repository.load(thread_id)
        latest_outcome = (
            session.turns[-1].outcome if session.turns else None
        )
        return ApplicationSessionSummary(
            thread_id=session.thread_id,
            revision=session.revision,
            turn_count=len(session.turns),
            cycle_count=len(session.field.history),
            latest_outcome=latest_outcome,
            reintegration_pending=(
                latest_outcome == TurnOutcomeKind.REINTEGRATION_PENDING
            ),
        )
