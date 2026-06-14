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
    for stream in dominant[:3]:
        dominant_payload.append(
            {
                "stream_id": stream.stream_id,
                "kind": stream.kind,
                "text": _stream_text(stream),
                "participation": round(stream.participation, 4),
                "persistence": round(stream.persistence, 4),
            }
        )

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
        "held_open_streams": [],
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
                ", ".join(dominant[:3])
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


def _compose_field_articulation(
    state: FieldState,
    basis: Dict[str, Any],
    topology: Dict[str, Any],
) -> str:
    """
    Generate articulation from actual field values and topology.

    This is still stylized prose, but it is no longer a fixed two-branch script.
    It changes with:
    - openness
    - coherence
    - difference activity
    - emergence
    - care tension
    - dominant streams
    - salient edges
    - movement vector
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
    user_stream = next(
        (item for item in dominant_streams if item.get("kind") == "user_input"),
        None,
    )
    live_stream = next(
        (item for item in dominant_streams if item.get("kind") == "live_world"),
        None,
    )

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

    stream_sentence_parts: List[str] = []

    if user_stream:
        stream_sentence_parts.append(
            "Your current proposition is entering through '{0}'.".format(
                str(user_stream.get("text", "") or focus)
            )
        )

    if live_stream:
        stream_sentence_parts.append(
            "Live-world material is participating through '{0}'.".format(
                str(live_stream.get("text", "") or "the current trace")
            )
        )

    if not stream_sentence_parts:
        stream_sentence_parts.append(
            "The inquiry is present, and the field is waiting for stronger cross-material participation."
        )

    movement_sentence = "The field presently leans toward this movement: {0}.".format(
        movement_vector
    )

    return "\n\n".join(
        [
            intro,
            topology_text,
            cut_sentence,
            " ".join(stream_sentence_parts).strip(),
            movement_sentence,
        ]
    ).strip()


def articulate(state: FieldState) -> str:
    """
    Render articulation from field state rather than from a fixed branch script.

    Primary source:
    - state.notes['articulation_basis']
    - state.notes['field_topology']

    Fallback:
    - derive a minimal basis from current streams and field values
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
