"""Application service for durable, architecture-native CBRA sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

from cbra.corpus import CanonicalCorpusSnapshot
from cbra.native import (
    DEFAULT_MAX_CYCLES,
    ArticulationRenderer,
    NativeSession,
    NativeSessionError,
    RuntimeHypotheses,
    Stream,
    TurnOutcome,
    TurnOutcomeKind,
    create_session,
    submit_turn,
)
from cbra.store import (
    NativeSessionRepository,
    SessionAlreadyExistsError,
    SessionNotFoundError,
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


@dataclass(frozen=True)
class ApplicationTurnProjection:
    """One ledger-owned turn rendered without exposing native field state."""

    turn_id: str
    revision: int
    user_text: str
    outcome: TurnOutcomeKind
    text: Optional[str]


@dataclass(frozen=True)
class ApplicationTurnPage:
    """One immutable, cursor-bounded page of public native turns."""

    thread_id: str
    session_revision: int
    turns: Tuple[ApplicationTurnProjection, ...]
    next_after_revision: int
    has_more: bool


class TurnProjectionPaginationError(ValueError):
    """A transcript cursor cannot name a valid bounded session page."""


class NativeApplicationService:
    """Coordinate native turn ingress with atomic durable ownership."""

    def __init__(
        self,
        repository: NativeSessionRepository,
        *,
        max_cycles: int = DEFAULT_MAX_CYCLES,
        hypotheses: Optional[RuntimeHypotheses] = None,
        canonical_corpus: Optional[CanonicalCorpusSnapshot] = None,
        renderer: Optional[ArticulationRenderer] = None,
    ) -> None:
        if type(max_cycles) is not int or max_cycles < 1:
            raise ValueError("max_cycles must be a positive integer")
        self.repository = repository
        self.max_cycles = max_cycles
        self.hypotheses = hypotheses
        self.canonical_corpus = canonical_corpus
        if (
            renderer is not None
            and not callable(getattr(renderer, "render", None))
        ):
            raise TypeError(
                "renderer must provide a callable render method"
            )
        self.renderer = renderer

    def create_thread(
        self,
        thread_id: str,
        user_text: str,
        *,
        turn_id: str,
        additional_streams: Sequence[Stream] = (),
    ) -> ApplicationTurnResult:
        """Create an exactly claimed session or replay its first turn."""
        initial_streams = (
            self.canonical_corpus.to_streams()
            if self.canonical_corpus is not None
            else ()
        )

        def create_or_replay(current):
            if current is not None:
                if (
                    not current.turns
                    or current.turns[0].turn_id != turn_id
                ):
                    raise SessionAlreadyExistsError(
                        "Session already exists for thread {0}".format(
                            thread_id
                        )
                    )
                updated, outcome = submit_turn(
                    current,
                    user_text,
                    additional_streams=additional_streams,
                    turn_id=turn_id,
                    expected_revision=0,
                    max_cycles=self.max_cycles,
                    hypotheses=self.hypotheses,
                    renderer=self.renderer,
                )
                return updated, ApplicationTurnResult(
                    outcome=outcome,
                    replayed=True,
                )

            session = create_session(
                thread_id=thread_id,
                initial_streams=initial_streams,
            )
            updated, outcome = submit_turn(
                session,
                user_text,
                additional_streams=additional_streams,
                turn_id=turn_id,
                expected_revision=0,
                max_cycles=self.max_cycles,
                hypotheses=self.hypotheses,
                renderer=self.renderer,
            )
            return updated, ApplicationTurnResult(
                outcome=outcome,
                replayed=False,
            )

        return self.repository.transact(thread_id, create_or_replay)

    def submit_thread_turn(
        self,
        thread_id: str,
        user_text: str,
        *,
        turn_id: Optional[str] = None,
        expected_revision: Optional[int] = None,
        additional_streams: Sequence[Stream] = (),
    ) -> ApplicationTurnResult:
        """Submit or replay one native turn inside its durable transaction."""

        def submit_or_replay(current):
            if current is None:
                raise SessionNotFoundError(
                    "Session not found for thread {0}".format(thread_id)
                )
            updated, outcome = submit_turn(
                current,
                user_text,
                additional_streams=additional_streams,
                turn_id=turn_id,
                expected_revision=expected_revision,
                max_cycles=self.max_cycles,
                hypotheses=self.hypotheses,
                renderer=self.renderer,
            )
            return updated, ApplicationTurnResult(
                outcome=outcome,
                replayed=updated is current,
            )

        return self.repository.transact(thread_id, submit_or_replay)

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

    def project_thread_turns(
        self,
        thread_id: str,
        *,
        after_revision: int = 0,
        limit: int = 50,
    ) -> ApplicationTurnPage:
        """Project one immutable page from ledger-owned public references."""
        if type(after_revision) is not int or after_revision < 0:
            raise TurnProjectionPaginationError(
                "after_revision must be a non-negative integer"
            )
        if type(limit) is not int or limit < 1 or limit > 100:
            raise TurnProjectionPaginationError(
                "limit must be between 1 and 100"
            )

        session = self.repository.load(thread_id)
        if after_revision > session.revision:
            raise TurnProjectionPaginationError(
                "after_revision exceeds the current session revision"
            )

        streams = {
            item.stream_id: item
            for item in session.field.streams
        }
        articulations = {
            item.articulation_id: item
            for item in session.field.articulations
        }
        selected = session.turns[
            after_revision : after_revision + limit
        ]
        projected = []
        for record in selected:
            user_stream = streams.get(record.user_stream_id)
            if user_stream is None or user_stream.kind != "user_input":
                raise NativeSessionError(
                    "turn projection references an invalid user stream"
                )
            user_text = user_stream.payload.get("text")
            if not isinstance(user_text, str) or not user_text.strip():
                raise NativeSessionError(
                    "turn projection user stream has invalid text"
                )

            text = None
            if record.outcome == TurnOutcomeKind.ACCEPTED_ARTICULATION:
                if len(record.articulation_ids) != 1:
                    raise NativeSessionError(
                        "accepted turn projection has invalid articulation "
                        "references"
                    )
                articulation = articulations.get(
                    record.articulation_ids[0]
                )
                if (
                    articulation is None
                    or not isinstance(articulation.text, str)
                    or not articulation.text.strip()
                ):
                    raise NativeSessionError(
                        "accepted turn projection references invalid text"
                    )
                text = articulation.text

            projected.append(
                ApplicationTurnProjection(
                    turn_id=record.turn_id,
                    revision=record.revision,
                    user_text=user_text,
                    outcome=record.outcome,
                    text=text,
                )
            )

        next_after_revision = (
            projected[-1].revision
            if projected
            else after_revision
        )
        return ApplicationTurnPage(
            thread_id=session.thread_id,
            session_revision=session.revision,
            turns=tuple(projected),
            next_after_revision=next_after_revision,
            has_more=next_after_revision < session.revision,
        )
