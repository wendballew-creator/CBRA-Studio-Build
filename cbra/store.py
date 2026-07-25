"""Durable file repository for architecture-native CBRA sessions."""

from __future__ import annotations

import fcntl
import hashlib
from copy import deepcopy
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator, Optional, Tuple, TypeVar, Union

from cbra.native.persistence import load_session, save_session
from cbra.native.session import (
    SessionOwnershipError,
    StaleRevisionError,
    assert_session_invariants,
)
from cbra.native.session_models import NativeSession


PathLike = Union[str, Path]
TransactionResult = TypeVar("TransactionResult")


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

    @staticmethod
    def _validate_owned(
        session: NativeSession,
        thread_id: str,
    ) -> None:
        if not isinstance(session, NativeSession):
            raise SessionRepositoryError(
                "transaction must return a native session"
            )
        if session.thread_id != thread_id:
            raise SessionOwnershipError(
                "Durable session belongs to a different thread"
            )
        assert_session_invariants(session)

    def _load_owned(
        self,
        path: Path,
        thread_id: str,
    ) -> NativeSession:
        session = load_session(path)
        self._validate_owned(session, thread_id)
        return session

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
            session = self._load_owned(path, thread_id)
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
            current = self._load_owned(path, session.thread_id)
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

    def transact(
        self,
        thread_id: str,
        operation: Callable[
            [Optional[NativeSession]],
            Tuple[NativeSession, TransactionResult],
        ],
    ) -> TransactionResult:
        """Execute and durably claim at most one revision under one lock."""
        if not callable(operation):
            raise TypeError("operation must be callable")
        path = self.path_for(thread_id)
        with self._lock(thread_id, exclusive=True):
            current = (
                self._load_owned(path, thread_id)
                if path.exists()
                else None
            )
            working = deepcopy(current)
            returned = operation(working)
            if not isinstance(returned, tuple) or len(returned) != 2:
                raise SessionRepositoryError(
                    "transaction operation must return (session, result)"
                )
            updated, result = returned
            self._validate_owned(updated, thread_id)

            if current is None:
                if updated.revision != 1:
                    raise StaleRevisionError(
                        "A new native session must claim revision 1"
                    )
                save_session(path, updated, compress=self.compress)
                return result

            if updated == current:
                return result
            if updated.revision != current.revision + 1:
                raise StaleRevisionError(
                    "Native session must advance exactly one revision"
                )
            if updated.turns[:-1] != current.turns:
                raise SessionRepositoryError(
                    "Native session transaction must preserve prior turns"
                )
            save_session(path, updated, compress=self.compress)
            return result

    def exists(self, thread_id: str) -> bool:
        return self.path_for(thread_id).exists()
