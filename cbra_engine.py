# cbra_engine.py
from __future__ import annotations

import os
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI

from cbra.corpus import load_manifest

load_dotenv()

# --- Paths ---
CORPUS_DIR = Path(__file__).parent / "corpus"

# --- CBRA Kernel (developer prompt) ---
# Current behavior:
# - Uses env var CBRA_KERNEL_TEXT if present, otherwise uses fallback text below.
# Commit 7 will lock this to corpus/CBRA_Kernel_v10_2.md.
CBRA_PROMPT = os.getenv("CBRA_KERNEL_TEXT", "").strip() or """
PASTE YOUR CBRA v10.2 KERNEL HERE
""".strip()

# --- Model ---
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")


def _require_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return api_key


def _tokenize(text: str) -> List[str]:
    """
    Lowercases, unicode-normalizes, and returns alphanumeric tokens.
    """
    s = unicodedata.normalize("NFKC", text or "")
    s = s.replace("–", "-").replace("—", "-").replace("−", "-")
    s = s.lower()

    import re
    return re.findall(r"[a-z0-9]+", s)


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
        "between",
        "stage",
    ]
    return any(t in q for t in triggers)


def _placement_rule_text() -> str:
    return (
        "\n\nPLACEMENT RULE (CBRA_Loops_Core grounding):\n"
        "When asked where something sits in the CBRA loop, use the exact canonical stage titles from CBRA_Loops_Core.md.\n"
        "Allowed stage titles only:\n"
        "- Field Entry\n"
        "- Noticing\n"
        "- Relational Framing\n"
        "- Diffractive Mapping\n"
        "- Situated Relevance Selection\n"
        "- Articulation\n"
        "- Action Orientation\n"
        "Placement format: between <Stage A> and <Stage B>.\n"
    )


def _output_rule_text() -> str:
    return (
        "\n\nOUTPUT RULE:\n"
        "Return only the user-facing text. Exclude debug objects, labels, or JSON.\n"
    )


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

    # Canonical gating: only active files from corpus/CBRA_Corpus_Index.md
    try:
        active_files = load_manifest(CORPUS_DIR)
    except Exception:
        # If manifest fails, return empty rather than silently globbing.
        return [], [], []

    paths = [CORPUS_DIR / fn for fn in active_files if (CORPUS_DIR / fn).exists()]
    if not paths:
        return [], [], []

    hits: List[Dict[str, Any]] = []

    # Mild boost for placement questions (helps surface loop core / stage language if active)
    boost = 1.25 if placement_q else 1.0

    for md_path in paths:
        try:
            lines = md_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines, start=1):
            l_tokens = _tokenize(line)
            if not l_tokens:
                continue

            score = 0
            for t in terms:
                if t in l_tokens:
                    score += 1

            if score <= 0:
                continue

            score_f = float(score) * boost
            snippet = line.strip()
            if len(snippet) > 140:
                snippet = snippet[:140]

            hits.append(
                {
                    "file": md_path.name,
                    "line": i,
                    "score": score_f,
                    "snippet": snippet,
                    "text": line.strip(),
                }
            )

    hits.sort(key=lambda h: h["score"], reverse=True)
    top = hits[: max(0, int(k))]

    sources = [h["text"] for h in top]
    citations = [f"[{h['file']} L{h['line']}+]" for h in top]

    return sources, citations, top


def _compress_hits_for_debug(hits: List[Dict[str, Any]], limit: int = 8) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for h in hits[:limit]:
        out.append(
            {
                "file": h.get("file", ""),
                "line": h.get("line", 0),
                "score": h.get("score", 0.0),
                "snippet": h.get("snippet", ""),
            }
        )
    return out


def _local_field_signature(user_text: str, citations: List[str]) -> Dict[str, Any]:
    return {
        "query_len": len(user_text or ""),
        "citations_count": len(citations),
    }


def _local_noticing_register(user_text: str) -> List[str]:
    # Placeholder; expand later into actual noticing heuristics.
    return ["conceptual_operator_work"]


def _local_drift_signal(user_text: str) -> List[str]:
    # Placeholder; expand later into drift heuristics.
    return []


def run_cbra(
    user_text: str,
    mode: Literal["production", "debug"] = "production",
    *,
    sources: Optional[List[str]] = None,
    system_identity: str = "CBRA Writing Support (local prototype).",
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Core CBRA execution call.
    - production: returns only user-facing text
    - debug: returns user-facing text + local debug object (no model-produced debug)
    """
    if not user_text or not user_text.strip():
        raise ValueError("user_text is empty")

    _require_api_key()
    client = OpenAI()
    model = model or DEFAULT_MODEL

    placement_q = _needs_loop_placement_rule(user_text)

    # --- Retrieval ---
    citations: List[str] = []
    raw_hits: List[Dict[str, Any]] = []

    if sources is None:
        k_retrieval = 12 if placement_q else 6
        sources, citations, raw_hits = retrieve_sources(
            user_text,
            k=k_retrieval,
            placement_q=placement_q,
        )
    else:
        sources = sources or []
        citations = []
        raw_hits = []

    # Human-readable labels for debug only
    retrieval_labels: List[str] = []
    for s in sources:
        first = (s.splitlines()[0].strip() if isinstance(s, str) else str(s))
        retrieval_labels.append(first[:180])

    # --- Field material block (fed into model) ---
    sources_block = ""
    if sources:
        joined = "\n\n---\n\n".join(sources)
        sources_block = f"\n\nSOURCES (field material):\n{joined}\n"

    placement_rule = _placement_rule_text() if placement_q else ""
    output_rule = _output_rule_text() if mode == "debug" else ""

    # --- Call model ---
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_identity},
            {"role": "developer", "content": CBRA_PROMPT},
            {
                "role": "user",
                "content": f"{user_text}{sources_block}{placement_rule}{output_rule}",
            },
        ],
    )

    text = getattr(resp, "output_text", "") or ""
    result: Dict[str, Any] = {"text": text}

    if mode == "debug":
        result["debug"] = {
            "field_signature": _local_field_signature(user_text, citations),
            "noticing_register": _local_noticing_register(user_text),
            "drift_signal": _local_drift_signal(user_text),
            "sources_used": citations,
            "retrieval_hits": _compress_hits_for_debug(raw_hits),
            "retrieval_labels": retrieval_labels,
        }

    return result
