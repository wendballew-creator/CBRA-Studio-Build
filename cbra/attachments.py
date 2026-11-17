"""Bounded, immutable extraction of user attachments into native streams."""

from __future__ import annotations

import hashlib
import io
import os
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping, Optional, Sequence, Tuple
from xml.etree import ElementTree

from cbra.native.models import Stream


DEFAULT_MAX_ATTACHMENTS = 8
DEFAULT_MAX_FILE_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_TOTAL_UPLOAD_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_EXTRACTED_CHARACTERS = 2 * 1024 * 1024
DEFAULT_MAX_TOTAL_EXTRACTED_CHARACTERS = 5 * 1024 * 1024
DEFAULT_MAX_PDF_PAGES = 100
DEFAULT_MAX_DOCX_EXPANDED_BYTES = 50 * 1024 * 1024
DEFAULT_MAX_DOCX_MEMBERS = 2048

ATTACHMENT_PARTICIPATION = 0.74
ATTACHMENT_PERSISTENCE = 0.90
ATTACHMENT_ID_PATTERN = re.compile(
    r"^attachment:[0-9a-f]{32}$"
)
_POSITIVE_INTEGER = re.compile(r"^[1-9][0-9]*$")
_DOCX_TEXT_PART = re.compile(
    r"^word/(?:document|footnotes|endnotes|comments|"
    r"header[0-9]+|footer[0-9]+)\.xml$"
)
_WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

_MEDIA_TYPES = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".docx": (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    ),
    ".pdf": "application/pdf",
}
_DECLARED_MEDIA_TYPES = {
    ".txt": {"", "application/octet-stream", "text/plain"},
    ".md": {
        "",
        "application/octet-stream",
        "text/markdown",
        "text/plain",
    },
    ".docx": {
        "",
        "application/octet-stream",
        "application/zip",
        _MEDIA_TYPES[".docx"],
    },
    ".pdf": {"", "application/octet-stream", "application/pdf"},
}


class AttachmentIngressError(ValueError):
    """A submitted attachment cannot safely enter the native field."""


class AttachmentTooLargeError(AttachmentIngressError):
    """An attachment request exceeds a configured finite resource bound."""


class UnsupportedAttachmentError(AttachmentIngressError):
    """An attachment uses a format this ingress boundary does not accept."""


class InvalidAttachmentError(AttachmentIngressError):
    """An attachment is malformed, empty, disguised, or ambiguously owned."""


@dataclass(frozen=True)
class AttachmentLimits:
    """Finite process policy for raw uploads and extracted document text."""

    max_attachments: int = DEFAULT_MAX_ATTACHMENTS
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES
    max_total_upload_bytes: int = DEFAULT_MAX_TOTAL_UPLOAD_BYTES
    max_extracted_characters: int = (
        DEFAULT_MAX_EXTRACTED_CHARACTERS
    )
    max_total_extracted_characters: int = (
        DEFAULT_MAX_TOTAL_EXTRACTED_CHARACTERS
    )
    max_pdf_pages: int = DEFAULT_MAX_PDF_PAGES
    max_docx_expanded_bytes: int = (
        DEFAULT_MAX_DOCX_EXPANDED_BYTES
    )
    max_docx_members: int = DEFAULT_MAX_DOCX_MEMBERS

    def __post_init__(self) -> None:
        for name in (
            "max_attachments",
            "max_file_bytes",
            "max_total_upload_bytes",
            "max_extracted_characters",
            "max_total_extracted_characters",
            "max_pdf_pages",
            "max_docx_expanded_bytes",
            "max_docx_members",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise InvalidAttachmentError(
                    "{0} must be a positive integer".format(name)
                )

    @classmethod
    def from_environment(
        cls,
        environ: Optional[Mapping[str, str]] = None,
    ) -> "AttachmentLimits":
        """Load strict positive limits from the process environment."""
        values = environ if environ is not None else os.environ
        return cls(
            max_attachments=_environment_limit(
                values,
                "CBRA_ATTACHMENT_MAX_COUNT",
                DEFAULT_MAX_ATTACHMENTS,
            ),
            max_file_bytes=_environment_limit(
                values,
                "CBRA_ATTACHMENT_MAX_FILE_BYTES",
                DEFAULT_MAX_FILE_BYTES,
            ),
            max_total_upload_bytes=_environment_limit(
                values,
                "CBRA_ATTACHMENT_MAX_TOTAL_UPLOAD_BYTES",
                DEFAULT_MAX_TOTAL_UPLOAD_BYTES,
            ),
            max_extracted_characters=_environment_limit(
                values,
                "CBRA_ATTACHMENT_MAX_EXTRACTED_CHARACTERS",
                DEFAULT_MAX_EXTRACTED_CHARACTERS,
            ),
            max_total_extracted_characters=_environment_limit(
                values,
                "CBRA_ATTACHMENT_MAX_TOTAL_EXTRACTED_CHARACTERS",
                DEFAULT_MAX_TOTAL_EXTRACTED_CHARACTERS,
            ),
            max_pdf_pages=_environment_limit(
                values,
                "CBRA_ATTACHMENT_MAX_PDF_PAGES",
                DEFAULT_MAX_PDF_PAGES,
            ),
            max_docx_expanded_bytes=_environment_limit(
                values,
                "CBRA_ATTACHMENT_MAX_DOCX_EXPANDED_BYTES",
                DEFAULT_MAX_DOCX_EXPANDED_BYTES,
            ),
            max_docx_members=_environment_limit(
                values,
                "CBRA_ATTACHMENT_MAX_DOCX_MEMBERS",
                DEFAULT_MAX_DOCX_MEMBERS,
            ),
        )


@dataclass(frozen=True)
class UploadedAttachment:
    """One bounded upload paired with its client-claimed identity."""

    attachment_id: str
    filename: str
    declared_media_type: str
    content: bytes


def _environment_limit(
    environ: Mapping[str, str],
    name: str,
    default: int,
) -> int:
    raw = environ.get(name)
    if raw is None:
        return default
    if not isinstance(raw, str) or not _POSITIVE_INTEGER.fullmatch(raw):
        raise InvalidAttachmentError(
            "{0} must be a positive decimal integer".format(name)
        )
    return int(raw)


def _validate_attachment_id(value: str) -> str:
    if (
        not isinstance(value, str)
        or ATTACHMENT_ID_PATTERN.fullmatch(value) is None
    ):
        raise InvalidAttachmentError(
            "attachment IDs must use attachment: plus 32 lowercase "
            "hexadecimal characters"
        )
    return value


def _validate_filename(value: Any) -> Tuple[str, str]:
    if not isinstance(value, str):
        raise InvalidAttachmentError(
            "each attachment requires a filename"
        )
    filename = unicodedata.normalize("NFC", value)
    if (
        not filename
        or filename != filename.strip()
        or "\x00" in filename
        or "/" in filename
        or "\\" in filename
        or any(
            unicodedata.category(character).startswith("C")
            for character in filename
        )
        or len(filename.encode("utf-8")) > 255
    ):
        raise InvalidAttachmentError(
            "attachment filename is invalid"
        )
    suffix = PurePosixPath(filename).suffix.lower()
    if suffix not in _MEDIA_TYPES:
        raise UnsupportedAttachmentError(
            "attachment format is unsupported"
        )
    return filename, suffix


def _validate_declared_media_type(
    declared: Any,
    suffix: str,
) -> str:
    if declared is None:
        normalized = ""
    elif isinstance(declared, str):
        normalized = declared.split(";", 1)[0].strip().lower()
    else:
        raise InvalidAttachmentError(
            "attachment media type is invalid"
        )
    if normalized not in _DECLARED_MEDIA_TYPES[suffix]:
        raise UnsupportedAttachmentError(
            "attachment media type does not match its format"
        )
    return normalized


def _require_text(
    text: str,
    *,
    limits: AttachmentLimits,
) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.strip():
        raise InvalidAttachmentError(
            "attachment contains no extractable text"
        )
    if len(normalized) > limits.max_extracted_characters:
        raise AttachmentTooLargeError(
            "attachment extracted text exceeds its character limit"
        )
    return normalized


def _extract_utf8_text(
    content: bytes,
    *,
    suffix: str,
    limits: AttachmentLimits,
) -> Tuple[str, str]:
    if (
        b"\x00" in content
        or content.startswith(b"%PDF-")
        or content.startswith((b"PK\x03\x04", b"PK\x05\x06"))
    ):
        raise InvalidAttachmentError(
            "text attachment is disguised or malformed"
        )
    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise InvalidAttachmentError(
            "text attachment is not valid UTF-8"
        ) from exc
    extractor = (
        "utf8-markdown-v1" if suffix == ".md" else "utf8-text-v1"
    )
    return _require_text(text, limits=limits), extractor


def _safe_docx_member(name: str) -> None:
    path = PurePosixPath(name)
    if (
        not name
        or "\x00" in name
        or "\\" in name
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise InvalidAttachmentError(
            "DOCX archive contains an unsafe member"
        )


def _append_word_text(element, output, remaining) -> None:
    local = element.tag.rsplit("}", 1)[-1]
    piece = ""
    if local == "t" and element.text:
        piece = element.text
    elif local == "tab":
        piece = "\t"
    elif local in {"br", "cr"}:
        piece = "\n"
    if piece:
        remaining[0] -= len(piece)
        if remaining[0] < 0:
            raise AttachmentTooLargeError(
                "DOCX extracted text exceeds its character limit"
            )
        output.append(piece)
    for child in element:
        _append_word_text(child, output, remaining)
    if local in {"p", "tr"}:
        remaining[0] -= 1
        if remaining[0] < 0:
            raise AttachmentTooLargeError(
                "DOCX extracted text exceeds its character limit"
            )
        output.append("\n")


def _extract_docx_text(
    content: bytes,
    *,
    limits: AttachmentLimits,
) -> Tuple[str, str]:
    if not content.startswith(
        (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
    ):
        raise InvalidAttachmentError(
            "DOCX attachment is disguised or malformed"
        )
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = archive.infolist()
            if len(members) > limits.max_docx_members:
                raise AttachmentTooLargeError(
                    "DOCX archive exceeds its member-count limit"
                )
            names = []
            expanded_bytes = 0
            for member in members:
                _safe_docx_member(member.filename)
                if member.flag_bits & 0x1:
                    raise InvalidAttachmentError(
                        "encrypted DOCX attachments are unsupported"
                    )
                expanded_bytes += member.file_size
                if expanded_bytes > limits.max_docx_expanded_bytes:
                    raise AttachmentTooLargeError(
                        "DOCX archive exceeds its expansion limit"
                    )
                names.append(member.filename)
            if len(names) != len(set(item.casefold() for item in names)):
                raise InvalidAttachmentError(
                    "DOCX archive contains duplicate members"
                )
            required = {"[Content_Types].xml", "word/document.xml"}
            if not required.issubset(set(names)):
                raise InvalidAttachmentError(
                    "DOCX attachment is missing required package parts"
                )

            targets = [
                name
                for name in names
                if _DOCX_TEXT_PART.fullmatch(name)
            ]
            targets.sort(
                key=lambda name: (
                    0 if name == "word/document.xml" else 1,
                    name,
                )
            )
            output = []
            remaining = [limits.max_extracted_characters]
            for name in targets:
                data = archive.read(name)
                if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
                    raise InvalidAttachmentError(
                        "DOCX XML declarations are unsupported"
                    )
                try:
                    root = ElementTree.fromstring(data)
                except ElementTree.ParseError as exc:
                    raise InvalidAttachmentError(
                        "DOCX attachment contains malformed XML"
                    ) from exc
                if not root.tag.startswith(
                    "{{{0}}}".format(_WORD_NAMESPACE)
                ):
                    raise InvalidAttachmentError(
                        "DOCX attachment has an invalid Word namespace"
                    )
                _append_word_text(root, output, remaining)
    except AttachmentIngressError:
        raise
    except Exception as exc:
        raise InvalidAttachmentError(
            "DOCX attachment is malformed"
        ) from exc
    return (
        _require_text("".join(output), limits=limits),
        "docx-ooxml-text-v1",
    )


def _extract_pdf_text(
    content: bytes,
    *,
    limits: AttachmentLimits,
) -> Tuple[str, str]:
    if not content.startswith(b"%PDF-"):
        raise InvalidAttachmentError(
            "PDF attachment is disguised or malformed"
        )
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content), strict=True)
        if reader.is_encrypted:
            raise InvalidAttachmentError(
                "encrypted PDF attachments are unsupported"
            )
        if len(reader.pages) > limits.max_pdf_pages:
            raise AttachmentTooLargeError(
                "PDF attachment exceeds its page limit"
            )
        pages = []
        character_count = 0
        for page in reader.pages:
            page_text = page.extract_text() or ""
            pages.append(page_text)
            character_count += len(page_text)
            if character_count + max(0, len(pages) - 1) * 2 > (
                limits.max_extracted_characters
            ):
                raise AttachmentTooLargeError(
                    "PDF extracted text exceeds its character limit"
                )
    except AttachmentIngressError:
        raise
    except Exception as exc:
        raise InvalidAttachmentError(
            "PDF attachment is malformed"
        ) from exc
    return (
        _require_text("\n\n".join(pages), limits=limits),
        "pypdf-text-v1",
    )


def _extract_text(
    content: bytes,
    *,
    suffix: str,
    limits: AttachmentLimits,
) -> Tuple[str, str]:
    if not content:
        raise InvalidAttachmentError("attachment file is empty")
    if suffix in {".txt", ".md"}:
        return _extract_utf8_text(
            content,
            suffix=suffix,
            limits=limits,
        )
    if suffix == ".docx":
        return _extract_docx_text(content, limits=limits)
    if suffix == ".pdf":
        return _extract_pdf_text(content, limits=limits)
    raise UnsupportedAttachmentError(
        "attachment format is unsupported"
    )


def _attachment_stream_id(
    thread_id: str,
    turn_id: str,
    attachment_id: str,
) -> str:
    identity = "\x00".join(
        (thread_id, turn_id, attachment_id)
    ).encode("utf-8")
    return "stream:attachment:{0}".format(
        hashlib.sha256(identity).hexdigest()
    )


def build_attachment_streams(
    *,
    thread_id: str,
    turn_id: str,
    attachments: Sequence[UploadedAttachment],
    limits: Optional[AttachmentLimits] = None,
) -> Tuple[Stream, ...]:
    """Extract a complete request into stable, full-thickness streams."""
    resolved_limits = limits or AttachmentLimits()
    if not attachments:
        raise InvalidAttachmentError(
            "at least one attachment is required"
        )
    if len(attachments) > resolved_limits.max_attachments:
        raise AttachmentTooLargeError(
            "attachment count exceeds its configured limit"
        )

    claimed_ids = [
        _validate_attachment_id(item.attachment_id)
        for item in attachments
    ]
    if len(claimed_ids) != len(set(claimed_ids)):
        raise InvalidAttachmentError(
            "attachment IDs must be unique within a turn"
        )

    total_uploaded = 0
    total_extracted = 0
    streams = []
    for item in attachments:
        content = item.content
        if not isinstance(content, bytes):
            raise InvalidAttachmentError(
                "attachment content must be binary"
            )
        if len(content) > resolved_limits.max_file_bytes:
            raise AttachmentTooLargeError(
                "attachment exceeds its per-file byte limit"
            )
        total_uploaded += len(content)
        if total_uploaded > resolved_limits.max_total_upload_bytes:
            raise AttachmentTooLargeError(
                "attachments exceed the total upload byte limit"
            )

        filename, suffix = _validate_filename(item.filename)
        _validate_declared_media_type(
            item.declared_media_type,
            suffix,
        )
        text, extractor = _extract_text(
            content,
            suffix=suffix,
            limits=resolved_limits,
        )
        total_extracted += len(text)
        if total_extracted > (
            resolved_limits.max_total_extracted_characters
        ):
            raise AttachmentTooLargeError(
                "attachments exceed the total extracted-text limit"
            )

        raw_digest = hashlib.sha256(content).hexdigest()
        text_digest = hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()
        media_type = _MEDIA_TYPES[suffix]
        metadata = {
            "attachment_id": item.attachment_id,
            "filename": filename,
            "media_type": media_type,
            "raw_content_sha256": raw_digest,
            "extracted_text_sha256": text_digest,
            "raw_byte_count": len(content),
            "extracted_character_count": len(text),
            "extractor": extractor,
            "thread_id": thread_id,
            "turn_id": turn_id,
        }
        streams.append(
            Stream(
                stream_id=_attachment_stream_id(
                    thread_id,
                    turn_id,
                    item.attachment_id,
                ),
                kind="attachment",
                participation=ATTACHMENT_PARTICIPATION,
                persistence=ATTACHMENT_PERSISTENCE,
                payload={
                    "text": text,
                    "material_handle": "{0}:{1}".format(
                        item.attachment_id,
                        filename,
                    ),
                    **metadata,
                },
                provenance={
                    "source": "user_attachment",
                    "immutable_turn_material": True,
                    **metadata,
                },
            )
        )

    return tuple(
        sorted(
            streams,
            key=lambda stream: stream.payload["attachment_id"],
        )
    )


async def read_uploaded_attachments(
    *,
    attachment_ids: Sequence[str],
    uploads: Sequence[Any],
    limits: Optional[AttachmentLimits] = None,
) -> Tuple[UploadedAttachment, ...]:
    """Read each multipart upload at most one bounded byte beyond policy."""
    resolved_limits = limits or AttachmentLimits()
    if not attachment_ids or not uploads:
        raise InvalidAttachmentError(
            "at least one attachment and attachment ID are required"
        )
    if len(attachment_ids) != len(uploads):
        raise InvalidAttachmentError(
            "each attachment ID must correspond to exactly one file"
        )
    if len(uploads) > resolved_limits.max_attachments:
        raise AttachmentTooLargeError(
            "attachment count exceeds its configured limit"
        )

    results = []
    total = 0
    try:
        for attachment_id, upload in zip(attachment_ids, uploads):
            _validate_attachment_id(attachment_id)
            advertised_size = getattr(upload, "size", None)
            if (
                type(advertised_size) is int
                and advertised_size > resolved_limits.max_file_bytes
            ):
                raise AttachmentTooLargeError(
                    "attachment exceeds its per-file byte limit"
                )
            if (
                type(advertised_size) is int
                and total + advertised_size
                > resolved_limits.max_total_upload_bytes
            ):
                raise AttachmentTooLargeError(
                    "attachments exceed the total upload byte limit"
                )
            content = await upload.read(
                resolved_limits.max_file_bytes + 1
            )
            if len(content) > resolved_limits.max_file_bytes:
                raise AttachmentTooLargeError(
                    "attachment exceeds its per-file byte limit"
                )
            total += len(content)
            if total > resolved_limits.max_total_upload_bytes:
                raise AttachmentTooLargeError(
                    "attachments exceed the total upload byte limit"
                )
            results.append(
                UploadedAttachment(
                    attachment_id=attachment_id,
                    filename=getattr(upload, "filename", None),
                    declared_media_type=getattr(
                        upload,
                        "content_type",
                        "",
                    ),
                    content=content,
                )
            )
    finally:
        for upload in uploads:
            close = getattr(upload, "close", None)
            if close is not None:
                await close()
    return tuple(results)
