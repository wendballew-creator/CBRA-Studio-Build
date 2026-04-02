from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from html import unescape
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from pypdf import PdfReader

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment]

load_dotenv()

from cbra.corpus import get_active_corpus_files, get_source_role

from cbra.models import (
    CutLedger,
    ExternalDocument,
    ExternalDocumentApparatus,
    FieldEvent,
    FieldState,
    OntologyGround,
    SituatedExpression,
    StabilizationFrame,
    TurnApparatus,
)

from cbra.store import get_field, update_field

from cbra.compression import enforce_fieldartifact_compression


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
LIVE_RETRIEVAL_ENABLED = (os.getenv("CBRA_ENABLE_LIVE_RETRIEVAL", "1") or "1").strip().lower() not in {"0", "false", "no"}
LIVE_RETRIEVAL_MODEL = "gpt-5"
MAX_LIVE_WEB_RESULTS = int((os.getenv("CBRA_MAX_LIVE_WEB_RESULTS", "4") or "4").strip())
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
CORPUS_DIR = PROJECT_ROOT / "corpus"
if not CORPUS_DIR.exists():
    fallback_corpus = BASE_DIR / "corpus"
    if fallback_corpus.exists():
        CORPUS_DIR = fallback_corpus

ROLE_WEIGHT = {
    "ground_anchor": 50.0,
    "operator_anchor": 35.0,
    "constraint_anchor": 30.0,
    "contextual_evidence": 10.0,
}

OPERATOR_SEQUENCE = [
    "field_entry",
    "notice",
    "relational_frame",
    "diffractive_read",
    "situated_relevance_select",
    "articulate",
    "orient_action",
]

_CANONICAL_BODY_CACHE: Dict[str, str] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_api_key() -> str:
    api_key = (os.getenv("OPENAI_API_KEY", "") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return api_key


def _make_openai_client() -> Any:
    if OpenAI is None:
        raise RuntimeError("openai package is not installed")
    _require_api_key()
    return OpenAI()


def _dump_model(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return dict(obj)


def _tokenize(text: str) -> List[str]:
    s = unicodedata.normalize("NFKC", text or "")
    s = s.replace("–", "-").replace("—", "-").replace("−", "-")
    s = s.lower()
    return re.findall(r"[a-z0-9]+", s)


def _normalize_terminology(text: str, user_text: str = "") -> str:
    t = text or ""
    u = (user_text or "").lower()
    if any(m in u for m in ["click", "button", "ui", "browser", "endpoint", "http", "upload"]):
        return t
    ontology_markers = ["barad", "entanglement", "field", "co-constitute", "materialize", "discursive", "cbra"]
    if any(m in (t.lower() + " " + u) for m in ontology_markers):
        t = re.sub(r"\binteractions\b", "intra-actions", t, flags=re.IGNORECASE)
        t = re.sub(r"\binteraction\b", "intra-action", t, flags=re.IGNORECASE)
    return t


def _extract_scalar_only(text: str) -> str:
    t = (text or "").strip()
    m = re.search(r"-?\d+(?:,\d{3})*(?:\.\d+)?%?", t)
    return m.group(0) if m else (t.splitlines()[0].strip() if t else t)

def _is_runtime_design_scope(user_text: str) -> bool:
    text = unicodedata.normalize("NFKC", user_text or "").lower()
    explicit_markers = [
        "cbra",
        "runtime",
        "engine",
        "kernel",
        "loops core",
        "drift constraints",
        "glossary",
        "canon",
        "canonical",
        "turn_apparatus",
        "fieldstate",
        "field state",
        "fieldevent",
        "field event",
        "cutledger",
        "cut ledger",
        "stabilizationframe",
        "stabilization frame",
        "situatedexpression",
        "situated expression",
        "externaldocumentapparatus",
        "external document apparatus",
        "operator_path",
        "run_cbra",
        "field pipeline",
        "runtime design",
    ]
    return any(marker in text for marker in explicit_markers)


def _should_materialize_prior_field(user_text: str, prior_snapshot: Dict[str, Any]) -> bool:
    if not prior_snapshot or not prior_snapshot.get("id"):
        return False
    text = unicodedata.normalize("NFKC", user_text or "").lower()
    carry_markers = [
        "you misunderstood",
        "you misread",
        "that is not what i asked",
        "not what i meant",
        "rewrite",
        "revise",
        "clarify",
        "follow up",
        "follow-up",
        "continue",
        "build on",
        "earlier",
        "previous",
        "last response",
        "that answer",
        "this answer",
        "what you said",
    ]
    return any(marker in text for marker in carry_markers)


def _attachment_debug_from_sources(sources: Optional[List[str]]) -> Dict[str, Any]:
    names: List[str] = []
    for source in sources or []:
        if not isinstance(source, str):
            continue
        first = source.splitlines()[0].strip()
        m = re.match(r"ATTACHMENT \((.+?)\):$", first)
        if m:
            names.append(m.group(1))
    names = list(dict.fromkeys(names))
    return {
        "active_attachment_count": len(names),
        "active_attachment_names": names,
        "active_attachment_present": bool(names),
    }


def _is_attachment_source(source: str) -> bool:
    return bool(re.match(r"ATTACHMENT \(.+?\):", (source or "").splitlines()[0].strip()))


def _extract_attachment_name(source: str) -> str:
    first = (source or "").splitlines()[0].strip()
    m = re.match(r"ATTACHMENT \((.+?)\):$", first)
    return m.group(1) if m else "attachment"


def _attachment_body(source: str) -> str:
    return "\n".join((source or "").splitlines()[1:]).strip()


def _attachment_materials(state: FieldState) -> List[Dict[str, Any]]:
    materials: List[Dict[str, Any]] = []
    for event in state.events:
        if event.kind != "attachment":
            continue
        body = str(event.payload.get("body", "") or "").strip()
        handle = str(event.payload.get("material_handle", "attachment") or "attachment")
        name = str(event.payload.get("name", handle) or handle)
        if body:
            materials.append({"handle": handle, "name": name, "body": body})
    return materials


def _normalize_attachment_lookup_term(term: str) -> str:
    cleaned = str(term or "").strip()
    for ch in ('"', "'", "“", "”", "‘", "’", "`"):
        cleaned = cleaned.strip(ch)
    cleaned = re.sub(r"^(the\s+word|the\s+term|the\s+phrase)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,:;!?")
    return cleaned


def _attachment_term_pattern(term: str) -> str:
    escaped = re.escape(term)
    escaped = escaped.replace("\\-", "[-‐-‒–—]")
    escaped = escaped.replace("\\ ", "\\s+")
    return escaped


def _extract_section_from_body(body: str, section_name: str) -> str:
    wanted = str(section_name or "").strip()
    if not wanted:
        return ""
    lines = body.splitlines()
    wanted_norm = re.sub(r"\s+", " ", wanted).strip().lower()
    heading_re = re.compile(r"^\s{0,3}(?:#{1,6}\s*)?(?P<title>[^\n]{1,200})\s*$")
    start = None
    for idx, line in enumerate(lines):
        match = heading_re.match(line)
        if not match:
            continue
        title_norm = re.sub(r"\s+", " ", match.group("title")).strip().lower().rstrip(":")
        if title_norm == wanted_norm or title_norm.endswith(" " + wanted_norm):
            start = idx + 1
            break
    if start is None:
        return ""
    collected: List[str] = []
    for line in lines[start:]:
        match = heading_re.match(line)
        if match:
            title_norm = re.sub(r"\s+", " ", match.group("title")).strip().lower().rstrip(":")
            if title_norm and title_norm != wanted_norm:
                break
        collected.append(line)
    return "\n".join(collected).strip()


def _resolve_attachment_operation(state: FieldState) -> FieldState:
    materials = _attachment_materials(state)
    if not materials:
        return state

    user_text = str(state.field_signature.get("phenomena", "") or "").strip()

    def finalize(operation: str, term: str, output: str, *, value: Any = None, matches: Optional[List[str]] = None, section: str = "") -> FieldState:
        op_handle = f"attachment_operation:{operation}:{term or section or 'result'}"
        payload: Dict[str, Any] = {
            "operation": operation,
            "term": term,
            "section": section,
            "value": value,
            "matches": list(matches or []),
            "output": str(output),
            "material_handles": [item["handle"] for item in materials],
        }
        state.events.append(FieldEvent(kind="attachment_operation_result", source="attachment_operator", payload=payload))
        state.notes["attachment_operation_resolved"] = True
        state.notes["attachment_operation_result"] = payload
        state.selected_elements = [{
            "label": op_handle,
            "rationale": str(output),
            "stage_source": "attachment_operation",
        }]
        state.relevance_gradient = {
            "candidate_elements": list(state.selected_elements),
            "selected_elements": list(state.selected_elements),
            "selection_basis": "direct_attachment_operation",
            "held_open": [],
        }
        state.cut_ledger = CutLedger(
            foregrounded=[op_handle],
            held_open=[],
            excluded=[],
            reasons={op_handle: f"direct attachment {operation} resolved before generic diffraction"},
            consequences={},
        )
        state.diffractive_map = {
            "materials": [{"handle": item["handle"], "kind": "attachment", "source": item["name"], "body_chars": len(item["body"])} for item in materials],
            "cross_readings": [],
            "resonance": [term or section] if (term or section) else [],
            "interference": [],
            "exclusions": [],
            "candidate_elements": list(state.selected_elements),
            "direct_attachment_operation": payload,
        }
        return state

    count_match = re.search(
        r'(?:how many times(?: is| does)?|count)\s+(?:the\s+word\s+|the\s+term\s+|the\s+phrase\s+)?["“”\']?([^"“”\']+?)["“”\']?\s+(?:used|appear(?:s)?|occur(?:s)?|in\s+the\s+attached\s+document|in\s+the\s+attachment|in\s+this\s+document|in\s+this\s+attachment)',
        user_text,
        flags=re.IGNORECASE,
    )
    if not count_match:
        count_match = re.search(
            r'count\s+(?:the\s+word\s+|the\s+term\s+|the\s+phrase\s+)?["“”\']?([^"“”\']+?)["“”\']?(?:\s|$)',
            user_text,
            flags=re.IGNORECASE,
        )
    if count_match:
        term = _normalize_attachment_lookup_term(count_match.group(1))
        pattern = _attachment_term_pattern(term)
        count = 0
        for item in materials:
            count += len(re.findall(pattern, item["body"], flags=re.IGNORECASE))
        return finalize("count", term, str(count), value=count)

    quote_match = re.search(
        r'(?:quote|show)\s+(?:the\s+)?(?:line|lines|sentence|sentences|passage|passages|occurrence|occurrences)?\s*(?:where\s+|with\s+)?["“”\']?([^"“”\']+?)["“”\']?\s+(?:appears|occur(?:s)?|is\s+used)',
        user_text,
        flags=re.IGNORECASE,
    )
    if quote_match:
        term = _normalize_attachment_lookup_term(quote_match.group(1))
        pattern = re.compile(_attachment_term_pattern(term), flags=re.IGNORECASE)
        hits: List[str] = []
        for item in materials:
            sentences = re.split(r'(?<=[.!?])\s+', item["body"])
            for sentence in sentences:
                if pattern.search(sentence):
                    cleaned = sentence.strip()
                    if cleaned:
                        hits.append(cleaned)
        hits = list(dict.fromkeys(hits))
        output = hits[0] if hits else ""
        return finalize("quote", term, output, matches=hits[:5])

    find_match = re.search(
        r'(?:find|locate|list)\s+(?:all\s+)?(?:occurrences|instances|places)?\s*(?:of\s+)?["“”\']?([^"“”\']+?)["“”\']?(?:\s|$)',
        user_text,
        flags=re.IGNORECASE,
    )
    if find_match:
        term = _normalize_attachment_lookup_term(find_match.group(1))
        pattern = re.compile(_attachment_term_pattern(term), flags=re.IGNORECASE)
        hits: List[str] = []
        for item in materials:
            sentences = re.split(r'(?<=[.!?])\s+', item["body"])
            for sentence in sentences:
                if pattern.search(sentence):
                    cleaned = sentence.strip()
                    if cleaned:
                        hits.append(cleaned)
        hits = list(dict.fromkeys(hits))
        output = "\n".join(hits[:5]) if hits else ""
        return finalize("find", term, output, matches=hits[:5], value=len(hits))

    extract_match = re.search(
        r'(?:extract|show|get)\s+(?:the\s+)?section\s+(?:called|titled|named)?\s*["“”\']?([^"“”\']+?)["“”\']?(?:\s|$)',
        user_text,
        flags=re.IGNORECASE,
    )
    if extract_match:
        section = _normalize_attachment_lookup_term(extract_match.group(1))
        extracted = ""
        for item in materials:
            extracted = _extract_section_from_body(item["body"], section)
            if extracted:
                break
        return finalize("extract", "", extracted, section=section)

    return state

def _seed_world_material(client: Any, user_text: str) -> str:
    if client is None:
        return ""
    prompt = (
        "Produce 3 to 5 short declarative sentences that can enter a reasoning field as worldly material. "
        "Write in ordinary prose. "
        "Keep the material grounded in broad world knowledge. "
        "When a concept has scientific, philosophical, and posthuman significance, include those layers together. "
        "Return only the material sentences.\n\n"
        f"QUESTION:\n{user_text}"
    )
    try:
        response = client.responses.create(
            model=DEFAULT_MODEL,
            input=[
                {"role": "developer", "content": "Return only the material sentences."},
                {"role": "user", "content": prompt},
            ],
        )
        return (getattr(response, "output_text", "") or "").strip()
    except Exception:
        return ""

def _read_canonical_body(file_name: str) -> str:
    cached = _CANONICAL_BODY_CACHE.get(file_name)
    if cached is not None:
        return cached
    for file_path in get_active_corpus_files(CORPUS_DIR):
        if file_path.name == file_name:
            body = file_path.read_text(encoding="utf-8", errors="replace")
            _CANONICAL_BODY_CACHE[file_name] = body
            return body
    _CANONICAL_BODY_CACHE[file_name] = ""
    return ""

def _build_ontology_ground() -> OntologyGround:
    return OntologyGround(
        primary_operators={
            "intra_action": {
                "active": True,
                "role": "mutual constitution within relation",
                "operator_type": "method_pillar",
            },
            "play": {
                "active": True,
                "role": "generative in-between enabling exploratory emergence",
                "operator_type": "method_pillar",
            },
            "diffraction": {
                "active": True,
                "role": "pattern mapping across difference while preserving multiplicity",
                "operator_type": "method_pillar",
            },
            "creative_becoming": {
                "active": True,
                "role": "ongoing emergence through entangled transformation",
                "operator_type": "method_pillar",
            },
        },
        play_conditions={
            "low_consequence_experimentation": True,
            "repetition_as_generative": True,
            "surprise_as_signal": True,
            "embodied_responsiveness": True,
            "environmental_responsiveness": True,
            "multiplicity_tolerance": True,
        },
        ethical_constraints={
            "posthuman_care": True,
            "livability": True,
            "non_closure": True,
        },
        principles={
            "creative_becoming_primary": True,
            "intra_action_primary": True,
            "play_primary": True,
            "diffraction_primary": True,
            "entanglement_primary": True,
            "intra_action_emergent_identity": True,
            "agential_cuts_operative": True,
            "diffraction_pattern_mapping": True,
            "play_generative": True,
            "posthuman_care_constrains_articulation": True,
            "field_as_primary_context": True,
        },
        operator_functions={
            "intra_action": "entities emerge through relational engagement",
            "play": "opens exploratory movement through repetition, surprise, and embodied responsiveness",
            "diffraction": "maps patterns across difference while preserving multiplicity",
            "creative_becoming": "sustains emergence without collapsing becoming into fixed identity",
            "posthuman_care": "constrains articulation toward livable futures",
            "field": "holds the current entangled conditions of the loop cycle",
        },
        articulation_constraints=[
            "descriptive rather than corrective",
            "additive rather than contrastive",
            "openness maintained",
            "no isolated-agent default",
            "no humanist baseline assumption",
            "play remains generative rather than decorative",
        ],
    )

def _collect_pattern_matches(text: str, patterns: Sequence[Tuple[str, str]]) -> Dict[str, List[str]]:
    lowered = (text or "").lower()
    out: Dict[str, List[str]] = {}
    for name, pattern in patterns:
        matches = re.findall(pattern, lowered)
        values: List[str] = []
        for match in matches:
            if isinstance(match, tuple):
                values.extend(str(item).strip() for item in match if str(item).strip())
            elif isinstance(match, str) and match.strip():
                values.append(match.strip())
        if values:
            out[name] = list(dict.fromkeys(values))
    return out


def _build_turn_apparatus(
    user_text: str,
    *,
    source_names: Optional[Sequence[str]] = None,
    prior_field_present: bool = False,
    event_kinds: Optional[Sequence[str]] = None,
    phase: str = "field_entry",
) -> TurnApparatus:
    text = (user_text or "").strip()
    source_list = list(dict.fromkeys(str(name).strip() for name in (source_names or []) if str(name).strip()))
    event_list = list(dict.fromkeys(str(kind).strip() for kind in (event_kinds or []) if str(kind).strip()))

    freshness_signals = _collect_pattern_matches(
        text,
        [
            ("relative_time", r"\b(today|tonight|this week|this weekend|right now)\b"),
            ("freshness_request", r"\b(current|latest|most recent|up[- ]to[- ]date|live)\b"),
            ("lookup_request", r"\b(look it up|check now|verify now|search now)\b"),
        ],
    )
    repair_signals = _collect_pattern_matches(
        text,
        [
            ("misread_claim", r"\b(that is not what i asked|you misunderstood|you misread|not what i meant)\b"),
            ("stabilization_tightening", r"\b(stop explaining|just answer|answer directly|plain language|shorter|one sentence|brief)\b"),
            ("prior_output_reference", r"\b(this|that|your|you|previous|earlier|last response)\b.*\b(answer|response|version|summary|rewrite)\b"),
        ],
    )
    inquiry_signals = _collect_pattern_matches(
        text,
        [
            ("definition_request", r"\b(what is|what's|define|definition of)\b"),
            ("explanation_request", r"\b(explain|tell me about|how does|how do|how is|how are|why does|why do|why is|why are)\b"),
            ("count_request", r"\b(how many times|count)\b"),
            ("quote_request", r"\bquote\b|\bshow\b.*\b(line|lines|sentence|sentences|passage|passages|occurrence|occurrences)\b"),
            ("extract_request", r"\b(extract|get|show)\b.*\bsection\b"),
        ],
    )

    if inquiry_signals.get("count_request"):
        inquiry_pressure = "count"
    elif inquiry_signals.get("quote_request"):
        inquiry_pressure = "quote"
    elif inquiry_signals.get("extract_request"):
        inquiry_pressure = "extract"
    elif inquiry_signals.get("definition_request"):
        inquiry_pressure = "definition"
    elif inquiry_signals.get("explanation_request"):
        inquiry_pressure = "explanation"
    else:
        inquiry_pressure = "open"

    requires_current_external_material = bool(freshness_signals)
    correction_requested = bool(repair_signals)

    boundary_logic: List[Dict[str, Any]] = []
    excluded_alternatives: List[Dict[str, str]] = []
    if requires_current_external_material:
        boundary_logic.append(
            {
                "pressure": "current_external_material",
                "decision": "enacted",
                "boundary": "treat the inquiry as current-bound rather than stable-historical",
                "because": [f"{name}: {', '.join(values)}" for name, values in freshness_signals.items()],
            }
        )
        excluded_alternatives.append(
            {"interpretation": "stable_historical_request", "reason": "freshness markers materially press on the turn"}
        )
    else:
        boundary_logic.append(
            {
                "pressure": "current_external_material",
                "decision": "not_enacted",
                "boundary": "hold the inquiry in the present field rather than escalating to freshness retrieval",
                "because": ["no current-time or freshness markers crossed threshold"],
            }
        )

    if correction_requested:
        because = [f"{name}: {', '.join(values)}" for name, values in repair_signals.items()]
        because.append("prior_field_present" if prior_field_present else "prior_field_absent_but_repair_language_present")
        boundary_logic.append(
            {
                "pressure": "correction",
                "decision": "enacted",
                "boundary": "treat the turn as perturbation of prior articulation rather than a wholly fresh prompt",
                "because": because,
            }
        )
        excluded_alternatives.append(
            {"interpretation": "fresh_prompt_without_repair", "reason": "repair language tightens the cut around revision and re-entry"}
        )
    else:
        boundary_logic.append(
            {
                "pressure": "correction",
                "decision": "not_enacted",
                "boundary": "treat the turn as continuing field material rather than explicit repair",
                "because": ["no repair markers crossed threshold"],
            }
        )

    if source_list:
        boundary_logic.append(
            {
                "pressure": "explicit_material_presence",
                "decision": "enacted",
                "boundary": "keep named attachments or explicit source matter inside the field conditions",
                "because": [f"sources: {', '.join(source_list[:4])}"],
            }
        )

    if inquiry_pressure != "open":
        boundary_logic.append(
            {
                "pressure": "inquiry_pressure",
                "decision": "enacted",
                "boundary": "treat the turn as carrying a bounded inquiry pressure without collapsing the field into legacy response families",
                "because": [f"inquiry_pressure: {inquiry_pressure}"],
            }
        )

    return TurnApparatus(
        phase=phase,
        context_inputs={
            "user_text_chars": len(text),
            "source_names": source_list,
            "source_count": len(source_list),
            "prior_field_present": prior_field_present,
            "event_kinds": event_list,
            "inquiry_pressure": inquiry_pressure,
        },
        signal_register={
            "freshness_signals": freshness_signals,
            "repair_signals": repair_signals,
            "inquiry_signals": inquiry_signals,
        },
        boundary_logic=boundary_logic,
        enacted_pressures={
            "timing": "current" if requires_current_external_material else "present",
            "requires_current_external_material": requires_current_external_material,
            "correction_requested": correction_requested,
            "source_count": len(source_list),
            "inquiry_pressure": inquiry_pressure,
        },
        excluded_alternatives=excluded_alternatives,
    )


def _fetch_url_body(url: str, max_bytes: int = 350000, max_chars: int = 12000) -> Dict[str, str]:
    request = Request(url, headers={"User-Agent": "CBRA/1.0"})
    with urlopen(request, timeout=10) as response:  # nosec B310
        content_type = response.headers.get("Content-Type", "text/plain")
        data = response.read(max_bytes)
    body = ""
    parse_status = "parsed"
    lower_type = content_type.lower()
    if "pdf" in lower_type or url.lower().endswith(".pdf"):
        try:
            reader = PdfReader(BytesIO(data))
            pages = []
            for page in reader.pages[:10]:
                pages.append((page.extract_text() or "").strip())
            body = "\n\n".join(page for page in pages if page)
        except Exception:
            body = ""
            parse_status = "parse_error"
    else:
        decoded = data.decode("utf-8", errors="replace")
        decoded = re.sub(r"<script.*?</script>", " ", decoded, flags=re.IGNORECASE | re.DOTALL)
        decoded = re.sub(r"<style.*?</style>", " ", decoded, flags=re.IGNORECASE | re.DOTALL)
        decoded = re.sub(r"<[^>]+>", " ", decoded)
        body = re.sub(r"\s+", " ", unescape(decoded)).strip()
    return {
        "body": body[:max_chars],
        "content_type": content_type,
        "parse_status": parse_status,
        "body_hash": hashlib.sha256(body[:max_chars].encode("utf-8", errors="ignore")).hexdigest() if body else "",
    }


def _discover_live_web_candidates(client: Any, user_text: str, apparatus: TurnApparatus) -> Dict[str, Any]:
    base = {
        "apparatus_kind": "external_document_apparatus",
        "status": "not_requested",
        "discovery_query": user_text,
        "selection_logic": [
            "discover candidate public URLs for current-bound questions",
            "prefer pages with stable provenance and directly relevant subject matter",
            "only fetched document bodies may enter the field as material",
        ],
        "fetch_constraints": {"max_results": MAX_LIVE_WEB_RESULTS, "max_body_chars": 12000},
        "parse_constraints": {"prefer": ["text/html", "application/pdf"], "summary_as_field_matter": False},
        "candidate_urls": [],
        "excluded_urls": [],
        "inaccessible_documents": [],
        "document_ids": [],
        "external_documents": [],
    }
    if not apparatus.enacted_pressures.get("requires_current_external_material"):
        return base
    if not LIVE_RETRIEVAL_ENABLED:
        return {**base, "status": "disabled"}
    if client is None:
        return {**base, "status": "client_unavailable"}

    prompt = (
        "Search the public web for current information needed to answer the user's question. "
        "Return JSON only with key candidates. candidates must be a list of up to 4 objects with keys title, source, url, why_relevant. "
        "Do not summarize the answer. Only surface candidate public documents.\n\n"
        f"USER_QUERY:\n{user_text}"
    )
    try:
        response = client.responses.create(
            model=LIVE_RETRIEVAL_MODEL,
            tools=[{"type": "web_search"}],
            input=[
                {"role": "developer", "content": "Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
        )
        raw = (getattr(response, "output_text", "") or "").strip()
        parsed = json.loads(raw) if raw else {}
        candidates = parsed.get("candidates", []) if isinstance(parsed, dict) else []
        urls: List[str] = []
        for item in candidates[:MAX_LIVE_WEB_RESULTS]:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", "") or "").strip()
            if url and url not in urls:
                urls.append(url)
        return {**base, "status": "discovered" if urls else "no_results", "candidate_urls": urls}
    except Exception as exc:  # pragma: no cover
        return {**base, "status": "discovery_error", "inaccessible_documents": [{"url": "", "reason": str(exc)}]}


def _build_external_document_apparatus(client: Any, user_text: str, turn_apparatus: TurnApparatus) -> ExternalDocumentApparatus:
    discovered = _discover_live_web_candidates(client, user_text, turn_apparatus)
    inaccessible_documents = list(discovered.get("inaccessible_documents", []))
    excluded_urls = list(discovered.get("excluded_urls", []))
    external_documents: List[ExternalDocument] = []
    document_ids: List[str] = []

    for index, url in enumerate(discovered.get("candidate_urls", [])[:MAX_LIVE_WEB_RESULTS], start=1):
        parsed_url = urlparse(url)
        if parsed_url.scheme not in {"http", "https"}:
            excluded_urls.append({"url": url, "reason": "unsupported_scheme"})
            continue
        try:
            fetched = _fetch_url_body(url)
        except (URLError, TimeoutError, ValueError) as exc:
            inaccessible_documents.append({"url": url, "reason": str(exc)})
            continue
        body = str(fetched.get("body", "") or "").strip()
        if not body:
            inaccessible_documents.append({"url": url, "reason": "empty_body_after_fetch"})
            continue
        doc = ExternalDocument(
            url=url,
            title=parsed_url.netloc or url,
            source=parsed_url.netloc or "web",
            content_type=str(fetched.get("content_type", "text/plain") or "text/plain"),
            fetch_status="fetched",
            parse_status=str(fetched.get("parse_status", "parsed") or "parsed"),
            body=body,
            body_chars=len(body),
            sections=[{"label": "body", "text": body[:4000]}],
            chunk_handles=[f"external:{index}:section:body"],
            body_hash=str(fetched.get("body_hash", "") or ""),
            provenance={"discovery_query": user_text, "candidate_rank": index},
        )
        external_documents.append(doc)
        document_ids.append(doc.doc_id)

    return ExternalDocumentApparatus(
        status=str(discovered.get("status", "not_requested") or "not_requested"),
        discovery_query=str(discovered.get("discovery_query", user_text) or user_text),
        selection_logic=list(discovered.get("selection_logic", [])),
        fetch_constraints=dict(discovered.get("fetch_constraints", {})),
        parse_constraints=dict(discovered.get("parse_constraints", {})),
        candidate_urls=list(discovered.get("candidate_urls", [])),
        excluded_urls=excluded_urls,
        inaccessible_documents=inaccessible_documents,
        document_ids=document_ids,
        external_documents=external_documents,
    )


def _score_line(query_terms: List[str], line_terms: List[str], role: str, line_text: str) -> float:
    if not line_terms:
        return 0.0
    score = ROLE_WEIGHT.get(role, 0.0)
    score += sum(1.0 for term in query_terms if term in line_terms)
    for operator_term in ["field", "constraint", "drift", "diffractive", "relevance", "articulation", "action"]:
        if operator_term in (line_text or "").lower():
            score += 1.5
    return score


def compose_grounded_sources(query: str, *, max_total_sources: int = 5) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
    query = (query or "").strip()
    if not query:
        return [], [], []
    query_terms = _tokenize(query)
    hits: List[Dict[str, Any]] = []
    for file_path in get_active_corpus_files(CORPUS_DIR):
        role = get_source_role(file_path.name)
        text = file_path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        for idx, line in enumerate(lines, start=1):
            score = _score_line(query_terms, _tokenize(line), role, line)
            if score <= ROLE_WEIGHT.get(role, 0.0):
                continue
            expanded = "\n".join(lines[max(0, idx - 2): min(len(lines), idx + 1)]).strip()
            hits.append(
                {
                    "file": file_path.name,
                    "line": idx,
                    "role": role,
                    "score": score,
                    "snippet": line.strip(),
                    "text": expanded,
                }
            )
    hits.sort(key=lambda item: item["score"], reverse=True)
    selected = hits[:max_total_sources]
    sources = [item["text"] for item in selected]
    citations = [f"[{item['file']} L{item['line']}+]" for item in selected]
    return sources, citations, hits


def _compress_hits_for_debug(hits: List[Dict[str, Any]], limit: int = 8) -> List[Dict[str, Any]]:
    return [
        {
            "file": hit.get("file", ""),
            "line": hit.get("line", 0),
            "role": hit.get("role", ""),
            "score": hit.get("score", 0),
            "snippet": hit.get("snippet", ""),
        }
        for hit in hits[:limit]
    ]


def _prior_field_snapshot(prior_field: Any) -> Dict[str, Any]:
    if prior_field is None:
        return {}
    if hasattr(prior_field, "model_dump"):
        data = prior_field.model_dump()
    elif hasattr(prior_field, "dict"):
        data = prior_field.dict()
    elif isinstance(prior_field, dict):
        data = dict(prior_field)
    else:
        return {}
    return {
        "id": data.get("id"),
        "selected_elements": data.get("selected_elements", []),
        "surface_flags": data.get("surface_flags", []),
        "field_signature": data.get("field_signature", {}),
        "cut_ledger": data.get("cut_ledger", {}),
        "stabilization_frame": data.get("stabilization_frame", {}),
        "situated_expression": data.get("situated_expression", {}),
        "notes": data.get("notes", {}),
    }


def assemble_field_events(
    *,
    user_text: str,
    canonical_sources: Sequence[str],
    citations: Sequence[str],
    raw_hits: Sequence[Dict[str, Any]],
    prior_field: Any,
    external_document_apparatus: Optional[ExternalDocumentApparatus] = None,
) -> List[FieldEvent]:
    events: List[FieldEvent] = [
        FieldEvent(kind="user_turn", source="user", payload={"text": (user_text or "").strip(), "material_handle": "user:turn"})
    ]

    for idx, source in enumerate([item for item in canonical_sources if isinstance(item, str) and _is_attachment_source(item)], start=1):
        body = _attachment_body(source)
        name = _extract_attachment_name(source)
        events.append(
            FieldEvent(
                kind="attachment",
                source="attachment",
                payload={
                    "name": name,
                    "material_handle": f"attachment:{idx}:{name}",
                    "body": body,
                    "body_chars": len(body),
                },
            )
        )

    if raw_hits or citations:
        documents: List[Dict[str, Any]] = []
        seen_documents: set[str] = set()
        for hit in raw_hits[:8]:
            file_name = str(hit.get("file", "") or "").strip()
            if not file_name or file_name in seen_documents:
                continue
            seen_documents.add(file_name)
            body = _read_canonical_body(file_name)
            documents.append(
                {
                    "file": file_name,
                    "role": hit.get("role", ""),
                    "material_handle": f"canonical:{file_name}",
                    "body": body,
                    "body_chars": len(body),
                    "line_hits": [
                        {
                            "line": item.get("line", 0),
                            "snippet": item.get("snippet", ""),
                            "text": item.get("text", ""),
                        }
                        for item in raw_hits
                        if item.get("file") == file_name
                    ][:5],
                }
            )
        events.append(FieldEvent(kind="retrieval", source="canonical", payload={"citations": list(citations), "documents": documents}))

    prior_snapshot = _prior_field_snapshot(prior_field)
    if prior_snapshot:
        events.append(FieldEvent(kind="prior_field_state", source="store", payload=prior_snapshot))

    apparatus = external_document_apparatus or ExternalDocumentApparatus()
    if apparatus.document_ids or apparatus.inaccessible_documents or apparatus.excluded_urls:
        events.append(
            FieldEvent(
                kind="external_document_apparatus",
                source="web",
                payload={
                    "status": apparatus.status,
                    "candidate_urls": list(apparatus.candidate_urls),
                    "document_ids": list(apparatus.document_ids),
                    "excluded_urls": list(apparatus.excluded_urls),
                    "inaccessible_documents": list(apparatus.inaccessible_documents),
                },
            )
        )
    for doc in apparatus.external_documents:
        events.append(
            FieldEvent(
                kind="external_document",
                source="web",
                payload={
                    "doc_id": doc.doc_id,
                    "title": doc.title,
                    "url": doc.url,
                    "source": doc.source,
                    "content_type": doc.content_type,
                    "material_handle": f"external:{doc.doc_id}",
                    "body": doc.body,
                    "body_chars": doc.body_chars,
                    "sections": doc.sections,
                    "chunk_handles": doc.chunk_handles,
                    "provenance": doc.provenance,
                },
            )
        )

    return events


def initialize_field_state(
    *,
    thread_id: Optional[str],
    field_id: Optional[str],
    user_text: str,
    sources: Sequence[str],
    citations: Sequence[str],
    raw_hits: Sequence[Dict[str, Any]],
    prior_field: Any,
    live_retrieval: Optional[Dict[str, Any]] = None,
) -> FieldState:
    prior_snapshot = _prior_field_snapshot(prior_field)
    materialize_prior_field = _should_materialize_prior_field(user_text, prior_snapshot)
    ontology_ground = _build_ontology_ground()

    turn_apparatus = _build_turn_apparatus(
        user_text,
        source_names=[
            _extract_attachment_name(source)
            for source in sources
            if isinstance(source, str) and _is_attachment_source(source)
        ],
        prior_field_present=materialize_prior_field,
        phase="initialize",
    )

    apparatus = (
        ExternalDocumentApparatus(**live_retrieval)
        if isinstance(live_retrieval, dict)
        else ExternalDocumentApparatus()
    )

    state = FieldState(
        id=field_id or FieldState().id,
        thread_id=thread_id,
        prior_field_id=prior_snapshot.get("id") if materialize_prior_field else None,
        ontology_ground=ontology_ground,
        updated_at=_now_iso(),
        surface_flags=["plain"],
        sources_citations=list(citations),
        turn_apparatus=turn_apparatus,
        external_document_apparatus=apparatus,
        notes={
            "renderer_mode": "field_native_stabilization",
            "surface_flags_deferred": True,
            "surface_flag_status": "deferred_until_articulation",
            "ground_enforced_retrieval": True,
            "correction_forced_reentry": False,
            "current_retrieval_requested": False,
            "turn_pressure_detection": "apparatus_traced",
            "prior_field_materialized": materialize_prior_field,
            "ontology_ground_installed": True,
            "ontology_kind": ontology_ground.ontology_kind,
        },
    )

    state.events = assemble_field_events(
        user_text=user_text,
        canonical_sources=sources,
        citations=citations,
        raw_hits=raw_hits,
        prior_field=prior_field if materialize_prior_field else None,
        external_document_apparatus=apparatus,
    )
    return state


def field_entry(state: FieldState) -> FieldState:
    state.operator_path.append("field_entry")
    user_event = next((event for event in state.events if event.kind == "user_turn"), None)
    user_text = str(user_event.payload.get("text", "") if user_event else "").strip()
    attachment_names = [
        str(event.payload.get("name", "attachment") or "attachment")
        for event in state.events
        if event.kind == "attachment"
    ]

    state.turn_apparatus = _build_turn_apparatus(
        user_text,
        source_names=attachment_names,
        prior_field_present=bool(state.prior_field_id),
        event_kinds=[event.kind for event in state.events],
        phase="field_entry",
    )

    pressures = state.turn_apparatus.enacted_pressures
    ontology = state.ontology_ground
    ontology_principles = dict(ontology.principles or {})
    ontology_constraints = list(ontology.articulation_constraints or [])

    material_lineages: List[str] = []
    if any(event.kind == "attachment" for event in state.events):
        material_lineages.append("attachment")
    if any(event.kind == "retrieval" for event in state.events):
        material_lineages.append("canonical_retrieval")
    if state.external_document_apparatus.external_documents:
        material_lineages.append("external_document")
    if any(event.kind == "prior_field_state" for event in state.events):
        material_lineages.append("prior_field")
    if not material_lineages:
        material_lineages.append("user_turn")

    constraints = [
        "ontology ground is active before material interpretation",
        "surface flags are deferred until the cut stabilizes",
    ]
    constraints.extend(ontology_constraints[:3])
    if state.external_document_apparatus.external_documents:
        constraints.append("only fetched external document bodies may enter the field as live material")

    stakes = [
        "preserve multiplicity",
        "trace pattern across entangled difference",
        "stabilize livable articulation without closure",
    ]

    state.field_signature = {
        "phenomena": user_text,
        "timing": pressures.get("timing", "present"),
        "constraints": constraints,
        "stakes": stakes,
        "attachments": attachment_names,
        "prior_field_id": state.prior_field_id,
        "event_count": len(state.events),
        "turn_apparatus_kind": state.turn_apparatus.apparatus_kind,
        "turn_apparatus_boundary_count": len(state.turn_apparatus.boundary_logic),
        "external_document_apparatus_kind": state.external_document_apparatus.apparatus_kind,
        "live_document_count": len(state.external_document_apparatus.external_documents),
        "ontology_kind": ontology.ontology_kind,
        "ontology_principles": ontology_principles,
        "material_lineages": material_lineages,
    }
    state.notes["ontology_ground_read_in_field_entry"] = True
    return state


def notice(state: FieldState) -> FieldState:
    state.operator_path.append("notice")
    pressures = state.turn_apparatus.enacted_pressures
    user_text = str(state.field_signature.get("phenomena", "") or "")

    if pressures.get("correction_requested") and not any(event.kind == "correction" for event in state.events):
        state.events.append(
            FieldEvent(
                kind="correction",
                source="field_apparatus",
                payload={
                    "text": user_text,
                    "effect": "field_reentry",
                    "boundary_logic": state.turn_apparatus.boundary_logic,
                    "signal_register": state.turn_apparatus.signal_register.get("repair_signals", {}),
                },
            )
        )
        state.notes["correction_forced_reentry"] = True
    else:
        state.notes["correction_forced_reentry"] = bool(
            any(event.kind == "correction" for event in state.events)
        )

    if pressures.get("requires_current_external_material") and not any(
        event.kind == "current_retrieval_request" for event in state.events
    ):
        state.events.append(
            FieldEvent(
                kind="current_retrieval_request",
                source="field_apparatus",
                payload={
                    "timing": pressures.get("timing", "current"),
                    "boundary_logic": state.turn_apparatus.boundary_logic,
                    "candidate_urls": list(state.external_document_apparatus.candidate_urls),
                    "document_ids": list(state.external_document_apparatus.document_ids),
                },
            )
        )
        state.notes["current_retrieval_requested"] = True
    else:
        state.notes["current_retrieval_requested"] = bool(
            pressures.get("requires_current_external_material")
        )

    ontology = state.ontology_ground
    ontology_principles = dict(ontology.principles or {})
    material_lineages = list(state.field_signature.get("material_lineages", []) or [])

    signals: List[str] = []
    if ontology_principles.get("entanglement_primary"):
        signals.append("entanglement is active as pre-interpretive ground")
    if ontology_principles.get("agential_cuts_operative"):
        signals.append("agential cuts are already shaping visibility")
    if ontology_principles.get("diffraction_pattern_mapping"):
        signals.append("difference is available for pattern tracing without consolidation")

    if any(event.kind == "attachment" for event in state.events):
        signals.append("explicit attachment material is present")
    if state.external_document_apparatus.external_documents:
        signals.append("external documents entered as fetched bodies")
    if state.external_document_apparatus.inaccessible_documents:
        signals.append("some external documents remained inaccessible")
    if state.notes.get("correction_forced_reentry"):
        signals.append("correction perturbs prior stabilization")
    if state.notes.get("current_retrieval_requested"):
        signals.append("current-bound inquiry is active")

    state.noticing_register = {
        "signals": signals,
        "signal_count": len(signals),
        "apparatus_signal_register": dict(state.turn_apparatus.signal_register),
        "external_document_status": state.external_document_apparatus.status,
        "external_document_count": len(state.external_document_apparatus.external_documents),
        "ontology_kind": ontology.ontology_kind,
        "ontology_principles": ontology_principles,
        "material_lineages": material_lineages,
    }
    state.notes["ontology_ground_read_in_notice"] = True
    return state


def relational_frame(state: FieldState) -> FieldState:
    state.operator_path.append("relational_frame")

    ontology = state.ontology_ground
    ontology_principles = dict(ontology.principles or {})
    field_constraints = list(state.field_signature.get("constraints", []) or [])
    material_lineages = list(state.field_signature.get("material_lineages", []) or [])
    noticing_signals = list(state.noticing_register.get("signals", []) or [])

    agency: List[str] = ["user", "runtime_apparatus"]
    if ontology_principles.get("entanglement_primary"):
        agency.append("entangled_field")
    if "attachment" in material_lineages:
        agency.append("attachment_material")
    if "canonical_retrieval" in material_lineages:
        agency.append("canonical_material")
    if "external_document" in material_lineages:
        agency.append("external_document_material")
    if "prior_field" in material_lineages:
        agency.append("prior_field_memory")

    relational_constraints = list(field_constraints)
    if ontology_principles.get("intra_action_emergent_identity"):
        relational_constraints.append("identity is treated as emergent within relation")
    if ontology_principles.get("agential_cuts_operative"):
        relational_constraints.append("boundaries are treated as enacted, not pre-given")
    if ontology_principles.get("posthuman_care_constrains_articulation"):
        relational_constraints.append("future articulation must remain livable across affected systems")

    capacity = {
        "operator_sequence_locked": True,
        "surface_flags_deferred": bool(state.notes.get("surface_flags_deferred", False)),
        "live_external_document_count": len(state.external_document_apparatus.external_documents),
        "multiplicity_preserved": ontology_principles.get("diffraction_pattern_mapping", False),
        "field_conditioned_reasoning": True,
    }

    consequence_visibility = {
        "held_open_required": True,
        "excluded_urls_visible": bool(
            state.external_document_apparatus.excluded_urls
            or state.external_document_apparatus.inaccessible_documents
        ),
        "distributed_consequence": ontology_principles.get("entanglement_primary", False),
        "articulation_constrained_by_posthuman_care": ontology_principles.get(
            "posthuman_care_constrains_articulation",
            False,
        ),
    }

    state.relational_map = {
        "agency": agency,
        "constraints": list(dict.fromkeys(relational_constraints)),
        "capacity": capacity,
        "consequence_visibility": consequence_visibility,
        "material_lineages": material_lineages,
        "ontology_kind": ontology.ontology_kind,
        "ontology_principles": ontology_principles,
        "noticing_signals": noticing_signals,
        "apparatus": {
            "turn_apparatus": _dump_model(state.turn_apparatus),
            "external_document_apparatus": _dump_model(state.external_document_apparatus),
        },
    }
    state.notes["ontology_ground_read_in_relational_frame"] = True
    return state


def _material_unique_terms(body: str) -> List[str]:
    return list(dict.fromkeys(_tokenize(body)))


def _build_diffractive_materials(state: FieldState) -> List[Dict[str, Any]]:
    materials: List[Dict[str, Any]] = []
    for event in state.events:
        if event.kind == "user_turn":
            body = str(event.payload.get("text", "") or "").strip()
            materials.append({"handle": "user:turn", "kind": "user_turn", "body": body, "terms": _material_unique_terms(body), "source": "user"})
        elif event.kind == "attachment":
            body = str(event.payload.get("body", "") or "").strip()
            handle = str(event.payload.get("material_handle", "attachment") or "attachment")
            materials.append({"handle": handle, "kind": "attachment", "body": body, "terms": _material_unique_terms(body), "source": "attachment"})
        elif event.kind == "retrieval":
            for doc in event.payload.get("documents", []):
                body = str(doc.get("body", "") or "").strip()
                handle = str(doc.get("material_handle", "canonical") or "canonical")
                materials.append({"handle": handle, "kind": "canonical_document", "body": body, "terms": _material_unique_terms(body), "source": doc.get("file", "canonical")})
        elif event.kind == "external_document":
            body = str(event.payload.get("body", "") or "").strip()
            handle = str(event.payload.get("material_handle", "external") or "external")
            materials.append({"handle": handle, "kind": "external_document", "body": body, "terms": _material_unique_terms(body), "source": event.payload.get("url", event.payload.get("source", "web"))})
        elif event.kind == "prior_field_state":
            body = json.dumps(
                {
                    "selected_elements": event.payload.get("selected_elements", []),
                    "cut_ledger": event.payload.get("cut_ledger", {}),
                    "stabilization_frame": event.payload.get("stabilization_frame", {}),
                },
                ensure_ascii=False,
            )
            materials.append({"handle": "prior_field:snapshot", "kind": "prior_field", "body": body, "terms": _material_unique_terms(body), "source": "store"})
    return materials


def _lexical_overlap(left: Sequence[str], right: Sequence[str]) -> List[str]:
    return sorted(set(left).intersection(right))[:12]


def diffractive_read(state: FieldState) -> FieldState:
    state.operator_path.append("diffractive_read")
    materials = _build_diffractive_materials(state)

    ontology = state.ontology_ground
    ontology_principles = dict(ontology.principles or {})
    correction_active = bool(state.notes.get("correction_forced_reentry"))

    cross_readings: List[Dict[str, Any]] = []
    resonance: List[str] = []
    interference: List[str] = []
    changed_salience: Dict[str, float] = {}
    candidate_elements: List[Dict[str, Any]] = []

    for idx, left in enumerate(materials):
        for right in materials[idx + 1 :]:
            shared = _lexical_overlap(left["terms"], right["terms"])
            pair_kinds = {left["kind"], right["kind"]}

            if not shared and "user_turn" not in pair_kinds:
                continue

            score = float(len(shared))
            if left["kind"] != right["kind"]:
                score += 1.0

            if ontology_principles.get("diffraction_pattern_mapping") and shared:
                score += 0.5
            if ontology_principles.get("entanglement_primary") and left["kind"] != right["kind"]:
                score += 0.5
            if "prior_field" in pair_kinds and not correction_active:
                score -= 2.0

            label = f"bridge:{left['handle']}<->{right['handle']}"
            rationale_parts: List[str] = []
            if shared:
                rationale_parts.append(f"pattern resonance through {', '.join(shared[:4])}")
            if left["kind"] != right["kind"]:
                rationale_parts.append(f"interference across {left['kind']} and {right['kind']}")
            if not rationale_parts:
                rationale_parts.append(f"cross-reading {left['kind']} with {right['kind']}")

            cross_readings.append(
                {
                    "label": label,
                    "left": left["handle"],
                    "right": right["handle"],
                    "shared_terms": shared,
                    "score": score,
                    "source_kinds": [left["kind"], right["kind"]],
                    "ontology_kind": ontology.ontology_kind,
                }
            )

            if shared:
                resonance.append(label)
            if left["kind"] != right["kind"]:
                interference.append(label)

            changed_salience[left["handle"]] = changed_salience.get(left["handle"], 0.0) + score
            changed_salience[right["handle"]] = changed_salience.get(right["handle"], 0.0) + score

            candidate_elements.append(
                {
                    "label": label,
                    "rationale": "; ".join(rationale_parts),
                    "stage_source": "diffractive_cross_read",
                    "score": score,
                }
            )

    for material in materials:
        changed_salience.setdefault(material["handle"], 0.0)
        score = changed_salience[material["handle"]]
        if material["kind"] == "prior_field" and not correction_active:
            score -= 2.0

        rationale = (
            f"material remains available within entangled field patterning with salience {score:.1f}"
            if ontology_principles.get("entanglement_primary")
            else f"material remained available with salience {score:.1f}"
        )

        candidate_elements.append(
            {
                "label": material["handle"],
                "rationale": rationale,
                "stage_source": "diffractive_material",
                "score": score,
            }
        )

    exclusions: List[str] = []
    for item in state.external_document_apparatus.inaccessible_documents:
        exclusions.append(f"inaccessible:{item.get('url', '')}")
    for item in state.external_document_apparatus.excluded_urls:
        exclusions.append(f"excluded:{item.get('url', '')}")
    if not correction_active and any(m["kind"] == "prior_field" for m in materials):
        exclusions.append("backgrounded:prior_field:snapshot")

    state.diffractive_map = {
        "materials": [
            {
                "handle": m["handle"],
                "kind": m["kind"],
                "source": m["source"],
                "body_chars": len(m["body"]),
            }
            for m in materials
        ],
        "cross_readings": sorted(cross_readings, key=lambda item: item["score"], reverse=True),
        "resonance": list(dict.fromkeys(resonance)),
        "interference": list(dict.fromkeys(interference)),
        "exclusions": exclusions,
        "candidate_elements": sorted(candidate_elements, key=lambda item: item["score"], reverse=True),
        "ontology_kind": ontology.ontology_kind,
        "ontology_principles": ontology_principles,
    }
    state.notes["ontology_ground_read_in_diffractive_read"] = True
    return state


def situated_relevance_select(state: FieldState) -> FieldState:
    state.operator_path.append("situated_relevance_select")
    candidate_elements = list(state.diffractive_map.get("candidate_elements", []))
    candidate_elements.sort(key=lambda item: item.get("score", 0.0), reverse=True)

    inquiry_pressure = str(
        state.turn_apparatus.enacted_pressures.get("inquiry_pressure", "open") or "open"
    )
    correction_active = bool(state.notes.get("correction_forced_reentry"))

    ontology = state.ontology_ground
    ontology_principles = dict(ontology.principles or {})
    preserve_multiplicity = bool(
        ontology_principles.get("diffraction_pattern_mapping", False)
    )
    entanglement_primary = bool(
        ontology_principles.get("entanglement_primary", False)
    )
    posthuman_care = bool(
        ontology_principles.get("posthuman_care_constrains_articulation", False)
    )

    material_lineages = list(
        state.relational_map.get("material_lineages", [])
        or state.field_signature.get("material_lineages", [])
        or []
    )
    consequence_visibility = dict(
        state.relational_map.get("consequence_visibility", {}) or {}
    )
    distributed_consequence = bool(
        consequence_visibility.get("distributed_consequence", False)
    )

    def _preview_from_text(text: str, max_chars: int = 260) -> str:
        cleaned = re.sub(r"\s+", " ", str(text or "").strip())
        if not cleaned:
            return ""
        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        preview = sentences[0].strip() if sentences and sentences[0].strip() else cleaned
        return preview[:max_chars].rstrip()

    source_evidence: Dict[str, str] = {}
    for event in state.events:
        if event.kind == "user_turn":
            source_evidence["user:turn"] = _preview_from_text(event.payload.get("text", ""))
        elif event.kind == "attachment":
            handle = str(event.payload.get("material_handle", "") or "")
            if handle:
                source_evidence[handle] = _preview_from_text(event.payload.get("body", ""))
        elif event.kind == "retrieval":
            for doc in event.payload.get("documents", []):
                handle = str(doc.get("material_handle", "") or "")
                line_hits = doc.get("line_hits", []) or []
                evidence = ""
                if line_hits:
                    first_hit = line_hits[0]
                    evidence = _preview_from_text(first_hit.get("text", "") or first_hit.get("snippet", ""))
                if not evidence:
                    evidence = _preview_from_text(doc.get("body", ""))
                if handle and evidence:
                    source_evidence[handle] = evidence
        elif event.kind == "external_document":
            handle = str(event.payload.get("material_handle", "") or "")
            evidence = _preview_from_text(event.payload.get("body", ""))
            if handle and evidence:
                source_evidence[handle] = evidence
        elif event.kind == "prior_field_state":
            source_evidence["prior_field:snapshot"] = "prior field remains available as background memory"

    rescored: List[Dict[str, Any]] = []
    non_user_lineages = [lineage for lineage in material_lineages if lineage != "user_turn"]
    multiple_materials_present = bool(non_user_lineages)

    for raw_item in candidate_elements:
        item = dict(raw_item)
        label = str(item.get("label", "") or "")
        if not label:
            continue

        stage_source = str(item.get("stage_source", "") or "")
        score = float(item.get("score", 0.0) or 0.0)

        if label == "prior_field:snapshot" and not correction_active:
            score -= 4.0

        if label == "user:turn" and multiple_materials_present:
            score -= 1.5

        if inquiry_pressure in {"definition", "explanation"}:
            if stage_source == "diffractive_material":
                score += 2.5
            elif stage_source == "diffractive_cross_read":
                score += 0.25 if preserve_multiplicity else -0.5

        if inquiry_pressure in {"count", "quote", "extract"}:
            if stage_source == "diffractive_material":
                score += 3.0
            elif stage_source == "diffractive_cross_read":
                score -= 1.0

        if entanglement_primary and stage_source == "diffractive_cross_read":
            score += 0.75

        if preserve_multiplicity and stage_source == "diffractive_material":
            score += 0.25

        if distributed_consequence and label == "user:turn":
            score -= 0.5

        item["score"] = score
        rescored.append(item)

    rescored.sort(key=lambda item: item.get("score", 0.0), reverse=True)

    direct_candidates = [
        item for item in rescored
        if str(item.get("stage_source", "") or "") == "diffractive_material"
    ]
    relational_candidates = [
        item for item in rescored
        if str(item.get("stage_source", "") or "") == "diffractive_cross_read"
    ]

    def _as_selected(item: Dict[str, Any]) -> Dict[str, Any]:
        label = str(item.get("label", "") or "")
        stage_source = str(item.get("stage_source", "") or "")
        rationale = str(item.get("rationale", "") or "")
        if stage_source == "diffractive_material" and label in source_evidence:
            rationale = source_evidence[label]
        return {
            "label": label,
            "rationale": rationale,
            "stage_source": stage_source,
        }

    selected_elements: List[Dict[str, Any]] = []
    foregrounded: List[str] = []
    held_open: List[str] = []
    excluded = list(state.diffractive_map.get("exclusions", []))
    reasons: Dict[str, str] = {}
    consequences: Dict[str, str] = {}
    used_labels: set[str] = set()

    if inquiry_pressure in {"definition", "explanation"}:
        preferred = direct_candidates[:2] + relational_candidates[:1]
    else:
        preferred = []
        if direct_candidates:
            preferred.append(direct_candidates[0])
        preferred.extend(relational_candidates[:2])
        if len(preferred) < 2:
            preferred.extend(direct_candidates[1:2])

    for item in preferred:
        label = str(item.get("label", "") or "")
        if not label or label in used_labels:
            continue
        if label == "prior_field:snapshot" and not correction_active:
            excluded.append("backgrounded:prior_field:snapshot")
            continue
        selected = _as_selected(item)
        selected_elements.append(selected)
        used_labels.add(label)
        foregrounded.append(label)
        if selected["stage_source"] == "diffractive_material":
            reasons[label] = selected["rationale"] or "selected as direct field matter"
            consequences[label] = (
                "grounds movement in available material"
                if not posthuman_care
                else "grounds movement in available material while keeping articulation livable"
            )
        elif selected["stage_source"] == "diffractive_cross_read":
            reasons[label] = selected["rationale"] or "selected as diffractive relation"
            consequences[label] = (
                "keeps pattern across difference visible"
                if preserve_multiplicity
                else "supports movement without collapsing the field"
            )
    if not selected_elements:
        for item in rescored[:2]:
            label = str(item.get("label", "") or "")
            if not label or label in used_labels:
                continue
            if label == "prior_field:snapshot" and not correction_active:
                excluded.append("backgrounded:prior_field:snapshot")
                continue
            selected = _as_selected(item)
            selected_elements.append(selected)
            used_labels.add(label)
            foregrounded.append(label)
            reasons[label] = selected["rationale"] or "selected because it remained available"
            consequences[label] = ""
    held_open_limit = 5 if preserve_multiplicity else 3
    if distributed_consequence:
        held_open_limit = max(held_open_limit, 4)

    for item in rescored:
        label = str(item.get("label", "") or "")
        if not label or label in used_labels:
            continue
        if label == "prior_field:snapshot" and not correction_active:
            excluded.append("backgrounded:prior_field:snapshot")
            continue
        if len(held_open) < held_open_limit:
            held_open.append(label)
            reasons[label] = str(item.get("rationale", "") or "held open as still-relevant material")
            consequences[label] = "remains available without forcing immediate closure"

    state.cut_ledger = CutLedger(
        foregrounded=list(dict.fromkeys(foregrounded))[:8],
        held_open=list(dict.fromkeys(held_open))[:8],
        excluded=list(dict.fromkeys(excluded))[:8],
        reasons=reasons,
        consequences=consequences,
    )
    state.selected_elements = selected_elements[:8]

    grouped_selection_bundle = {
        "inquiry_pressure": inquiry_pressure,
        "direct_material": [
            item
            for item in state.selected_elements
            if item.get("stage_source") == "diffractive_material"
        ],
        "relational_bridges": [
            item
            for item in state.selected_elements
            if item.get("stage_source") == "diffractive_cross_read"
        ],
        "held_open": list(state.cut_ledger.held_open),
        "ontology_kind": ontology.ontology_kind,
        "movement_priority": "movement_and_multiplicity" if preserve_multiplicity else "movement",
        "distributed_consequence": distributed_consequence,
        "multiplicity_preserved": preserve_multiplicity,
    }
    state.notes["grouped_selection_bundle"] = grouped_selection_bundle
    state.notes["ontology_ground_read_in_situated_relevance_select"] = True
    state.relevance_gradient = {
        "selected_elements": state.selected_elements,
        "what_to_hold_open": state.cut_ledger.held_open,
        "excluded": state.cut_ledger.excluded,
        "why": state.cut_ledger.reasons,
        "candidate_count": len(candidate_elements),
        "cross_read_count": len(state.diffractive_map.get("cross_readings", [])),
        "selection_basis": "grouped_selection_bundle",
        "grouped_selection_bundle": grouped_selection_bundle,
        "ontology_kind": ontology.ontology_kind,
        "ontology_principles": ontology_principles,    
}
    return state


def _first_numeric_scalar(*texts: str) -> Optional[str]:
    for text in texts:
        if not text:
            continue
        match = re.search(r"-?\d+(?:,\d{3})*(?:\.\d+)?%?", text)
        if match:
            return match.group(0)
    return None


def _clean_cut_label(label: str) -> str:
    text = str(label or "").strip()
    if text.startswith("bridge:"):
        text = text[len("bridge:") :]
    text = text.replace("_", " ").replace(":", " ")
    return re.sub(r"\s+", " ", text).strip()


def _selection_phrase(state: FieldState, item: Dict[str, Any]) -> str:
    label = str(item.get("label", "") or "").strip()
    rationale = str(item.get("rationale", "") or state.cut_ledger.reasons.get(label, "") or "").strip()
    consequence = str(state.cut_ledger.consequences.get(label, "") or "").strip()
    cleaned = _clean_cut_label(label)
    parts: List[str] = []
    if rationale:
        parts.append(rationale.rstrip("."))
    elif cleaned:
        parts.append(cleaned)
    if consequence:
        parts.append(consequence.rstrip("."))
    return ". ".join(part for part in parts if part)


def _derive_stabilization_constraints(state: FieldState, frame: StabilizationFrame) -> List[str]:
    flags = ["plain"]

    user_text_lower = str(state.field_signature.get("phenomena", "") or "").lower()
    explicit_number_only = any(
        phrase in user_text_lower
        for phrase in [
            "only a number",
            "only the number",
            "just the number",
            "number only",
            "just a number",
            "digits only",
            "return only a number",
            "give me only a number",
            "answer with only a number",
        ]
    )

    if frame.mode == "scalar" or explicit_number_only:
        flags.append("number_only")
    if frame.mode in {"scalar", "brief_sentence", "operative_sentence"}:
        flags.append("brief")
    if frame.mode in {"operative_sentence", "bounded_options"}:
        flags.append("operative")

    return list(dict.fromkeys(flags))


def _build_stabilization_frame(state: FieldState) -> StabilizationFrame:
    scalar = _first_numeric_scalar(
        str(state.field_signature.get("phenomena", "") or ""),
        *(item.get("label", "") for item in state.selected_elements),
        *(item.get("rationale", "") for item in state.selected_elements),
        *(state.cut_ledger.foregrounded or []),
    )
    selected_count = len(state.selected_elements)
    held_open_count = len(state.cut_ledger.held_open)
    correction_active = bool(state.notes.get("correction_forced_reentry"))
    current_active = bool(state.notes.get("current_retrieval_requested"))

    if scalar and selected_count <= 2 and held_open_count == 0:
        mode = "scalar"
    elif correction_active or current_active or held_open_count > 0:
        mode = "operative_sentence"
    elif selected_count <= 2:
        mode = "brief_sentence"
    else:
        mode = "layered_paragraph"

    movement_vector = _clean_cut_label(state.cut_ledger.foregrounded[0]) if state.cut_ledger.foregrounded else ""
    return StabilizationFrame(
        mode=mode,
        foregrounded_threads=[_clean_cut_label(item) for item in state.cut_ledger.foregrounded[:4]],
        held_open_threads=[_clean_cut_label(item) for item in state.cut_ledger.held_open[:3]],
        excluded_threads=[_clean_cut_label(item) for item in state.cut_ledger.excluded[:3]],
        movement_vector=movement_vector,
        closure_level="bounded" if mode in {"scalar", "brief_sentence"} else "open",
        format_affordances=[mode],
        language_constraints=[
            "descriptive rather than corrective",
            "additive rather than contrastive",
            "keep held-open material visible when present",
        ],
        basis={
            "selected_count": selected_count,
            "held_open_count": held_open_count,
            "correction_active": correction_active,
            "current_active": current_active,
            "scalar_detected": bool(scalar),
        },
    )


def _compose_situated_expression(state: FieldState, frame: StabilizationFrame) -> SituatedExpression:
    scalar = _first_numeric_scalar(
        str(state.field_signature.get("phenomena", "") or ""),
        *(item.get("label", "") for item in state.selected_elements),
        *(item.get("rationale", "") for item in state.selected_elements),
    )

    bundle = dict(state.relevance_gradient.get("grouped_selection_bundle", {}) or state.notes.get("grouped_selection_bundle", {}) or {})
    inquiry_pressure = str(bundle.get("inquiry_pressure") or state.turn_apparatus.enacted_pressures.get("inquiry_pressure", "open") or "open")
    direct_items = list(bundle.get("direct_material", []))
    relational_items = list(bundle.get("relational_bridges", []))
    held_open = frame.held_open_threads[:2]

    def _segments_from(items: List[Dict[str, Any]], limit: int = 2) -> List[str]:
        out: List[str] = []
        for item in items[:limit]:
            phrase = _selection_phrase(state, item)
            if phrase:
                out.append(phrase)
        return out

    def _dedupe(items: List[str]) -> List[str]:
        seen: set[str] = set()
        out: List[str] = []
        for item in items:
            if not item or item in seen:
                continue
            seen.add(item)
            out.append(item)
        return out

    direct_segments = _segments_from(direct_items)
    relational_segments = _segments_from(relational_items)
    fallback_segments = _segments_from(list(state.selected_elements), limit=3)

    if frame.mode == "scalar":
        text = scalar or "0"
        return SituatedExpression(form="scalar", text=text, segments=[text], supports=frame.foregrounded_threads, held_open=[], movement_note=frame.movement_vector)

    ordered_segments: List[str] = []
    if inquiry_pressure in {"definition", "explanation"}:
        ordered_segments.extend(direct_segments[:2])
        ordered_segments.extend(relational_segments[:1])
    else:
        ordered_segments.extend(direct_segments[:1])
        ordered_segments.extend(relational_segments[:2])
        if not ordered_segments:
            ordered_segments.extend(direct_segments[:2])

    ordered_segments = _dedupe(ordered_segments)
    if not ordered_segments:
        ordered_segments = _dedupe(fallback_segments)

    if not ordered_segments and frame.foregrounded_threads:
        ordered_segments = frame.foregrounded_threads[:2]
    if not ordered_segments:
        ordered_segments = [str(state.field_signature.get("phenomena", "") or "").strip()]

    if frame.mode == "brief_sentence":
        chosen = ordered_segments[:2]
        text = ". ".join(chosen)
        return SituatedExpression(form="sentence", text=text, segments=chosen, supports=frame.foregrounded_threads, held_open=held_open, movement_note=frame.movement_vector)

    if frame.mode == "operative_sentence":
        chosen = ordered_segments[:2]
        text = ". ".join(chosen)
        return SituatedExpression(form="operative_sentence", text=text, segments=chosen, supports=frame.foregrounded_threads, held_open=held_open, movement_note=frame.movement_vector)

    chosen = ordered_segments[:3]
    text = ". ".join(chosen)
    if held_open:
        text += f". Held open: {', '.join(held_open)}."
    return SituatedExpression(form="paragraph", text=text, segments=chosen, supports=frame.foregrounded_threads, held_open=held_open, movement_note=frame.movement_vector)


def articulate(state: FieldState) -> FieldState:
    state.operator_path.append("articulate")

    direct_result = state.notes.get("attachment_operation_result")
    if isinstance(direct_result, dict):
        operation = str(direct_result.get("operation", "") or "")
        output = str(direct_result.get("output", "") or "")
        direct_mode = "scalar" if operation == "count" else "brief_sentence"
        state.stabilization_frame = StabilizationFrame(
            mode=direct_mode,
            foregrounded_threads=list(state.cut_ledger.foregrounded[:1]),
            held_open_threads=[],
            excluded_threads=[],
            movement_vector="",
            closure_level="bounded",
            format_affordances=[direct_mode],
            language_constraints=["render direct attachment operation result"],
            basis={"attachment_operation": direct_result},
        )
        state.surface_flags = ["plain"]
        if operation == "count":
            state.surface_flags.extend(["number_only", "brief"])
        else:
            state.surface_flags.append("brief")
        state.situated_expression = SituatedExpression(
            form="scalar" if operation == "count" else "sentence",
            text=output,
            segments=[output] if output else [],
            supports=list(state.cut_ledger.foregrounded[:1]),
            held_open=[],
            movement_note="",
        )
        state.notes["surface_flags_deferred"] = False
        state.notes["surface_flag_status"] = "derived_from_field_and_cut"
        state.notes["ontology_ground_read_in_articulate"] = True
        state.articulation_output = output
        return state

    ontology = state.ontology_ground
    ontology_principles = dict(ontology.principles or {})
    posthuman_care = bool(
        ontology_principles.get("posthuman_care_constrains_articulation", False)
    )
    preserve_multiplicity = bool(
        ontology_principles.get("diffraction_pattern_mapping", False)
    )

    frame = _build_stabilization_frame(state)
    if posthuman_care:
        livable_constraint = "keep articulation livable across affected systems"
        if livable_constraint not in frame.language_constraints:
            frame.language_constraints.append(livable_constraint)
    if preserve_multiplicity:
        multiplicity_constraint = "do not collapse held-open multiplicity into one closure"
        if multiplicity_constraint not in frame.language_constraints:
            frame.language_constraints.append(multiplicity_constraint)

    state.stabilization_frame = frame
    state.surface_flags = _derive_stabilization_constraints(state, frame)
    state.situated_expression = _compose_situated_expression(state, frame)
    state.notes["surface_flags_deferred"] = False
    state.notes["surface_flag_status"] = "derived_from_field_and_cut"
    state.articulation_output = _normalize_terminology(
        state.situated_expression.text,
        user_text=str(state.field_signature.get("phenomena", "") or ""),
    )
    if posthuman_care:
        keep_match = re.match(
            r"^(.*)\.\s+Keep\s+(.+?)\s+visible while you move\.$",
            state.articulation_output or "",
        )
        if keep_match:
            prefix = keep_match.group(1).strip()
            held = keep_match.group(2).strip()
            state.articulation_output = f"{prefix}. Held open: {held}."

        state.articulation_output = (state.articulation_output or "").replace(
            "Move from the foregrounded cut without forcing full closure.",
            "Held-open material remains available without forced closure.",
        )

    if preserve_multiplicity and state.situated_expression and state.situated_expression.held_open:
        if (
            state.situated_expression.form in {"sentence", "operative_sentence"}
            and "Held open:" not in (state.articulation_output or "")
        ):
            held = ", ".join(state.situated_expression.held_open[:2])
            if held:
                state.articulation_output = f"{state.articulation_output}. Held open: {held}."

    state.notes["ontology_ground_read_in_articulate"] = True

    if "number_only" in state.surface_flags:
        preferred_scalar = _first_numeric_scalar(
            str(state.field_signature.get("phenomena", "") or ""),
            state.articulation_output or "",
            *(item.get("label", "") for item in state.selected_elements),
            *(item.get("rationale", "") for item in state.selected_elements),
            *(state.cut_ledger.foregrounded or []),
        )
        state.articulation_output = preferred_scalar or _extract_scalar_only(state.articulation_output or "")
        state.situated_expression.text = state.articulation_output
        state.situated_expression.segments = [state.articulation_output]
    if state.situated_expression is not None:
        state.situated_expression.text = state.articulation_output or state.situated_expression.text

    return state

def orient_action(state: FieldState) -> FieldState:
    state.operator_path.append("orient_action")
    action_vector = {
        "mode": "movement-oriented" if "operative" in state.surface_flags else "descriptive",
        "foregrounded": list(state.cut_ledger.foregrounded)[:3],
        "held_open": list(state.cut_ledger.held_open)[:2],
        "movement_vector": state.stabilization_frame.movement_vector,
    }
    if any(event.kind == "correction" for event in state.events):
        action_vector["reentry"] = "forced"
    if "number_only" in state.surface_flags:
        action_vector["surface"] = "scalar"
    state.action_vector = action_vector
    return state


def evaluate_invariants(state: FieldState) -> Dict[str, Any]:
    violations: List[str] = []
    if state.operator_path != OPERATOR_SEQUENCE:
        violations.append("operator_path_mismatch")
    if set(_dump_model(state.cut_ledger).keys()) != {"foregrounded", "held_open", "excluded", "reasons", "consequences"}:
        violations.append("cut_ledger_shape_mismatch")
    if any(key in state.notes for key in ["response_formation", "turn_profile", "active_stages", "render_payload_keys"]):
        violations.append("legacy_dispatch_key_present")
    if state.selected_elements != state.relevance_gradient.get("selected_elements", []):
        violations.append("selected_elements_not_aligned")
    if not state.stabilization_frame.mode:
        violations.append("stabilization_frame_missing")
    if state.situated_expression is None:
        violations.append("situated_expression_missing")
    if state.notes.get("surface_flag_status") != "derived_from_field_and_cut":
        violations.append("surface_flags_not_derived_downstream")
    return {"ok": not violations, "violations": violations, "operator_path": list(state.operator_path)}


def detect_drift(state: FieldState, invariants: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
    if not invariants.get("ok", False):
        violations = invariants.get("violations", [])
        if "operator_path_mismatch" in violations:
            return True, "Procedural Bypass", "Field Entry"
        if "selected_elements_not_aligned" in violations:
            return True, "Interpretive Compression", "Noticing"
        return True, "Ontological Drift", "Field Entry"
    if any(event.kind == "correction" for event in state.events):
        return False, None, "Field Entry"
    return False, None, None


def execute_field_pipeline(state: FieldState) -> Tuple[FieldState, Dict[str, Any], bool, Optional[str], Optional[str]]:
    for operator in [field_entry, notice, relational_frame]:
        state = operator(state)

    state = _resolve_attachment_operation(state)
    if state.notes.get("attachment_operation_resolved"):
        state.operator_path.append("diffractive_read")
        state.operator_path.append("situated_relevance_select")
    else:
        for operator in [diffractive_read, situated_relevance_select]:
            state = operator(state)

    if enforce_fieldartifact_compression is not None:
        compressed_field, compression_violations = enforce_fieldartifact_compression({"selected_elements": state.selected_elements, "relevance_gradient": state.relevance_gradient})
        state.selected_elements = compressed_field.get("selected_elements", [])
        state.relevance_gradient = compressed_field.get("relevance_gradient", {})
        if compression_violations:
            state.notes["compression_violations"] = compression_violations
    state = articulate(state)
    state = orient_action(state)
    invariants = evaluate_invariants(state)
    drift_detected, drift_kind, reintegration_stage = detect_drift(state, invariants)
    state.notes["invariants"] = invariants
    if drift_kind:
        state.notes["drift_kind"] = drift_kind
    return state, invariants, drift_detected, drift_kind, reintegration_stage


def _state_patch(state: FieldState) -> Dict[str, Any]:
    return {
        "prior_field_id": state.prior_field_id,
        "updated_at": _now_iso(),
        "events": [_dump_model(event) for event in state.events],
        "operator_path": list(state.operator_path),
        "surface_flags": list(state.surface_flags),
        "ontology_ground": _dump_model(state.ontology_ground),
        "sources_citations": list(state.sources_citations),
        "turn_apparatus": _dump_model(state.turn_apparatus),
        "external_document_apparatus": _dump_model(state.external_document_apparatus),
        "field_signature": dict(state.field_signature),
        "noticing_register": dict(state.noticing_register),
        "relational_map": dict(state.relational_map),
        "diffractive_map": dict(state.diffractive_map),
        "relevance_gradient": dict(state.relevance_gradient),
        "selected_elements": list(state.selected_elements),
        "cut_ledger": _dump_model(state.cut_ledger),
        "stabilization_frame": _dump_model(state.stabilization_frame),
        "situated_expression": _dump_model(state.situated_expression) if state.situated_expression else None,
        "articulation_output": state.articulation_output,
        "action_vector": dict(state.action_vector or {}),
        "notes": dict(state.notes),
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
    _ = system_identity
    _ = model or DEFAULT_MODEL

    client = None
    if OpenAI is not None and os.getenv("OPENAI_API_KEY"):
        try:
            client = _make_openai_client()
        except Exception:
            client = None

    runtime_design_scope = _is_runtime_design_scope(user_text)

    input_sources = list(sources or [])
    preflight_apparatus = _build_turn_apparatus(
        user_text,
        source_names=[
            _extract_attachment_name(source)
            for source in input_sources
            if isinstance(source, str) and _is_attachment_source(source)
        ],
        phase="run_cbra_preflight",
    )

    material_sources: List[str] = []
    citations: List[str] = []
    raw_hits: List[Dict[str, Any]] = []

    if not input_sources:
        if runtime_design_scope:
            material_sources, citations, raw_hits = compose_grounded_sources(
                user_text,
                max_total_sources=5,
            )
    else:
        material_sources = list(input_sources)
        attachment_only = [
            source
            for source in material_sources
            if isinstance(source, str) and _is_attachment_source(source)
        ]
        if attachment_only and runtime_design_scope:
            source_text = "\n".join(attachment_only)
            supplemental_sources, citations, raw_hits = compose_grounded_sources(
                user_text + "\n" + source_text,
                max_total_sources=5,
            )
            material_sources = list(dict.fromkeys(material_sources + supplemental_sources))

    external_document_apparatus = _build_external_document_apparatus(
        client,
        user_text,
        preflight_apparatus,
    )

    retrieval_labels = []
    for source in material_sources:
        first = source.splitlines()[0].strip() if isinstance(source, str) else str(source)
        retrieval_labels.append(first[:180])
    retrieval_labels.extend(external_document_apparatus.candidate_urls)

    prior_field = get_field(field_id) if field_id and get_field is not None else None
    state = initialize_field_state(
        thread_id=thread_id,
        field_id=field_id,
        user_text=user_text,
        sources=material_sources,
        citations=citations,
        raw_hits=raw_hits,
        prior_field=prior_field,
        live_retrieval=_dump_model(external_document_apparatus),
    )
    state.notes["articulation_renderer"] = "field_native"
    state.notes["articulation_client_available"] = bool(client is not None)
    state.notes["ground_enforced_retrieval"] = bool(citations)
    state.notes["grounding_scope"] = "runtime_design" if runtime_design_scope else "world_or_user_material"

    state, invariants, drift_detected, drift_kind, reintegration_stage = execute_field_pipeline(state)
    state.notes["drift_detected"] = drift_detected
    state.notes["detected_at_stage"] = "articulate" if drift_detected else None
    state.notes["reintegration_target"] = reintegration_stage if drift_detected else None

    if field_id and update_field is not None:
        update_field(field_id, _state_patch(state))

    attachment_debug = _attachment_debug_from_sources(material_sources)
    loopcycle: Dict[str, Any] = {
        "field_id": field_id,
        "operator_path": list(state.operator_path),
        "events": [_dump_model(event) for event in state.events],
        "surface_flags": list(state.surface_flags),
        "turn_apparatus": _dump_model(state.turn_apparatus),
        "external_document_apparatus": _dump_model(state.external_document_apparatus),
        "field_signature": state.field_signature,
        "noticing_register": state.noticing_register,
        "relational_map": state.relational_map,
        "diffractive_map": state.diffractive_map,
        "relevance_gradient": state.relevance_gradient,
        "selected_elements": state.selected_elements,
        "cut_ledger": _dump_model(state.cut_ledger),
        "stabilization_frame": _dump_model(state.stabilization_frame),
        "situated_expression": _dump_model(state.situated_expression) if state.situated_expression else None,
        "notes": state.notes,
        "articulation_output": state.articulation_output,
        "action_vector": state.action_vector,
        "drift_detected": drift_detected,
        "reintegration_stage": reintegration_stage,
    }
    result: Dict[str, Any] = {"text": state.articulation_output or "", "loopcycle": loopcycle}
    if mode == "debug":
        result["debug"] = {
            "operator_path": list(state.operator_path),
            "surface_flags": list(state.surface_flags),
            "invariants": invariants,
            "drift_signal": {
                "drift_detected": drift_detected,
                "drift_kind": drift_kind,
                "reintegration_stage": reintegration_stage,
            },
            "sources_used": citations,
            "retrieval_hits": _compress_hits_for_debug(raw_hits),
            "retrieval_labels": retrieval_labels,
            "attachments": attachment_debug,
            "events": [_dump_model(event) for event in state.events],
            "turn_apparatus": _dump_model(state.turn_apparatus),
            "external_document_apparatus": _dump_model(state.external_document_apparatus),
            "cut_ledger": _dump_model(state.cut_ledger),
            "stabilization_frame": _dump_model(state.stabilization_frame),
            "situated_expression": _dump_model(state.situated_expression) if state.situated_expression else None,
        }
    return result

