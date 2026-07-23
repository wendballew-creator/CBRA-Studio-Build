"""Lossless checkpoint and trace persistence for the native CBRA field."""

from __future__ import annotations

import gzip
import hashlib
import hmac
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

from pydantic import ValidationError

from .models import (
    ArticulationBasis,
    ArticulationCandidate,
    CyclePhase,
    FieldSnapshot,
    FieldState,
    HistoryEntry,
)
from .runtime import assert_native_invariants
from .schemas import (
    CHECKPOINT_PAYLOAD_TYPE,
    SCHEMA_VERSION,
    TRACE_PAYLOAD_TYPE,
    CheckpointEnvelopeSchema,
    FieldStateSchema,
    HistoryEntrySchema,
    IntegritySchema,
    TraceEnvelopeSchema,
    TracePayloadSchema,
    assert_json_compatible,
    model_dump,
    model_validate,
)


PathLike = Union[str, os.PathLike]
Serialized = Union[str, bytes, bytearray]
GZIP_MAGIC = b"\x1f\x8b"
SHA256_ALGORITHM = "sha256"


class NativePersistenceError(ValueError):
    """Base error for native checkpoint and trace persistence."""


class NativeFormatError(NativePersistenceError):
    """Serialized bytes are not a supported canonical JSON record."""


class NativeValidationError(NativePersistenceError):
    """A record is typed JSON but cannot form a valid native object."""


class UnsupportedSchemaVersionError(NativePersistenceError):
    """A record uses a schema version this runtime cannot restore."""


class PayloadTypeError(NativePersistenceError):
    """A checkpoint or trace was supplied to the wrong restoration path."""


class IntegrityError(NativePersistenceError):
    """A record's content no longer matches its integrity metadata."""


@dataclass(frozen=True)
class NativeTraceArchive:
    """Restored append-only lifecycle history for one native field."""

    field_id: str
    entries: Tuple[HistoryEntry, ...]


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        assert_json_compatible(value, "serialized record")
        text = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise NativeValidationError(str(exc)) from exc
    return text.encode("utf-8")


def _integrity_input(
    schema_version: int,
    payload_type: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "schema_version": schema_version,
        "payload_type": payload_type,
        "payload": payload,
    }


def _payload_digest(
    schema_version: int,
    payload_type: str,
    payload: Dict[str, Any],
) -> str:
    material = _canonical_json_bytes(
        _integrity_input(schema_version, payload_type, payload)
    )
    return hashlib.sha256(material).hexdigest()


def _make_envelope(
    payload_type: str,
    payload_schema,
    envelope_type,
) -> bytes:
    payload = model_dump(payload_schema)
    digest = _payload_digest(
        SCHEMA_VERSION,
        payload_type,
        payload,
    )
    envelope = envelope_type(
        schema_version=SCHEMA_VERSION,
        payload_type=payload_type,
        integrity=IntegritySchema(
            algorithm=SHA256_ALGORITHM,
            payload_sha256=digest,
        ),
        payload=payload_schema,
    )
    return _canonical_json_bytes(model_dump(envelope))


def serialize_checkpoint(state: FieldState) -> bytes:
    """Return canonical UTF-8 JSON containing a complete native field."""
    try:
        schema = FieldStateSchema.from_native(state)
        _validate_restored_field(schema.to_native())
    except (ValidationError, AssertionError, ValueError) as exc:
        if isinstance(exc, NativePersistenceError):
            raise
        raise NativeValidationError(
            "Native field cannot be checkpointed: {0}".format(exc)
        ) from exc
    return _make_envelope(
        CHECKPOINT_PAYLOAD_TYPE,
        schema,
        CheckpointEnvelopeSchema,
    )


def serialize_trace(state: FieldState) -> bytes:
    """Return canonical UTF-8 JSON for one field's lifecycle history."""
    try:
        entries = [
            HistoryEntrySchema.from_native(item)
            for item in state.history
        ]
        archive = NativeTraceArchive(
            field_id=state.field_id,
            entries=tuple(item.to_native() for item in entries),
        )
        _validate_trace_archive(archive)
        payload = TracePayloadSchema(
            field_id=state.field_id,
            entries=entries,
        )
    except (ValidationError, AssertionError, ValueError) as exc:
        if isinstance(exc, NativePersistenceError):
            raise
        raise NativeValidationError(
            "Native trace cannot be serialized: {0}".format(exc)
        ) from exc
    return _make_envelope(
        TRACE_PAYLOAD_TYPE,
        payload,
        TraceEnvelopeSchema,
    )


def _decode_record(data: Serialized) -> Dict[str, Any]:
    if isinstance(data, str):
        text = data
    elif isinstance(data, (bytes, bytearray)):
        try:
            text = bytes(data).decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise NativeFormatError(
                "Serialized record is not valid UTF-8"
            ) from exc
    else:
        raise TypeError("serialized data must be str, bytes, or bytearray")

    try:
        value = json.loads(
            text,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError("non-finite JSON number: {0}".format(token))
            ),
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise NativeFormatError(
            "Serialized record is not valid canonical JSON"
        ) from exc
    if not isinstance(value, dict):
        raise NativeFormatError("Serialized record must be a JSON object")
    return value


def _validate_envelope_header(
    value: Dict[str, Any],
    expected_payload_type: str,
) -> None:
    version = value.get("schema_version")
    if type(version) is not int:
        raise NativeValidationError(
            "schema_version must be an integer"
        )
    if version != SCHEMA_VERSION:
        raise UnsupportedSchemaVersionError(
            "Unsupported native schema version {0}; supported version is {1}".format(
                version,
                SCHEMA_VERSION,
            )
        )
    payload_type = value.get("payload_type")
    if not isinstance(payload_type, str):
        raise NativeValidationError("payload_type must be a string")
    if payload_type != expected_payload_type:
        raise PayloadTypeError(
            "Expected payload type {0}, received {1}".format(
                expected_payload_type,
                payload_type,
            )
        )


def _verify_integrity(value: Dict[str, Any]) -> None:
    integrity = value.get("integrity")
    payload = value.get("payload")
    if not isinstance(integrity, dict):
        raise NativeValidationError("integrity metadata is required")
    if not isinstance(payload, dict):
        raise NativeValidationError("payload must be a JSON object")
    if integrity.get("algorithm") != SHA256_ALGORITHM:
        raise NativeValidationError(
            "Only sha256 integrity metadata is supported"
        )
    recorded = integrity.get("payload_sha256")
    if not isinstance(recorded, str) or len(recorded) != 64:
        raise NativeValidationError(
            "payload_sha256 must be a 64-character hexadecimal digest"
        )
    try:
        int(recorded, 16)
    except ValueError as exc:
        raise NativeValidationError(
            "payload_sha256 must be hexadecimal"
        ) from exc
    actual = _payload_digest(
        value["schema_version"],
        value["payload_type"],
        payload,
    )
    if not hmac.compare_digest(recorded.lower(), actual):
        raise IntegrityError(
            "Native record checksum does not match its payload"
        )


def _parse_envelope(
    data: Serialized,
    expected_payload_type: str,
    envelope_type,
):
    value = _decode_record(data)
    _validate_envelope_header(value, expected_payload_type)
    _verify_integrity(value)
    try:
        return model_validate(envelope_type, value)
    except ValidationError as exc:
        raise NativeValidationError(
            "Native record does not match its versioned schema: {0}".format(
                exc
            )
        ) from exc


def restore_checkpoint(data: Serialized) -> FieldState:
    """Strictly reconstruct a live native field from canonical JSON."""
    envelope = _parse_envelope(
        data,
        CHECKPOINT_PAYLOAD_TYPE,
        CheckpointEnvelopeSchema,
    )
    try:
        state = envelope.payload.to_native()
        _validate_restored_field(state)
    except (AssertionError, ValueError) as exc:
        if isinstance(exc, NativePersistenceError):
            raise
        raise NativeValidationError(
            "Restored native field violates runtime invariants: {0}".format(
                exc
            )
        ) from exc
    return state


def restore_trace(data: Serialized) -> NativeTraceArchive:
    """Strictly reconstruct one field's immutable lifecycle trace."""
    envelope = _parse_envelope(
        data,
        TRACE_PAYLOAD_TYPE,
        TraceEnvelopeSchema,
    )
    archive = NativeTraceArchive(
        field_id=envelope.payload.field_id,
        entries=tuple(
            item.to_native() for item in envelope.payload.entries
        ),
    )
    try:
        _validate_trace_archive(archive)
    except (AssertionError, ValueError) as exc:
        if isinstance(exc, NativePersistenceError):
            raise
        raise NativeValidationError(
            "Restored native trace violates lifecycle invariants: {0}".format(
                exc
            )
        ) from exc
    return archive


def _ids(items: Iterable[Any], attribute: str, label: str) -> Set[str]:
    values = [getattr(item, attribute) for item in items]
    if len(values) != len(set(values)):
        duplicates = sorted(
            {
                value
                for value in values
                if values.count(value) > 1
            }
        )
        raise AssertionError(
            "{0} IDs must be unique; duplicated: {1}".format(
                label,
                ", ".join(duplicates),
            )
        )
    return set(values)


def _require_subset(
    values: Sequence[str],
    available: Set[str],
    label: str,
) -> None:
    missing = sorted(set(values) - available)
    if missing:
        raise AssertionError(
            "{0} references absent IDs: {1}".format(
                label,
                ", ".join(missing),
            )
        )


def _relation_universe(
    state: Optional[FieldState] = None,
    entries: Sequence[HistoryEntry] = (),
) -> Set[str]:
    values: Set[str] = set()
    if state is not None:
        values.update(item.relation_id for item in state.relations)
    for entry in entries:
        for phase in entry.phases:
            values.update(
                item.relation_id for item in phase.field.relations
            )
        for delta in entry.step_trace.deltas:
            values.update(delta.relation_updates)
    return values


def _validate_basis(
    basis: ArticulationBasis,
    cut_ids: Set[str],
    phenomenon_ids: Set[str],
    stream_ids: Set[str],
    relation_ids: Set[str],
    articulation_ids: Set[str],
    apparatus_id: str,
    label: str,
) -> None:
    if basis.cut_id not in cut_ids:
        raise AssertionError("{0} references an absent cut".format(label))
    if basis.apparatus_id != apparatus_id:
        raise AssertionError(
            "{0} references a different apparatus".format(label)
        )
    _require_subset(
        basis.included_stream_ids,
        stream_ids,
        "{0} included streams".format(label),
    )
    _require_subset(
        basis.held_open_stream_ids,
        stream_ids,
        "{0} held-open streams".format(label),
    )
    _require_subset(
        basis.relation_ids,
        relation_ids,
        "{0} relations".format(label),
    )
    for index, material in enumerate(basis.held_open_materials):
        _require_subset(
            [material.stream_id] + list(material.source_stream_ids),
            stream_ids,
            "{0} held-open material {1}".format(label, index),
        )
    for index, formation in enumerate(basis.formations):
        if formation.phenomenon_id not in phenomenon_ids:
            raise AssertionError(
                "{0} formation {1} references an absent phenomenon".format(
                    label,
                    index,
                )
            )
        _require_subset(
            formation.relation_ids,
            relation_ids,
            "{0} formation {1} relations".format(label, index),
        )
        _require_subset(
            formation.apparatus_stream_ids,
            stream_ids,
            "{0} formation {1} apparatus streams".format(label, index),
        )
        _require_subset(
            formation.play_variation_ids,
            stream_ids,
            "{0} formation {1} play variations".format(label, index),
        )
        _require_subset(
            formation.prior_articulation_ids,
            articulation_ids,
            "{0} formation {1} prior articulations".format(label, index),
        )
        for material_index, material in enumerate(formation.materials):
            _require_subset(
                [material.stream_id] + list(material.source_stream_ids),
                stream_ids,
                "{0} formation {1} material {2}".format(
                    label,
                    index,
                    material_index,
                ),
            )


def _validate_collections(
    field,
    relation_universe: Set[str],
    label: str,
) -> None:
    stream_ids = _ids(field.streams, "stream_id", "{0} stream".format(label))
    current_relation_ids = _ids(
        field.relations,
        "relation_id",
        "{0} relation".format(label),
    )
    pattern_ids = _ids(
        field.patterns,
        "pattern_id",
        "{0} pattern".format(label),
    )
    phenomenon_ids = _ids(
        field.phenomena,
        "phenomenon_id",
        "{0} phenomenon".format(label),
    )
    cut_ids = _ids(field.cuts, "cut_id", "{0} cut".format(label))
    candidate_ids = _ids(
        field.articulation_candidates,
        "candidate_id",
        "{0} articulation candidate".format(label),
    )
    evaluation_ids = _ids(
        field.articulation_evaluations,
        "evaluation_id",
        "{0} articulation evaluation".format(label),
    )
    articulation_ids = _ids(
        field.articulations,
        "articulation_id",
        "{0} articulation".format(label),
    )

    for relation in field.relations:
        _require_subset(
            [relation.left_id, relation.right_id],
            stream_ids,
            "{0} relation endpoints".format(label),
        )
    for pattern in field.patterns:
        _require_subset(
            pattern.stream_ids,
            stream_ids,
            "{0} pattern streams".format(label),
        )
        _require_subset(
            pattern.relation_ids,
            relation_universe,
            "{0} pattern relations".format(label),
        )
    for phenomenon in field.phenomena:
        _require_subset(
            phenomenon.stream_ids,
            stream_ids,
            "{0} phenomenon streams".format(label),
        )
        _require_subset(
            phenomenon.relation_ids,
            relation_universe,
            "{0} phenomenon relations".format(label),
        )
    for cut in field.cuts:
        _require_subset(
            cut.phenomenon_ids,
            phenomenon_ids,
            "{0} cut phenomena".format(label),
        )
        _require_subset(
            list(cut.included_stream_ids)
            + list(cut.held_open_stream_ids),
            stream_ids,
            "{0} cut streams".format(label),
        )
        _require_subset(
            cut.relation_ids,
            relation_universe,
            "{0} cut relations".format(label),
        )
        if cut.apparatus_id != field.apparatus.apparatus_id:
            raise AssertionError(
                "{0} cut references a different apparatus".format(label)
            )
        if cut.excluded_stream_ids:
            raise AssertionError(
                "{0} cut discards material".format(label)
            )
    for candidate in field.articulation_candidates:
        _validate_basis(
            candidate.basis,
            cut_ids,
            phenomenon_ids,
            stream_ids,
            relation_universe,
            articulation_ids,
            field.apparatus.apparatus_id,
            "{0} candidate {1}".format(label, candidate.candidate_id),
        )
    evaluations = {
        item.evaluation_id: item
        for item in field.articulation_evaluations
    }
    for evaluation in field.articulation_evaluations:
        if evaluation.candidate_id not in candidate_ids:
            raise AssertionError(
                "{0} evaluation references an absent candidate".format(
                    label
                )
            )
    for articulation in field.articulations:
        if articulation.candidate_id not in candidate_ids:
            raise AssertionError(
                "{0} articulation references an absent candidate".format(
                    label
                )
            )
        evaluation = evaluations.get(articulation.evaluation_id)
        if evaluation is None or not evaluation.accepted:
            raise AssertionError(
                "{0} articulation requires an accepted evaluation".format(
                    label
                )
            )
        if articulation.cut_id not in cut_ids:
            raise AssertionError(
                "{0} articulation references an absent cut".format(label)
            )
        _require_subset(
            articulation.phenomenon_ids,
            phenomenon_ids,
            "{0} articulation phenomena".format(label),
        )
        _require_subset(
            list(articulation.included_stream_ids)
            + list(articulation.held_open_stream_ids)
            + list(articulation.lineage_stream_ids),
            stream_ids,
            "{0} articulation streams".format(label),
        )
        _require_subset(
            articulation.relation_ids,
            relation_universe,
            "{0} articulation relations".format(label),
        )

    _require_subset(
        field.current_pattern_ids,
        pattern_ids,
        "{0} current patterns".format(label),
    )
    _require_subset(
        field.current_phenomenon_ids,
        phenomenon_ids,
        "{0} current phenomena".format(label),
    )
    optional_current = (
        ("cut", field.current_cut_id, cut_ids),
        ("candidate", field.current_candidate_id, candidate_ids),
        ("evaluation", field.current_evaluation_id, evaluation_ids),
        (
            "articulation",
            field.current_articulation_id,
            articulation_ids,
        ),
    )
    for kind, value, available in optional_current:
        if value is not None and value not in available:
            raise AssertionError(
                "{0} current {1} is absent".format(label, kind)
            )
    if not current_relation_ids.issubset(relation_universe):
        raise AssertionError(
            "{0} relations are absent from the trace universe".format(label)
        )


def _validate_history_entry(
    entry: HistoryEntry,
    field_id: str,
    relation_universe: Set[str],
) -> None:
    expected_phases = list(CyclePhase)
    actual_phases = [item.phase for item in entry.phases]
    if actual_phases != expected_phases:
        raise AssertionError(
            "cycle {0} must contain all lifecycle phases in canonical order".format(
                entry.cycle
            )
        )
    for phase in entry.phases:
        if phase.field.field_id != field_id:
            raise AssertionError(
                "cycle {0} contains a snapshot for another field".format(
                    entry.cycle
                )
            )
        _validate_collections(
            phase.field,
            relation_universe,
            "cycle {0} phase {1}".format(
                entry.cycle,
                phase.phase.value,
            ),
        )

    before = entry.before
    after_update = entry.after_update_and_emergence
    if entry.step_trace.timestep_before != before.timestep:
        raise AssertionError(
            "cycle {0} trace does not begin at its before snapshot".format(
                entry.cycle
            )
        )
    if entry.step_trace.timestep_after != after_update.timestep:
        raise AssertionError(
            "cycle {0} trace does not end at its update snapshot".format(
                entry.cycle
            )
        )
    after = entry.after
    references = (
        ("cut", entry.cut_id, {item.cut_id for item in after.cuts}),
        (
            "candidate",
            entry.candidate_id,
            {
                item.candidate_id
                for item in after.articulation_candidates
            },
        ),
        (
            "evaluation",
            entry.evaluation_id,
            {
                item.evaluation_id
                for item in after.articulation_evaluations
            },
        ),
        (
            "articulation",
            entry.articulation_id,
            {
                item.articulation_id
                for item in after.articulations
            },
        ),
    )
    for kind, value, available in references:
        if value is not None and value not in available:
            raise AssertionError(
                "cycle {0} records an absent {1}".format(
                    entry.cycle,
                    kind,
                )
            )


def _validate_trace_entries(
    field_id: str,
    entries: Sequence[HistoryEntry],
    relation_universe: Set[str],
) -> None:
    expected_cycles = list(range(1, len(entries) + 1))
    actual_cycles = [item.cycle for item in entries]
    if actual_cycles != expected_cycles:
        raise AssertionError(
            "history cycles must be append-only and contiguous from 1"
        )
    for entry in entries:
        _validate_history_entry(entry, field_id, relation_universe)


def _validate_restored_field(state: FieldState) -> None:
    assert_native_invariants(state)
    relation_universe = _relation_universe(
        state=state,
        entries=state.history,
    )
    _validate_collections(state, relation_universe, "current field")
    _validate_trace_entries(
        state.field_id,
        state.history,
        relation_universe,
    )
    if state.history and state.timestep < state.history[-1].after.timestep:
        raise AssertionError(
            "current field timestep precedes its latest history snapshot"
        )


def _validate_trace_archive(archive: NativeTraceArchive) -> None:
    relation_universe = _relation_universe(entries=archive.entries)
    _validate_trace_entries(
        archive.field_id,
        archive.entries,
        relation_universe,
    )


def _encode_file_payload(data: bytes, compress: bool) -> bytes:
    return gzip.compress(data, compresslevel=9, mtime=0) if compress else data


def _decode_file_payload(data: bytes) -> bytes:
    if data.startswith(GZIP_MAGIC):
        try:
            return gzip.decompress(data)
        except (OSError, EOFError) as exc:
            raise NativeFormatError(
                "Compressed native record is corrupt"
            ) from exc
    return data


def _atomic_write(path: Path, data: bytes) -> None:
    parent = path.parent
    if not parent.exists():
        raise FileNotFoundError(
            "Checkpoint directory does not exist: {0}".format(parent)
        )
    if not parent.is_dir():
        raise NotADirectoryError(str(parent))

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".{0}.".format(path.name),
        suffix=".tmp",
        dir=str(parent),
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, str(path))
        try:
            directory_descriptor = os.open(str(parent), os.O_RDONLY)
        except OSError:
            directory_descriptor = None
        if directory_descriptor is not None:
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _use_gzip(path: Path, compress: Optional[bool]) -> bool:
    if compress is not None:
        return compress
    return path.suffix.lower() in {".gz", ".gzip"}


def save_checkpoint(
    path: PathLike,
    state: FieldState,
    compress: Optional[bool] = None,
) -> None:
    """Atomically save a complete checkpoint to an explicit path."""
    destination = Path(path)
    data = serialize_checkpoint(state)
    _atomic_write(
        destination,
        _encode_file_payload(data, _use_gzip(destination, compress)),
    )


def load_checkpoint(path: PathLike) -> FieldState:
    """Load and validate a complete checkpoint from an explicit path."""
    source = Path(path)
    return restore_checkpoint(_decode_file_payload(source.read_bytes()))


def save_trace(
    path: PathLike,
    state: FieldState,
    compress: Optional[bool] = None,
) -> None:
    """Atomically save append-only lifecycle trace to an explicit path."""
    destination = Path(path)
    data = serialize_trace(state)
    _atomic_write(
        destination,
        _encode_file_payload(data, _use_gzip(destination, compress)),
    )


def load_trace(path: PathLike) -> NativeTraceArchive:
    """Load and validate a lifecycle trace from an explicit path."""
    source = Path(path)
    return restore_trace(_decode_file_payload(source.read_bytes()))
