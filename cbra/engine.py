
from __future__ import annotations

import uuid
from typing import Any, Dict, List

from .models import FieldState, Stream
from .operators import apply_intra_action, check_field_resonance


def initialize_field_state(inquiry: str) -> FieldState:
    """
    Create a new field centered on the current inquiry.

    The field starts with:
    - a signature naming the phenomena
    - empty stream participation
    - notes prepared for topology and articulation basis
    """
    state = FieldState(
        id=str(uuid.uuid4()),
        field_signature={
            "phenomena": inquiry,
            "current_focus": inquiry,
            "focus_history": [inquiry],
        },
        notes={
            "field_topology": {},
            "articulation_basis": {},
            "movement_vector": "hold relation while the field continues to shift",
            "resonance_ready": False,
        },
    )
    return state


def _stream_text(stream: Stream) -> str:
    return str(stream.payload.get("text", "") or "").strip()


def _ensure_focus_stream(state: FieldState, focus: str) -> None:
    """
    Ensure the field contains the current user-input stream.

    The rebuilt app already appends a user_input stream before each turn.
    This function keeps engine.py self-sufficient and avoids duplicates.
    """
    focus = str(focus or "").strip()
    if not focus:
        return

    for stream in reversed(state.streams):
        if stream.kind == "user_input" and _stream_text(stream) == focus:
            return

    state.streams.append(
        Stream(
            stream_id="user_{0}".format(state.timestep + 1),
            kind="user_input",
            payload={"text": focus},
            participation=1.0,
            persistence=0.8,
        )
    )


def step_field(state: FieldState, focus: str) -> None:
    """
    Advance the field by one timestep.

    This:
    - guarantees the current inquiry is materially present as a stream
    - updates focus history
    - delegates relational dynamics to operators.py
    - records whether the field is resonant enough for articulation
    """
    focus = str(focus or state.field_signature.get("phenomena", "") or "").strip()
    if not focus:
        focus = "the current inquiry"

    _ensure_focus_stream(state, focus)

    state.field_signature["current_focus"] = focus
    history = list(state.field_signature.get("focus_history", []))
    if not history or history[-1] != focus:
        history.append(focus)
    state.field_signature["focus_history"] = history[-8:]

    apply_intra_action(state, focus)
    state.notes["resonance_ready"] = check_field_resonance(state)
    state.clamp()


def _band(value: float) -> str:
    if value >= 0.8:
        return "very high"
    if value >= 0.6:
        return "high"
    if value >= 0.4:
        return "moderate"
    if value >= 0.2:
        return "low"
    return "very low"


def _dominant_streams(state: FieldState) -> List[Stream]:
    streams = [s for s in state.streams if s.active]
    return sorted(
        streams,
        key=lambda s: ((s.participation * 0.7) + (s.persistence * 0.3), s.participation, s.persistence),
        reverse=True,
    )


def _stream_detail(stream: Stream) -> Dict[str, Any]:
    return {
        "stream_id": stream.stream_id,
        "kind": stream.kind,
        "text": _stream_text(stream),
        "source": stream.payload.get("source"),
        "participation": round(stream.participation, 4),
        "persistence": round(stream.persistence, 4),
    }


def _details_by_ids(state: FieldState, stream_ids: List[str]) -> List[Dict[str, Any]]:
    lookup = {
        stream.stream_id: _stream_detail(stream)
        for stream in state.streams
        if stream.active
    }
    details: List[Dict[str, Any]] = []
    for stream_id in stream_ids:
        item = lookup.get(stream_id)
        if item is not None:
            details.append(item)
    return details


def _shorten(text: str, limit: int = 220) -> str:
    cleaned = " ".join((text or "").split()).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _source_label(item: Dict[str, Any]) -> str:
    source = str(item.get("source") or "").strip()
    return source if source else "the vault"


def _fallback_articulation_basis(state: FieldState) -> Dict[str, Any]:
    """
    Build a minimal articulation basis if operators.py has not provided one.

    This keeps engine.py resilient while still grounding articulation in field state.
    """
    dominant = _dominant_streams(state)
    focus = str(
        state.field_signature.get(
            "current_focus",
            state.field_signature.get("phenomena", "the current inquiry"),
        )
    )

    dominant_payload: List[Dict[str, Any]] = []
    for stream in dominant[:4]:
        dominant_payload.append(_stream_detail(stream))

    held_open_ids = [
        stream.stream_id
        for stream in dominant
        if 0.35 <= stream.participation <= 0.75 and stream.persistence >= 0.45
    ][:4]

    basis = {
        "focus": focus,
        "field_values": {
            "openness": round(state.field_values.openness, 4),
            "difference_activity": round(state.field_values.difference_activity, 4),
            "emergence_level": round(state.field_values.emergence_level, 4),
            "cut_pressure": round(state.field_values.cut_pressure, 4),
            "cut_permeability": round(state.field_values.cut_permeability, 4),
            "coherence": round(state.field_values.coherence, 4),
            "care_tension": round(state.field_values.care_tension, 4),
        },
        "dominant_streams": dominant_payload,
        "held_open_streams": held_open_ids,
        "held_open_details": _details_by_ids(state, held_open_ids),
        "salient_edges": [],
        "movement_vector": str(
            state.notes.get("movement_vector", "hold relation while the field continues to shift")
        ),
    }
    state.notes["articulation_basis"] = basis
    return basis


def _describe_topology(topology: Dict[str, Any]) -> str:
    dominant = topology.get("dominant_streams", []) or []
    held_open = topology.get("held_open_streams", []) or []
    edges = topology.get("salient_edges", []) or []

    parts: List[str] = []

    if dominant:
        parts.append(
            "Dominant participation is currently carried by {0}.".format(
                ", ".join(dominant[:4])
            )
        )

    if held_open:
        parts.append(
            "Held-open streams remain {0}.".format(
                ", ".join(held_open[:4])
            )
        )

    if edges:
        edge = edges[0]
        left = str(edge.get("left", "one stream"))
        right = str(edge.get("right", "another stream"))
        resonance = _band(float(edge.get("resonance", 0.0)))
        difference = _band(float(edge.get("difference", 0.0)))
        parts.append(
            "A salient relation is active between {0} and {1}, with {2} resonance and {3} difference.".format(
                left,
                right,
                resonance,
                difference,
            )
        )

    return " ".join(parts).strip()


def _weave_live_material(
    dominant_live: List[Dict[str, Any]],
    held_open_details: List[Dict[str, Any]],
) -> str:
    if not dominant_live and not held_open_details:
        return "The inquiry is present, and the field is waiting for stronger cross-material participation."

    sentences: List[str] = []

    if dominant_live:
        primary = dominant_live[0]
        sentences.append(
            "A primary live strand from {0} enters through '{1}'.".format(
                _source_label(primary),
                _shorten(str(primary.get("text", "") or "")),
            )
        )

    if len(dominant_live) > 1:
        secondary = dominant_live[1]
        sentences.append(
            "A second strand from {0} complicates that cut through '{1}'.".format(
                _source_label(secondary),
                _shorten(str(secondary.get("text", "") or "")),
            )
        )

    if held_open_details:
        held = held_open_details[0]
        held_id = str(held.get("stream_id", "a held-open strand"))
        if not any(item.get("stream_id") == held_id for item in dominant_live):
            sentences.append(
                "The field keeps another strand from {0} held open rather than resolved: '{1}'.".format(
                    _source_label(held),
                    _shorten(str(held.get("text", "") or "")),
                )
            )

    return " ".join(sentences).strip()


def _compose_field_articulation(
    state: FieldState,
    basis: Dict[str, Any],
    topology: Dict[str, Any],
) -> str:
    """
    Generate articulation from actual field values and topology.
    """
    focus = str(
        basis.get("focus")
        or state.field_signature.get("phenomena")
        or "the current inquiry"
    )

    values = basis.get("field_values", {}) or {}
    openness = float(values.get("openness", state.field_values.openness))
    coherence = float(values.get("coherence", state.field_values.coherence))
    difference_activity = float(
        values.get("difference_activity", state.field_values.difference_activity)
    )
    emergence = float(values.get("emergence_level", state.field_values.emergence_level))
    care_tension = float(values.get("care_tension", state.field_values.care_tension))
    cut_pressure = float(values.get("cut_pressure", state.field_values.cut_pressure))
    movement_vector = str(
        basis.get("movement_vector")
        or state.notes.get("movement_vector")
        or "hold relation while the field continues to shift"
    )

    dominant_streams = basis.get("dominant_streams", []) or []
    if not dominant_streams:
        dominant_streams = _details_by_ids(state, topology.get("dominant_streams", []) or [])

    held_open_details = basis.get("held_open_details", []) or []
    if not held_open_details:
        held_open_details = _details_by_ids(state, basis.get("held_open_streams", []) or topology.get("held_open_streams", []) or [])

    user_stream = next(
        (item for item in dominant_streams if item.get("kind") == "user_input"),
        None,
    )
    dominant_live = [item for item in dominant_streams if item.get("kind") == "live_world"]

    intro = (
        "The field around '{0}' is currently holding {1} openness, {2} coherence, "
        "{3} difference activity, and {4} care tension.".format(
            focus,
            _band(openness),
            _band(coherence),
            _band(difference_activity),
            _band(care_tension),
        )
    )

    topology_text = _describe_topology(topology)
    if not topology_text:
        topology_text = "The current topology is still sparse, so the cut remains provisional."

    if emergence >= 0.65 and coherence >= 0.55:
        cut_sentence = (
            "Emergence is {0}, and the field is generating enough stability for a provisional articulation. "
            "Cut pressure remains {1}, so closure stays temporary.".format(
                _band(emergence),
                _band(cut_pressure),
            )
        )
    elif difference_activity >= 0.55 and coherence < 0.5:
        cut_sentence = (
            "Difference is outpacing coherence, so the field is widening rather than settling. "
            "The cut stays permeable while relation continues to reorganize."
        )
    else:
        cut_sentence = (
            "The field is still composing itself through uneven relation. "
            "A gentle articulation is available without forcing final closure."
        )

    if user_stream:
        user_sentence = "Your current proposition is entering through '{0}'.".format(
            str(user_stream.get("text", "") or focus)
        )
    else:
        user_sentence = "The inquiry remains the current orienting pressure."

    live_sentence = _weave_live_material(dominant_live, held_open_details)

    movement_sentence = "The field presently leans toward this movement: {0}.".format(
        movement_vector
    )

    return "\n\n".join(
        [
            intro,
            topology_text,
            cut_sentence,
            user_sentence,
            live_sentence,
            movement_sentence,
        ]
    ).strip()


def articulate(state: FieldState) -> str:
    """
    Render articulation from field state rather than from a fixed branch script.
    """
    basis = dict(state.notes.get("articulation_basis") or {})
    if not basis:
        basis = _fallback_articulation_basis(state)

    topology = dict(state.notes.get("field_topology") or {})
    if not topology:
        topology = {
            "dominant_streams": [
                item.get("stream_id")
                for item in basis.get("dominant_streams", [])
                if item.get("stream_id")
            ],
            "held_open_streams": basis.get("held_open_streams", []),
            "salient_edges": basis.get("salient_edges", []),
        }

    text = _compose_field_articulation(state, basis, topology)
    state.notes["last_articulation"] = text
    return text

