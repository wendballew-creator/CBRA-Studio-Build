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
        stage_name="Diffractive Mapping (Humanism → CBRA ontology)",
        instructions=(
            "Produce a DIFFRACTIVE MAP as JSON using CBRA ontology as the diffractive ground. "
            "Include keys: phenomenon, humanist_configuration {core_assumptions, subject_position, agency_model, knowledge_model, stabilization_mechanisms}, "
            "posthumanist_reading {ontology_shift, agency_reconfiguration, boundary_redefinition, material_discursive_entanglements}, "
            "differences_that_matter (list of {difference, why_it_matters, what_becomes_possible}), "
            "exclusions_revealed (list of {previously_stabilized_element, now_visible_as_exclusion, implication}), "
            "apparatus_effects {discursive, material, institutional}, "
            "loop_impact {activation_shift, drift_risk, reintegration_stage}"
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

    # --- Drift detection (structural, minimal v0) ---
    drift_detected = False
    reintegration_stage = None

    if isinstance(stage_diffractive, dict):
        posthuman = stage_diffractive.get("posthumanist_reading") or {}
        exclusions = stage_diffractive.get("exclusions_revealed") or []
        loop_impact = stage_diffractive.get("loop_impact") or {}
        drift_risk = (loop_impact.get("drift_risk") or "").lower()

        # Mirror reintegration_stage from diffractive loop_impact even when drift_detected is False
        if isinstance(loop_impact, dict):
            reintegration_stage = loop_impact.get("reintegration_stage") or reintegration_stage

        if not posthuman or (isinstance(exclusions, list) and len(exclusions) == 0):
            drift_detected = True
            reintegration_stage = loop_impact.get("reintegration_stage") or "Noticing Register"

        if "high" in drift_risk:
            drift_detected = True
            reintegration_stage = loop_impact.get("reintegration_stage") or "Diffractive Mapping"

    if field_id:
        update_field(
            field_id,
            {
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
                    "reintegration_stage": reintegration_stage,
                },
            },
        )

    persisted_field = get_field(field_id) if field_id else None

    placement_rule = _placement_rule_text() if placement_q else ""
    output_rule = _output_rule_text() if mode == "debug" else ""

    field_payload = persisted_field.model_dump() if persisted_field else {}

    articulation_prompt = (
        "ARTICULATION\n"
        "Generate the user-facing response grounded ONLY in FIELD_PAYLOAD.\n\n"
        "Constraints:\n"
        "- Use ONLY information present in FIELD_PAYLOAD.\n"
        "- Prioritize FIELD_PAYLOAD.selected_elements.\n"
        "- Do not output stage labels.\n"
        "- Do not explain the architecture.\n"
        "- Do not introduce new concepts not present in FIELD_PAYLOAD.\n"
        "- If FIELD_PAYLOAD.notes.drift_detected is true, be concise and orient toward FIELD_PAYLOAD.notes.reintegration_stage.\n\n"
        f"FIELD_PAYLOAD:\n{json.dumps(field_payload, indent=2)}\n\n"
        f"USER_INPUT:\n{user_text}\n\n"
        f"{placement_rule}{output_rule}"
    )

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_identity},
            {"role": "developer", "content": CBRA_PROMPT + "\n\n" + ANTI_COMPRESSION_POLICY},
            {"role": "user", "content": articulation_prompt},
        ],
    )

    text = getattr(resp, "output_text", "") or ""
    text = _normalize_terminology(text, user_text=user_text)

    if (not _user_asked_for_bullets_or_summary(user_text)) and _looks_like_outline_or_bullets(text):
        repair_prompt = (
            "Rewrite as continuous prose paragraphs.\n"
            "Do not summarize. Do not outline. Do not use bullet points.\n"
            "Produce finished prose in full sentences.\n\n"
            "Use ONLY information present in FIELD_PAYLOAD.\n"
            "Do not introduce new concepts.\n"
            f"FIELD_PAYLOAD:\n{json.dumps(field_payload, indent=2)}\n\n"
            f"USER_INPUT:\n{user_text}"
        )

        repair = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_identity},
                {"role": "developer", "content": CBRA_PROMPT + "\n\n" + ANTI_COMPRESSION_POLICY},
                {"role": "user", "content": repair_prompt},
            ],
        )
        text = getattr(repair, "output_text", "") or text
        text = _normalize_terminology(text, user_text=user_text)

    # --- LoopCycle record (internal storage) ---
    loopcycle: Dict[str, Any] = {
        "field_id": field_id,
        "field_signature": stage_field_signature or {},
        "noticing_register": stage_noticing or {},
        "relational_map": stage_relational or {},
        "diffractive_map": stage_diffractive or {},
        "relevance_gradient": stage_relevance or {},
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
            "drift_signal": drift_signal,
            "sources_used": citations,
            "retrieval_hits": _compress_hits_for_debug(raw_hits),
            "retrieval_labels": retrieval_labels,
        }

    return result
