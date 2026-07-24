"""Durable file repository for architecture-native CBRA sessions."""

from __future__ import annotations

import fcntl
import hashlib
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Union

from cbra.native.persistence import load_session, save_session
from cbra.native.session import (
    SessionOwnershipError,
    StaleRevisionError,
    assert_session_invariants,
)
from cbra.native.session_models import NativeSession


PathLike = Union[str, Path]


class SessionRepositoryError(ValueError):
    """Base error for durable native-session ownership."""


class SessionNotFoundError(SessionRepositoryError):
    """No durable native session exists for the requested thread."""


class SessionAlreadyExistsError(SessionRepositoryError):
    """A durable native session already owns the requested thread."""


class NativeSessionRepository:
    """Atomic compare-and-save repository keyed by native thread identity."""

    def __init__(self, root: PathLike, compress: bool = True) -> None:
        self.root = Path(root)
        self.compress = compress
        if not self.root.exists():
            raise FileNotFoundError(
                "Session repository directory does not exist: {0}".format(
                    self.root
                )
            )
        if not self.root.is_dir():
            raise NotADirectoryError(str(self.root))

    @staticmethod
    def _key(thread_id: str) -> str:
        if not isinstance(thread_id, str) or not thread_id.strip():
            raise SessionRepositoryError(
                "thread_id must be a non-empty string"
            )
        return hashlib.sha256(thread_id.encode("utf-8")).hexdigest()

    def path_for(self, thread_id: str) -> Path:
        suffix = ".json.gz" if self.compress else ".json"
        return self.root / "native-session-{0}{1}".format(
            self._key(thread_id),
            suffix,
        )

    def _lock_path(self, thread_id: str) -> Path:
        return self.root / ".native-session-{0}.lock".format(
            self._key(thread_id)
        )

    @contextmanager
    def _lock(
        self,
        thread_id: str,
        exclusive: bool,
    ) -> Iterator[None]:
        lock_path = self._lock_path(thread_id)
        with lock_path.open("a+b") as handle:
            operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            fcntl.flock(handle.fileno(), operation)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def create(self, session: NativeSession) -> None:
        """Persist a newly owned session only when no record exists."""
        assert_session_invariants(session)
        path = self.path_for(session.thread_id)
        with self._lock(session.thread_id, exclusive=True):
            if path.exists():
                raise SessionAlreadyExistsError(
                    "Session already exists for thread {0}".format(
                        session.thread_id
                    )
                )
            save_session(path, session, compress=self.compress)

    def load(self, thread_id: str) -> NativeSession:
        """Load the one session owned by ``thread_id``."""
        path = self.path_for(thread_id)
        with self._lock(thread_id, exclusive=False):
            if not path.exists():
                raise SessionNotFoundError(
                    "Session not found for thread {0}".format(thread_id)
                )
            session = load_session(path)
        if session.thread_id != thread_id:
            raise SessionOwnershipError(
                "Durable session belongs to a different thread"
            )
        assert_session_invariants(session)
        return session

    def save(
        self,
        session: NativeSession,
        expected_revision: int,
    ) -> None:
        """Atomically replace a session only from its observed revision."""
        assert_session_invariants(session)
        if type(expected_revision) is not int or expected_revision < 0:
            raise SessionRepositoryError(
                "expected_revision must be a non-negative integer"
            )
        path = self.path_for(session.thread_id)
        with self._lock(session.thread_id, exclusive=True):
            if not path.exists():
                raise SessionNotFoundError(
                    "Session not found for thread {0}".format(
                        session.thread_id
                    )
                )
            current = load_session(path)
            if current.thread_id != session.thread_id:
                raise SessionOwnershipError(
                    "Durable session belongs to a different thread"
                )
            if current.revision != expected_revision:
                raise StaleRevisionError(
                    "Expected durable revision {0}, found {1}".format(
                        expected_revision,
                        current.revision,
                    )
                )
            if current == session:
                return
            if session.revision != expected_revision + 1:
                raise StaleRevisionError(
                    "Native session must advance exactly one revision"
                )
            save_session(path, session, compress=self.compress)

    def exists(self, thread_id: str) -> bool:
        return self.path_for(thread_id).exists()
