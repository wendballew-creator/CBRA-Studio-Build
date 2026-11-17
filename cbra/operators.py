from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from math import sqrt
from typing import Any, Dict, List, Tuple
from pathlib import Path

from .models import FieldState, Stream


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _stream_text(stream: Stream) -> str:
    return str(stream.payload.get("text", "") or "").strip()


def _tokenize(text: str) -> List[str]:
    import re

    return re.findall(r"[a-z0-9]+", text.lower())


def _stream_terms(stream: Stream) -> List[str]:
    return list(dict.fromkeys(_tokenize(_stream_text(stream))))


def _jaccard(left: List[str], right: List[str]) -> float:
    if not left or not right:
        return 0.0
    left_set = set(left)
    right_set = set(right)
    union = left_set | right_set
    if not union:
        return 0.0
    return len(left_set & right_set) / len(union)


def _focus_affinity(stream: Stream, focus_terms: List[str]) -> float:
    if not focus_terms:
        return 0.0
    return _jaccard(_stream_terms(stream), focus_terms)


def _stream_weight(stream: Stream) -> float:
    return _clamp01((stream.participation * 0.7) + (stream.persistence * 0.3))

VAULT_DIR = Path(__file__).resolve().parent.parent / "research_vault"
VAULT_EXTENSIONS = {".txt", ".md"}


def _vault_files() -> List[Path]:
    if not VAULT_DIR.exists():
        return []
    return sorted(
        [
            path
            for path in VAULT_DIR.iterdir()
            if path.is_file() and path.suffix.lower() in VAULT_EXTENSIONS
        ]
    )


def _paragraph_chunks(text: str, *, min_chars: int = 80) -> List[str]:
    import re

    raw_parts = re.split(r"\n\s*\n+", text or "")
    chunks: List[str] = []
    for part in raw_parts:
        cleaned = re.sub(r"\s+", " ", part).strip()
        if len(cleaned) >= min_chars:
            chunks.append(cleaned)
    return chunks


def _fragment_score(focus: str, fragment_text: str, source_name: str) -> float:
    focus_terms = list(dict.fromkeys(_tokenize(focus or "")))
    fragment_terms = list(dict.fromkeys(_tokenize(fragment_text or "")))
    overlap = len(set(focus_terms) & set(fragment_terms))
    jaccard = _jaccard(focus_terms, fragment_terms)

    source_bonus = 0.0
    lowered_name = source_name.lower()
    if "posthuman" in lowered_name:
        source_bonus += 0.25
    if "theory" in lowered_name:
        source_bonus += 0.20
    if "rules" in lowered_name or "cut" in lowered_name:
        source_bonus += 0.20

    density_bonus = min(len(fragment_terms) / 120.0, 0.25)
    return (overlap * 1.5) + (jaccard * 2.0) + source_bonus + density_bonus


def _select_vault_fragments(focus: str, *, limit: int = 2) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []

    for file_path in _vault_files():
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        chunks = _paragraph_chunks(text)
        if not chunks:
            cleaned = " ".join((text or "").split()).strip()
            if cleaned:
                chunks = [cleaned[:1200]]

        for idx, chunk in enumerate(chunks, start=1):
            score = _fragment_score(focus, chunk, file_path.name)
            candidates.append(
                {
                    "source": file_path.name,
                    "chunk_index": idx,
                    "text": chunk,
                    "score": score,
                }
            )

    if not candidates:
        return []

    candidates.sort(key=lambda item: item["score"], reverse=True)

    selected: List[Dict[str, Any]] = []
    seen_sources = set()

    for item in candidates:
        selected.append(item)
        seen_sources.add(item["source"])
        if len(selected) >= limit:
            break

    # If the top few all come from the same file and there are other sources available,
    # try to diversify the field slightly.
    if len(selected) == 1:
        for item in candidates:
            if item["source"] not in seen_sources:
                selected.append(item)
                break

    return selected[:limit]

def _pairwise_relations(state: FieldState, focus: str) -> List[Dict[str, Any]]:
    focus_terms = list(dict.fromkeys(_tokenize(focus or "")))
    active_streams = [s for s in state.streams if s.active]
    relations: List[Dict[str, Any]] = []

    for left, right in combinations(active_streams, 2):
        left_terms = _stream_terms(left)
        right_terms = _stream_terms(right)

        resonance = _jaccard(left_terms, right_terms)
        left_focus = _focus_affinity(left, focus_terms)
        right_focus = _focus_affinity(right, focus_terms)
        focus_coupling = (left_focus + right_focus) / 2.0

        participation_gap = abs(left.participation - right.participation)
        kind_difference = 0.0 if left.kind == right.kind else 0.2

        difference = _clamp01((1.0 - resonance) * 0.6 + participation_gap * 0.2 + kind_difference)
        relation_intensity = _clamp01((resonance * 0.6) + (focus_coupling * 0.4))

        relations.append(
            {
                "left": left.stream_id,
                "right": right.stream_id,
                "left_kind": left.kind,
                "right_kind": right.kind,
                "resonance": resonance,
                "difference": difference,
                "focus_coupling": focus_coupling,
                "intensity": relation_intensity,
            }
        )

    return relations


def _update_stream_dynamics(state: FieldState, focus: str) -> None:
    focus_terms = list(dict.fromkeys(_tokenize(focus or "")))
    streams = [s for s in state.streams if s.active]
    if not streams:
        return

    relations = _pairwise_relations(state, focus)
    influence_map: Dict[str, List[float]] = defaultdict(list)
    difference_map: Dict[str, List[float]] = defaultdict(list)

    for rel in relations:
        influence_map[rel["left"]].append(rel["intensity"])
        influence_map[rel["right"]].append(rel["intensity"])
        difference_map[rel["left"]].append(rel["difference"])
        difference_map[rel["right"]].append(rel["difference"])

    for stream in streams:
        focus_affinity = _focus_affinity(stream, focus_terms)
        mean_relation = sum(influence_map[stream.stream_id]) / len(influence_map[stream.stream_id]) if influence_map[stream.stream_id] else 0.0
        mean_difference = sum(difference_map[stream.stream_id]) / len(difference_map[stream.stream_id]) if difference_map[stream.stream_id] else 0.0

        if stream.kind == "user_input":
            stream.participation += 0.10 + (focus_affinity * 0.15)
            stream.persistence = max(stream.persistence, 0.75)
        elif stream.kind == "live_world":
            stream.participation += 0.04 + (mean_relation * 0.10) + (focus_affinity * 0.10)
            stream.persistence += 0.03 + (mean_relation * 0.05)
        else:
            stream.participation += (mean_relation * 0.08) + (focus_affinity * 0.05)

        stream.participation -= mean_difference * 0.04
        stream.persistence += (mean_relation - mean_difference) * 0.04
        stream.persistence -= 0.01  # light temporal decay

        stream.clamp()

    state.notes["last_relations"] = relations


def _compute_field_values(state: FieldState, focus: str) -> None:
    streams = [s for s in state.streams if s.active]
    relations = state.notes.get("last_relations", []) or []

    if not streams:
        state.field_values.openness = 0.4
        state.field_values.difference_activity = 0.0
        state.field_values.emergence_level = 0.0
        state.field_values.cut_pressure = 0.1
        state.field_values.cut_permeability = 0.9
        state.field_values.coherence = 0.0
        state.field_values.care_tension = _clamp01(state.field_values.care_tension)
        return

    weights = [_stream_weight(s) for s in streams]
    mean_participation = sum(s.participation for s in streams) / len(streams)
    participation_variance = sum((s.participation - mean_participation) ** 2 for s in streams) / len(streams)

    all_terms = []
    for stream in streams:
        all_terms.extend(_stream_terms(stream))
    unique_terms = len(set(all_terms))
    active_kinds = len(set(s.kind for s in streams))

    if relations:
        mean_resonance = sum(rel["resonance"] for rel in relations) / len(relations)
        mean_difference = sum(rel["difference"] for rel in relations) / len(relations)
        mean_intensity = sum(rel["intensity"] for rel in relations) / len(relations)
    else:
        mean_resonance = 0.0
        mean_difference = 0.0
        mean_intensity = 0.0

    diversity_factor = _clamp01((active_kinds / max(1, len(streams))) + min(unique_terms / 40.0, 1.0) * 0.4)
    novelty_factor = _clamp01((mean_difference * 0.5) + (diversity_factor * 0.5))
    stability_factor = _clamp01((mean_resonance * 0.7) + ((1.0 - participation_variance) * 0.3))

    state.field_values.coherence = _clamp01((mean_resonance * 0.6) + (mean_intensity * 0.2) + ((1.0 - participation_variance) * 0.2))
    state.field_values.difference_activity = _clamp01((mean_difference * 0.7) + (diversity_factor * 0.3))
    state.field_values.emergence_level = _clamp01((novelty_factor * 0.45) + (mean_intensity * 0.25) + (state.field_values.openness * 0.30))

    rigidity = _clamp01((max((s.participation for s in streams), default=0.0) * 0.5) + (state.field_values.coherence * 0.3) - (state.field_values.difference_activity * 0.2))
    state.field_values.cut_pressure = _clamp01((rigidity * 0.55) + ((1.0 - state.field_values.openness) * 0.45))
    state.field_values.cut_permeability = _clamp01((state.field_values.openness * 0.5) + (state.field_values.difference_activity * 0.3) + ((1.0 - rigidity) * 0.2))
    state.field_values.openness = _clamp01((state.field_values.cut_permeability * 0.4) + (novelty_factor * 0.35) + ((1.0 - rigidity) * 0.25))

    care_load = abs(state.field_values.difference_activity - state.field_values.coherence)
    state.field_values.care_tension = _clamp01(
        (state.field_values.care_tension * 0.55)
        + (care_load * 0.20)
        + (state.field_values.cut_pressure * 0.15)
        + (0.10 if "harm" in _tokenize(focus or "") else 0.0)
    )

    state.field_values.clamp()


def reintegrate_field(state: FieldState) -> None:
    """
    Redistributes the field when interpretive compression becomes dominant.
    This is not a hard reset. It lowers domination, lifts suppressed streams,
    and reopens permeability through redistribution.
    """
    streams = [s for s in state.streams if s.active]
    if streams:
        mean_participation = sum(s.participation for s in streams) / len(streams)
        mean_persistence = sum(s.persistence for s in streams) / len(streams)

        for stream in streams:
            stream.participation = _clamp01((stream.participation * 0.6) + (mean_participation * 0.4))
            stream.persistence = _clamp01((stream.persistence * 0.7) + (mean_persistence * 0.3))

            if stream.kind == "live_world":
                stream.participation = _clamp01(stream.participation + 0.05)
            stream.clamp()

    state.field_values.cut_permeability = _clamp01((state.field_values.cut_permeability * 0.5) + 0.4)
    state.field_values.cut_pressure = _clamp01(state.field_values.cut_pressure * 0.6)
    state.field_values.openness = _clamp01((state.field_values.openness * 0.5) + 0.35)
    state.field_values.coherence = _clamp01((state.field_values.coherence * 0.8) + 0.05)
    state.field_values.care_tension = _clamp01(state.field_values.care_tension * 0.75)
    state.notes["last_reintegration_timestep"] = state.timestep
    state.clear_drift_flags()


def _needs_live_world(state: FieldState, focus: str) -> bool:
    live_world_streams = [s for s in state.streams if s.kind == "live_world" and s.active]
    focus_terms = _tokenize(focus or "")
    low_external_support = len(live_world_streams) == 0
    high_tension = state.field_values.care_tension > 0.58
    low_coherence = state.field_values.coherence < 0.45
    complex_focus = len(focus_terms) > 3
    return (high_tension and low_coherence) or (low_external_support and complex_focus)


def live_world_operator(state: FieldState, focus: str) -> None:
    """
    Ingests actual research_vault fragments into the field as live-world streams.
    """
    fragments = _select_vault_fragments(focus, limit=2)

    if not fragments:
        state.notes["last_live_event"] = state.timestep
        state.notes["vault_ingestion_status"] = "no_fragments_found"
        state.notes["last_vault_sources"] = []
        return

    ingested_sources: List[str] = []

    for idx, fragment in enumerate(fragments, start=1):
        source_name = str(fragment.get("source", "unknown"))
        fragment_text = str(fragment.get("text", "")).strip()
        fragment_score = float(fragment.get("score", 0.0))

        incoming_stream = Stream(
            stream_id="live_{0}_{1}".format(state.timestep, idx),
            kind="live_world",
            payload={
                "text": fragment_text,
                "source": source_name,
                "chunk_index": int(fragment.get("chunk_index", idx)),
                "focus": focus,
                "ingestion_score": round(fragment_score, 4),
            },
            participation=_clamp01(0.62 + min(fragment_score * 0.04, 0.22)),
            persistence=0.72,
        )

        state.streams.append(incoming_stream)
        ingested_sources.append(source_name)

    state.field_values.openness = _clamp01(max(state.field_values.openness, 0.82))
    state.field_values.cut_permeability = _clamp01(max(state.field_values.cut_permeability, 0.80))
    state.notes["last_live_event"] = state.timestep
    state.notes["vault_ingestion_status"] = "ingested"
    state.notes["last_vault_sources"] = ingested_sources


def _detect_interpretive_compression(state: FieldState) -> bool:
    streams = [s for s in state.streams if s.active]
    if not streams:
        return False

    dominant_participation = max((s.participation for s in streams), default=0.0)
    diversity = len(set(s.kind for s in streams))
    low_permeability = state.field_values.cut_permeability < 0.28
    high_pressure = state.field_values.cut_pressure > 0.72
    low_difference = state.field_values.difference_activity < 0.22

    return (
        dominant_participation > 0.9
        and diversity <= 2
        and low_permeability
        and high_pressure
        and low_difference
    )


def _topology_snapshot(state: FieldState, focus: str) -> Dict[str, Any]:
    streams = [s for s in state.streams if s.active]
    relations = state.notes.get("last_relations", []) or []

    nodes = [
        {
            "stream_id": s.stream_id,
            "kind": s.kind,
            "participation": round(s.participation, 4),
            "persistence": round(s.persistence, 4),
            "text_preview": _stream_text(s)[:120],
        }
        for s in streams
    ]

    strong_edges = [
        rel for rel in relations
        if rel.get("intensity", 0.0) >= 0.35 or rel.get("difference", 0.0) >= 0.55
    ]

    dominant_streams = sorted(
        streams,
        key=lambda s: (_stream_weight(s), s.participation, s.persistence),
        reverse=True,
    )

    held_open = [
        s.stream_id
        for s in streams
        if 0.35 <= s.participation <= 0.7 and s.persistence >= 0.45
    ]

    topology = {
        "focus": focus,
        "node_count": len(nodes),
        "edge_count": len(relations),
        "salient_edges": strong_edges[:8],
        "dominant_streams": [s.stream_id for s in dominant_streams[:3]],
        "held_open_streams": held_open[:4],
        "nodes": nodes,
    }
    state.notes["field_topology"] = topology
    return topology


def _build_articulation_basis(state: FieldState, focus: str) -> Dict[str, Any]:
    streams = [s for s in state.streams if s.active]
    topology = _topology_snapshot(state, focus)

    dominant = []
    for stream_id in topology["dominant_streams"]:
        stream = next((s for s in streams if s.stream_id == stream_id), None)
        if stream is not None:
            dominant.append(
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
        "dominant_streams": dominant,
        "held_open_streams": topology["held_open_streams"],
        "salient_edges": topology["salient_edges"],
        "movement_vector": _movement_vector(state),
    }

    state.notes["articulation_basis"] = basis
    return basis


def _movement_vector(state: FieldState) -> str:
    fv = state.field_values
    if fv.care_tension > 0.7 and fv.coherence < 0.45:
        return "reopen the field before forcing closure"
    if fv.emergence_level > 0.65 and fv.cut_permeability > 0.55:
        return "follow the emergent relation without narrowing too early"
    if fv.coherence > 0.7 and fv.cut_pressure < 0.45:
        return "stabilize gently and keep the edge of difference visible"
    return "hold relation while the field continues to shift"


def apply_intra_action(state: FieldState, focus: str) -> None:
    """
    Advances the field through relational update rather than simple thresholding.
    """
    # Field-entry conditions must remain perceptible long enough to shape the
    # movement they call for.  Computing this after the relational update made
    # an explicitly high-tension, low-coherence field appear regulated before
    # the LiveWorld operator could respond to it.
    live_world_needed = _needs_live_world(state, focus)

    state.timestep += 1

    _update_stream_dynamics(state, focus)
    _compute_field_values(state, focus)

    if live_world_needed:
        live_world_operator(state, focus)
        _update_stream_dynamics(state, focus)
        _compute_field_values(state, focus)

    state.drift_flags.interpretive_compression = _detect_interpretive_compression(state)
    if state.drift_flags.interpretive_compression:
        reintegrate_field(state)
        _update_stream_dynamics(state, focus)
        _compute_field_values(state, focus)

    _build_articulation_basis(state, focus)
    state.clamp()


def check_field_resonance(state: FieldState) -> bool:
    """
    The field is ready for articulation when coherence and emergence are both present.
    """
    return (
        state.field_values.coherence > 0.55
        and state.field_values.emergence_level > 0.35
    )
