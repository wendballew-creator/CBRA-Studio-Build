from datetime import datetime
from uuid import uuid4
from typing import Dict, Optional

from .models import Thread, Message, LoopCycle, DriftEvent

# In-memory thread storage (Phase 1)
THREADS: Dict[str, Thread] = {}


def create_thread(thread_id: Optional[str] = None) -> Thread:
    """
    Create a new thread or use provided thread_id.
    """
    if not thread_id:
        thread_id = str(uuid4())

    thread = Thread(
        id=thread_id,
        messages=[],
        loop_history=[],
        drift_events=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    THREADS[thread_id] = thread
    return thread


def get_thread(thread_id: str) -> Optional[Thread]:
    """
    Retrieve an existing thread.
    """
    return THREADS.get(thread_id)


def append_message(thread_id: str, message: Message) -> None:
    thread = THREADS[thread_id]
    thread.messages.append(message)
    thread.updated_at = datetime.utcnow()


def append_loopcycle(thread_id: str, loopcycle: LoopCycle) -> None:
    thread = THREADS[thread_id]
    thread.loop_history.append(loopcycle)
    thread.updated_at = datetime.utcnow()


def append_drift_event(thread_id: str, drift_event: DriftEvent) -> None:
    thread = THREADS[thread_id]
    thread.drift_events.append(drift_event)
    thread.updated_at = datetime.utcnow()
