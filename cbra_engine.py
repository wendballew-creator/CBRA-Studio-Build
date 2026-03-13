# cbra_engine.py
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import json
from datetime import datetime

from cbra.store import get_field, update_field, create_field

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ------------------------------
# Configuration
# ------------------------------

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
CORPUS_DIR = Path(__file__).parent / "corpus"

# If you set CBRA_KERNEL_TEXT in .env it will be used.
# Otherwise we fall back to loading kernel from corpus/CBRA_Kernel_v10_2.md if present.
ENV_KERNEL = (os.getenv("CBRA_KERNEL_TEXT", "") or "").strip()
KERNEL_FALLBACK_PATH = CORPUS_DIR / "CBRA_Kernel_v10_2.md"


def _load_kernel_text() -> str:
    if ENV_KERNEL:
        return ENV_KERNEL
    if KERNEL_FALLBACK_PATH.exists():
        return KERNEL_FALLBACK_PATH.read_text(encoding="utf-8", errors="replace").strip()
    # Last resort placeholder so the system still runs
    return "CBRA kernel not found. (Set CBRA_KERNEL_TEXT or add corpus/CBRA_Kernel_v10_2.md)"


CBRA_PROMPT = _load_kernel_text()


def _require_api_key() -> str:
    api_key = (os.getenv("OPENAI_API_KEY", "") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return api_key


# ------------------------------
# Retrieval (simple local lexical)
# ------------------------------

def _tokenize(text: str) -> List[str]:
    s = unicodedata.normalize("NFKC", text or "")
    s = s.replace("–", "-").replace("—", "-").replace("−", "-")
    s = s.lower()
    return re.findall(r"[a-z0-9]+", s)


def retrieve_sources(
    query: str,
    k: int = 6,
    *,
    placement_q: bool = False,
) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
    """
    Returns:
      sources:   list[str] chunks to pass into the model as field material
      citations: list[str] stable refs like "[CBRA_Glossary_v3.md L607+]"
      hits:      list[dict] raw hit objects for debug (file/line/score/snippet/text)
    """
    query = (query or "").strip()
    if not query:
        return [], [], []

    if not CORPUS_DIR.exists():
        return [], [], []

    terms = _tokenize(query)
    if not terms:
        return [], [], []

    EXCLUDE = {"CBRA_Corpus_Index.md"}
    BOOST_FILES = {
        "CBRA_Loops_Core.md": 2.5 if placement_q else 1.2,
        "Drift_Constraints.md": 2.0 if "drift" in query.lower() else 1.1,
        "CBRA_Kernel_v10_2.md": 1.2,
        "CBRA_Glossary_v3.md": 1.3,
    }

    hits: List[Dict[str, Any]] = []

    for md_path in CORPUS_DIR.glob("*.md"):
        if md_path.name in EXCLUDE:
            continue

        try:
            lines = md_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue

        boost = float(BOOST_FILES.get(md_path.name, 1.0))

        for i, line in enumerate(lines, start=1):
            ltoks = _tokenize(line)
            if not ltoks:
                continue

            score = 0
            for t in terms:
                if t in ltoks:
                    score += 1

            if score <= 0:
                continue

            score = float(score) * boost

            snippet = line.strip()
            if len(snippet) > 160:
                snippet = snippet[:160]

            hits.append(
                {
                    "file": md_path.name,
                    "line": i,
                    "score": score,
                    "snippet": snippet,
                    "text": line.strip(),
                }
            )

    hits.sort(key=lambda h: h["score"], reverse=True)
    top = hits[: max(0, int(k))]

    sources = [h["text"] for h in top]
    citations = [f"[{h['file']} L{h['line']}+]" for h in top]

    return sources, citations, hits


def _compress_hits_for_debug(hits: List[Dict[str, Any]], limit: int = 8) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for h in hits[:limit]:
        out.append(
            {
                "file": h.get("file", ""),
                "line": h.get("line", 0),
                "score": h.get("score", 0),
                "snippet": h.get("snippet", ""),
            }
        )
    return out


# ------------------------------
# Rules / Helpers
# ------------------------------

def _needs_loop_placement_rule(user_text: str) -> bool:
    q = (user_text or "").lower()
    triggers = [
        "where does",
        "where it sits",
        "where it belongs",
        "placement",
        "in the loop",
        "cbra loop",
        "what phase",
        "between stages",
        "give placement",
    ]
    return any(t in q for t in triggers)


def _placement_rule_text() -> str:
    return (
        "\n\nPLACEMENT RULE (CBRA_Loops_Core grounding):\n"
        "When asked where something sits in the CBRA loop, you MUST use the exact canonical stage titles from CBRA_Loops_Core.md.\n"
        "Allowed stage titles are ONLY:\n"
        "- Field Entry\n"
        "- Noticing\n"
        "- Relational Framing\n"
        "- Diffractive Mapping\n"
        "- Situated Relevance Selection\n"
        "- Articulation\n"
        "- Action Orientation\n"
        "Give placement as: 'between <Stage A> and <Stage B>'.\n"
        "Do not paraphrase stage names. Do not invent stage names.\n"
        "If uncertain, choose the closest adjacent stages and keep the answer short.\n"
    )


def _output_rule_text() -> str:
    return (
        "\n\nOUTPUT RULE:\n"
        "Return only the user-facing text. Do not include JSON, debug objects, labels, citations, or analysis.\n"
    )


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


def _normalize_terminology(text: str, user_text: str = "") -> str:
    """
    Silent terminology guard:
    - avoids treating interaction/intra-action as interchangeable
    - uses intra-action when ontology markers are present
    - keeps interaction for UI/software contexts
    """
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
    # Defensive: import in-function so it can never be missing.
    import re as _re

    if not s:
        return False
    s2 = s.strip()
    if "\n- " in s2 or "\n* " in s2:
        return True
    if _re.search(r"(?m)^\s*\d+\.\s+", s2):
        return True
    if _re.search(r"(?m)^\s*(outline|summary|key points|bullets)\b", s2.lower()):
        return True
    return False


def _user_asked_for_bullets_or_summary(u: str) -> bool:
    u = (u or "").lower()
    return any(k in u for k in ["summarize", "summary", "bullet", "bullets", "outline", "key points", "tl;dr", "tldr"])


# ------------------------------
# Local loop record stubs (you can deepen later)
# ------------------------------

def _local_field_signature(user_text: str, citations: List[str]) -> Dict[str, Any]:
    return {"query_len": len((user_text or "")), "citations_count": len(citations or [])}


def _local_noticing_register(user_text: str) -> List[str]:
    return ["conceptual_operator_work"]


def _local_drift_signal(user_text: str) -> List[str]:
    q = (user_text or "").lower()
    # Minimal, conservative: only flags when user is explicitly asking about drift
    return ["drift_query"] if "drift" in q else []


# ------------------------------
# Engine entrypoint
# ------------------------------

def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _safe_json_loads(s: str) -> Dict[str, Any]:
    if not s:
        return {}
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    try:
        return json.loads(s)
    except Exception:
        pass
    m = re.search(r"\{.*\}", s, flags=re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}


def _run_json_stage(
    *,
    client: OpenAI,
    model: str,
    system_identity: str,
    stage_name: str,
    instructions: str,
    user_text: str,
    sources_block: str,
    field_id: str,
) -> Dict[str, Any]:
    prompt = (
        f"INTERNAL CBRA STAGE: {stage_name}\n"
        f"FIELD_ID: {field_id}\n\n"
        f"{instructions}\n\n"
        "Return ONLY valid JSON. No markdown. No prose.\n\n"
        f"USER_INPUT:\n{user_text}\n"
        f"{sources_block}"
    )

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_identity},
            {"role": "developer", "content": CBRA_PROMPT + "\n\n" + ANTI_COMPRESSION_POLICY},
            {"role": "user", "content": prompt},
        ],
    )
    raw = getattr(resp, "output_text", "") or ""
    return _safe_json_loads(raw)

def _select_response_formation(user_text: str, aligned_turn_state: Dict[str, Any]) -> str:
    """
    Selects which response formation the turn is calling for.

    Returns one of:
    - operative
    - noticing
    - diffractive
    """
    u = (user_text or "").strip().lower()

    # Direct user correction can immediately reshape formation
    correction_markers = [
        "plain language",
        "say it plainly",
        "ordinary sentence",
        "ordinary language",
        "everyday language",
        "no theory words",
        "no theory word",
        "one sentence",
        "one direct sentence",
        "one short sentence",
        "one short ordinary sentence",
        "one concrete next step",
        "give me one concrete next step",
        "stop explaining",
        "answer briefly",
        "just answer",
        "direct answer",
        "give me a list",
        "give me options",
        "tips",
        "suggest",
        "recommend",
        "what should i do",
        "next step",
    ]
    if any(m in u for m in correction_markers):
        return "operative"

    # Explicit conceptual working / requested diffraction
    diffractive_markers = [
        "provide a diffraction",
        "give me a diffraction",
        "diffract",
        "clarify the difference",
        "what changes under cbra",
        "explain this operator",
        "architecture explanation",
        "ontological distinction",
        "why does this fail",
        "explain why",
        "explain the difference",
        "don't explain cbra",
        "dont explain cbra",
        "answer from it",
        "without citing the framework",
        "without citing the framework behind it",
        "don't explain the framework",
        "dont explain the framework",
        "say that again without citing",
        "say it without citing",
        "what does cbra mean by",
        "how does cbra use",
        "within cbra",
        "in cbra",
        "cbra's use of",
        "cbra use of",
        "how is this used in cbra",
        "how does this function in cbra",
        "what is this operator in cbra",
    ]
    if any(m in u for m in diffractive_markers):
        return "diffractive"

    # Natural practical support
    operative_markers = [
        "what should i do",
        "what do i do",
        "help me choose",
        "list",
        "options",
        "recommend",
        "suggest",
        "tips",
        "next step",
        "steps",
        "restaurants",
        "where should i go",
        "give me",
        "plain answer",
        "concise",
        "short answer",
    ]
    if any(m in u for m in operative_markers):
        return "operative"

    # Unfinishedness / subtle signal / staying with what is forming
    noticing_markers = [
        "i can't quite say it",
        "i cant quite say it",
        "something feels off",
        "unfinished",
        "stay with",
        "what is happening here",
        "what's happening here",
        "what is forming",
        "circling around an idea",
        "not fully articulated",
        "something is forming",
        "remain with",
    ]
    if any(m in u for m in noticing_markers):
        return "noticing"

    # Default:
    # practical questions should tend toward movement;
    # otherwise stay close to noticing rather than defaulting to explanation.
    if "?" in u:
        return "operative"
    return "noticing"

def _select_conceptual_mode(user_text: str) -> str:
    """
    Select conceptual clarification stance for diffractive responses.

    Returns one of:
    - grounded_response
    - framework_internal_clarification
    - lineage_context_clarification
    """
    u = (user_text or "").strip().lower()

    grounded_markers = [
        "don't explain cbra",
        "dont explain cbra",
        "answer from it",
        "without citing the framework",
        "without citing the framework behind it",
        "don't explain the framework",
        "dont explain the framework",
        "say that again without citing",
        "say it without citing",
    ]
    if any(m in u for m in grounded_markers):
        return "grounded_response"

    framework_internal_markers = [
        "what does cbra mean by",
        "how does cbra use",
        "within cbra",
        "in cbra",
        "cbra's use of",
        "cbra use of",
        "how is this used in cbra",
        "how does this function in cbra",
        "what is this operator in cbra",
        "action orientation",
        "noticing register",
        "relational framing",
        "situated relevance selection",
        "action vector",
        "field entry",
        "loop reintegration",
        "drift constraints",
        "generative stabilization",
    ]
    if any(m in u for m in framework_internal_markers):
        return "framework_internal_clarification"

    lineage_context_markers = [
        "diffraction",
        "reflection",
        "barad",
        "posthumanism",
        "agential realism",
        "agential cut",
        "intra-action",
        "entanglement",
        "material-discursive",
        "performativity",
        "lineage",
        "context",
        "broader context",
        "larger context",
    ]
    if any(m in u for m in lineage_context_markers):
        return "lineage_context_clarification"

    return "framework_internal_clarification"

def _run_response_formation(
    *,
    formation: str,
    client: OpenAI,
    model: str,
    system_identity: str,
    field_payload: Dict[str, Any],
    user_text: str,
    conceptual_mode: Optional[str] = None,
) -> str:
    """
    Forms user-facing response from the aligned turn-state.
    """
    if formation == "operative":
        prompt = (
            "OPERATIVE FORMATION\n"
            "Form a response that supports movement from within FIELD_PAYLOAD.\n\n"
            "Requirements:\n"
            "- Respond directly to the user's ask.\n"
            "- Plain language is valid.\n"
            "- Lists, steps, options, and direct answers are valid stabilizations.\n"
            "- Give the action itself, not discourse about choosing, identifying, articulating, noticing, mapping, or surfacing the action.\n"
            "- Do not tell the user to identify the next step. Give the next step.\n"
            "- If the user asks for one concrete next step, output exactly one concrete imperative sentence.\n"
            "- If the user asks for options or a list, provide them directly.\n"
            "- Use specific, ordinary wording.\n"
            "- Do not explain the architecture.\n"
            "- Do not substitute discourse about action for action.\n\n"
            f"FIELD_PAYLOAD:\n{json.dumps(field_payload, indent=2)}\n\n"
            f"USER_INPUT:\n{user_text}\n"
        )
    elif formation == "noticing":
        prompt = (
            "NOTICING FORMATION\n"
            "Form a short response that registers what is happening in this exchange from within FIELD_PAYLOAD.\n\n"
            "Requirements:\n"
            "- Stay close to this exchange.\n"
            "- Register tensions, pressures, signals, or unfinishedness.\n"
            "- Keep the response specific, plain, and provisional.\n"
            "- Prefer 1 to 3 sentences.\n"
            "- Use ordinary language.\n"
            "- Do not use metaphor unless the user already has.\n"
            "- Do not embellish.\n"
            "- Do not generalize into portable academic discourse.\n"
            "- Do not explain the architecture.\n"
            "- Do not interpret beyond what is present in the exchange.\n\n"
            f"FIELD_PAYLOAD:\n{json.dumps(field_payload, indent=2)}\n\n"
            f"USER_INPUT:\n{user_text}\n"
        )
    else:
        conceptual_mode = conceptual_mode or "framework_internal_clarification"

        if conceptual_mode == "grounded_response":
            prompt = (
                "GROUNDED RESPONSE\n"
                "Answer from the aligned turn-state without turning CBRA, the framework, the sources, or the architecture into the object of explanation.\n\n"
                "Requirements:\n"
                "- Answer directly.\n"
                "- Do not mention CBRA, framework, sources, field material, or architecture.\n"
                "- Do not describe the user's instruction.\n"
                "- Do not comment on the exchange.\n"
                "- Do not explain what you are doing.\n"
                "- Output only the revised answer.\n\n"
                f"FIELD_PAYLOAD:\n{json.dumps(field_payload, indent=2)}\n\n"
                f"USER_INPUT:\n{user_text}\n"
            )

        elif conceptual_mode == "lineage_context_clarification":
            prompt = (
                "LINEAGE / CONTEXT CLARIFICATION\n"
                "Clarify the term in its broader lineage or context first, then state how CBRA works within or operationalizes it.\n\n"
                "Requirements:\n"
                "- Begin with the broader lineage, context, or inheritance of the term.\n"
                "- Then state how CBRA uses, works within, or operationalizes that term.\n"
                "- Do not imply that CBRA contains or exhausts the concept.\n"
                "- Do not begin with 'within CBRA' or treat CBRA as the primary container of meaning.\n"
                "- Keep the response bounded and readable.\n"
                "- Answer the explicit conceptual question.\n\n"
                f"FIELD_PAYLOAD:\n{json.dumps(field_payload, indent=2)}\n\n"
                f"USER_INPUT:\n{user_text}\n"
            )

        else:
            prompt = (
                "FRAMEWORK-INTERNAL CLARIFICATION\n"
                "Clarify how the concept functions within CBRA.\n\n"
                "Requirements:\n"
                "- Explain the concept as it functions inside CBRA.\n"
                "- Focus on runtime role, operator function, stage placement, or design use.\n"
                "- Keep the response bounded and readable.\n"
                "- Answer the explicit conceptual question.\n"
                "- Do not drift into broader lineage unless the user asks for it.\n\n"
                f"FIELD_PAYLOAD:\n{json.dumps(field_payload, indent=2)}\n\n"
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
    """
    Core CBRA execution call.
    - production: returns only user-facing text (+ loopcycle record for internal storage)
    - debug: returns user-facing text + local debug object (no model-produced debug)
    """
    if not user_text or not user_text.strip():
        raise ValueError("user_text is empty")

    _require_api_key()
    client = OpenAI()
    model = model or DEFAULT_MODEL

    if thread_id and not field_id:
        f = create_field(thread_id=thread_id)
        field_id = f.id

    if field_id:
        existing = get_field(field_id)
        if existing is None and thread_id:
            f = create_field(thread_id=thread_id)
            field_id = f.id

    placement_q = _needs_loop_placement_rule(user_text)

    # --- Retrieval ---
    citations: List[str] = []
    raw_hits: List[Dict[str, Any]] = []

    if sources is None:
        k_retrieval = 12 if placement_q else 6
        sources, citations, raw_hits = retrieve_sources(user_text, k=k_retrieval, placement_q=placement_q)
    else:
        sources = sources or []

    retrieval_labels: List[str] = []
    for s in sources:
        first = (s.splitlines()[0].strip() if isinstance(s, str) else str(s))
        retrieval_labels.append(first[:180])

    sources_block = ""
    if sources:
        joined = "\n\n---\n\n".join(sources)
        sources_block = f"\n\nSOURCES (field material):\n{joined}\n"

    stage_field_signature = _run_json_stage(
        client=client,
        model=model,
        system_identity=system_identity,
        stage_name="Field Entry",
        instructions=(
            "Produce a FIELD SIGNATURE as JSON with keys: "
            "phenomena, time_pressure, stakes, constraints, participants, uncertainty, citations_used (list)."
        ),
        user_text=user_text,
        sources_block=sources_block,
        field_id=field_id or "NO_FIELD",
    )

    stage_noticing = _run_json_stage(
        client=client,
        model=model,
        system_identity=system_identity,
        stage_name="Noticing Register",
        instructions=(
            "Produce a NOTICING REGISTER as JSON with keys: "
            "signals (list), affect_markers (list), somatic_markers (list), attentional_shifts (list)."
        ),
        user_text=user_text,
        sources_block=sources_block,
        field_id=field_id or "NO_FIELD",
    )

    stage_relational = _run_json_stage(
        client=client,
        model=model,
        system_identity=system_identity,
        stage_name="Relational Framing",
        instructions=(
            "Produce a RELATIONAL MAP as JSON with keys: "
            "actors (list), relations (list of {from,to,type}), constraints (list), amplifiers (list), dampeners (list)."
        ),
        user_text=user_text,
        sources_block=sources_block,
        field_id=field_id or "NO_FIELD",
    )

    stage_diffractive = _run_json_stage(
        client=client,
        model=model,
        system_identity=system_identity,
        stage_name="Diffractive Working",
        instructions=(
            "Produce a DIFFRACTIVE MAP as JSON using CBRA ground. "
            "Work the field through difference, interference, exclusions, and emergent patterning without requiring a contrastive humanism-versus-CBRA frame. "
            "Include keys: "
            "phenomenon, "
            "patterning_through_difference (list of {pattern, why_it_matters, what_it_conditions}), "
            "interference_points (list of {site, tension, effect}), "
            "exclusions_revealed (list of {stabilized_element, exclusion, implication}), "
            "apparatus_effects {discursive, material, institutional}, "
            "stabilization_dynamics {what_is_stabilizing, how_it_is_forming, whether_it_supports_movement}, "
            "loop_impact {activation_shift, drift_risk, reintegration_stage}. "
            "reintegration_stage must be one of: Field Entry, Noticing Register, Relational Framing, Diffractive Mapping, Situated Relevance Selection, Articulation. "
            "Return ONLY JSON."
        ),
        user_text=user_text,
        sources_block=sources_block,
        field_id=field_id or "NO_FIELD",
    )

    stage_relevance = _run_json_stage(
        client=client,
        model=model,
        system_identity=system_identity,
        stage_name="Situated Relevance Selection",
        instructions=(
            "Produce a RELEVANCE GRADIENT as JSON with keys: "
            "selected_elements (list of {label, rationale, stage_source}), "
            "what_to_hold_open (list), what_to_act_on (list), what_to_defer (list)."
        ),
        user_text=user_text,

        sources_block=sources_block,
        field_id=field_id or "NO_FIELD",
    )

    # Derive selected_elements from relevance_gradient.selected_elements (single source of truth)
    selected_elements = []
    if isinstance(stage_relevance, dict):
        se = stage_relevance.get("selected_elements")
        if isinstance(se, list):
            selected_elements = se

    # --- Drift detection (matched to current diffractive schema) ---
    drift_detected = False
    reintegration_stage = None

    if isinstance(stage_diffractive, dict):
        patterning = stage_diffractive.get("patterning_through_difference") or []
        interference = stage_diffractive.get("interference_points") or []
        exclusions = stage_diffractive.get("exclusions_revealed") or []
        stabilization = stage_diffractive.get("stabilization_dynamics") or {}
        loop_impact = stage_diffractive.get("loop_impact") or {}
        drift_risk = (loop_impact.get("drift_risk") or "").lower()

        # Mirror reintegration_stage from loop_impact even when drift_detected is False
        if isinstance(loop_impact, dict):
            reintegration_stage = loop_impact.get("reintegration_stage") or reintegration_stage

        has_patterning = isinstance(patterning, list) and len(patterning) > 0
        has_interference = isinstance(interference, list) and len(interference) > 0
        has_exclusions = isinstance(exclusions, list) and len(exclusions) > 0
        has_stabilization = isinstance(stabilization, dict) and len(stabilization) > 0

        if not (has_patterning and has_interference and has_stabilization):
            drift_detected = True
            reintegration_stage = loop_impact.get("reintegration_stage") or "Noticing Register"

        # Exclusions are useful but not required every turn.
        if "high" in drift_risk:
            drift_detected = True
            reintegration_stage = loop_impact.get("reintegration_stage") or "Diffractive Mapping"

    aligned_turn_state: Dict[str, Any] = {
        "updated_at": _now_iso(),
        "sources_citations": citations,
        "field_signature": stage_field_signature or {},
        "noticing_register": stage_noticing or {},
        "relational_map": stage_relational or {},
        "diffractive_map": stage_diffractive or {},
        "relevance_gradient": stage_relevance or {},
        "selected_elements": selected_elements,
        "notes": {
            "drift_detected": drift_detected,
            "detected_at_stage": "Articulation" if drift_detected else None,
            "reintegration_target": reintegration_stage if drift_detected else None,
            "reintegration_stage": reintegration_stage,
        },
    }

    if field_id:
        update_field(field_id, aligned_turn_state)

    placement_rule = _placement_rule_text() if placement_q else ""
    output_rule = _output_rule_text() if mode == "debug" else ""

    field_payload = {"id": field_id, **aligned_turn_state} if field_id else dict(aligned_turn_state)

    # Response formation selection happens before wording begins.
    response_formation = _select_response_formation(user_text, aligned_turn_state)

    conceptual_mode = None
    if response_formation == "diffractive":
        conceptual_mode = _select_conceptual_mode(user_text)

    text = _run_response_formation(
        formation=response_formation,
        client=client,
        model=model,
        system_identity=system_identity,
        field_payload=field_payload,
        user_text=user_text + ("\n\n" + placement_rule if placement_rule else "") + ("\n\n" + output_rule if output_rule else ""),
        conceptual_mode=conceptual_mode,
    )

    # Persist formation choice in notes for debugging / audit.
    if isinstance(aligned_turn_state.get("notes"), dict):
        aligned_turn_state["notes"]["response_formation"] = response_formation
        if conceptual_mode:
            aligned_turn_state["notes"]["conceptual_mode"] = conceptual_mode

    # --- LoopCycle record (internal storage) ---
    loopcycle: Dict[str, Any] = {
        "field_id": field_id,
        "field_signature": aligned_turn_state.get("field_signature") or {},
        "noticing_register": aligned_turn_state.get("noticing_register") or {},
        "relational_map": aligned_turn_state.get("relational_map") or {},
        "diffractive_map": aligned_turn_state.get("diffractive_map") or {},
        "relevance_gradient": aligned_turn_state.get("relevance_gradient") or {},
        "selected_elements": aligned_turn_state.get("selected_elements") or [],
        "notes": aligned_turn_state.get("notes") or {},
        "articulation_output": text,
        "action_vector": None,
        "drift_detected": drift_detected,
        "reintegration_stage": reintegration_stage,
    }

    result: Dict[str, Any] = {"text": text, "loopcycle": loopcycle}

    if mode == "debug":
        result["debug"] = {
            "field_signature": _local_field_signature(user_text, citations),
            "noticing_register": _local_noticing_register(user_text),
            "drift_signal": {"drift_detected": drift_detected, "reintegration_stage": reintegration_stage},
            "sources_used": citations,
            "retrieval_hits": _compress_hits_for_debug(raw_hits),
            "retrieval_labels": retrieval_labels,
            "response_formation": response_formation,
            "conceptual_mode": conceptual_mode,
        }

    return result
