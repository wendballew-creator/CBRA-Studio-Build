"""Strict, immutable snapshots of the canonical CBRA corpus."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Mapping, Optional, Tuple

from cbra.native.models import Stream


CANONICAL_MANIFEST = "CBRA_Corpus_Index.md"
ACTIVE_SECTION = "## Canonical Files (Active)"
DEFAULT_MAX_FILES = 32
DEFAULT_MAX_FILE_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 8 * 1024 * 1024
CANONICAL_PARTICIPATION = 0.74
CANONICAL_PERSISTENCE = 0.90

CANONICAL_ROLE_MAP = {
    "CBRA_Kernel_v10_2.md": "ground_anchor",
    "CBRA_Loops_Core.md": "ground_anchor",
    "Drift_Constraints.md": "constraint_anchor",
    "CBRA_Glossary_v3.md": "operator_anchor",
}

_NUMBERED_ENTRY = re.compile(r"^([0-9]+)\.\s+(.+?)\s*$")
_POSITIVE_INTEGER = re.compile(r"^[1-9][0-9]*$")


class CanonicalCorpusError(ValueError):
    """The configured canonical corpus cannot form a safe snapshot."""


@dataclass(frozen=True)
class CorpusLimits:
    """Resource bounds applied before canonical text enters the runtime."""

    max_files: int = DEFAULT_MAX_FILES
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES

    def __post_init__(self) -> None:
        for name in (
            "max_files",
            "max_file_bytes",
            "max_total_bytes",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise CanonicalCorpusError(
                    "{0} must be a positive integer".format(name)
                )

    @classmethod
    def from_environment(
        cls,
        environ: Optional[Mapping[str, str]] = None,
    ) -> "CorpusLimits":
        """Load strict positive bounds from the process environment."""
        values = environ if environ is not None else os.environ
        return cls(
            max_files=_environment_limit(
                values,
                "CBRA_CORPUS_MAX_FILES",
                DEFAULT_MAX_FILES,
            ),
            max_file_bytes=_environment_limit(
                values,
                "CBRA_CORPUS_MAX_FILE_BYTES",
                DEFAULT_MAX_FILE_BYTES,
            ),
            max_total_bytes=_environment_limit(
                values,
                "CBRA_CORPUS_MAX_TOTAL_BYTES",
                DEFAULT_MAX_TOTAL_BYTES,
            ),
        )


@dataclass(frozen=True)
class CanonicalSource:
    """One complete source held by an immutable process snapshot."""

    filename: str
    role: str
    text: str
    content_digest: str
    stream_id: str

    def to_stream(
        self,
        *,
        manifest_digest: str,
        corpus_digest: str,
    ) -> Stream:
        """Materialize a fresh full-thickness native stream."""
        metadata = {
            "filename": self.filename,
            "canonical_role": self.role,
            "content_digest": self.content_digest,
            "manifest_digest": manifest_digest,
            "corpus_digest": corpus_digest,
        }
        return Stream(
            stream_id=self.stream_id,
            kind="document",
            participation=CANONICAL_PARTICIPATION,
            persistence=CANONICAL_PERSISTENCE,
            payload={
                "text": self.text,
                "material_handle": "canonical:{0}".format(self.filename),
                **metadata,
            },
            provenance={
                "source": "canonical_corpus",
                "immutable_snapshot": True,
                **metadata,
            },
        )


@dataclass(frozen=True)
class CanonicalCorpusSnapshot:
    """Ordered canonical material loaded exactly once for a process."""

    root: str
    manifest_digest: str
    corpus_digest: str
    sources: Tuple[CanonicalSource, ...]

    def to_streams(self) -> Tuple[Stream, ...]:
        """Return new stream objects without exposing mutable snapshot state."""
        return tuple(
            source.to_stream(
                manifest_digest=self.manifest_digest,
                corpus_digest=self.corpus_digest,
            )
            for source in self.sources
        )


def _environment_limit(
    environ: Mapping[str, str],
    name: str,
    default: int,
) -> int:
    raw = environ.get(name)
    if raw is None:
        return default
    if not isinstance(raw, str) or not _POSITIVE_INTEGER.fullmatch(raw):
        raise CanonicalCorpusError(
            "{0} must be a positive decimal integer".format(name)
        )
    return int(raw)


def _read_bytes(path: Path, *, label: str) -> bytes:
    try:
        return path.read_bytes()
    except (OSError, ValueError) as exc:
        raise CanonicalCorpusError(
            "{0} is missing or unreadable".format(label)
        ) from exc


def _file_size(path: Path, *, label: str) -> int:
    try:
        return path.stat().st_size
    except (OSError, ValueError) as exc:
        raise CanonicalCorpusError(
            "{0} is missing or unreadable".format(label)
        ) from exc


def _read_bounded_bytes(
    path: Path,
    *,
    label: str,
    max_bytes: int,
) -> bytes:
    if _file_size(path, label=label) > max_bytes:
        raise CanonicalCorpusError(
            "{0} exceeds the per-file byte limit".format(label)
        )
    data = _read_bytes(path, label=label)
    if len(data) > max_bytes:
        raise CanonicalCorpusError(
            "{0} exceeds the per-file byte limit".format(label)
        )
    return data


def _decode_utf8(data: bytes, *, label: str) -> str:
    try:
        return data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CanonicalCorpusError(
            "{0} is not valid UTF-8".format(label)
        ) from exc


def _active_filenames(manifest_text: str) -> Tuple[str, ...]:
    active_found = False
    in_active = False
    filenames = []
    expected_number = 1

    for line in manifest_text.splitlines():
        stripped = line.strip()
        if stripped == ACTIVE_SECTION:
            if active_found:
                raise CanonicalCorpusError(
                    "canonical manifest repeats the active section"
                )
            active_found = True
            in_active = True
            continue
        if in_active and stripped.startswith("##"):
            in_active = False
            continue
        if not in_active or not stripped:
            continue

        match = _NUMBERED_ENTRY.fullmatch(stripped)
        if match is None:
            raise CanonicalCorpusError(
                "canonical manifest contains a malformed active entry"
            )
        number = int(match.group(1))
        if number != expected_number:
            raise CanonicalCorpusError(
                "canonical manifest active entries must be contiguous"
            )
        filenames.append(match.group(2).strip())
        expected_number += 1

    if not active_found:
        raise CanonicalCorpusError(
            "canonical manifest has no active section"
        )
    if not filenames:
        raise CanonicalCorpusError(
            "canonical manifest active section is empty"
        )
    return tuple(filenames)


def _safe_relative_filename(filename: str) -> str:
    if (
        not filename
        or "\x00" in filename
        or "\\" in filename
        or filename.startswith("/")
        or PureWindowsPath(filename).is_absolute()
    ):
        raise CanonicalCorpusError(
            "canonical manifest contains an unsafe path"
        )
    parts = filename.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise CanonicalCorpusError(
            "canonical manifest contains an unsafe path"
        )
    return "/".join(parts)


def _canonical_digest(value) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_canonical_snapshot(
    corpus_root: Path,
    *,
    limits: Optional[CorpusLimits] = None,
) -> CanonicalCorpusSnapshot:
    """Fail closed while loading one ordered, content-addressed snapshot."""
    resolved_limits = limits or CorpusLimits()
    try:
        root = Path(corpus_root).resolve(strict=True)
    except (OSError, ValueError) as exc:
        raise CanonicalCorpusError(
            "canonical corpus root is missing or unreadable"
        ) from exc
    if not root.is_dir():
        raise CanonicalCorpusError(
            "canonical corpus root is not a directory"
        )

    try:
        manifest_path = (root / CANONICAL_MANIFEST).resolve(strict=True)
        manifest_path.relative_to(root)
    except (OSError, ValueError) as exc:
        raise CanonicalCorpusError(
            "canonical manifest is missing or escapes the corpus root"
        ) from exc
    if not manifest_path.is_file():
        raise CanonicalCorpusError(
            "canonical manifest is not a readable file"
        )
    manifest_bytes = _read_bounded_bytes(
        manifest_path,
        label="canonical manifest",
        max_bytes=resolved_limits.max_file_bytes,
    )
    manifest_text = _decode_utf8(
        manifest_bytes,
        label="canonical manifest",
    )
    filenames = _active_filenames(manifest_text)
    if len(filenames) > resolved_limits.max_files:
        raise CanonicalCorpusError(
            "canonical manifest exceeds the active file-count limit"
        )

    normalized = [_safe_relative_filename(item) for item in filenames]
    duplicate_keys = [item.casefold() for item in normalized]
    if len(duplicate_keys) != len(set(duplicate_keys)):
        raise CanonicalCorpusError(
            "canonical manifest contains duplicate active entries"
        )

    total_bytes = 0
    sources = []
    digest_entries = []
    for filename in normalized:
        role = CANONICAL_ROLE_MAP.get(filename)
        if role is None:
            raise CanonicalCorpusError(
                "canonical source has no declared role: {0}".format(
                    filename
                )
            )

        candidate = root.joinpath(*filename.split("/"))
        try:
            source_path = candidate.resolve(strict=True)
            source_path.relative_to(root)
        except (OSError, ValueError) as exc:
            raise CanonicalCorpusError(
                "canonical source is missing or escapes the corpus root: "
                "{0}".format(filename)
            ) from exc
        if not source_path.is_file():
            raise CanonicalCorpusError(
                "canonical source is not a readable file: {0}".format(
                    filename
                )
            )

        label = "canonical source {0}".format(filename)
        anticipated_bytes = _file_size(source_path, label=label)
        if total_bytes + anticipated_bytes > (
            resolved_limits.max_total_bytes
        ):
            raise CanonicalCorpusError(
                "canonical sources exceed the total byte limit"
            )
        content = _read_bounded_bytes(
            source_path,
            label=label,
            max_bytes=resolved_limits.max_file_bytes,
        )
        total_bytes += len(content)
        if total_bytes > resolved_limits.max_total_bytes:
            raise CanonicalCorpusError(
                "canonical sources exceed the total byte limit"
            )

        text = _decode_utf8(
            content,
            label="canonical source {0}".format(filename),
        )
        content_digest = hashlib.sha256(content).hexdigest()
        identity = hashlib.sha256(
            "{0}\x00{1}".format(
                filename,
                content_digest,
            ).encode("utf-8")
        ).hexdigest()
        sources.append(
            CanonicalSource(
                filename=filename,
                role=role,
                text=text,
                content_digest=content_digest,
                stream_id="stream:canonical:{0}".format(identity),
            )
        )
        digest_entries.append(
            {
                "filename": filename,
                "role": role,
                "content_digest": content_digest,
            }
        )

    return CanonicalCorpusSnapshot(
        root=str(root),
        manifest_digest=_canonical_digest(
            {"active_files": normalized}
        ),
        corpus_digest=_canonical_digest(digest_entries),
        sources=tuple(sources),
    )
