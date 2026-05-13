from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from cbra_runtime.runtime.field_state import FieldState
from cbra_runtime.runtime.history import FieldHistoryEntry
from cbra_runtime.runtime.history_export import export_history_payload


def field_state_to_dict(state: FieldState) -> dict[str, Any]:
    """
    Convert live runtime FieldState into a JSON-safe dictionary for persistence.
    """
    return asdict(state)


def build_snapshot_payload(
    state: FieldState,
    history: list[FieldHistoryEntry],
) -> dict[str, Any]:
    """
    Build a stable snapshot payload containing field state and exported history.
    """
    return {
        "field_state": field_state_to_dict(state),
        "history": export_history_payload(
            history,
            field_id=state.field_id,
            final_timestep=state.timestep,
        ),
    }


def save_snapshot(
    state: FieldState,
    history: list[FieldHistoryEntry],
    path: str | Path,
) -> Path:
    """
    Persist field state and history together as JSON.
    """
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_snapshot_payload(state, history)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def load_snapshot(path: str | Path) -> dict[str, Any]:
    """
    Load a previously saved snapshot payload.
    This returns raw JSON-safe dictionaries and does not reconstruct runtime dataclasses yet.
    """
    in_path = Path(path)
    return json.loads(in_path.read_text(encoding="utf-8"))
