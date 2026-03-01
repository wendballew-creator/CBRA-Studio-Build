from __future__ import annotations

from typing import Dict, Optional
from uuid import uuid4

from cbra.models import DriftEvent, FieldArtifact, LoopCycle, Message, Thread


THREADS: Dict[str, Thread] = {}
FIELDS: Dict[str, FieldArtifact] = {}


def create_field(thread_id: str) -> FieldArtifact:
    field = FieldArtifact(thread_id=thread_id)
    FIELDS[field.id] = field
    return field


def get_field(field_id: str) -> Optional[FieldArtifact]:
    return FIELDS.get(field_id)


def update_field(field_id: str, patch: dict) -> Optional[FieldArtifact]:
    field = FIELDS.get(field_id)
    if field is None:
        return None
    # Pydantic v1 compatibility: create updated copy
    updated = field.copy(update=patch)
    FIELDS[field_id] = updated
    return updated


def create_thread(thread_id: Optional[str] = None) -> Thread:
    tid = thread_id or str(uuid4())
    thread = Thread(id=tid)
    # Attach a field artifact by default
    f = create_field(thread_id=tid)
    thread.current_field_id = f.id
    THREADS[tid] = thread
    return thread


def get_thread(thread_id: str) -> Optional[Thread]:
    return THREADS.get(thread_id)


def append_message(thread_id: str, msg: Message) -> None:
    THREADS[thread_id].messages.append(msg)


def append_loopcycle(thread_id: str, cycle: LoopCycle) -> None:
    THREADS[thread_id].loop_cycles.append(cycle)


def append_drift_event(thread_id: str, event: DriftEvent) -> None:
    THREADS[thread_id].drift_events.append(event)
