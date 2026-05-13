from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from cbra.cbra_runtime_rebuilt.runtime.field_state import FieldState

def _shorten(text: str, limit: int = 160) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"

def stream_label(state: FieldState, stream_id: str) -> str:
    for s in state.streams:
        if s.stream_id != stream_id:
            continue
        if "concept" in s.payload and s.payload["concept"]:
            return str(s.payload["concept"])
        if "label" in s.payload and s.payload["label"]:
            return str(s.payload["label"])
        if "place" in s.payload and s.payload["place"]:
            return str(s.payload["place"])
        if "title" in s.payload and s.payload["title"]:
            return str(s.payload["title"])
        if "text" in s.payload and s.payload["text"]:
            return _shorten(str(s.payload["text"]), 80)
        return s.kind
    return stream_id

def choose_lead_label(state: FieldState) -> str:
    ef = state.emergent_form
    if ef.label:
        return ef.label
    if ef.lead_stream_ids:
        return stream_label(state, ef.lead_stream_ids[0])
    active = [s for s in state.streams if s.active]
    if not active:
        return "the field"
    lead = max(active, key=lambda s: s.participation)
    return stream_label(state, lead.stream_id)

def choose_articulation_stock(state: FieldState) -> str:
    live_world_active = any(s.active and s.kind == "live_world" for s in state.streams)
    attachment_active = any(s.active and s.kind == "attachment" for s in state.streams)
    fv = state.field_values
    interference_active = bool(state.emergent_form.interference_stream_ids)
    held_open_active = bool(state.emergent_form.held_open_stream_ids)
    document_bias = attachment_active or state.apparatus.framing == "document-grounded inquiry"
    situated_bias = live_world_active or state.apparatus.framing == "situated live-world inquiry"
    if situated_bias and (fv.care_tension >= 0.45 or interference_active or fv.difference_activity >= 0.65):
        return "situated_live_world"
    if document_bias and (fv.coherence >= 0.45 or fv.cut_pressure >= 0.20 or not situated_bias):
        return "document_grounded"
    if situated_bias and fv.coherence >= 0.40:
        return "situated_live_world"
    if document_bias:
        return "document_grounded"
    if held_open_active and fv.cut_permeability >= 0.55 and fv.openness >= 0.55:
        return "plain_conceptual"
    return "plain_conceptual"

def _labels_from_ids(state: FieldState, ids: list[str], limit: int = 3) -> list[str]:
    out = []
    for sid in ids[:limit]:
        lab = stream_label(state, sid)
        if lab not in out:
            out.append(lab)
    return out

def _recent_reintegration_count(history: Optional[List[Any]]) -> int:
    if not history:
        return 0
    return sum(1 for entry in history[-3:] if getattr(entry, "reintegration_target", None))

def _recent_drift_signal_count(history: Optional[List[Any]]) -> int:
    if not history:
        return 0
    total = 0
    for entry in history[-3:]:
        flags = getattr(entry, "drift_flags_before", {}) or {}
        total += sum(1 for _, v in flags.items() if v)
    return total

def articulation_density_profile(state: FieldState, history: Optional[List[Any]] = None) -> str:
    fv = state.field_values
    reintegrations = _recent_reintegration_count(history)
    drift_signals = _recent_drift_signal_count(history)
    if fv.care_tension >= 0.70 or reintegrations >= 2 or drift_signals >= 2:
        return "minimal"
    if fv.care_tension >= 0.45 or fv.coherence < 0.50 or reintegrations >= 1:
        return "compact"
    if fv.coherence >= 0.75 and fv.care_tension <= 0.30:
        return "full"
    return "standard"

def _describe_field_tone(state: FieldState, history: Optional[List[Any]] = None) -> str:
    fv = state.field_values
    reintegrations = _recent_reintegration_count(history)
    drift_signals = _recent_drift_signal_count(history)
    if fv.care_tension >= 0.70 or reintegrations >= 2 or drift_signals >= 2:
        return "The field is fragile enough that articulation should stay brief, careful, and non-forcing."
    if fv.care_tension > 0.65:
        return "The field is under notable care tension, so articulation should stay careful and non-forcing."
    if reintegrations >= 1 or drift_signals >= 1:
        return "The field has recently needed reintegration, so articulation should stay steady, careful, and revisable."
    if fv.coherence >= 0.75 and fv.care_tension <= 0.35:
        return "The field is relatively coherent and not under heavy care strain."
    if fv.coherence >= 0.55 and fv.care_tension <= 0.55:
        return "The field has enough coherence to speak, while still needing some care."
    return "The field remains in motion, so articulation should stay descriptive and revisable."

def _render_cut_sentence(state: FieldState) -> str:
    fg = list(state.cut.foregrounded[:3]); bg = list(state.cut.backgrounded[:3]); held = list(state.cut.held_open[:3])
    parts = []
    if fg: parts.append(f"Foregrounded now: {', '.join(fg)}.")
    if bg: parts.append(f"Backgrounded but still present: {', '.join(bg)}.")
    if held: parts.append(f"Held open: {', '.join(held)}.")
    return " ".join(parts) if parts else "No strong cut has stabilized yet."

def _render_relational_sentence(state: FieldState) -> str:
    support = _labels_from_ids(state, state.emergent_form.support_stream_ids, limit=3)
    interference = _labels_from_ids(state, state.emergent_form.interference_stream_ids, limit=3)
    if support and interference:
        return f"Support is coming through {', '.join(support)}, while interference or productive difference remains active through {', '.join(interference)}."
    if support:
        return f"Support is coming through {', '.join(support)}."
    if interference:
        return f"Interference or productive difference remains active through {', '.join(interference)}."
    return "Support and interference remain distributed across the active field."

def _assemble(parts: list[str], density: str, limit: int = 700) -> str:
    parts = [p for p in parts if p]
    if not parts:
        return ""
    if density == "minimal":
        kept = [parts[0]]
        if len(parts) > 1: kept.append(parts[-1])
        parts = kept; limit = 320
    elif density == "compact":
        kept = [parts[0]]
        if len(parts) > 2:
            kept.extend([parts[1], parts[-1]])
        elif len(parts) > 1:
            kept.append(parts[-1])
        parts = kept; limit = 460
    elif density == "standard":
        parts = parts[:4]; limit = 620
    else:
        limit = 760
    return _shorten(" ".join(parts), limit)

def decode_plain_conceptual(state: FieldState, history: Optional[List[Any]] = None) -> str:
    lead = choose_lead_label(state)
    held = _labels_from_ids(state, state.emergent_form.held_open_stream_ids, limit=3)
    density = articulation_density_profile(state, history)
    s1 = f"The field is currently organizing around {lead}." if lead else "The field has begun to organize, but no stable lead is fully clear yet."
    s2 = _render_relational_sentence(state)
    s3 = _render_cut_sentence(state)
    s4 = _describe_field_tone(state, history)
    s5 = f"What remains explicitly open in the emerging form includes {', '.join(held)}." if held else ""
    return _assemble([s1,s2,s3,s4,s5], density)

def decode_situated_live_world(state: FieldState, history: Optional[List[Any]] = None) -> str:
    lead = choose_lead_label(state)
    support = _labels_from_ids(state, state.emergent_form.support_stream_ids, limit=3)
    interference = _labels_from_ids(state, state.emergent_form.interference_stream_ids, limit=3)
    places = [str(s.payload.get("place")) for s in state.streams if s.active and s.payload.get("place")]
    times = [str(s.payload.get("time")) for s in state.streams if s.active and s.payload.get("time")]
    live_labels = [stream_label(state, s.stream_id) for s in state.streams if s.active and s.kind == "live_world"]
    density = articulation_density_profile(state, history)
    s1 = f"The field is organizing around {lead} in a situated way." if lead else "The field is organizing around the current situation in a situated way."
    if places or times:
        pt = []
        if places: pt.append(f"place: {', '.join(list(dict.fromkeys(places))[:2])}")
        if times: pt.append(f"time: {', '.join(list(dict.fromkeys(times))[:2])}")
        s2 = f"The strongest local conditions are {', '.join(pt)}."
    elif live_labels:
        s2 = f"Live-world material is active through {', '.join(list(dict.fromkeys(live_labels))[:3])}."
    else:
        s2 = "Current-world material is active in the field."
    if support and interference:
        s3 = f"Support is coming through {', '.join(support)}, while interference remains active through {', '.join(interference)}."
    elif support:
        s3 = f"Support is coming through {', '.join(support)}."
    elif interference:
        s3 = f"Interference remains active through {', '.join(interference)}."
    else:
        s3 = "Support remains distributed across the active field."
    return _assemble([s1,s2,s3,_render_cut_sentence(state),_describe_field_tone(state, history)], density)

def decode_document_grounded(state: FieldState, history: Optional[List[Any]] = None) -> str:
    lead = choose_lead_label(state)
    support = _labels_from_ids(state, state.emergent_form.support_stream_ids, limit=3)
    interference = _labels_from_ids(state, state.emergent_form.interference_stream_ids, limit=3)
    doc_titles = [stream_label(state, s.stream_id) for s in state.streams if s.active and s.kind == "attachment"]
    unique_titles = list(dict.fromkeys(doc_titles))[:3]
    density = articulation_density_profile(state, history)
    s1 = f"The field is organizing around {lead} through document-grounded material." if lead else "The field is organizing through document-grounded material."
    s2 = f"Active document material includes {', '.join(unique_titles)}." if unique_titles else "Document material is active in the field."
    if support and interference:
        s3 = f"Support is coming through {', '.join(support)}, while interference or unresolved difference remains active through {', '.join(interference)}."
    elif support:
        s3 = f"Support is coming through {', '.join(support)}."
    elif interference:
        s3 = f"Interference or unresolved difference remains active through {', '.join(interference)}."
    else:
        s3 = "Support and interference remain distributed across the document-grounded field."
    return _assemble([s1,s2,s3,_render_cut_sentence(state),_describe_field_tone(state, history)], density)

def decode_articulation(state: FieldState, history: Optional[List[Any]] = None) -> str:
    stock = choose_articulation_stock(state)
    if stock == "situated_live_world":
        return decode_situated_live_world(state, history)
    if stock == "document_grounded":
        return decode_document_grounded(state, history)
    return decode_plain_conceptual(state, history)
