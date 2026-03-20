from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

try:
    from cbra.corpus import load_manifest
except ImportError:
    from corpus import load_manifest

try:
    from cbra.store import get_field, update_field
except ImportError:
    try:
        from store import get_field, update_field
    except ImportError:
        get_field = None
        update_field = None

try:
    from cbra.compression import compress_selected_elements
except ImportError:
    from compression import compress_selected_elements


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
BASE_DIR = Path(__file__).parent
CORPUS_DIR = BASE_DIR / "corpus" if (BASE_DIR / "corpus").exists() else BASE_DIR
MAX_CANONICAL_SNIPPETS = 6
MAX_REINTEGRATION_PASSES = 1

DRIFT_TARGETS = {
    "ontological_drift": "Field Entry",
    "interpretive_compression": "Noticing",
    "capacity_collapse": "Noticing",
    "narrative_dominance": "Noticing",
    "moralization_drift": "Noticing",
    "procedural_bypass": "Field Entry",
}

BODY_TERMS = ["body", "somatic", "pain", "hurt", "tired", "fatigue", "sleep", "breath", "shaking", "anxious"]
AFFECT_TERMS = ["angry", "sad", "worried", "anxious", "irritated", "overwhelmed", "stuck", "uneasy", "excited"]
POWER_TERMS = ["power", "authority", "control", "boss", "state", "court", "police", "company", "board", "system"]
MATERIAL_TERMS = ["money", "bills", "mortgage", "battery", "engine", "radiator", "truck", "fuel", "document", "file", "calendar", "email", "api", "build"]
TIME_TERMS = ["today", "tonight", "this week", "this weekend", "now", "soon", "deadline", "urgent", "late"]
CONFLICT_TERMS = ["fight", "argue", "angry", "misaligned", "conflict", "yelled", "walked out"]
ROLE_TERMS = [
    "mother", "father", "mom", "dad", "wife", "husband", "partner", "friend", "child", "children",
    "family", "doctor", "therapist", "teacher", "student", "boss", "coworker", "neighbor", "landlord",
    "police", "court", "state", "school", "hospital", "company", "system", "board", "team", "community",
    "truck", "engine", "battery", "radiator", "fuel", "pump", "calendar", "email", "runtime", "build", "engine",
]


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


@lru_cache(maxsize=1)
def _require_api_key() -> str:
    api_key = (os.getenv("OPENAI_API_KEY", "") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return api_key


@lru_cache(maxsize=1)
def _corpus_dir() -> Path:
    if not CORPUS_DIR.exists():
        raise FileNotFoundError("CBRA corpus directory not found")
    manifest = CORPUS_DIR / "CBRA_Corpus_Index.md"
    if not manifest.exists():
        raise FileNotFoundError("CBRA_Corpus_Index.md not found")
    return CORPUS_DIR


@lru_cache(maxsize=1)
def _canonical_paths() -> Tuple[Path, ...]:
    corpus_dir = _corpus_dir()
    filenames = load_manifest(corpus_dir)
    if not filenames:
        raise RuntimeError("No active canonical files found in CBRA_Corpus_Index.md")
    paths: List[Path] = []
    for name in filenames:
        path = corpus_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Canonical file missing: {name}")
        paths.append(path)
    return tuple(paths)


@lru_cache(maxsize=1)
def _canonical_filenames() -> Tuple[str, ...]:
    return tuple(path.name for path in _canonical_paths())


@lru_cache(maxsize=1)
def _runtime_grounding() -> str:
    parts: List[str] = []
    for path in _canonical_paths():
        parts.append(f"FILE: {path.name}\n{path.read_text(encoding='utf-8', errors='replace').strip()}")
    return "\n\n".join(parts)


@lru_cache(maxsize=1)
def _canonical_chunks() -> Tuple[Dict[str, Any], ...]:
    chunks: List[Dict[str, Any]] = []
    for path in _canonical_paths():
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        heading = "Document"
        buffer: List[Tuple[int, str]] = []

        def flush() -> None:
            nonlocal buffer
            if not buffer:
                return
            text = " ".join(item[1].strip() for item in buffer).strip()
            if text:
                chunks.append(
                    {
                        "file": path.name,
                        "heading": heading,
                        "start_line": buffer[0][0],
                        "end_line": buffer[-1][0],
                        "text": text,
                    }
                )
            buffer = []

        for idx, raw in enumerate(lines, start=1):
            stripped = raw.strip()
            if stripped.startswith("#"):
                flush()
                heading = stripped.lstrip("#").strip() or heading
                continue
            if not stripped:
                flush()
                continue
            buffer.append((idx, raw))
        flush()
    return tuple(chunks)


WORD_RE = re.compile(r"[a-z0-9][a-z0-9_\-']*")


@lru_cache(maxsize=1)
def _stopwords() -> set:
    return {
        "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by", "can", "could",
        "did", "do", "does", "for", "from", "had", "has", "have", "how", "i", "if", "in", "into",
        "is", "it", "its", "just", "me", "my", "no", "not", "of", "on", "or", "our", "so", "that",
        "the", "their", "them", "there", "they", "this", "to", "up", "us", "was", "we", "what", "when",
        "where", "which", "who", "why", "will", "with", "you", "your", "yours",
    }


def _normalize_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "")
    return value.replace("–", "-").replace("—", "-").replace("−", "-")


def _tokenize(text: str) -> List[str]:
    return [t for t in WORD_RE.findall(_normalize_text(text).lower()) if t not in _stopwords()]


def _truncate(value: Any, max_chars: int = 280) -> str:
    text = str(value or "").strip()
    return text if len(text) <= max_chars else text[:max_chars].rstrip()


def _safe_dump(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return dict(obj)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()  # type: ignore[no-any-return]
    if hasattr(obj, "dict"):
        return obj.dict()  # type: ignore[no-any-return]
    return dict(obj)


def _dedupe(items: List[Any]) -> List[Any]:
    out: List[Any] = []
    seen = set()
    for item in items:
        key = json.dumps(item, sort_keys=True, default=str) if isinstance(item, (dict, list)) else str(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _contains_any(text: str, terms: List[str]) -> List[str]:
    lower = _normalize_text(text).lower()
    return [term for term in terms if term in lower]


def _extract_turn_conditions(user_text: str, sources: Optional[List[str]] = None) -> Dict[str, Any]:
    lower = _normalize_text(user_text).lower()

    hard_correction_terms = [
        "i am correcting you",
        "you misunderstood",
        "that is not what i asked",
        "you are answering a different question",
        "stop explaining",
        "don't explain cbra",
        "dont explain cbra",
        "don't explain the framework",
        "dont explain the framework",
        "answer from it",
        "without citing the framework",
        "you keep",
        "that is not what you did",
    ]
    action_terms = [
        "what should i do",
        "next step",
        "one step",
        "what action",
        "what can i do",
        "give me options",
        "give me three options",
        "practical",
        "concrete",
    ]
    conceptual_terms = [
        "difference between",
        "meaning of",
        "define",
        "definition of",
        "clarify",
        "conceptual",
        "diffraction",
        "entanglement",
        "intra-action",
        "apparatus",
        "agential cut",
        "relational emergence",
    ]
    conceptual_question_terms = [
        "what is diffraction",
        "what is entanglement",
        "what is intra-action",
        "what is an apparatus",
        "what is apparatus",
        "what is agential cut",
        "what does that mean",
        "what does this mean",
    ]
    noticing_terms = [
        "something is off",
        "feels off",
        "circling around",
        "stuck",
        "misaligned",
        "uneasy",
        "can't quite say",
        "cannot quite say",
    ]
    current_terms = [
        "today",
        "tonight",
        "this week",
        "this weekend",
        "right now",
        "latest",
        "current",
        "recent",
        "schedule",
        "price",
        "news",
        "happening",
        "now",
    ]
    direct_terms = [
        "brief",
        "short",
        "plain",
        "direct",
        "simple",
        "ordinary",
        "plainly",
        "one sentence",
        "one short sentence",
    ]
    list_terms = ["bullet", "bullets", "list", "outline", "steps"]
    contrast_terms = [" but ", " however ", " although ", " at the same time ", " on the one hand "]

    exact_quantity: Optional[int] = None
    match = re.search(r"\b(\d{1,2})\s+(?:options|steps|sentences|bullets|points|things)\b", lower)
    if match:
        exact_quantity = int(match.group(1))
    elif "one sentence" in lower or "one short sentence" in lower or "one step" in lower:
        exact_quantity = 1

    asks_conceptual = (
        any(term in lower for term in conceptual_terms)
        or any(term in lower for term in conceptual_question_terms)
        or bool(re.search(r"\bwhat does .+ mean\b", lower))
    )

    return {
        "correction": any(term in lower for term in hard_correction_terms),
        "asks_action": any(term in lower for term in action_terms),
        "asks_conceptual": asks_conceptual,
        "asks_noticing": any(term in lower for term in noticing_terms),
        "asks_current_factual": any(term in lower for term in current_terms),
        "asks_plain_surface": any(term in lower for term in direct_terms),
        "allow_list_format": any(term in lower for term in list_terms),
        "exact_quantity": exact_quantity,
        "has_attachment": "attachment (" in lower or "[attached:" in lower,
        "has_competing_conditions": any(term in lower for term in contrast_terms),
        "source_count": len(sources or []),
        "user_length": len(user_text or ""),
    }


def _load_prior_field(field_id: Optional[str]) -> Dict[str, Any]:
    if not field_id or get_field is None:
        return {}
    return _safe_dump(get_field(field_id))



def _extract_actors(user_text: str, retrieved: List[Dict[str, Any]]) -> List[str]:
    lower = _normalize_text(user_text).lower()
    actors: List[str] = ["user"]

    abstract_nonactors = {
        "answer",
        "when",
        "drift",
        "meaning",
        "input",
        "field",
        "entry",
        "noticing",
        "relational",
        "framing",
        "articulation",
        "action",
        "status",
        "version",
        "architecture",
        "runtime",
        "enforcement",
        "location",
        "build",
        "purpose",
        "creative",
        "becoming",
    }
    interrogative_nonactors = {"what", "why", "how", "when", "where", "who", "which"}
    nonactor_phrases = {
        "creative becoming",
        "field entry",
        "relational framing",
        "situated relevance selection",
        "action orientation",
        "runtime enforcement location",
        "canonical drift detection",
        "architecture version",
    }
    prompt_verbs = {
        "answer",
        "tell",
        "give",
        "show",
        "write",
        "explain",
        "clarify",
        "define",
        "list",
    }

    if re.search(r"\b(you|your)\b", lower):
        actors.append("assistant")

    for term in ROLE_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", lower):
            if term not in abstract_nonactors and term not in interrogative_nonactors:
                actors.append(term)

    for match in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", user_text or ""):
        phrase = match.group(1).strip()
        phrase_lower = phrase.lower()
        if phrase_lower in nonactor_phrases:
            continue
        if phrase.split() and phrase.split()[0].lower() in interrogative_nonactors:
            continue
        if all(token.lower() in abstract_nonactors or token.lower() in interrogative_nonactors for token in phrase.split()):
            continue
        actors.append(phrase)

    sentences = re.split(r"(?<=[.!?])\s+", user_text or "")
    for sentence in sentences:
        words = re.findall(r"\b[A-Z][a-z]+\b", sentence)
        if not words:
            continue

        first = words[0]
        if (
            first.lower() not in abstract_nonactors
            and first.lower() not in interrogative_nonactors
            and first.lower() not in prompt_verbs
            and re.search(rf"^\s*{re.escape(first)}\s+(said|walked|told|left|called|came|went|is|was)\b", sentence)
        ):
            actors.append(first)

        for word in words[1:]:
            if word.lower() in abstract_nonactors or word.lower() in interrogative_nonactors:
                continue
            actors.append(word)

    return _dedupe([actor for actor in actors if actor])[:10]


def _extract_material_conditions(user_text: str, prior_field: Dict[str, Any], explicit_sources: List[str]) -> List[str]:
    conditions = _contains_any(user_text, MATERIAL_TERMS)
    if explicit_sources:
        conditions.append(f"explicit source material provided ({len(explicit_sources)})")
    if prior_field:
        conditions.append("prior field artifact available")
    return _dedupe(conditions)[:8]


def _extract_power_gradients(user_text: str) -> List[str]:
    gradients = _contains_any(user_text, POWER_TERMS)
    lower = _normalize_text(user_text).lower()
    if re.search(r"\bi\b", lower) and re.search(r"\byou\b", lower):
        gradients.append("assistant-user instruction relation is active")
    return _dedupe(gradients)[:6]


def _extract_temporal_pressures(user_text: str, prior_field: Dict[str, Any]) -> List[str]:
    pressures = _contains_any(user_text, TIME_TERMS)
    updated = prior_field.get("updated_at")
    if updated:
        pressures.append(f"prior field updated at {updated}")
    return _dedupe(pressures)[:5]


def _extract_stakes(user_text: str, prior_field: Dict[str, Any]) -> List[str]:
    lower = _normalize_text(user_text).lower()
    stakes: List[str] = []

    if _contains_any(user_text, ["safe", "unsafe", "danger", "harm", "risk"]):
        stakes.append("safety")
    if _contains_any(user_text, ["money", "income", "mortgage", "bills", "cost", "price"]):
        stakes.append("money")
    if _contains_any(user_text, ["relationship", "wife", "partner", "friend", "family", "student", "board"]):
        stakes.append("relational")
    if _contains_any(user_text, ["job", "work", "build", "project", "engine", "repo"]):
        stakes.append("work")
    if _contains_any(user_text, TIME_TERMS):
        stakes.append("timing")
    if "i am correcting you" in lower or "you misunderstood" in lower or "that is not what i asked" in lower:
        stakes.append("correction alignment")
    if isinstance(prior_field.get("selected_elements"), list) and prior_field.get("selected_elements"):
        stakes.append("prior field selections remain live")
    if "what should i do" in lower or "next step" in lower:
        stakes.append("movement")

    return _dedupe(stakes)[:8]


def _extract_constraints(user_text: str, turn_conditions: Dict[str, Any], explicit_sources: List[str], prior_field: Dict[str, Any]) -> List[str]:
    constraints: List[str] = []
    if turn_conditions["correction"]:
        constraints.append("user correction is a primary field signal")
    if turn_conditions["asks_plain_surface"]:
        constraints.append("articulation must stay plain and direct")
    if turn_conditions["exact_quantity"]:
        constraints.append(f"respect requested quantity: {turn_conditions['exact_quantity']}")
    if turn_conditions["asks_current_factual"]:
        constraints.append("use available sources only for current claims")
    if explicit_sources:
        constraints.append("user-provided sources are present in the field")
    prior_notes = prior_field.get("notes") if isinstance(prior_field.get("notes"), dict) else {}
    if prior_notes.get("drift_detected"):
        constraints.append("prior cycle drift remains relevant to reinsertion")
    return constraints[:8]


def _extract_history(user_text: str, prior_field: Dict[str, Any]) -> List[str]:
    signals: List[str] = []
    if _contains_any(user_text, ["before", "again", "still", "used to", "history", "last", "recently"]):
        signals.append("user turn references prior or ongoing conditions")
    if isinstance(prior_field.get("notes"), dict) and prior_field.get("notes", {}).get("last_user_input"):
        signals.append("prior field state is available for reinsertion")
    return signals[:5]


def _assemble_field(user_text: str, prior_field: Dict[str, Any], retrieved: List[Dict[str, Any]], explicit_sources: Optional[List[str]], turn_conditions: Dict[str, Any]) -> Dict[str, Any]:
    explicit = explicit_sources or []
    carryover_terms: List[str] = []
    prior_notes = prior_field.get("notes") if isinstance(prior_field.get("notes"), dict) else {}
    for section in [prior_field.get("selected_elements", []), prior_field.get("field_signature", {}).get("stakes", []), prior_notes.get("carryover_terms", [])]:
        if isinstance(section, list):
            for item in section:
                carryover_terms.append(item.get("label", "") if isinstance(item, dict) else str(item))

    discourse = _dedupe(_contains_any(user_text, ["narrative", "language", "discourse", "story", "frame", "theory", "plain language"]))[:6]
    bodies = _dedupe(_contains_any(user_text, BODY_TERMS))[:6]
    power_gradients = _extract_power_gradients(user_text)
    material_conditions = _extract_material_conditions(user_text, prior_field, explicit)
    temporal_pressures = _extract_temporal_pressures(user_text, prior_field)
    stakes = _extract_stakes(user_text, prior_field)
    constraints = _extract_constraints(user_text, turn_conditions, explicit, prior_field)

    return {
        "user_text": user_text,
        "prior_field": prior_field,
        "turn_conditions": turn_conditions,
        "carryover_terms": [term for term in carryover_terms if term],
        "retrieved_material": retrieved,
        "constructed_field": {
            "actors": _extract_actors(user_text, retrieved),
            "bodies": bodies,
            "discourse": discourse,
            "history": _extract_history(user_text, prior_field),
            "material_conditions": material_conditions,
            "power_gradients": power_gradients,
            "temporal_pressures": temporal_pressures,
            "constraints": constraints,
            "stakes": stakes,
            "pressures": _dedupe(_contains_any(user_text, CONFLICT_TERMS + TIME_TERMS + MATERIAL_TERMS))[:8],
            "sources": {
                "canonical": [
                    {
                        "file": hit["file"],
                        "heading": hit["heading"],
                        "start_line": hit["start_line"],
                        "end_line": hit["end_line"],
                        "text": hit["text"],
                    }
                    for hit in retrieved
                ],
                "explicit": explicit,
            },
            "prior_field_carryover": {
                "selected_elements": prior_field.get("selected_elements", []),
                "notes": prior_notes,
            },
        },
    }


def _retrieve_canonical_material(user_text: str, carryover_terms: List[str], turn_conditions: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    query_terms = _dedupe(_tokenize(user_text) + _tokenize(" ".join(carryover_terms)))
    selected: List[Tuple[float, Dict[str, Any]]] = []
    for chunk in _canonical_chunks():
        chunk_terms = _tokenize(chunk["text"])
        overlap = sum(1 for term in query_terms if term in chunk_terms)
        if not overlap:
            lowered = chunk["text"].lower()
            if turn_conditions["correction"] and "drift" in lowered:
                overlap = 1
            elif turn_conditions["asks_action"] and "action" in lowered:
                overlap = 1
            elif turn_conditions["asks_current_factual"] and "available" in lowered:
                overlap = 1
        if not overlap:
            continue
        score = float(overlap)
        heading = chunk["heading"].lower()
        if "field" in heading or "noticing" in heading:
            score += 0.4
        if "drift" in heading:
            score += 0.5
        selected.append((score, chunk))
    selected.sort(key=lambda item: item[0], reverse=True)

    hits: List[Dict[str, Any]] = []
    citations: List[str] = []
    seen = set()
    for _, chunk in selected:
        key = (chunk["file"], chunk["start_line"], chunk["end_line"])
        if key in seen:
            continue
        seen.add(key)
        hits.append(chunk)
        citations.append(f"{chunk['file']} L{chunk['start_line']}-L{chunk['end_line']}")
        if len(hits) >= MAX_CANONICAL_SNIPPETS:
            break
    return hits, citations


def _build_field_signature(field_context: Dict[str, Any]) -> Dict[str, Any]:
    cf = field_context["constructed_field"]
    tc = field_context["turn_conditions"]
    return {
        "relational_conditions": _dedupe(cf["actors"] + cf["power_gradients"])[:10],
        "stakes": cf["stakes"][:8],
        "constraints": cf["constraints"][:8],
        "pressures": _dedupe(cf["pressures"] + cf["temporal_pressures"])[:8],
        "timing": cf["temporal_pressures"][:6],
        "material_conditions": cf["material_conditions"][:8],
        "power_gradients": cf["power_gradients"][:6],
        "prior_field_carryover": cf["prior_field_carryover"],
        "verification_mode": "available_sources_only" if tc["asks_current_factual"] else "not_applicable",
        "source_frame": {
            "canonical_count": len(cf["sources"]["canonical"]),
            "explicit_count": len(cf["sources"]["explicit"]),
        },
    }


def _build_noticing_register(field_context: Dict[str, Any]) -> Dict[str, Any]:
    user_text = field_context["user_text"]
    lower = _normalize_text(user_text).lower()
    affective = _contains_any(user_text, AFFECT_TERMS)
    relational: List[str] = []
    narrative: List[str] = []
    environmental: List[str] = []
    latency_markers: List[str] = []

    if field_context["turn_conditions"]["correction"]:
        relational.append("user is correcting runtime behavior in the current turn")
    if re.search(r"\bi\b", lower):
        relational.append("user self-positioning is present")
    if re.search(r"\byou\b", lower):
        relational.append("assistant is directly implicated in the current field")
    if any(word in lower for word in ["story", "narrative", "because", "after", "then"]):
        narrative.append("narrative sequencing is present in the turn")
    if any(word in lower for word in ["always", "never", "everyone", "nobody"]):
        narrative.append("globalizing language is present")
    if field_context["turn_conditions"]["has_attachment"]:
        environmental.append("attachment material entered the field")
    if field_context["turn_conditions"]["asks_current_factual"]:
        environmental.append("current-fact pressure is active")
    environmental.extend(field_context["constructed_field"]["material_conditions"][:3])
    for marker in ["maybe", "not sure", "can't quite", "cannot quite", "circling", "still"]:
        if marker in lower:
            latency_markers.append(marker)

    return {
        "somatic": field_context["constructed_field"]["bodies"][:6],
        "affective": affective[:6],
        "relational": _dedupe(relational)[:6],
        "narrative": _dedupe(narrative + field_context["constructed_field"]["history"][:2])[:6],
        "environmental": _dedupe(environmental)[:6],
        "latency_markers": _dedupe(latency_markers)[:6],
    }


def _build_relational_map(field_context: Dict[str, Any]) -> Dict[str, Any]:
    cf = field_context["constructed_field"]
    actors: List[Dict[str, Any]] = []
    for actor in cf["actors"][:10]:
        kind = "person"
        lower = str(actor).lower()
        if lower in {"assistant", "runtime", "build", "engine"}:
            kind = "runtime"
        elif lower in {"system", "state", "company", "board", "school", "court", "hospital"}:
            kind = "institution"
        elif lower in {"truck", "engine", "battery", "radiator", "calendar", "email", "document", "file"}:
            kind = "material_or_infrastructure"
        actors.append({"name": str(actor), "kind": kind})

    relations: List[Dict[str, str]] = []
    actor_names = [item["name"] for item in actors]
    if "user" in [name.lower() for name in actor_names]:
        for actor in actor_names:
            if actor.lower() == "user":
                continue
            relations.append({"from": "user", "to": actor, "relation": "situated_with", "evidence": "co-present in current field"})
    if field_context["turn_conditions"]["correction"]:
        relations.append({"from": "user", "to": "assistant", "relation": "corrects_runtime_behavior", "evidence": "current turn requests immediate reshaping of articulation"})
    if field_context["turn_conditions"]["asks_action"]:
        relations.append({"from": "field", "to": "user", "relation": "requires_movement_visibility", "evidence": "user requested action orientation"})

    capacities: List[str] = []
    if field_context["turn_conditions"]["asks_plain_surface"]:
        capacities.append("plain articulation can stabilize coherence")
    if field_context["turn_conditions"]["asks_action"]:
        capacities.append("next-step visibility is requested")
    if cf["prior_field_carryover"].get("selected_elements"):
        capacities.append("prior field selections can support reinsertion")

    consequences = [f"movement will affect {stake}" for stake in cf["stakes"][:5]]

    return {
        "actors": actors,
        "relations": relations[:10],
        "constraints": cf["constraints"][:8],
        "pressures": _dedupe(cf["pressures"] + cf["temporal_pressures"])[:8],
        "capacities": _dedupe(capacities)[:6],
        "consequences": _dedupe(consequences)[:6],
        "embodied_material_conditions": _dedupe(cf["bodies"] + cf["material_conditions"])[:8],
    }


def _build_diffractive_map(field_context: Dict[str, Any]) -> Dict[str, Any]:
    cf = field_context["constructed_field"]
    lower = _normalize_text(field_context["user_text"]).lower()
    patterning: List[str] = []
    interference: List[str] = []
    exclusions: List[str] = []
    apparatus: List[str] = []
    stabilization: List[str] = []

    if cf["history"] and cf["temporal_pressures"]:
        patterning.append("history and timing are co-shaping the current field")
    if cf["power_gradients"] and cf["material_conditions"]:
        patterning.append("power and material conditions are jointly shaping what is actionable")
    if field_context["turn_conditions"]["correction"]:
        patterning.append("user correction is reconfiguring articulation conditions in real time")

    if field_context["turn_conditions"]["asks_action"] and field_context["turn_conditions"]["asks_conceptual"]:
        interference.append("the turn asks for movement and conceptual clarity at once")
    if field_context["turn_conditions"]["asks_current_factual"]:
        interference.append("specificity is requested under limited verification conditions")
    if "but" in lower or "however" in lower:
        interference.append("contrast markers indicate competing conditions in the turn")

    if not cf["power_gradients"]:
        exclusions.append("power gradients are not strongly specified in the available field")
    if not cf["bodies"]:
        exclusions.append("bodily conditions are not strongly specified in the available field")
    if field_context["turn_conditions"]["asks_current_factual"]:
        exclusions.append("fresh external verification is outside the current runtime")

    apparatus.append("active canonical corpus shapes what counts as runtime-grounded")
    if field_context["turn_conditions"]["correction"]:
        apparatus.append("user correction changes relevance and articulation thresholds immediately")
    if field_context["turn_conditions"]["has_attachment"]:
        apparatus.append("attachment ingestion widens the field through file-translated text")

    if field_context["turn_conditions"]["asks_plain_surface"]:
        stabilization.append("plain direct language supports coherence for this turn")
    if field_context["turn_conditions"]["asks_action"]:
        stabilization.append("bounded next-step vectors support movement without forced closure")
    if field_context["turn_conditions"]["asks_noticing"]:
        stabilization.append("keeping multiple live signals visible supports regulation")

    return {
        "patterning_through_difference": _dedupe(patterning)[:6],
        "interference_points": _dedupe(interference)[:6],
        "exclusions_revealed": _dedupe(exclusions)[:6],
        "apparatus_effects": _dedupe(apparatus)[:6],
        "stabilization_dynamics": _dedupe(stabilization)[:6],
    }


def _build_relevance_gradient(field_context: Dict[str, Any], field_signature: Dict[str, Any], relational_map: Dict[str, Any], diffractive_map: Dict[str, Any]) -> Dict[str, Any]:
    tc = field_context["turn_conditions"]
    selected: List[Dict[str, Any]] = []
    for stake in field_signature["stakes"][:3]:
        selected.append({"label": str(stake), "rationale": "visible stake in the current field", "stage_source": "Field Entry"})
    for constraint in relational_map["constraints"][:2]:
        selected.append({"label": str(constraint), "rationale": "constraint shaping movement", "stage_source": "Relational Framing"})
    for item in diffractive_map["interference_points"][:2]:
        selected.append({"label": str(item), "rationale": "interference point affecting what can move now", "stage_source": "Diffractive Mapping"})
    if tc["asks_current_factual"]:
        selected.append({"label": "available-sources-only honesty", "rationale": "current claims must stay inside present verification limits", "stage_source": "Situated Relevance Selection"})
    if tc["correction"]:
        selected.append({"label": "user correction reshapes articulation immediately", "rationale": "correction is active field data", "stage_source": "Situated Relevance Selection"})
    normalized = compress_selected_elements(selected)

    hold_open = diffractive_map["interference_points"][:2]
    act_on: List[str] = []
    defer: List[str] = []
    if tc["asks_action"]:
        act_on.append("surface bounded next-step visibility")
    if tc["correction"]:
        act_on.append("tighten articulation to the corrected request")
    if tc["asks_current_factual"]:
        act_on.append("state verification limit plainly")
    if tc["asks_conceptual"] and not tc["asks_action"]:
        act_on.append("clarify the concept without theory performance")
    if len(field_context["constructed_field"]["actors"]) > 5:
        defer.append("less central actors can remain backgrounded for this turn")
    if len(field_context["constructed_field"]["history"]) > 2:
        defer.append("extended history can stay available without dominating articulation")

    return {
        "selected_elements": normalized,
        "hold_open": _dedupe(hold_open)[:4],
        "act_on": _dedupe(act_on)[:4],
        "defer": _dedupe(defer)[:4],
        "why_now": _dedupe(field_signature["pressures"][:3] + field_signature["stakes"][:2])[:5],
    }


def _build_action_vector(field_context: Dict[str, Any], relevance_gradient: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tc = field_context["turn_conditions"]
    if not tc["asks_action"]:
        if tc["correction"]:
            return {"mode": "structural_orientation", "next_steps": ["respond inside the corrected request shape"], "capacity_alignment": "keep output bounded and direct", "optional": True}
        return None
    next_steps = [str(item) for item in relevance_gradient["act_on"][:2]]
    for item in relevance_gradient["selected_elements"][:2]:
        if isinstance(item, dict):
            next_steps.append(f"stay with {item.get('label', '')}")
    return {
        "mode": "requested_action",
        "next_steps": _dedupe([step for step in next_steps if step])[:3],
        "capacity_alignment": "movement remains optional and timing-sensitive",
        "optional": True,
    }


def _fallback_stage_outputs(field_context: Dict[str, Any]) -> Dict[str, Any]:
    field_signature = _build_field_signature(field_context)
    noticing_register = _build_noticing_register(field_context)
    relational_map = _build_relational_map(field_context)
    diffractive_map = _build_diffractive_map(field_context)
    relevance_gradient = _build_relevance_gradient(field_context, field_signature, relational_map, diffractive_map)
    action_vector = _build_action_vector(field_context, relevance_gradient)
    return {
        "field_signature": field_signature,
        "noticing_register": noticing_register,
        "relational_map": relational_map,
        "diffractive_map": diffractive_map,
        "relevance_gradient": relevance_gradient,
        "action_vector": action_vector,
    }


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw).strip()
        raw = re.sub(r"```$", "", raw).strip()
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(raw[start:end + 1])
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                return None
    return None


def _normalize_stage_outputs(candidate: Dict[str, Any], field_context: Dict[str, Any]) -> Dict[str, Any]:
    fallback = _fallback_stage_outputs(field_context)

    def merge_dict(candidate_dict: Any, fallback_dict: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(candidate_dict, dict):
            return fallback_dict

        merged: Dict[str, Any] = {}
        for key, fallback_value in fallback_dict.items():
            candidate_value = candidate_dict.get(key)

            if isinstance(fallback_value, dict):
                merged[key] = merge_dict(candidate_value, fallback_value)

            elif isinstance(fallback_value, list):
                if isinstance(candidate_value, list) and candidate_value:
                    merged[key] = candidate_value
                else:
                    merged[key] = fallback_value

            else:
                if candidate_value in (None, ""):
                    merged[key] = fallback_value
                else:
                    merged[key] = candidate_value

        for key, value in candidate_dict.items():
            if key not in merged:
                merged[key] = value

        return merged

    normalized = {
        "field_signature": merge_dict(candidate.get("field_signature"), fallback["field_signature"]),
        "noticing_register": merge_dict(candidate.get("noticing_register"), fallback["noticing_register"]),
        "relational_map": merge_dict(candidate.get("relational_map"), fallback["relational_map"]),
        "diffractive_map": merge_dict(candidate.get("diffractive_map"), fallback["diffractive_map"]),
        "relevance_gradient": merge_dict(candidate.get("relevance_gradient"), fallback["relevance_gradient"]),
        "action_vector": merge_dict(candidate.get("action_vector"), fallback["action_vector"]) if isinstance(fallback["action_vector"], dict) else candidate.get("action_vector") or fallback["action_vector"],
    }

    normalized["relevance_gradient"]["selected_elements"] = compress_selected_elements(
        normalized["relevance_gradient"].get("selected_elements")
    )
    return normalized


def _enrich_stage_outputs(client: OpenAI, model: str, system_identity: str, field_context: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "constructed_field": field_context["constructed_field"],
        "turn_conditions": field_context["turn_conditions"],
        "user_text": field_context["user_text"],
    }
    prompt = (
        "Build CBRA stage objects from the provided field and return JSON only.\n"
        "Required keys: field_signature, noticing_register, relational_map, diffractive_map, relevance_gradient, action_vector.\n"
        "Rules:\n"
        "- field_signature keeps stakes, constraints, pressures, timing, material_conditions, power_gradients visible\n"
        "- noticing_register stays pre-interpretive\n"
        "- relational_map includes actors, relations, constraints, pressures, capacities, consequences, embodied_material_conditions\n"
        "- diffractive_map includes patterning_through_difference, interference_points, exclusions_revealed, apparatus_effects, stabilization_dynamics\n"
        "- relevance_gradient includes selected_elements, hold_open, act_on, defer, why_now\n"
        "- action_vector remains optional, never coercive\n"
        "- user correction is a primary field signal when present\n"
        "- current-fact requests preserve available-sources-only honesty\n\n"
        f"CANONICAL_RUNTIME:\n{_runtime_grounding()}\n\n"
        f"FIELD_PAYLOAD:\n{json.dumps(payload, ensure_ascii=False)}"
    )
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_identity},
            {"role": "developer", "content": "Return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
    )
    parsed = _extract_json_object(getattr(response, "output_text", "") or "")
    if parsed is None:
        return _fallback_stage_outputs(field_context)
    return _normalize_stage_outputs(parsed, field_context)


def _detect_drift(stage_outputs: Dict[str, Any], turn_conditions: Dict[str, Any], draft_text: Optional[str] = None) -> Dict[str, Any]:
    field_signature = stage_outputs["field_signature"]
    noticing_register = stage_outputs["noticing_register"]
    relational_map = stage_outputs["relational_map"]
    diffractive_map = stage_outputs["diffractive_map"]
    relevance_gradient = stage_outputs["relevance_gradient"]

    kind: Optional[str] = None
    stage: Optional[str] = None
    notes: List[str] = []

    if not field_signature.get("stakes") or not field_signature.get("constraints"):
        kind, stage = "procedural_bypass", "Field Entry"
        notes.append("field grounding is missing stakes or constraints")

    elif not any(noticing_register.get(key) for key in ["somatic", "affective", "relational", "narrative", "environmental", "latency_markers"]):
        kind, stage = "interpretive_compression", "Noticing"
        notes.append("noticing register collapsed before expansion")

    else:
        relational_density_required = (
            turn_conditions.get("correction")
            or turn_conditions.get("asks_action")
            or turn_conditions.get("asks_noticing")
            or turn_conditions.get("asks_conceptual")
            or turn_conditions.get("has_competing_conditions")
        )

        actors = relational_map.get("actors") or []
        embodied = relational_map.get("embodied_material_conditions") or []
        pressures = relational_map.get("pressures") or []

        if relational_density_required and not actors and not embodied and not pressures:
            kind, stage = "capacity_collapse", "Noticing"
            notes.append("relational framing lost agency, conditions, and pressure under a turn that required them")

        else:
            requires_diffractive_density = (
                turn_conditions.get("asks_conceptual")
                or turn_conditions.get("asks_noticing")
                or turn_conditions.get("has_competing_conditions")
                or (turn_conditions.get("asks_action") and turn_conditions.get("asks_conceptual"))
            )

            patterning = diffractive_map.get("patterning_through_difference") or []
            interference = diffractive_map.get("interference_points") or []
            exclusions = diffractive_map.get("exclusions_revealed") or []

            if requires_diffractive_density and not patterning and not interference and not exclusions:
                kind, stage = "narrative_dominance", "Noticing"
                notes.append("diffractive mapping collapsed before difference and interference became visible")

    if draft_text:
        lower = _normalize_text(draft_text).lower()

        if any(token in lower for token in ["should", "must", "obviously", "clearly you need to"]) and not turn_conditions["asks_action"]:
            kind, stage = "moralization_drift", "Noticing"
            notes.append("articulation became corrective rather than situated")

        elif turn_conditions["asks_current_factual"] and any(token in lower for token in ["maybe", "probably", "i think"]):
            kind, stage = "procedural_bypass", "Field Entry"
            notes.append("current-fact articulation drifted beyond available verification")

        elif turn_conditions["correction"] and len(re.findall(r"[.!?]+", draft_text.strip())) > 2:
            kind, stage = "interpretive_compression", "Noticing"
            notes.append("correction signal did not sufficiently reshape articulation")

        elif any(token in lower for token in ["everyone", "nobody", "always", "never"]):
            kind, stage = "ontological_drift", "Field Entry"
            notes.append("articulation globalized beyond situated conditions")

    return {
        "drift_detected": bool(kind),
        "drift_kind": kind,
        "detected_at_stage": stage,
        "reintegration_target": DRIFT_TARGETS.get(kind) if kind else None,
        "notes": notes,
    }


def _reintegrate(field_context: Dict[str, Any], stage_outputs: Dict[str, Any], drift_signal: Dict[str, Any]) -> Dict[str, Any]:
    target = drift_signal.get("reintegration_target") or "Field Entry"
    field_context["constructed_field"]["constraints"] = _dedupe(
        list(field_context["constructed_field"].get("constraints", [])) + [f"drift reintegration via {target}"]
    )

    if target in {"Field Entry", "Noticing"}:
        return _fallback_stage_outputs(field_context)
    if target == "Relational Framing":
        stage_outputs["relational_map"] = _build_relational_map(field_context)
        stage_outputs["diffractive_map"] = _build_diffractive_map(field_context)
        stage_outputs["relevance_gradient"] = _build_relevance_gradient(field_context, stage_outputs["field_signature"], stage_outputs["relational_map"], stage_outputs["diffractive_map"])
        stage_outputs["action_vector"] = _build_action_vector(field_context, stage_outputs["relevance_gradient"])
        return stage_outputs
    if target == "Diffractive Mapping":
        stage_outputs["diffractive_map"] = _build_diffractive_map(field_context)
        stage_outputs["relevance_gradient"] = _build_relevance_gradient(field_context, stage_outputs["field_signature"], stage_outputs["relational_map"], stage_outputs["diffractive_map"])
        stage_outputs["action_vector"] = _build_action_vector(field_context, stage_outputs["relevance_gradient"])
        return stage_outputs
    return stage_outputs

def _reintegrate(field_context: Dict[str, Any], stage_outputs: Dict[str, Any], drift_signal: Dict[str, Any]) -> Dict[str, Any]:
    target = drift_signal.get("reintegration_target") or "Field Entry"
    if target not in {"Field Entry", "Noticing"}:
        target = "Noticing"

    field_context["constructed_field"]["constraints"] = _dedupe(
        list(field_context["constructed_field"].get("constraints", [])) + [f"drift reintegration via {target}"]
    )

    if target == "Field Entry":
        return _fallback_stage_outputs(field_context)

    field_signature = _build_field_signature(field_context)
    noticing_register = _build_noticing_register(field_context)
    relational_map = _build_relational_map(field_context)
    diffractive_map = _build_diffractive_map(field_context)
    relevance_gradient = _build_relevance_gradient(field_context, field_signature, relational_map, diffractive_map)
    action_vector = _build_action_vector(field_context, relevance_gradient)

    return {
        "field_signature": field_signature,
        "noticing_register": noticing_register,
        "relational_map": relational_map,
        "diffractive_map": diffractive_map,
        "relevance_gradient": relevance_gradient,
        "action_vector": action_vector,
    }


def _articulation_constraints(turn_conditions: Dict[str, Any], field_signature: Dict[str, Any], relevance_gradient: Dict[str, Any]) -> Dict[str, Any]:
    mode = "grounded_response"
    if turn_conditions["correction"] and not (turn_conditions["asks_action"] or turn_conditions["asks_conceptual"]):
        mode = "correction_ack"
    elif turn_conditions["asks_current_factual"]:
        mode = "verified_direct"
    elif turn_conditions["asks_action"]:
        mode = "operative"
    elif turn_conditions["asks_noticing"]:
        mode = "noticing"
    elif turn_conditions["asks_conceptual"]:
        mode = "diffractive"
    return {
        "mode": mode,
        "plain_language": bool(turn_conditions["asks_plain_surface"]),
        "allow_list_format": bool(turn_conditions["allow_list_format"]),
        "exact_quantity": turn_conditions["exact_quantity"],
        "verification_mode": field_signature.get("verification_mode", "not_applicable"),
        "selected_elements": relevance_gradient.get("selected_elements", []),
    }


def _articulation_prompt(stage_outputs: Dict[str, Any], user_text: str, citations: List[str], turn_conditions: Dict[str, Any], constraints: Dict[str, Any]) -> str:
    mode_instructions = {
        "correction_ack": [
            "Acknowledge the correction plainly.",
            "Reshape the response immediately around the corrected request.",
            "Do not explain the framework or the process.",
        ],
        "verified_direct": [
            "Answer directly from available sources only.",
            "State fresh external verification limits plainly when relevant.",
            "Do not invent current details.",
        ],
        "operative": [
            "Give visible next-step orientation that remains optional, not coercive.",
            "Stay close to what can move now.",
            "Do not pad with theory.",
        ],
        "noticing": [
            "Keep multiple signals visible without forcing consolidation.",
            "Use descriptive language.",
        ],
        "diffractive": [
            "Clarify the concept through difference, relation, and interference.",
            "Keep competing readings visible where relevant.",
            "Stay readable and bounded.",
        ],
        "grounded_response": [
            "Answer from the situated field conditions.",
            "Stay descriptive and additive.",
        ],
    }
    instructions = list(mode_instructions.get(constraints["mode"], mode_instructions["grounded_response"]))
    if constraints["plain_language"]:
        instructions.append("Use plain direct language.")
    if constraints["exact_quantity"]:
        instructions.append(f"Respect the user-requested quantity: {constraints['exact_quantity']}.")
    if constraints["mode"] == "correction_ack" and constraints["exact_quantity"] == 1:
        instructions.append("Your entire response must be exactly one sentence.")
        instructions.append("Register the correction inside that one sentence rather than using a separate acknowledgment sentence.")
 
    if not constraints["allow_list_format"]:
        instructions.append("Do not use bullets unless the user explicitly asked for a list.")
    if constraints["verification_mode"] == "available_sources_only":
        instructions.append("If current verification is incomplete, say that plainly.")

    payload = {
        "user_text": user_text,
        "citations": citations,
        "turn_conditions": turn_conditions,
        "articulation_constraints": constraints,
        "field_signature": stage_outputs["field_signature"],
        "noticing_register": stage_outputs["noticing_register"],
        "relational_map": stage_outputs["relational_map"],
        "diffractive_map": stage_outputs["diffractive_map"],
        "relevance_gradient": stage_outputs["relevance_gradient"],
        "action_vector": stage_outputs.get("action_vector"),
    }
    return (
        "Execute articulation from the provided CBRA stage objects.\n"
        "Only produce the user-facing response.\n"
        "Do not explain CBRA unless the user explicitly asks for it.\n"
        "Constraints:\n- " + "\n- ".join(instructions) + "\n\n"
        f"CANONICAL_RUNTIME:\n{_runtime_grounding()}\n\n"
        f"STAGE_PAYLOAD:\n{json.dumps(payload, ensure_ascii=False)}"
    )


def _generate_articulation(client: OpenAI, model: str, system_identity: str, stage_outputs: Dict[str, Any], user_text: str, citations: List[str], turn_conditions: Dict[str, Any], constraints: Dict[str, Any]) -> str:
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_identity},
            {"role": "developer", "content": "Produce the user-facing answer only."},
            {"role": "user", "content": _articulation_prompt(stage_outputs, user_text, citations, turn_conditions, constraints)},
        ],
    )
    return (getattr(response, "output_text", "") or "").strip()


def _build_field_patch(field_context: Dict[str, Any], stage_outputs: Dict[str, Any], selected_elements: List[Dict[str, Any]], citations: List[str], text: str, drift_signal: Dict[str, Any], notes: Dict[str, Any]) -> Dict[str, Any]:
    prior_notes = field_context["prior_field"].get("notes") if isinstance(field_context["prior_field"].get("notes"), dict) else {}
    merged = dict(prior_notes)
    merged.update(
        {
            "last_user_input": field_context["user_text"],
            "last_articulation": text,
            "last_action_vector": stage_outputs.get("action_vector"),
            "drift_detected": drift_signal["drift_detected"],
            "drift_kind": drift_signal.get("drift_kind"),
            "detected_at_stage": drift_signal.get("detected_at_stage"),
            "reintegration_target": drift_signal.get("reintegration_target"),
            "reintegration_stage": drift_signal.get("reintegration_target"),
            "carryover_terms": [item.get("label", "") for item in selected_elements if isinstance(item, dict)],
            "runtime_notes": notes,
        }
    )
    return {
        "updated_at": _now_iso(),
        "sources_citations": citations,
        "field_signature": stage_outputs["field_signature"],
        "noticing_register": stage_outputs["noticing_register"],
        "relational_map": stage_outputs["relational_map"],
        "diffractive_map": stage_outputs["diffractive_map"],
        "relevance_gradient": stage_outputs["relevance_gradient"],
        "selected_elements": selected_elements,
        "notes": merged,
    }


def _build_loopcycle(field_id: Optional[str], stage_outputs: Dict[str, Any], selected_elements: List[Dict[str, Any]], text: str, drift_signal: Dict[str, Any], notes: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "field_id": field_id,
        "field_signature": stage_outputs["field_signature"],
        "noticing_register": stage_outputs["noticing_register"],
        "relational_map": stage_outputs["relational_map"],
        "diffractive_map": stage_outputs["diffractive_map"],
        "relevance_gradient": stage_outputs["relevance_gradient"],
        "selected_elements": selected_elements,
        "notes": notes,
        "articulation_output": text,
        "action_vector": stage_outputs.get("action_vector"),
        "drift_detected": drift_signal["drift_detected"],
        "reintegration_stage": drift_signal.get("reintegration_target"),
    }


def run_cbra(
    user_text: str,
    mode: Literal["production", "debug"] = "production",
    *,
    thread_id: Optional[str] = None,
    field_id: Optional[str] = None,
    sources: Optional[List[str]] = None,
    system_identity: str = "CBRA Studio (local prototype).",
    model: Optional[str] = None,
) -> Dict[str, Any]:
    if not user_text or not user_text.strip():
        raise ValueError("user_text is empty")

    _require_api_key()
    client = OpenAI()
    model = model or DEFAULT_MODEL

    prior_field = _load_prior_field(field_id)
    turn_conditions = _extract_turn_conditions(user_text, sources)
    carryover_terms = prior_field.get("notes", {}).get("carryover_terms", []) if isinstance(prior_field.get("notes"), dict) else []
    retrieved, citations = _retrieve_canonical_material(user_text, carryover_terms, turn_conditions)
    field_context = _assemble_field(user_text, prior_field, retrieved, sources, turn_conditions)

    stage_outputs = _enrich_stage_outputs(client, model, system_identity, field_context)
    stage_outputs["relevance_gradient"]["selected_elements"] = compress_selected_elements(stage_outputs["relevance_gradient"].get("selected_elements"))
    selected_elements = stage_outputs["relevance_gradient"]["selected_elements"]

    drift_signal = _detect_drift(stage_outputs, turn_conditions)
    reintegration_passes = 0
    if drift_signal["drift_detected"] and reintegration_passes < MAX_REINTEGRATION_PASSES:
        stage_outputs = _reintegrate(field_context, stage_outputs, drift_signal)
        stage_outputs["relevance_gradient"]["selected_elements"] = compress_selected_elements(stage_outputs["relevance_gradient"].get("selected_elements"))
        selected_elements = stage_outputs["relevance_gradient"]["selected_elements"]
        reintegration_passes += 1

    constraints = _articulation_constraints(turn_conditions, stage_outputs["field_signature"], stage_outputs["relevance_gradient"])
    text = _generate_articulation(client, model, system_identity, stage_outputs, user_text, citations, turn_conditions, constraints)

    post_drift = _detect_drift(stage_outputs, turn_conditions, draft_text=text)
    if post_drift["drift_detected"] and reintegration_passes < MAX_REINTEGRATION_PASSES:
        stage_outputs = _reintegrate(field_context, stage_outputs, post_drift)
        stage_outputs["relevance_gradient"]["selected_elements"] = compress_selected_elements(stage_outputs["relevance_gradient"].get("selected_elements"))
        selected_elements = stage_outputs["relevance_gradient"]["selected_elements"]
        constraints = _articulation_constraints(turn_conditions, stage_outputs["field_signature"], stage_outputs["relevance_gradient"])
        text = _generate_articulation(client, model, system_identity, stage_outputs, user_text, citations, turn_conditions, constraints)
        drift_signal = post_drift
        reintegration_passes += 1
    elif post_drift["drift_detected"]:
        drift_signal = post_drift

    notes = {
        "response_mode": constraints["mode"],
        "turn_conditions": turn_conditions,
        "canonical_files": list(_canonical_filenames()),
        "sources_citations": citations,
        "drift_kind": drift_signal.get("drift_kind"),
        "drift_detected": drift_signal["drift_detected"],
        "detected_at_stage": drift_signal.get("detected_at_stage"),
        "reintegration_target": drift_signal.get("reintegration_target"),
        "reintegration_stage": drift_signal.get("reintegration_target"),
        "reintegration_passes": reintegration_passes,
        "verification_mode": constraints.get("verification_mode"),
        "thread_id": thread_id,
    }

    if field_id and update_field is not None:
        patch = _build_field_patch(field_context, stage_outputs, selected_elements, citations, text, drift_signal, notes)
        update_field(field_id, patch)

    loopcycle = _build_loopcycle(field_id, stage_outputs, selected_elements, text, drift_signal, notes)
    result: Dict[str, Any] = {"text": text, "loopcycle": loopcycle}

    if mode == "debug":
        result["debug"] = {
            "canonical_files": list(_canonical_filenames()),
            "turn_conditions": turn_conditions,
            "constructed_field": field_context["constructed_field"],
            "field_signature": stage_outputs["field_signature"],
            "noticing_register": stage_outputs["noticing_register"],
            "relational_map": stage_outputs["relational_map"],
            "diffractive_map": stage_outputs["diffractive_map"],
            "relevance_gradient": stage_outputs["relevance_gradient"],
            "action_vector": stage_outputs.get("action_vector"),
            "sources_used": citations,
            "retrieved_material": retrieved,
            "drift_signal": drift_signal,
            "articulation_constraints": constraints,
        }
    return result
