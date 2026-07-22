"""Provisional cuts and articulation derived from field configuration."""

from __future__ import annotations

from hashlib import sha1
from typing import List, Optional

from .hypotheses import RuntimeHypotheses
from .models import Articulation, FieldState, ProvisionalCut, Stream


def _stable_id(prefix: str, *parts: str) -> str:
    body = "|".join(str(part) for part in parts)
    return "{0}:{1}".format(prefix, sha1(body.encode("utf-8")).hexdigest()[:14])


def ready_for_provisional_cut(
    state: FieldState,
    hypotheses: RuntimeHypotheses,
) -> bool:
    values = state.field_values
    return bool(
        state.current_phenomenon_ids
        and not state.active_drifts
        and values.emergence_level >= hypotheses.articulation_emergence_floor
        and values.coherence >= hypotheses.articulation_coherence_floor
        and values.cut_permeability >= hypotheses.articulation_permeability_floor
    )


def form_provisional_cut(
    state: FieldState,
    hypotheses: Optional[RuntimeHypotheses] = None,
) -> Optional[ProvisionalCut]:
    hypotheses = hypotheses or RuntimeHypotheses()
    if not ready_for_provisional_cut(state, hypotheses):
        return None

    phenomena = [
        state.phenomenon(item_id)
        for item_id in state.current_phenomenon_ids
    ]
    phenomena = [item for item in phenomena if item is not None]
    if not phenomena:
        return None

    included_ids = sorted(
        {
            stream_id
            for phenomenon in phenomena
            for stream_id in phenomenon.stream_ids
        }
    )
    relation_ids = sorted(
        {
            relation_id
            for phenomenon in phenomena
            for relation_id in phenomenon.relation_ids
        }
    )
    active_ids = {
        item.stream_id for item in state.streams if item.active
    }
    held_open_ids = sorted(active_ids - set(included_ids))
    phenomenon_ids = sorted(item.phenomenon_id for item in phenomena)
    cut_id = _stable_id(
        "cut",
        state.field_id,
        str(state.timestep),
        *phenomenon_ids,
    )
    cut = ProvisionalCut(
        cut_id=cut_id,
        phenomenon_ids=phenomenon_ids,
        included_stream_ids=included_ids,
        held_open_stream_ids=held_open_ids,
        relation_ids=relation_ids,
        apparatus_id=state.apparatus.apparatus_id,
        permeability=state.field_values.cut_permeability,
        timestep=state.timestep,
        # The core deliberately makes no semantic exclusion.  Material that is
        # not participating in this temporary relational component is held
        # open and remains available to later field updates.
        excluded_stream_ids=[],
    )
    if state.latest_cut() is None or state.latest_cut().cut_id != cut.cut_id:
        state.cuts.append(cut)
    return cut


def _shorten(text: str, limit: int = 180) -> str:
    text = " ".join(str(text or "").split()).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _stream_clause(stream: Stream) -> str:
    if stream.kind == "apparatus":
        facet = str(stream.payload.get("facet", "apparatus"))
        values = stream.payload.get("values", [])
        rendered = ", ".join(str(item) for item in values)
        return "apparatus {0} ({1})".format(facet, _shorten(rendered))

    if stream.kind == "play_variation":
        source_ids = stream.payload.get("source_stream_ids", [])
        return "a playable reconfiguration across {0}".format(
            " and ".join(str(item) for item in source_ids)
        )

    if stream.kind == "articulation":
        return "a prior articulation ({0})".format(
            _shorten(str(stream.payload.get("text", "")), 120)
        )

    text = str(
        stream.payload.get("text")
        or stream.payload.get("label")
        or stream.payload.get("title")
        or ""
    ).strip()
    source = str(stream.payload.get("source", "") or "").strip()
    label = stream.kind
    if source:
        label = "{0} from {1}".format(label, source)
    if text:
        return "{0} ('{1}')".format(label, _shorten(text))
    return "{0} ({1})".format(label, stream.stream_id)


def _join_clauses(clauses: List[str]) -> str:
    if not clauses:
        return ""
    if len(clauses) == 1:
        return clauses[0]
    if len(clauses) == 2:
        return "{0} and {1}".format(clauses[0], clauses[1])
    return "{0}, and {1}".format(", ".join(clauses[:-1]), clauses[-1])


def articulate(
    state: FieldState,
    cut: Optional[ProvisionalCut] = None,
) -> Optional[Articulation]:
    cut = cut or state.latest_cut()
    if cut is None:
        return None

    included = [
        state.stream(item_id) for item_id in cut.included_stream_ids
    ]
    included = [item for item in included if item is not None]
    held_open = [
        state.stream(item_id) for item_id in cut.held_open_stream_ids
    ]
    held_open = [item for item in held_open if item is not None]
    phenomena = [
        state.phenomenon(item_id) for item_id in cut.phenomenon_ids
    ]
    phenomena = [item for item in phenomena if item is not None]

    opening = (
        "Within the {0} apparatus, this field is provisionally forming through {1}."
    ).format(
        state.apparatus.medium,
        _join_clauses([_stream_clause(item) for item in included]),
    )

    pattern_clauses: List[str] = []
    for phenomenon in phenomena:
        strength = phenomenon.qualities.get("relational_strength", 0.0)
        resonance = phenomenon.qualities.get("resonance", 0.0)
        difference = phenomenon.qualities.get("difference", 0.0)
        pattern_clauses.append(
            "{0} Relational strength is {1:.2f}, resonance {2:.2f}, and difference {3:.2f}; difference remains part of the form.".format(
                phenomenon.description,
                strength,
                resonance,
                difference,
            )
        )
    pattern_text = " ".join(pattern_clauses)

    if held_open:
        held_open_text = (
            "Material held open rather than resolved is {0}."
        ).format(
            _join_clauses([_stream_clause(item) for item in held_open])
        )
    else:
        held_open_text = (
            "No active stream is discarded by this cut; the boundary remains available to revision."
        )

    closing = (
        "This articulation is a permeable cut ({0:.2f}), not a final account."
    ).format(cut.permeability)
    text = "\n\n".join(
        item for item in [opening, pattern_text, held_open_text, closing] if item
    )

    articulation_id = _stable_id(
        "articulation",
        state.field_id,
        cut.cut_id,
        text,
    )
    articulation = Articulation(
        articulation_id=articulation_id,
        text=text,
        cut_id=cut.cut_id,
        phenomenon_ids=list(cut.phenomenon_ids),
        included_stream_ids=list(cut.included_stream_ids),
        held_open_stream_ids=list(cut.held_open_stream_ids),
        relation_ids=list(cut.relation_ids),
        timestep=state.timestep,
    )
    if not any(
        item.articulation_id == articulation_id
        for item in state.articulations
    ):
        state.articulations.append(articulation)
    return articulation


def reinsert_articulation(
    state: FieldState,
    articulation: Articulation,
    hypotheses: Optional[RuntimeHypotheses] = None,
) -> str:
    hypotheses = hypotheses or RuntimeHypotheses()
    stream_id = "stream:{0}".format(articulation.articulation_id)
    if state.stream(stream_id) is not None:
        return stream_id

    state.streams.append(
        Stream(
            stream_id=stream_id,
            kind="articulation",
            payload={
                "text": articulation.text,
                "cut_id": articulation.cut_id,
                "phenomenon_ids": list(articulation.phenomenon_ids),
                "held_open_stream_ids": list(
                    articulation.held_open_stream_ids
                ),
                "provisional": articulation.provisional,
            },
            participation=hypotheses.articulation_stream_participation,
            persistence=hypotheses.articulation_stream_persistence,
            provenance={
                "movement": "articulation_reinsertion",
                "articulation_id": articulation.articulation_id,
                "timestep": state.timestep,
            },
        )
    )
    state.clamp()
    return stream_id
