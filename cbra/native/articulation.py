"""Provisional cuts, situated expression, evaluation, and reinsertion."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import re
from typing import Iterable, List, Optional, Protocol, Sequence

from .hypotheses import RuntimeHypotheses
from .models import (
    Articulation,
    ArticulationBasis,
    ArticulationCandidate,
    ArticulationEvaluation,
    ArticulationFormation,
    ArticulationMaterial,
    DriftKind,
    DriftSignal,
    FieldState,
    ProvisionalCut,
    Stream,
    clamp01,
)


MORALIZATION_PATTERNS = (
    r"\byou should\b",
    r"\byou must\b",
    r"\byou need to\b",
    r"\byou have to\b",
    r"\bought to\b",
    r"\bthe right (?:answer|choice|way)\b",
    r"\bthe wrong (?:answer|choice|way)\b",
    r"\bclearly\b",
    r"\bobviously\b",
)

CLOSURE_PATTERNS = (
    r"\bthe answer is\b",
    r"\bthere is no alternative\b",
    r"\bthis settles\b",
    r"\bmust be resolved\b",
    r"\bfinal account\b",
)

NARRATIVE_DOMINANCE_PATTERNS = (
    r"\bthe only explanation\b",
    r"\bthe real reason\b",
    r"\bthis proves\b",
    r"\bnothing else explains\b",
    r"\bsimply because\b",
)

PROCEDURAL_PATTERNS = (
    r"\b(?:stream|relation|phenomenon|cut|articulation):[a-z0-9]",
    r"\bfield id\b",
    r"\bapparatus id\b",
    r"\btimestep\b",
    r"\boperator delta\b",
    r"\bpipeline\b",
    r"\bprovisional cut\b",
    r"\bcut permeability\b",
    r"\brelational strength\b",
    r"\bstream type\b",
    r"\bselected elements\b",
    r"\btext_chat apparatus\b",
    r"\b(?:coherence|resonance|difference|permeability|mutuality)"
    r"\s+(?:is\s+)?0\.\d+",
)

MAX_RENDERED_ARTICULATION_CHARS = 32768


class ArticulationRenderer(Protocol):
    """Propose text from an isolated native articulation basis."""

    def render(self, basis: ArticulationBasis) -> str:
        """Return proposed user-facing text without mutating native state."""


class ArticulationRendererError(ValueError):
    """A renderer returned text that cannot become a native candidate."""


class NativeTemplateArticulationRenderer:
    """Deterministic renderer preserving the original native wording."""

    def __init__(
        self,
        hypotheses: Optional[RuntimeHypotheses] = None,
    ) -> None:
        self.hypotheses = hypotheses or RuntimeHypotheses()

    def render(self, basis: ArticulationBasis) -> str:
        paragraphs = [
            _render_formation(formation, index, self.hypotheses)
            for index, formation in enumerate(basis.formations)
        ]
        held_fragments = [
            item.text for item in basis.held_open_materials if item.text
        ]
        if basis.held_open_materials:
            if held_fragments:
                held_text = (
                    "Alongside these formations, this material remains held "
                    "open: {0}. It stays available without being forced into "
                    "resolution."
                ).format(_join_fragments(held_fragments))
            else:
                held_text = (
                    "Alongside these formations, additional relational "
                    "effects remain held open without being forced into "
                    "resolution."
                )
            paragraphs.append(held_text)
        paragraphs.append(
            "This orientation is temporary: it can change as these relations "
            "and the conditions around them change."
        )
        return "\n\n".join(item for item in paragraphs if item)


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
        # The core deliberately makes no semantic exclusion. Material that is
        # not participating in this temporary relational component is held
        # open and remains available to later field updates.
        excluded_stream_ids=[],
    )
    if state.latest_cut() is None or state.latest_cut().cut_id != cut.cut_id:
        state.cuts.append(cut)
    state.current_cut_id = cut.cut_id
    state.current_candidate_id = None
    state.current_evaluation_id = None
    state.current_articulation_id = None
    state.articulation_eligible = True
    return cut


def _clean_text(text: str) -> str:
    return " ".join(str(text or "").split()).strip()


def _descriptive_fragment(text: str, limit: int = 180) -> str:
    """Keep material present without returning a user's question as a quote."""
    text = _clean_text(text)
    was_question = text.endswith("?")
    text = text.rstrip("?.! ")
    if was_question:
        text = re.sub(
            r"^(?:how|what|why|when|where|who)\s+"
            r"(?:can|could|should|would|do|does|did|is|are|am|"
            r"might|may|will)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"^(?:can|could|should|would|do|does|did|is|are|am|"
            r"might|may|will)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
    if text and text[0].isupper() and not text[:2].isupper():
        text = text[0].lower() + text[1:]
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def _stream_source_ids(stream: Stream) -> List[str]:
    source_ids = set()
    keys = (
        ("source_stream_ids",)
        if stream.payload.get("source_stream_ids")
        else ("included_stream_ids",)
    )
    for key in keys:
        values = stream.payload.get(key, [])
        if isinstance(values, (list, tuple, set)):
            source_ids.update(str(item) for item in values)
    return sorted(source_ids)


def _flatten_material_lineage(
    state: FieldState,
    basis: ArticulationBasis,
) -> List[str]:
    """Return original included material without recursive mediator lineage."""
    lineage = set()
    frontier = list(basis.included_stream_ids)
    visited = set()
    while frontier:
        stream_id = frontier.pop()
        if stream_id in visited:
            continue
        visited.add(stream_id)
        stream = state.stream(stream_id)
        if stream is None:
            continue
        if stream.kind == "apparatus":
            continue
        if stream.kind in {"articulation", "play_variation"}:
            frontier.extend(_stream_source_ids(stream))
            continue
        lineage.add(stream.stream_id)
    return sorted(lineage)


def _stream_material(stream: Stream) -> ArticulationMaterial:
    # Prior articulations return through lineage and relational effects. Their
    # complete accepted text remains in append-only history, not in the next
    # expression basis.
    if stream.kind in {"apparatus", "articulation", "play_variation"}:
        text = ""
    else:
        text = str(
            stream.payload.get("text")
            or stream.payload.get("label")
            or stream.payload.get("title")
            or stream.payload.get("summary")
            or stream.payload.get("description")
            or ""
        )
    return ArticulationMaterial(
        stream_id=stream.stream_id,
        kind=stream.kind,
        text=_descriptive_fragment(text),
        source_stream_ids=_stream_source_ids(stream),
        provenance=deepcopy(stream.provenance),
    )


def build_articulation_basis(
    state: FieldState,
    cut: Optional[ProvisionalCut] = None,
) -> Optional[ArticulationBasis]:
    """Preserve every current formation without ranking its material."""
    cut = cut or state.current_cut()
    if cut is None or state.current_cut_id != cut.cut_id:
        return None

    formations: List[ArticulationFormation] = []
    for phenomenon_id in cut.phenomenon_ids:
        phenomenon = state.phenomenon(phenomenon_id)
        if phenomenon is None:
            continue
        streams = [
            state.stream(stream_id) for stream_id in phenomenon.stream_ids
        ]
        streams = [item for item in streams if item is not None]
        materials = [_stream_material(item) for item in streams]
        formations.append(
            ArticulationFormation(
                phenomenon_id=phenomenon.phenomenon_id,
                materials=materials,
                relation_ids=list(phenomenon.relation_ids),
                qualities=dict(phenomenon.qualities),
                apparatus_stream_ids=[
                    item.stream_id
                    for item in streams
                    if item.kind == "apparatus"
                ],
                prior_articulation_ids=[
                    str(item.payload.get("articulation_id", ""))
                    for item in streams
                    if item.kind == "articulation"
                    and item.payload.get("articulation_id")
                ],
                play_variation_ids=[
                    item.stream_id
                    for item in streams
                    if item.kind == "play_variation"
                ],
            )
        )

    held_open = [
        state.stream(stream_id) for stream_id in cut.held_open_stream_ids
    ]
    return ArticulationBasis(
        cut_id=cut.cut_id,
        apparatus_id=cut.apparatus_id,
        formations=formations,
        held_open_materials=[
            _stream_material(item)
            for item in held_open
            if item is not None
        ],
        included_stream_ids=list(cut.included_stream_ids),
        held_open_stream_ids=list(cut.held_open_stream_ids),
        relation_ids=list(cut.relation_ids),
    )


def _join_fragments(fragments: Sequence[str]) -> str:
    fragments = [item for item in fragments if item]
    if not fragments:
        return ""
    if len(fragments) == 1:
        return fragments[0]
    if len(fragments) == 2:
        return "{0}; and {1}".format(fragments[0], fragments[1])
    return "{0}; and {1}".format("; ".join(fragments[:-1]), fragments[-1])


def _formation_quality_text(
    formation: ArticulationFormation,
    hypotheses: RuntimeHypotheses,
) -> str:
    floor = hypotheses.articulation_quality_signal_floor
    resonance = formation.qualities.get("resonance", 0.0)
    difference = formation.qualities.get("difference", 0.0)
    interference = formation.qualities.get("interference", 0.0)
    if resonance >= floor and difference >= floor:
        return (
            "Shared pattern and difference remain active together, so neither "
            "has to absorb the other."
        )
    if interference >= floor or difference >= floor:
        return (
            "Difference remains active within the relation without being "
            "treated as a problem to resolve."
        )
    if resonance >= floor:
        return (
            "A shared pattern is perceptible while the account remains open "
            "to revision."
        )
    return "The relation remains tentative and available to change."


def _render_formation(
    formation: ArticulationFormation,
    index: int,
    hypotheses: RuntimeHypotheses,
) -> str:
    label = "One formation" if index == 0 else "Another formation"
    fragments = [
        item.text for item in formation.materials if item.text
    ]
    if fragments:
        opening = "{0} brings these strands into relation: {1}.".format(
            label,
            _join_fragments(fragments),
        )
    else:
        opening = (
            "{0} remains perceptible through relational effects that do not "
            "need to be restated as source material."
        ).format(label)

    sentences = [opening, _formation_quality_text(formation, hypotheses)]
    if formation.apparatus_stream_ids:
        sentences.append(
            "The conditions of this exchange participate in how the relation "
            "can appear."
        )
    if formation.prior_articulation_ids:
        sentences.append(
            "What has already been articulated is present through its effects "
            "without being repeated as evidence."
        )
    if formation.play_variation_ids:
        sentences.append(
            "A possible reconfiguration also remains active within this "
            "formation."
        )
    return " ".join(sentences)


def _validated_rendered_text(value: object) -> str:
    if not isinstance(value, str):
        raise ArticulationRendererError(
            "articulation renderer must return text"
        )
    if not value.strip():
        raise ArticulationRendererError(
            "articulation renderer returned empty text"
        )
    if len(value) > MAX_RENDERED_ARTICULATION_CHARS:
        raise ArticulationRendererError(
            "articulation renderer text exceeds {0} characters".format(
                MAX_RENDERED_ARTICULATION_CHARS
            )
        )
    if any(
        (
            character != "\n"
            and (
                ord(character) < 0x20
                or 0x7F <= ord(character) <= 0x9F
                or 0xD800 <= ord(character) <= 0xDFFF
            )
        )
        for character in value
    ):
        raise ArticulationRendererError(
            "articulation renderer text contains unsafe control characters"
        )
    return value


def form_articulation_candidate(
    state: FieldState,
    cut: Optional[ProvisionalCut] = None,
    hypotheses: Optional[RuntimeHypotheses] = None,
    renderer: Optional[ArticulationRenderer] = None,
) -> Optional[ArticulationCandidate]:
    hypotheses = hypotheses or RuntimeHypotheses()
    basis = build_articulation_basis(state, cut)
    if basis is None or not basis.formations:
        return None
    resolved_renderer = (
        renderer
        if renderer is not None
        else NativeTemplateArticulationRenderer(hypotheses)
    )
    render = getattr(resolved_renderer, "render", None)
    if not callable(render):
        raise TypeError("renderer must provide a callable render method")
    text = _validated_rendered_text(render(deepcopy(basis)))
    candidate_id = _stable_id(
        "candidate",
        state.field_id,
        basis.cut_id,
        text,
    )
    candidate = ArticulationCandidate(
        candidate_id=candidate_id,
        text=text,
        basis=basis,
        timestep=state.timestep,
    )
    if not any(
        item.candidate_id == candidate_id
        for item in state.articulation_candidates
    ):
        state.articulation_candidates.append(candidate)
    state.current_candidate_id = candidate_id
    state.current_evaluation_id = None
    state.current_articulation_id = None
    return candidate


def _pattern_evidence(
    text: str,
    patterns: Iterable[str],
) -> List[str]:
    evidence = []
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match is not None:
            evidence.append("candidate language includes '{0}'".format(match.group(0)))
    return evidence


def _signal_intensity(
    base: float,
    evidence_count: int,
    hypotheses: RuntimeHypotheses,
) -> float:
    return clamp01(
        base
        + (
            hypotheses.post_articulation_evidence_increment
            * max(0, evidence_count - 1)
        )
    )


def _question_echo_evidence(
    state: FieldState,
    candidate: ArticulationCandidate,
) -> List[str]:
    normalized_candidate = _clean_text(candidate.text).lower()
    evidence = []
    for stream_id in candidate.basis.included_stream_ids:
        stream = state.stream(stream_id)
        if stream is None or stream.kind != "user_input":
            continue
        text = _clean_text(str(stream.payload.get("text", "")))
        if text.endswith("?") and text.lower() in normalized_candidate:
            evidence.append(
                "candidate repeats a user question instead of forming a relation"
            )
    return evidence


def evaluate_articulation_candidate(
    state: FieldState,
    candidate: ArticulationCandidate,
    hypotheses: Optional[RuntimeHypotheses] = None,
) -> ArticulationEvaluation:
    """Evaluate expression after formation and before acceptance or reinsertion."""
    hypotheses = hypotheses or RuntimeHypotheses()
    text = candidate.text
    signals: List[DriftSignal] = []

    moralization = _pattern_evidence(
        text,
        MORALIZATION_PATTERNS + CLOSURE_PATTERNS,
    )
    if candidate.basis.held_open_materials and "held open" not in text.lower():
        moralization.append(
            "candidate closes material that the provisional boundary holds open"
        )
    if moralization:
        intensity = _signal_intensity(
            hypotheses.post_articulation_moralization_intensity,
            len(moralization),
            hypotheses,
        )
        if intensity >= hypotheses.post_articulation_drift_threshold:
            signals.append(
                DriftSignal(
                    kind=DriftKind.MORALIZATION,
                    intensity=intensity,
                    evidence=moralization,
                    detected_at=state.timestep,
                    source="post_articulation_evaluation",
                )
            )

    narrative = _pattern_evidence(text, NARRATIVE_DOMINANCE_PATTERNS)
    formation_count = len(
        re.findall(
            r"(?m)^(?:One|Another) formation\b",
            text,
        )
    )
    if formation_count < len(candidate.basis.formations):
        narrative.append(
            "candidate does not keep every current formation perceptible"
        )
    narrative.extend(_question_echo_evidence(state, candidate))
    if narrative:
        intensity = _signal_intensity(
            hypotheses.post_articulation_narrative_intensity,
            len(narrative),
            hypotheses,
        )
        if intensity >= hypotheses.post_articulation_drift_threshold:
            signals.append(
                DriftSignal(
                    kind=DriftKind.NARRATIVE_DOMINANCE,
                    intensity=intensity,
                    evidence=narrative,
                    detected_at=state.timestep,
                    source="post_articulation_evaluation",
                )
            )

    procedural = _pattern_evidence(text, PROCEDURAL_PATTERNS)
    if procedural:
        intensity = _signal_intensity(
            hypotheses.post_articulation_procedural_intensity,
            len(procedural),
            hypotheses,
        )
        if intensity >= hypotheses.post_articulation_drift_threshold:
            signals.append(
                DriftSignal(
                    kind=DriftKind.PROCEDURAL_BYPASS,
                    intensity=intensity,
                    evidence=procedural,
                    detected_at=state.timestep,
                    source="post_articulation_evaluation",
                )
            )

    evidence = [
        item
        for signal in signals
        for item in signal.evidence
    ]
    evaluation_id = _stable_id(
        "evaluation",
        candidate.candidate_id,
        *(signal.kind.value for signal in signals),
    )
    evaluation = ArticulationEvaluation(
        evaluation_id=evaluation_id,
        candidate_id=candidate.candidate_id,
        accepted=not signals,
        drift_signals=signals,
        evidence=evidence,
        timestep=state.timestep,
    )
    if not any(
        item.evaluation_id == evaluation_id
        for item in state.articulation_evaluations
    ):
        state.articulation_evaluations.append(evaluation)
    state.current_evaluation_id = evaluation_id
    if signals:
        state.active_drifts = deepcopy(signals)
        state.articulation_eligible = False
    return evaluation


def accept_articulation(
    state: FieldState,
    candidate: ArticulationCandidate,
    evaluation: ArticulationEvaluation,
) -> Optional[Articulation]:
    if not evaluation.accepted:
        return None
    if evaluation.candidate_id != candidate.candidate_id:
        return None
    if state.current_cut_id != candidate.basis.cut_id:
        return None
    articulation_id = _stable_id(
        "articulation",
        state.field_id,
        candidate.candidate_id,
        evaluation.evaluation_id,
    )
    articulation = Articulation(
        articulation_id=articulation_id,
        candidate_id=candidate.candidate_id,
        evaluation_id=evaluation.evaluation_id,
        text=candidate.text,
        cut_id=candidate.basis.cut_id,
        phenomenon_ids=[
            item.phenomenon_id for item in candidate.basis.formations
        ],
        included_stream_ids=list(candidate.basis.included_stream_ids),
        held_open_stream_ids=list(candidate.basis.held_open_stream_ids),
        relation_ids=list(candidate.basis.relation_ids),
        lineage_stream_ids=_flatten_material_lineage(
            state,
            candidate.basis,
        ),
        timestep=state.timestep,
    )
    if not any(
        item.articulation_id == articulation_id
        for item in state.articulations
    ):
        state.articulations.append(articulation)
    state.current_articulation_id = articulation_id
    return articulation


def articulate(
    state: FieldState,
    cut: Optional[ProvisionalCut] = None,
    hypotheses: Optional[RuntimeHypotheses] = None,
) -> Optional[Articulation]:
    """Compatibility movement for direct, accepted native articulation."""
    hypotheses = hypotheses or RuntimeHypotheses()
    candidate = form_articulation_candidate(state, cut, hypotheses)
    if candidate is None:
        return None
    evaluation = evaluate_articulation_candidate(
        state,
        candidate,
        hypotheses,
    )
    return accept_articulation(state, candidate, evaluation)


def reinsert_articulation(
    state: FieldState,
    articulation: Articulation,
    hypotheses: Optional[RuntimeHypotheses] = None,
) -> str:
    """Reinsert one accepted articulation through lineage, not recursive text."""
    hypotheses = hypotheses or RuntimeHypotheses()
    if not any(
        item.articulation_id == articulation.articulation_id
        for item in state.articulations
    ):
        raise ValueError("Only accepted articulations can be reinserted")
    stream_id = "stream:{0}".format(articulation.articulation_id)
    if state.stream(stream_id) is not None:
        return stream_id

    state.streams.append(
        Stream(
            stream_id=stream_id,
            kind="articulation",
            payload={
                "articulation_id": articulation.articulation_id,
                "candidate_id": articulation.candidate_id,
                "evaluation_id": articulation.evaluation_id,
                "cut_id": articulation.cut_id,
                "phenomenon_ids": list(articulation.phenomenon_ids),
                "included_stream_ids": list(
                    articulation.included_stream_ids
                ),
                "source_stream_ids": list(
                    articulation.lineage_stream_ids
                ),
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
