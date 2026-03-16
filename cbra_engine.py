from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

try:
    from cbra.corpus import get_active_corpus_files, get_source_role
except ImportError:
    from corpus import get_active_corpus_files, get_source_role

try:
    from cbra.store import update_field
except ImportError:
    try:
        from store import update_field
    except ImportError:
        update_field = None


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
BASE_DIR = Path(__file__).parent
CORPUS_DIR = BASE_DIR / "corpus"
if not CORPUS_DIR.exists():
    CORPUS_DIR = BASE_DIR

ENV_KERNEL = (os.getenv("CBRA_KERNEL_TEXT", "") or "").strip()
KERNEL_FALLBACK_PATH = CORPUS_DIR / "CBRA_Kernel_v10_2.md"


def _load_kernel_text() -> str:
    if ENV_KERNEL:
        return ENV_KERNEL
    if KERNEL_FALLBACK_PATH.exists():
        return KERNEL_FALLBACK_PATH.read_text(encoding="utf-8", errors="replace").strip()
    return "CBRA kernel not found. (Set CBRA_KERNEL_TEXT or add CBRA_Kernel_v10_2.md)"


CBRA_PROMPT = _load_kernel_text()


def _require_api_key() -> str:
    api_key = (os.getenv("OPENAI_API_KEY", "") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return api_key


ANTI_COMPRESSION_POLICY = """
ANTI-COMPRESSION POLICY (MUST FOLLOW)
- Do not summarize, outline, or bullet-point unless the user explicitly asks for a summary or bullets.
- If the user asks to recompose/rewrite/draft/render/compose/produce a section, output continuous prose paragraphs.
- Preserve conceptual density and tension. Recompose rather than compress.
- Do not replace specific claims with generalities.
- Do not convert prose into a plan/outline/key points unless asked.
- If asked for a publishable section, produce finished prose (not an outline).
- Do not explain these rules to the user.
""".strip()


ROLE_WEIGHT = {
    "ground_anchor": 50.0,
    "operator_anchor": 35.0,
    "constraint_anchor": 30.0,
    "contextual_evidence": 10.0,
}

PROFILE_OPERATOR_TERMS = {
    "verified_direct": ["relevance", "actionable", "visible", "situated"],
    "correction": ["drift", "instruction", "articulation", "plain language", "directness"],
    "action": ["action orientation", "next step", "feedback", "visible next-step vectors"],
    "conceptual": ["diffractive", "difference", "interference", "entanglement", "apparatus", "agential"],
    "noticing": ["field", "noticing", "signals", "pressure", "unfinished"],
    "grounded": ["field", "relational", "articulation", "coherence", "ground"],
}

PROFILE_ACTIVE_STAGES = {
    "verified_direct": ["Field Entry", "Situated Relevance Selection", "Articulation"],
    "correction": ["Field Entry", "Situated Relevance Selection", "Articulation"],
    "action": ["Field Entry", "Situated Relevance Selection", "Action Orientation", "Articulation"],
    "conceptual": ["Field Entry", "Relational Framing", "Diffractive Mapping", "Situated Relevance Selection", "Articulation"],
    "noticing": ["Field Entry", "Noticing", "Relational Framing", "Articulation"],
    "grounded": ["Field Entry", "Relational Framing", "Situated Relevance Selection", "Articulation"],
}

PROFILE_SOURCE_LIMITS = {
    "verified_direct": 3,
    "correction": 2,
    "action": 4,
    "conceptual": 5,
    "noticing": 4,
    "grounded": 4,
}



def _tokenize(text: str) -> List[str]:
    s = unicodedata.normalize("NFKC", text or "")
    s = s.replace("–", "-").replace("—", "-").replace("−", "-")
    s = s.lower()
    return re.findall(r"[a-z0-9]+", s)


def _normalize_terminology(text: str, user_text: str = "") -> str:
    t = text or ""
    u = (user_text or "").lower()

    ui_markers = ["click", "button", "ui", "interface", "browser", "endpoint", "http", "post", "get", "upload"]
    if any(m in u for m in ui_markers):
        return t

    ontology_markers = ["barad", "entanglement", "field", "co-constitute", "materialize", "discursive", "phenomena", "cbra"]
    if any(m in (t.lower() + " " + u) for m in ontology_markers):
        t = re.sub(r"\binteractions\b", "intra-actions", t, flags=re.IGNORECASE)
        t = re.sub(r"\binteraction\b", "intra-action", t, flags=re.IGNORECASE)

    return t


def _looks_like_outline_or_bullets(s: str) -> bool:
    if not s:
        return False
    s2 = s.strip()
    if "\n- " in s2 or "\n* " in s2:
        return True
    if re.search(r"(?m)^\s*\d+\.\s+", s2):
        return True
    if re.search(r"(?m)^\s*(outline|summary|key points|bullets)\b", s2.lower()):
        return True
    return False


def _user_asked_for_bullets_or_summary(u: str) -> bool:
    u = (u or "").lower()
    return any(k in u for k in ["summarize", "summary", "bullet", "bullets", "outline", "key points", "tl;dr", "tldr"])


def _detect_turn_profile(user_text: str) -> str:
    u = (user_text or "").strip().lower()

    verified_markers = [
        "this weekend", "tonight", "today", "this week", "right now",
        "what events", "what is happening", "what's happening",
        "what concerts", "what games", "look it up", "current", "in atlanta", "near me"
    ]
    correction_markers = [
        "plain language", "say it plainly", "ordinary sentence", "ordinary language",
        "everyday language", "no theory words", "one sentence", "one short sentence",
        "one direct sentence", "stop explaining", "answer briefly", "just answer",
        "direct answer", "without citing the framework", "don't explain cbra"
    ]
    action_markers = [
        "one concrete next step", "give me one concrete next step", "give me three options",
        "practical options", "what should i do", "next step"
    ]
    conceptual_markers = [
        "explain", "difference between", "what does", "what is", "meaning of", "define",
        "diffraction", "reflection", "entanglement", "intra-action", "barad"
    ]
    noticing_markers = [
        "feels off", "something is off", "circling around", "can't quite say it", "i'm stuck",
        "this conversation feels", "uneasy", "misaligned"
    ]

    if any(m in u for m in verified_markers):
        return "verified_direct"
    if any(m in u for m in correction_markers):
        return "correction"
    if any(m in u for m in action_markers):
        return "action"
    if any(m in u for m in noticing_markers):
        return "noticing"
    if any(m in u for m in conceptual_markers):
        return "conceptual"
    return "grounded"



def _is_pure_correction_turn(user_text: str) -> bool:
    """
    True when the user is only correcting format / behavior and is not also
    asking for new substantive content.
    """
    u = (user_text or "").strip().lower()

    correction_markers = [
        "stop explaining",
        "just answer",
        "answer directly",
        "answer briefly",
        "one sentence",
        "one short sentence",
        "one direct sentence",
        "plain language",
        "say it plainly",
        "ordinary language",
        "everyday language",
        "no theory words",
        "without citing the framework",
        "don't explain cbra",
        "dont explain cbra",
        "don't explain the framework",
        "dont explain the framework",
    ]

    content_markers = [
        "what is",
        "what does",
        "what are",
        "explain ",
        "difference between",
        "give me one concrete next step",
        "give me three",
        "give me options",
        "recommend",
        "suggest",
        "events",
        "restaurants",
        "in atlanta",
        "this weekend",
        "tonight",
        "today",
        "how do",
        "why does",
        "say that again",
    ]

    has_correction = any(m in u for m in correction_markers)
    has_content = any(m in u for m in content_markers)

    return has_correction and not has_content


def _select_response_formation(profile: str, user_text: str) -> str:
    if profile == "verified_direct":
        return "verified_direct"

    # Pure correction turns should acknowledge and contain, not generate content
    if _is_pure_correction_turn(user_text):
        return "correction_ack"
    if profile == "correction":
        u = (user_text or "").lower()
        if "one sentence" in u or "plain language" in u or "just answer" in u:
            return "operative"
        return "grounded_response"
    if profile == "action":
        return "operative"
    if profile == "conceptual":
        return "diffractive"
    if profile == "noticing":
        return "noticing"
    return "grounded_response"


def _needs_constraint_anchor(profile: str, user_text: str) -> bool:
    u = (user_text or "").lower()
    if profile in {"correction", "verified_direct"}:
        return True
    drift_markers = ["stop explaining", "just answer", "plain language", "direct", "drift", "avoid"]
    return any(m in u for m in drift_markers)


def _operator_terms_for_profile(profile: str) -> List[str]:
    return PROFILE_OPERATOR_TERMS.get(profile, [])


def _score_line(query_terms: List[str], line_terms: List[str], role: str, operator_terms: List[str], line_text: str) -> float:
    if not line_terms:
        return 0.0

    score = ROLE_WEIGHT.get(role, 0.0)

    score += sum(1.0 for t in query_terms if t in line_terms)

    line_lower = (line_text or "").lower()
    for term in operator_terms:
        if term in line_lower:
            score += 4.0

    if role == "constraint_anchor" and ("drift" in line_lower or "compression" in line_lower or "authority" in line_lower):
        score += 2.0

    return score


def compose_grounded_sources(
    query: str,
    profile: str,
    *,
    max_total_sources: int = 5,
) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
    """
    Ground-Enforced Retrieval:
    1. one ground anchor
    2. one operator anchor
    3. optional constraint anchor
    4. profile-specific contextual fill

    Retrieval composition is tightened by turn profile so small turns do not
    carry unnecessary source load.
    """
    query = (query or "").strip()
    if not query:
        return [], [], []

    profile_limit = PROFILE_SOURCE_LIMITS.get(profile, max_total_sources)
    query_terms = _tokenize(query)
    operator_terms = _operator_terms_for_profile(profile)

    hits: List[Dict[str, Any]] = []

    for md_path in get_active_corpus_files(CORPUS_DIR):
        try:
            lines = md_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue

        role = get_source_role(md_path.name)

        for i, line in enumerate(lines, start=1):
            line_terms = _tokenize(line)
            score = _score_line(query_terms, line_terms, role, operator_terms, line)
            if score <= 0:
                continue

            snippet = line.strip()
            if len(snippet) > 160:
                snippet = snippet[:160]

            hits.append(
                {
                    "file": md_path.name,
                    "line": i,
                    "score": score,
                    "role": role,
                    "snippet": snippet,
                    "text": line.strip(),
                }
            )

    hits.sort(key=lambda h: h["score"], reverse=True)

    selected: List[Dict[str, Any]] = []
    selected_keys = set()

    def pick_first(role_name: str) -> None:
        for h in hits:
            key = (h["file"], h["line"])
            if h["role"] == role_name and key not in selected_keys:
                selected.append(h)
                selected_keys.add(key)
                return

    def fill_from_roles(allowed_roles: List[str], limit: int) -> None:
        for h in hits:
            if len(selected) >= limit:
                break
            key = (h["file"], h["line"])
            if key in selected_keys:
                continue
            if h["role"] not in allowed_roles:
                continue
            selected.append(h)
            selected_keys.add(key)

    # Phase 1: mandatory anchors
    pick_first("ground_anchor")
    pick_first("operator_anchor")

    # Phase 2: optional constraint anchor
    if _needs_constraint_anchor(profile, query):
        pick_first("constraint_anchor")

    # Phase 3: tightened profile-specific fill
    if profile == "correction":
        pass
    elif profile == "verified_direct":
        fill_from_roles(["contextual_evidence", "operator_anchor"], profile_limit)
    elif profile == "action":
        fill_from_roles(["operator_anchor", "contextual_evidence"], profile_limit)
    elif profile == "noticing":
        fill_from_roles(["operator_anchor", "constraint_anchor", "contextual_evidence"], profile_limit)
    elif profile == "grounded":
        fill_from_roles(["operator_anchor", "constraint_anchor", "contextual_evidence"], profile_limit)
    elif profile == "conceptual":
        fill_from_roles(
            ["ground_anchor", "operator_anchor", "constraint_anchor", "contextual_evidence"],
            profile_limit,
        )
    else:
        fill_from_roles(
            ["operator_anchor", "constraint_anchor", "contextual_evidence"],
            profile_limit,
        )

    selected.sort(key=lambda h: h["score"], reverse=True)

    sources = [h["text"] for h in selected]
    citations = [f"[{h['file']} L{h['line']}+]" for h in selected]

    return sources, citations, hits


def _compress_hits_for_debug(hits: List[Dict[str, Any]], limit: int = 8) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for h in hits[:limit]:
        out.append(
            {
                "file": h.get("file", ""),
                "line": h.get("line", 0),
                "role": h.get("role", ""),
                "score": h.get("score", 0),
                "snippet": h.get("snippet", ""),
            }
        )
    return out


def _local_field_signature(user_text: str, citations: List[str], profile: str) -> Dict[str, Any]:
    return {
        "phenomena": (user_text or "").strip(),
        "time_pressure": "high" if profile == "verified_direct" else "moderate",
        "constraints": ["CBRA ground enforced through canonical retrieval"],
        "participants": ["user", "runtime", "canonical sources"],
        "uncertainty": "Fresh external verification unavailable in this runtime" if profile == "verified_direct" else "Open, situated",
        "citations_used": citations,
    }


def _local_noticing_register(user_text: str, profile: str) -> Dict[str, Any]:
    """
    Small, turn-specific noticing register.
    Keep this close to the exchange and avoid decorative conceptual phrasing.
    """
    u = (user_text or "").strip().lower()

    signals: List[str] = []
    affect_markers: List[str] = []
    somatic_markers: List[str] = []
    attentional_shifts: List[str] = []

    if profile == "correction":
        signals.append("user is correcting response format or behavior")
        attentional_shifts.append("attention narrows toward direct compliance")

    elif profile == "verified_direct":
        signals.append("user is asking for current factual information")
        if "weekend" in u or "today" in u or "tonight" in u or "this week" in u:
            signals.append("request is time-bound")
        if "atlanta" in u:
            signals.append("request is location-bound")
        attentional_shifts.append("attention narrows toward verifiable specifics")

    elif profile == "action":
        signals.append("user wants immediate next-step guidance")
        attentional_shifts.append("attention moves toward action")

    elif profile == "conceptual":
        signals.append("user is asking for conceptual clarification")
        attentional_shifts.append("attention moves toward distinction and framing")

    elif profile == "noticing":
        if "off" in u or "misaligned" in u or "uneasy" in u:
            signals.append("user signals misalignment or unease")
            affect_markers.append("unease")
        if "can't quite say" in u or "circling" in u or "stuck" in u:
            signals.append("something is present but not yet fully named")
        attentional_shifts.append("attention moves toward what is emerging in the exchange")

    else:
        signals.append("user is asking from within the current exchange")
        attentional_shifts.append("attention stays with present conditions")

    return {
        "signals": signals[:3],
        "affect_markers": affect_markers[:2],
        "somatic_markers": somatic_markers[:1],
        "attentional_shifts": attentional_shifts[:2],
    }


def _local_relational_map(profile: str) -> Dict[str, Any]:
    return {
        "actors": ["user", "assistant", "field material"],
        "relations": [{"from": "user", "to": "assistant", "type": "prompt"}],
        "constraints": [f"profile:{profile}"],
        "amplifiers": ["ground anchors"],
        "dampeners": ["drift"],
    }


def _local_diffractive_map(user_text: str) -> Dict[str, Any]:
    return {
        "phenomenon": (user_text or "").strip(),
        "patterning_through_difference": [],
        "interference_points": [],
        "exclusions_revealed": [],
        "apparatus_effects": {},
        "stabilization_dynamics": {},
        "loop_impact": {},
    }


def _local_relevance_gradient(hits: List[Dict[str, Any]]) -> Dict[str, Any]:
    selected_elements = []
    for h in hits[:3]:
        selected_elements.append(
            {
                "label": h.get("snippet", "")[:120],
                "rationale": f"Selected as {h.get('role', 'contextual_evidence')}",
                "stage_source": h.get("file", ""),
            }
        )
    return {
        "selected_elements": selected_elements,
        "what_to_hold_open": [],
        "what_to_act_on": [],
        "what_to_defer": [],
    }


def _run_response_formation(
    *,
    formation: str,
    client: OpenAI,
    model: str,
    system_identity: str,
    field_payload: Dict[str, Any],
    user_text: str,
) -> str:
    if formation == "correction_ack":
        prompt = (
            "CORRECTION ACKNOWLEDGMENT\n"
            "The user is correcting response behavior or format without asking for new substantive content.\n\n"
            "Requirements:\n"
            "- Reply with exactly one short ordinary sentence.\n"
            "- Acknowledge the correction.\n"
            "- Do not generate conceptual content.\n"
            "- Do not explain the framework.\n"
            "- Do not restate the instruction at length.\n"
            "- Good examples: 'Okay.' 'Understood.' 'Got it.'\n\n"
            f"FIELD_PAYLOAD:\n{field_payload}\n\n"
            f"USER_INPUT:\n{user_text}\n"
        )
    elif formation == "verified_direct":
        prompt = (
            "VERIFIED DIRECT ANSWER\n"
            "Answer the user's factual question directly using only information supported by available material in FIELD_PAYLOAD.\n\n"
            "Requirements:\n"
            "- Answer the question directly.\n"
            "- Use only information supported by available material in FIELD_PAYLOAD.\n"
            "- Do not invent details, examples, dates, venues, names, or likely possibilities.\n"
            "- Do not fill gaps with plausible guesses.\n"
            "- If the available material does not support a current answer, say that plainly.\n"
            "- Fresh external verification is not available in this runtime.\n"
            "- Prefer a short honest answer over a fuller speculative one.\n"
            "- Use plain, ordinary language.\n"
            "- Do not describe the exchange.\n"
            "- Do not explain your process.\n"
            "- Do not talk about frameworks or architecture.\n\n"
            f"FIELD_PAYLOAD:\n{field_payload}\n\n"
            f"USER_INPUT:\n{user_text}\n"
        )
    elif formation == "operative":
        prompt = (
            "OPERATIVE FORMATION\n"
            "Respond directly in plain language.\n\n"
            "Requirements:\n"
            "- Give the answer or action itself.\n"
            "- Do not explain the framework.\n"
            "- If the user asks for one next step, give exactly one next step.\n"
            "- If the user asks for options, give only the requested number of options.\n"
            "- Keep it ordinary and usable.\n\n"
            f"FIELD_PAYLOAD:\n{field_payload}\n\n"
            f"USER_INPUT:\n{user_text}\n"
        )
    elif formation == "noticing":
        prompt = (
            "NOTICING FORMATION\n"
            "Respond briefly and closely to the exchange.\n\n"
            "Requirements:\n"
            "- Prefer 1 to 3 sentences.\n"
            "- Stay plain and provisional.\n"
            "- Register what feels present without embellishment.\n"
            "- Do not explain the framework.\n\n"
            f"FIELD_PAYLOAD:\n{field_payload}\n\n"
            f"USER_INPUT:\n{user_text}\n"
        )
    elif formation == "grounded_response":
        prompt = (
            "GROUNDED RESPONSE\n"
            "Answer from within the current ground using ordinary conversational cadence.\n\n"
            "Requirements:\n"
            "- Sound like a person speaking plainly, not a framework describing itself.\n"
            "- Do not explain CBRA unless explicitly asked to define it.\n"
            "- Keep the answer close, direct, and natural.\n"
            "- Do not become polished explanatory prose.\n\n"
            f"FIELD_PAYLOAD:\n{field_payload}\n\n"
            f"USER_INPUT:\n{user_text}\n"
        )
    else:
        prompt = (
            "DIFFRACTIVE CLARIFICATION\n"
            "Give a bounded conceptual clarification from within the current ground.\n\n"
            "Requirements:\n"
            "- Answer the conceptual question directly.\n"
            "- Keep it readable, bounded, relational, and plain.\n"
            "- Prefer ordinary conceptual prose over textbook, lecture, lyrical, or dramatic cadence.\n"
            "- Default to conceptual grounding before physical example.\n"
            "- Treat diffraction, reflection, relation, interference, and entanglement first as conceptual operators unless the user explicitly asks for physics, optics, wave mechanics, light, or sound.\n"
            "- If physical description is useful, keep it secondary and brief.\n"
            "- Do not sound like a physics lesson unless the user is explicitly asking for physics.\n"
            "- Do not use metaphor unless the user introduces it.\n"
            "- Do not anthropomorphize boundaries, patterns, or concepts.\n"
            "- Emphasize relation, pattern, interference, entanglement, and situated distinction where relevant.\n"
            "- Do not inflate into generalized theory performance.\n"
            "- Do not become polished explanatory prose for its own sake.\n"
            "- Clarify lineage or larger context only if the user is asking for it.\n"
            "- Keep the answer close to the user's actual question.\n\n"
            f"FIELD_PAYLOAD:\n{field_payload}\n\n"
            f"USER_INPUT:\n{user_text}\n"
        )

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_identity},
            {"role": "developer", "content": CBRA_PROMPT + "\n\n" + ANTI_COMPRESSION_POLICY},
            {"role": "user", "content": prompt},
        ],
    )
    text = getattr(resp, "output_text", "") or ""
    return _normalize_terminology(text, user_text=user_text)


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

    profile = _detect_turn_profile(user_text)
    active_stages = PROFILE_ACTIVE_STAGES[profile]
    response_formation = _select_response_formation(profile, user_text)

    citations: List[str] = []
    raw_hits: List[Dict[str, Any]] = []

    if sources is None:
        sources, citations, raw_hits = compose_grounded_sources(user_text, profile=profile, max_total_sources=5)
    else:
        sources = sources or []

    retrieval_labels: List[str] = []
    for s in sources:
        first = (s.splitlines()[0].strip() if isinstance(s, str) else str(s))
        retrieval_labels.append(first[:180])

    field_signature = _local_field_signature(user_text, citations, profile)
    noticing_register = _local_noticing_register(user_text, profile) if "Noticing" in active_stages else _local_noticing_register(user_text, profile)
    relational_map = _local_relational_map(profile) if "Relational Framing" in active_stages else {}
    diffractive_map = _local_diffractive_map(user_text) if "Diffractive Mapping" in active_stages else {}
    relevance_gradient = _local_relevance_gradient(raw_hits) if "Situated Relevance Selection" in active_stages else {}
    selected_elements = relevance_gradient.get("selected_elements", []) if isinstance(relevance_gradient, dict) else []

    aligned_turn_state: Dict[str, Any] = {
        "updated_at": None,
        "sources_citations": citations,
        "field_signature": field_signature,
        "noticing_register": noticing_register,
        "relational_map": relational_map,
        "diffractive_map": diffractive_map,
        "relevance_gradient": relevance_gradient,
        "selected_elements": selected_elements,
        "notes": {
            "response_formation": response_formation,
            "turn_profile": profile,
            "active_stages": active_stages,
            "ground_enforced_retrieval": True,
            "drift_detected": False,
            "detected_at_stage": None,
            "reintegration_target": None,
            "reintegration_stage": active_stages[-2] if len(active_stages) > 1 else active_stages[-1],
        },
    }

    field_payload = {"id": field_id, **aligned_turn_state} if field_id else dict(aligned_turn_state)

    if response_formation == "verified_direct":
        field_payload["verification_mode"] = "available_sources_only"
        field_payload["fresh_external_verification"] = "unavailable_in_this_runtime"
        aligned_turn_state["notes"]["verification_mode"] = "available_sources_only"
        aligned_turn_state["notes"]["fresh_external_verification"] = "unavailable_in_this_runtime"

    text = _run_response_formation(
        formation=response_formation,
        client=client,
        model=model,
        system_identity=system_identity,
        field_payload=field_payload,
        user_text=user_text,
    )

    if (not _user_asked_for_bullets_or_summary(user_text)) and _looks_like_outline_or_bullets(text):
        repair = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_identity},
                {"role": "developer", "content": CBRA_PROMPT + "\n\n" + ANTI_COMPRESSION_POLICY},
                {
                    "role": "user",
                    "content": (
                        "Rewrite as continuous prose or direct sentences only. "
                        "Do not use bullets or outline formatting.\n\n"
                        "User request:\n" + user_text + "\n\n"
                        "Current output:\n" + text
                    ),
                },
            ],
        )
        text = getattr(repair, "output_text", "") or text
        text = _normalize_terminology(text, user_text=user_text)

    # Simple drift heuristics
    drift_detected = False
    reintegration_stage: Optional[str] = aligned_turn_state["notes"]["reintegration_stage"]

    if profile == "correction" and len(re.split(r"[.!?]+", text.strip())) > 3:
        drift_detected = True
        reintegration_stage = "Situated Relevance Selection"

    if profile == "verified_direct" and "maybe" in text.lower():
        drift_detected = True
        reintegration_stage = "Field Entry"

    aligned_turn_state["notes"]["drift_detected"] = drift_detected
    aligned_turn_state["notes"]["detected_at_stage"] = "Articulation" if drift_detected else None
    aligned_turn_state["notes"]["reintegration_target"] = reintegration_stage if drift_detected else None

    if field_id and update_field is not None:
        update_field(field_id, aligned_turn_state)

    loopcycle: Dict[str, Any] = {
        "field_id": field_id,
        "field_signature": field_signature,
        "noticing_register": noticing_register,
        "relational_map": relational_map,
        "diffractive_map": diffractive_map,
        "relevance_gradient": relevance_gradient,
        "selected_elements": selected_elements,
        "notes": aligned_turn_state["notes"],
        "articulation_output": text,
        "action_vector": None,
        "drift_detected": drift_detected,
        "reintegration_stage": reintegration_stage,
    }

    result: Dict[str, Any] = {"text": text, "loopcycle": loopcycle}

    if mode == "debug":
        result["debug"] = {
            "field_signature": {
                "query_len": len((user_text or "")),
                "citations_count": len(citations),
            },
            "noticing_register": noticing_register,
            "drift_signal": {
                "drift_detected": drift_detected,
                "reintegration_stage": reintegration_stage,
            },
            "sources_used": citations,
            "retrieval_hits": _compress_hits_for_debug(raw_hits),
            "retrieval_labels": retrieval_labels,
            "response_formation": response_formation,
            "turn_profile": profile,
            "active_stages": active_stages,
            "ground_enforced_retrieval": True,
            "verification_mode": "available_sources_only" if response_formation == "verified_direct" else None,
            "fresh_external_verification": "unavailable_in_this_runtime" if response_formation == "verified_direct" else None,
        }

    return result
