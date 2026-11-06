"""Native thread ownership, truthful turn ingress, and bounded orchestration."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Dict, Optional, Sequence, Tuple
from uuid import uuid4

from .articulation import (
    ArticulationRenderer,
    ArticulationRendererBinding,
    assert_renderer_binding,
    materialize_renderer_binding,
)
from .hypotheses import RuntimeHypotheses
from .models import Apparatus, FieldState, Stream
from .runtime import (
    assert_native_invariants,
    initialize_field,
    run_cycle,
)
from .schemas import StreamSchema, model_dump
from .session_models import (
    NativeSession,
    ReintegrationReference,
    TurnOutcome,
    TurnOutcomeKind,
    TurnRecord,
)


DEFAULT_MAX_CYCLES = 8


class NativeSessionError(ValueError):
    """Base error for native session ownership and turn ingress."""


class StaleRevisionError(NativeSessionError):
    """A caller attempted to continue an out-of-date session revision."""


class TurnConflictError(NativeSessionError):
    """An existing turn ID was reused with different material."""


class SessionOwnershipError(NativeSessionError):
    """A session and its authoritative native field do not belong together."""


def _owned_field_id(thread_id: str) -> str:
    digest = hashlib.sha256(thread_id.encode("utf-8")).hexdigest()
    return "field:thread:{0}".format(digest)


def _turn_stream_id(thread_id: str, turn_id: str) -> str:
    material = "{0}\x00{1}".format(thread_id, turn_id).encode("utf-8")
    return "stream:turn:{0}".format(hashlib.sha256(material).hexdigest())


def _canonical_bytes(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _material_digest(
    user_text: str,
    additional_streams: Sequence[Stream],
) -> str:
    streams = [
        model_dump(StreamSchema.from_native(item))
        for item in additional_streams
    ]
    material = {
        "additional_streams": streams,
        "user_text": user_text,
    }
    return hashlib.sha256(_canonical_bytes(material)).hexdigest()


def _record_history_references(
    field: FieldState,
    cycle_start: int,
    cycle_end: int,
) -> Tuple[
    Tuple[str, ...],
    Tuple[str, ...],
    Tuple[str, ...],
    Tuple[ReintegrationReference, ...],
]:
    entries = field.history[cycle_start - 1 : cycle_end]
    candidate_ids = tuple(
        item.candidate_id
        for item in entries
        if item.candidate_id is not None
    )
    evaluation_ids = tuple(
        item.evaluation_id
        for item in entries
        if item.evaluation_id is not None
    )
    articulation_ids = tuple(
        item.articulation_id
        for item in entries
        if item.articulation_id is not None
    )
    reintegrations = tuple(
        ReintegrationReference(
            cycle=entry.cycle,
            index=index,
            drift_kind=trace.drift_kind,
            reentry_target=trace.reentry_target,
        )
        for entry in entries
        for index, trace in enumerate(entry.reintegrations)
    )
    return (
        candidate_ids,
        evaluation_ids,
        articulation_ids,
        reintegrations,
    )


def _outcome_from_record(
    session: NativeSession,
    record: TurnRecord,
) -> TurnOutcome:
    articulations = {
        item.articulation_id: item for item in session.field.articulations
    }
    articulation = (
        deepcopy(articulations[record.articulation_ids[-1]])
        if record.articulation_ids
        else None
    )
    return TurnOutcome(
        thread_id=session.thread_id,
        turn_id=record.turn_id,
        revision=record.revision,
        kind=record.outcome,
        cycle_start=record.cycle_start,
        cycle_end=record.cycle_end,
        articulation=articulation,
        reintegrations=record.reintegrations,
    )


def create_session(
    thread_id: Optional[str] = None,
    initial_streams: Sequence[Stream] = (),
    apparatus: Optional[Apparatus] = None,
    hypotheses: Optional[RuntimeHypotheses] = None,
    renderer_binding: Optional[ArticulationRendererBinding] = None,
) -> NativeSession:
    """Create one native field whose ownership is fixed to a thread."""
    resolved_thread_id = thread_id or "thread:{0}".format(uuid4().hex)
    if not isinstance(resolved_thread_id, str) or not resolved_thread_id.strip():
        raise NativeSessionError("thread_id must be a non-empty string")
    field_id = _owned_field_id(resolved_thread_id)
    field = initialize_field(
        initial_streams,
        apparatus=materialize_renderer_binding(
            apparatus,
            renderer_binding,
        ),
        field_id=field_id,
        hypotheses=hypotheses,
    )
    session = NativeSession(
        thread_id=resolved_thread_id,
        field_id=field_id,
        field=field,
    )
    assert_session_invariants(session)
    return session


def submit_turn(
    session: NativeSession,
    user_text: str,
    additional_streams: Sequence[Stream] = (),
    turn_id: Optional[str] = None,
    expected_revision: Optional[int] = None,
    max_cycles: int = DEFAULT_MAX_CYCLES,
    hypotheses: Optional[RuntimeHypotheses] = None,
    renderer: Optional[ArticulationRenderer] = None,
    renderer_binding: Optional[ArticulationRendererBinding] = None,
) -> Tuple[NativeSession, TurnOutcome]:
    """Append material once and expose the field's bounded truthful outcome."""
    assert_session_invariants(session)
    if not isinstance(user_text, str) or not user_text.strip():
        raise NativeSessionError("user_text must be a non-empty string")

    resolved_turn_id = turn_id or "turn:{0}".format(uuid4().hex)
    if not isinstance(resolved_turn_id, str) or not resolved_turn_id.strip():
        raise NativeSessionError("turn_id must be a non-empty string")
    if (
        expected_revision is not None
        and (
            type(expected_revision) is not int
            or expected_revision < 0
        )
    ):
        raise NativeSessionError(
            "expected_revision must be a non-negative integer"
        )
    if type(max_cycles) is not int or max_cycles < 1:
        raise NativeSessionError(
            "max_cycles must be a positive integer"
        )

    material = tuple(deepcopy(item) for item in additional_streams)
    existing = next(
        (
            item
            for item in session.turns
            if item.turn_id == resolved_turn_id
        ),
        None,
    )
    if existing is not None:
        digest = _material_digest(user_text, material)
        if existing.material_digest != digest:
            raise TurnConflictError(
                "turn_id {0} already names different material".format(
                    resolved_turn_id
                )
            )
        return session, _outcome_from_record(session, existing)

    if (
        expected_revision is not None
        and expected_revision != session.revision
    ):
        raise StaleRevisionError(
            "Expected session revision {0}, found {1}".format(
                expected_revision,
                session.revision,
            )
        )
    digest = _material_digest(user_text, material)
    assert_renderer_binding(
        session.field.apparatus,
        renderer,
        renderer_binding,
    )

    working = deepcopy(session)
    user_stream_id = _turn_stream_id(
        working.thread_id,
        resolved_turn_id,
    )
    incoming_ids = [user_stream_id] + [
        item.stream_id for item in material
    ]
    if len(incoming_ids) != len(set(incoming_ids)):
        raise NativeSessionError(
            "turn ingress contains duplicate stream IDs"
        )
    existing_stream_ids = {
        item.stream_id for item in working.field.streams
    }
    collisions = sorted(set(incoming_ids) & existing_stream_ids)
    if collisions:
        raise NativeSessionError(
            "turn ingress collides with existing stream IDs: {0}".format(
                ", ".join(collisions)
            )
        )

    next_revision = working.revision + 1
    working.field.streams.append(
        Stream(
            stream_id=user_stream_id,
            kind="user_input",
            participation=1.0,
            persistence=0.8,
            payload={"text": user_text},
            provenance={
                "role": "user",
                "thread_id": working.thread_id,
                "turn_id": resolved_turn_id,
                "revision": next_revision,
            },
        )
    )
    working.field.streams.extend(deepcopy(material))
    assert_native_invariants(working.field)

    cycle_start = len(working.field.history) + 1
    kind = TurnOutcomeKind.NO_ARTICULATION
    for _ in range(max_cycles):
        if renderer is None:
            result = run_cycle(working.field, hypotheses)
        else:
            result = run_cycle(
                working.field,
                hypotheses,
                renderer,
                renderer_binding,
            )
        if result.articulation is not None:
            kind = TurnOutcomeKind.ACCEPTED_ARTICULATION
            break
        if result.reintegrations:
            kind = TurnOutcomeKind.REINTEGRATION_PENDING
            break
    cycle_end = len(working.field.history)
    (
        candidate_ids,
        evaluation_ids,
        articulation_ids,
        reintegrations,
    ) = _record_history_references(
        working.field,
        cycle_start,
        cycle_end,
    )
    record = TurnRecord(
        turn_id=resolved_turn_id,
        revision=next_revision,
        material_digest=digest,
        user_stream_id=user_stream_id,
        additional_stream_ids=tuple(
            item.stream_id for item in material
        ),
        cycle_start=cycle_start,
        cycle_end=cycle_end,
        candidate_ids=candidate_ids,
        evaluation_ids=evaluation_ids,
        articulation_ids=articulation_ids,
        reintegrations=reintegrations,
        outcome=kind,
    )
    working.revision = next_revision
    working.turns = working.turns + (record,)
    assert_session_invariants(working)
    return working, _outcome_from_record(working, record)


def assert_session_invariants(session: NativeSession) -> None:
    """Reject mixed ownership, broken ledgers, and invalid native references."""
    if not isinstance(session.thread_id, str) or not session.thread_id.strip():
        raise SessionOwnershipError(
            "native session requires a non-empty thread_id"
        )
    if session.field_id != session.field.field_id:
        raise SessionOwnershipError(
            "native session field does not match its recorded ownership"
        )
    if session.field_id != _owned_field_id(session.thread_id):
        raise SessionOwnershipError(
            "native field is owned by a different thread"
        )
    assert_native_invariants(session.field)
    if session.revision != len(session.turns):
        raise NativeSessionError(
            "session revision must equal its append-only turn count"
        )

    turn_ids = [item.turn_id for item in session.turns]
    if len(turn_ids) != len(set(turn_ids)):
        raise NativeSessionError("turn IDs must be unique")
    user_stream_ids = [item.user_stream_id for item in session.turns]
    if len(user_stream_ids) != len(set(user_stream_ids)):
        raise NativeSessionError("turn user stream IDs must be unique")

    streams: Dict[str, Stream] = {
        item.stream_id: item for item in session.field.streams
    }
    expected_cycle_start = 1
    for revision, record in enumerate(session.turns, start=1):
        if record.revision != revision:
            raise NativeSessionError(
                "turn revisions must be contiguous from 1"
            )
        if (
            len(record.material_digest) != 64
            or any(
                character not in "0123456789abcdef"
                for character in record.material_digest.lower()
            )
        ):
            raise NativeSessionError(
                "turn material digest must be a SHA-256 hexadecimal value"
            )
        if record.cycle_start != expected_cycle_start:
            raise NativeSessionError(
                "turn cycle ranges must be contiguous"
            )
        if record.cycle_end < record.cycle_start:
            raise NativeSessionError(
                "each turn must record at least one lifecycle cycle"
            )
        if record.cycle_end > len(session.field.history):
            raise NativeSessionError(
                "turn cycle range exceeds native lifecycle history"
            )
        expected_cycle_start = record.cycle_end + 1

        expected_user_stream_id = _turn_stream_id(
            session.thread_id,
            record.turn_id,
        )
        if record.user_stream_id != expected_user_stream_id:
            raise NativeSessionError(
                "turn user stream ID does not match its ownership"
            )
        user_stream = streams.get(record.user_stream_id)
        if user_stream is None or user_stream.kind != "user_input":
            raise NativeSessionError(
                "turn references an absent native user stream"
            )
        if (
            user_stream.provenance.get("thread_id") != session.thread_id
            or user_stream.provenance.get("turn_id") != record.turn_id
            or user_stream.provenance.get("revision") != record.revision
        ):
            raise NativeSessionError(
                "turn user stream provenance does not match its ledger"
            )
        missing_material = sorted(
            set(record.additional_stream_ids) - set(streams)
        )
        if len(record.additional_stream_ids) != len(
            set(record.additional_stream_ids)
        ):
            raise NativeSessionError(
                "turn additional stream IDs must be unique"
            )
        if missing_material:
            raise NativeSessionError(
                "turn references absent additional streams: {0}".format(
                    ", ".join(missing_material)
                )
            )

        (
            candidate_ids,
            evaluation_ids,
            articulation_ids,
            reintegrations,
        ) = _record_history_references(
            session.field,
            record.cycle_start,
            record.cycle_end,
        )
        if candidate_ids != record.candidate_ids:
            raise NativeSessionError(
                "turn candidate references do not match lifecycle history"
            )
        if evaluation_ids != record.evaluation_ids:
            raise NativeSessionError(
                "turn evaluation references do not match lifecycle history"
            )
        if articulation_ids != record.articulation_ids:
            raise NativeSessionError(
                "turn articulation references do not match lifecycle history"
            )
        if reintegrations != record.reintegrations:
            raise NativeSessionError(
                "turn reintegration references do not match lifecycle history"
            )

        if record.outcome == TurnOutcomeKind.ACCEPTED_ARTICULATION:
            if len(record.articulation_ids) != 1 or record.reintegrations:
                raise NativeSessionError(
                    "accepted turn must reference one articulation only"
                )
        elif record.outcome == TurnOutcomeKind.REINTEGRATION_PENDING:
            if record.articulation_ids or not record.reintegrations:
                raise NativeSessionError(
                    "reintegration outcome must reference reintegration only"
                )
        elif record.articulation_ids or record.reintegrations:
            raise NativeSessionError(
                "no-articulation turn cannot hide a formed outcome"
            )

    if session.turns:
        if session.turns[-1].cycle_end != len(session.field.history):
            raise NativeSessionError(
                "turn ledger must account for complete lifecycle history"
            )
    elif session.field.history:
        raise NativeSessionError(
            "unowned lifecycle history cannot enter a native session"
        )
