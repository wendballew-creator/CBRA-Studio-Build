from __future__ import annotations

from typing import Any, Dict, List, Tuple

# Compression limits
MAX_SELECTED_ELEMENTS: int = 8
MAX_LABEL_CHARS: int = 120
MAX_RATIONALE_CHARS: int = 260
MAX_STAGE_SOURCE_CHARS: int = 60


def _truncate(s: str, max_chars: int) -> str:
    s = (s or "").strip()
    if len(s) <= max_chars:
        return s
    return s[:max_chars].rstrip()


def _dedupe_preserve_order(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    De-dupe by stable key. Prefer label.
    """
    seen = set()
    out: List[Dict[str, Any]] = []
    for it in items:
        label = (it.get("label") or "").strip()
        key = label if label else str(it)
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def _normalize_element(x: Any) -> Dict[str, Any]:
    """
    Normalizes an element into the canonical dict form:
      {"label": str, "rationale": str|None, "stage_source": str|None}
    Accepts:
      - dict with keys
      - string
      - any scalar (converted to string)
    """
    if isinstance(x, dict):
        label = _truncate(str(x.get("label") or "").strip(), MAX_LABEL_CHARS)
        rationale = x.get("rationale")
        stage_source = x.get("stage_source")
        rationale_s = _truncate(str(rationale).strip(), MAX_RATIONALE_CHARS) if rationale is not None else None
        stage_s = _truncate(str(stage_source).strip(), MAX_STAGE_SOURCE_CHARS) if stage_source is not None else None
        out: Dict[str, Any] = {"label": label}
        if rationale_s:
            out["rationale"] = rationale_s
        if stage_s:
            out["stage_source"] = stage_s
        return out

    # string/scalar -> label only
    label2 = _truncate(str(x).strip(), MAX_LABEL_CHARS)
    return {"label": label2}


def compress_selected_elements(items: Any) -> List[Dict[str, Any]]:
    """
    Normalize -> drop empties -> dedupe -> cap list length.
    """
    if items is None:
        arr: List[Any] = []
    elif isinstance(items, list):
        arr = items
    else:
        arr = [items]

    normed: List[Dict[str, Any]] = []
    for x in arr:
        el = _normalize_element(x)
        if el.get("label"):
            normed.append(el)

    normed = _dedupe_preserve_order(normed)
    return normed[:MAX_SELECTED_ELEMENTS]


def enforce_fieldartifact_compression(field: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Enforces invariant:
      field["selected_elements"] == field["relevance_gradient"]["selected_elements"]

    Also enforces:
      - list length cap
      - label/rationale truncation
      - normalization/dedup
    Returns:
      (field_mutated, violations)
    """
    violations: List[str] = []

    if not isinstance(field, dict):
        return {"selected_elements": [], "relevance_gradient": {"selected_elements": []}}, ["fieldartifact_not_dict"]

    rg = field.get("relevance_gradient")
    if not isinstance(rg, dict):
        rg = {}
        field["relevance_gradient"] = rg
        violations.append("relevance_gradient_missing_or_not_dict")

    top_raw = field.get("selected_elements")
    nested_raw = rg.get("selected_elements")

    top = compress_selected_elements(top_raw)
    nested = compress_selected_elements(nested_raw)

    if not top and nested:
        top = nested
        violations.append("top_selected_elements_missing_used_nested")
    elif not nested and top:
        nested = top
        violations.append("nested_selected_elements_missing_used_top")

    if top != nested:
        if nested:
            top = nested
            violations.append("selected_elements_mismatch_forced_to_nested")
        else:
            nested = top
            violations.append("selected_elements_mismatch_forced_to_top")

    rg["selected_elements"] = nested
    field["selected_elements"] = top

    return field, violations
